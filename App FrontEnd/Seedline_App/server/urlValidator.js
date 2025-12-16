/**
 * URL Validator Server for Seedline
 * 
 * This Express server provides automated URL validation for user-submitted games.
 * It fetches the provided URL, parses the content for game data, and validates
 * that the submitted information matches what's found on the page.
 * 
 * USAGE:
 *   cd server
 *   npm install
 *   npm start
 * 
 * ENDPOINTS:
 *   POST /api/validate-url   - Validate a game submission URL
 *   POST /api/validate-batch - Batch validate multiple games
 *   GET  /api/health         - Health check
 */

const express = require('express');
const cors = require('cors');
const https = require('https');
const http = require('http');
const { URL } = require('url');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// ============================================================================
// URL FETCHING
// ============================================================================

/**
 * Fetch URL content with timeout and redirect handling
 */
function fetchUrl(urlString, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) {
      reject(new Error('Too many redirects'));
      return;
    }

    try {
      const parsedUrl = new URL(urlString);
      const protocol = parsedUrl.protocol === 'https:' ? https : http;
      
      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method: 'GET',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
        },
        timeout: 15000,
      };

      const req = protocol.request(options, (res) => {
        // Handle redirects
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          let redirectUrl = res.headers.location;
          // Handle relative redirects
          if (!redirectUrl.startsWith('http')) {
            redirectUrl = new URL(redirectUrl, urlString).toString();
          }
          fetchUrl(redirectUrl, maxRedirects - 1).then(resolve).catch(reject);
          return;
        }

        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode}`));
          return;
        }

        let data = '';
        res.setEncoding('utf8');
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(data));
      });

      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });

      req.end();
    } catch (err) {
      reject(err);
    }
  });
}

// ============================================================================
// SCORE EXTRACTION PATTERNS
// ============================================================================

/**
 * Extract scores from various formats
 */
function extractScores(text) {
  const scores = [];
  
  // Pattern 1: "Team1 3 - 1 Team2" or "Team1 3-1 Team2"
  const dashPattern = /(\d{1,2})\s*[-–—]\s*(\d{1,2})/g;
  let match;
  while ((match = dashPattern.exec(text)) !== null) {
    scores.push({
      score1: parseInt(match[1]),
      score2: parseInt(match[2]),
      context: text.substring(Math.max(0, match.index - 100), match.index + match[0].length + 100)
    });
  }
  
  // Pattern 2: "Final: 3-1" or "Final Score: 3 - 1"
  const finalPattern = /final\s*(?:score)?[:\s]+(\d{1,2})\s*[-–—]\s*(\d{1,2})/gi;
  while ((match = finalPattern.exec(text)) !== null) {
    scores.push({
      score1: parseInt(match[1]),
      score2: parseInt(match[2]),
      context: text.substring(Math.max(0, match.index - 50), match.index + match[0].length + 50),
      isFinal: true
    });
  }
  
  // Pattern 3: "(W 3-1)" or "(L 1-3)"
  const resultPattern = /\([WLD]\s*(\d{1,2})\s*[-–—]\s*(\d{1,2})\)/gi;
  while ((match = resultPattern.exec(text)) !== null) {
    scores.push({
      score1: parseInt(match[1]),
      score2: parseInt(match[2]),
      context: text.substring(Math.max(0, match.index - 50), match.index + match[0].length + 50)
    });
  }
  
  return scores;
}

/**
 * Normalize team name for comparison
 */
function normalizeTeamName(name) {
  if (!name) return '';
  return name
    .toLowerCase()
    .replace(/\s*(fc|sc|soccer|club|youth|academy|united|city)\s*/gi, ' ')
    .replace(/\s*(ecnl|ga|girls academy|aspire|rl|regional league)\s*/gi, ' ')
    .replace(/\s*\d{2,4}[gbu]?\s*/gi, ' ')  // Remove age groups like 13G, 2012G
    .replace(/\s*[gbu]\d{2,4}\s*/gi, ' ')   // Remove age groups like G13, G2012
    .replace(/[^\w\s]/g, '')                 // Remove special chars
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Check if two team names are similar enough to match
 */
function teamsMatch(name1, name2, threshold = 0.6) {
  const n1 = normalizeTeamName(name1);
  const n2 = normalizeTeamName(name2);
  
  // Exact match after normalization
  if (n1 === n2) return true;
  
  // One contains the other
  if (n1.includes(n2) || n2.includes(n1)) return true;
  
  // Check word overlap
  const words1 = new Set(n1.split(' ').filter(w => w.length > 2));
  const words2 = new Set(n2.split(' ').filter(w => w.length > 2));
  
  if (words1.size === 0 || words2.size === 0) return false;
  
  let matches = 0;
  for (const word of words1) {
    if (words2.has(word)) matches++;
  }
  
  const similarity = matches / Math.max(words1.size, words2.size);
  return similarity >= threshold;
}

/**
 * Extract dates from text
 */
function extractDates(text) {
  const dates = [];
  
  // Pattern 1: "Sep 6, 2025" or "September 6, 2025"
  const monthPattern = /(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s*(\d{4})/gi;
  let match;
  while ((match = monthPattern.exec(text)) !== null) {
    dates.push({
      text: match[0],
      month: match[1],
      day: parseInt(match[2]),
      year: parseInt(match[3])
    });
  }
  
  // Pattern 2: "2025-09-06" (ISO format)
  const isoPattern = /(\d{4})-(\d{2})-(\d{2})/g;
  while ((match = isoPattern.exec(text)) !== null) {
    dates.push({
      text: match[0],
      year: parseInt(match[1]),
      month: parseInt(match[2]),
      day: parseInt(match[3])
    });
  }
  
  // Pattern 3: "09/06/2025" or "9/6/25"
  const slashPattern = /(\d{1,2})\/(\d{1,2})\/(\d{2,4})/g;
  while ((match = slashPattern.exec(text)) !== null) {
    let year = parseInt(match[3]);
    if (year < 100) year += 2000;
    dates.push({
      text: match[0],
      month: parseInt(match[1]),
      day: parseInt(match[2]),
      year: year
    });
  }
  
  return dates;
}

/**
 * Convert month name to number
 */
function monthToNumber(month) {
  const months = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
  };
  return months[month.toLowerCase()] || 0;
}

/**
 * Check if a date matches the submitted date
 */
function dateMatches(foundDate, submittedDate) {
  // Parse submitted date (expected format: YYYY-MM-DD)
  const parts = submittedDate.split('-');
  if (parts.length !== 3) return false;
  
  const subYear = parseInt(parts[0]);
  const subMonth = parseInt(parts[1]);
  const subDay = parseInt(parts[2]);
  
  // Compare
  let foundMonth = foundDate.month;
  if (typeof foundMonth === 'string') {
    foundMonth = monthToNumber(foundMonth);
  }
  
  return foundDate.year === subYear && 
         foundMonth === subMonth && 
         foundDate.day === subDay;
}

// ============================================================================
// SITE-SPECIFIC PARSERS
// ============================================================================

/**
 * Parse GotSport/TotalGlobalSports pages
 */
function parseGotSport(html, gameData) {
  const result = {
    found: false,
    confidence: 0,
    details: {},
    matches: {
      score: false,
      teams: false,
      date: false
    }
  };
  
  // Strip HTML tags for text analysis
  const text = html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ');
  
  // Check for team names
  const homeTeamNorm = normalizeTeamName(gameData.homeTeam);
  const awayTeamNorm = normalizeTeamName(gameData.awayTeam);
  const textLower = text.toLowerCase();
  
  const homeFound = textLower.includes(homeTeamNorm) || 
                    homeTeamNorm.split(' ').some(w => w.length > 3 && textLower.includes(w));
  const awayFound = textLower.includes(awayTeamNorm) ||
                    awayTeamNorm.split(' ').some(w => w.length > 3 && textLower.includes(w));
  
  result.details.homeTeamFound = homeFound;
  result.details.awayTeamFound = awayFound;
  result.matches.teams = homeFound && awayFound;
  
  // Check for date
  const dates = extractDates(text);
  for (const date of dates) {
    if (dateMatches(date, gameData.date)) {
      result.matches.date = true;
      result.details.dateFound = date.text;
      break;
    }
  }
  
  // Check for score
  const scores = extractScores(text);
  const submittedHome = parseInt(gameData.homeScore);
  const submittedAway = parseInt(gameData.awayScore);
  
  for (const score of scores) {
    // Score could be in either order
    if ((score.score1 === submittedHome && score.score2 === submittedAway) ||
        (score.score1 === submittedAway && score.score2 === submittedHome)) {
      result.matches.score = true;
      result.details.scoreFound = `${score.score1}-${score.score2}`;
      break;
    }
  }
  
  // Calculate confidence
  let confidence = 0;
  if (result.matches.teams) confidence += 40;
  if (result.matches.date) confidence += 30;
  if (result.matches.score) confidence += 30;
  
  // Bonus for having all three
  if (result.matches.teams && result.matches.date && result.matches.score) {
    confidence = 100;
  }
  
  result.confidence = confidence;
  result.found = confidence >= 70;
  
  return result;
}

/**
 * Parse social media posts (Instagram, Facebook, Twitter)
 */
function parseSocialMedia(html, gameData) {
  const result = {
    found: false,
    confidence: 0,
    details: {},
    matches: {
      score: false,
      teams: false,
      date: false
    }
  };
  
  const text = html
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ');
  
  const scores = extractScores(text);
  
  // Check score
  for (const score of scores) {
    const submittedHome = parseInt(gameData.homeScore);
    const submittedAway = parseInt(gameData.awayScore);
    
    if ((score.score1 === submittedHome && score.score2 === submittedAway) ||
        (score.score1 === submittedAway && score.score2 === submittedHome)) {
      result.matches.score = true;
      result.details.scoreFound = `${score.score1}-${score.score2}`;
      break;
    }
  }
  
  // Check for any team name
  const textLower = text.toLowerCase();
  const homeWords = normalizeTeamName(gameData.homeTeam).split(' ');
  const awayWords = normalizeTeamName(gameData.awayTeam).split(' ');
  
  const homeMatch = homeWords.some(w => w.length > 3 && textLower.includes(w));
  const awayMatch = awayWords.some(w => w.length > 3 && textLower.includes(w));
  
  result.details.homeTeamFound = homeMatch;
  result.details.awayTeamFound = awayMatch;
  result.matches.teams = homeMatch || awayMatch;
  
  // Calculate confidence (more lenient for social media)
  let confidence = 0;
  if (result.matches.score) confidence += 60;
  if (result.matches.teams) confidence += 40;
  
  result.confidence = confidence;
  result.found = confidence >= 60;
  
  return result;
}

// ============================================================================
// MAIN VALIDATION LOGIC
// ============================================================================

/**
 * Validate a URL against submitted game data
 */
async function validateUrl(url, gameData) {
  const result = {
    success: false,
    verified: false,
    confidence: 0,
    message: '',
    details: {},
    error: null
  };
  
  // Validate URL format
  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch (e) {
    result.error = 'Invalid URL format';
    result.message = 'The provided URL is not valid';
    return result;
  }
  
  // Check for allowed domains
  const allowedDomains = [
    'gotsport.com', 'gotsoccer.com', 'system.gotsport.com',
    'totalglobalsports.com',
    'instagram.com', 'facebook.com', 'fb.com',
    'twitter.com', 'x.com',
    'ecnlboys.com', 'ecnlgirls.com', 'ecnl.com',
    'girlsacademyleague.com', 'girlsacademy.com',
    'usclubsoccer.org', 'ussoccer.com',
    'maxpreps.com', 'scorebooklive.com',
    'youtube.com', 'youtu.be'
  ];
  
  const hostname = parsedUrl.hostname.replace('www.', '');
  const isAllowed = allowedDomains.some(d => hostname.includes(d));
  
  if (!isAllowed) {
    result.message = 'URL domain not in allowed list for automatic verification';
    result.details.domain = hostname;
    result.details.suggestion = 'Community verification will be used instead';
    return result;
  }
  
  // Fetch the URL
  let html;
  try {
    html = await fetchUrl(url);
    result.success = true;
  } catch (e) {
    result.error = `Failed to fetch URL: ${e.message}`;
    result.message = 'Could not access the URL for verification';
    return result;
  }
  
  // Parse based on site type
  let parseResult;
  if (hostname.includes('gotsport') || hostname.includes('gotsoccer') || hostname.includes('totalglobalsports')) {
    parseResult = parseGotSport(html, gameData);
  } else if (hostname.includes('instagram') || hostname.includes('facebook') || hostname.includes('twitter') || hostname.includes('x.com')) {
    parseResult = parseSocialMedia(html, gameData);
  } else {
    // Generic parsing
    parseResult = parseGotSport(html, gameData);
  }
  
  result.verified = parseResult.found;
  result.confidence = parseResult.confidence;
  result.details = {
    ...result.details,
    ...parseResult.details,
    matches: parseResult.matches
  };
  
  // Build message
  if (result.verified) {
    const matchList = [];
    if (parseResult.matches.score) matchList.push('score');
    if (parseResult.matches.teams) matchList.push('teams');
    if (parseResult.matches.date) matchList.push('date');
    result.message = `Verified! Found matching ${matchList.join(', ')} on the page.`;
  } else if (result.confidence > 0) {
    result.message = `Partial match (${result.confidence}% confidence). Some information found but not all details could be verified.`;
  } else {
    result.message = 'Could not verify. The submitted game data was not found on the page.';
  }
  
  return result;
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Validate URL endpoint
app.post('/api/validate-url', async (req, res) => {
  const { url, gameData } = req.body;
  
  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }
  
  if (!gameData || !gameData.homeTeam || !gameData.awayTeam) {
    return res.status(400).json({ error: 'Game data with homeTeam and awayTeam is required' });
  }
  
  try {
    const result = await validateUrl(url, gameData);
    res.json(result);
  } catch (e) {
    console.error('Validation error:', e);
    res.status(500).json({ 
      error: 'Validation failed', 
      message: e.message 
    });
  }
});

// Batch validation (for processing multiple pending games)
app.post('/api/validate-batch', async (req, res) => {
  const { games } = req.body;
  
  if (!games || !Array.isArray(games)) {
    return res.status(400).json({ error: 'Games array is required' });
  }
  
  const results = [];
  for (const game of games) {
    if (game.scoreUrl) {
      try {
        const result = await validateUrl(game.scoreUrl, game);
        results.push({ gameId: game.id, ...result });
      } catch (e) {
        results.push({ 
          gameId: game.id, 
          success: false, 
          error: e.message 
        });
      }
      // Small delay between requests to be nice
      await new Promise(r => setTimeout(r, 500));
    }
  }
  
  res.json({ results });
});

// ============================================================================
// START SERVER
// ============================================================================

app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════════════════════╗
║           Seedline URL Validator Server                          ║
╠══════════════════════════════════════════════════════════════════╣
║  Server running on http://localhost:${PORT}                         ║
║                                                                  ║
║  Endpoints:                                                      ║
║    POST /api/validate-url   - Validate a game submission URL     ║
║    POST /api/validate-batch - Batch validate multiple games      ║
║    GET  /api/health         - Health check                       ║
╚══════════════════════════════════════════════════════════════════╝
`);
});

module.exports = { validateUrl, normalizeTeamName, teamsMatch };
