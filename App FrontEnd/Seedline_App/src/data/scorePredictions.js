// Score Prediction Utility for Seedline V2
// Based on analysis of 50,000+ actual games
// Predicts game outcomes using empirical win probabilities and GPG/GAPG stats

// ============================================================================
// AGE GROUP UTILITIES
// Handle cross-age-group predictions with appropriate adjustments
// ============================================================================

/**
 * Parse ACTUAL age from age group string
 * Age groups use BIRTH YEAR format - supports multiple formats:
 * - "2013G" or "2011B" (full year)
 * - "G13" or "B11" (2-digit year)
 * - "G06" (2-digit with leading zero)
 *
 * Lower birth year numbers = OLDER players (2006 is oldest, 2019 is youngest)
 *
 * @param {string} ageGroup - e.g., "2013G", "G13", "B11", "2011B"
 * @returns {number|null} - Actual age (e.g., 2011G -> 14, 2013G -> 12 in 2025)
 */
function parseAgeFromAgeGroup(ageGroup) {
  if (!ageGroup) return null;

  const currentYear = new Date().getFullYear();

  // Try full 4-digit year first: "2013G", "2011B", "G2013", "B2011"
  const fullYearMatch = ageGroup.match(/[GB]?(20\d{2})[GB]?/i);
  if (fullYearMatch) {
    const birthYear = parseInt(fullYearMatch[1], 10);
    return currentYear - birthYear;
  }

  // Try 2-digit year: "G13", "B11", "G06", "13G", "11B"
  const shortYearMatch = ageGroup.match(/[GB]?(\d{1,2})[GB]?/i);
  if (shortYearMatch) {
    const birthYearSuffix = parseInt(shortYearMatch[1], 10);
    // Convert 2-digit to full year (06-25 = 2006-2025, youth soccer range)
    const birthYear = 2000 + birthYearSuffix;
    return currentYear - birthYear;
  }

  return null;
}

/**
 * Calculate power score adjustment for age group differences
 * Older teams are stronger - this converts to equivalent power score difference
 *
 * Key insights from real data:
 * - A highly-ranked younger team vs low-ranked older team (2 year gap) = close game or older wins
 * - Age gap is MASSIVE advantage - can overcome large ranking differences
 * - Even a #5 ranked 13G team would struggle against a #150 ranked 11G team
 *
 * @param {number} homeAge - Actual age of home team (e.g., 12 for 2013 birth year)
 * @param {number} awayAge - Actual age of away team (e.g., 14 for 2011 birth year)
 * @param {number} homePower - Home team power score
 * @param {number} awayPower - Away team power score
 * @returns {number} Power adjustment to add to home team's effective power
 */
function calculateAgeGroupPowerAdjustment(homeAge, awayAge, homePower, awayPower) {
  if (homeAge === null || awayAge === null) return 0;
  if (homeAge === awayAge) return 0;

  const ageDiff = homeAge - awayAge; // positive = home is older

  // Base power adjustment per year of age difference
  // VERY large - 1 year age gap is roughly equivalent to 300-400 ranking positions
  const BASE_POWER_PER_YEAR = 425;

  // Scale adjustment based on team quality
  // Elite teams (high power) have smaller age gaps
  // Lower-tier teams have larger age gaps
  const avgPower = (homePower + awayPower) / 2;

  // Scale factor based on power level:
  // - Power 1100 (low): scale = 2.0 → 700 pts/year
  // - Power 1400 (mid-low): scale = 1.5 → 525 pts/year
  // - Power 1600 (mid): scale = 1.2 → 420 pts/year
  // - Power 1800 (high): scale = 0.9 → 315 pts/year
  // - Power 2000 (elite): scale = 0.6 → 210 pts/year
  let scaleFactor = 2.0 - ((avgPower - 1100) / 600);
  scaleFactor = Math.max(0.5, Math.min(2.2, scaleFactor));

  const adjustment = ageDiff * BASE_POWER_PER_YEAR * scaleFactor;

  return adjustment;
}

// ============================================================================
// EMPIRICAL WIN PROBABILITY TABLE
// Based on analysis of 50,394 matched games with team rankings
// ============================================================================

const WIN_PROBABILITY_TABLE = [
  { low: -3000, high: -800, homeWin: 0.142, draw: 0.110, awayWin: 0.748 },
  { low: -800, high: -600, homeWin: 0.157, draw: 0.116, awayWin: 0.727 },
  { low: -600, high: -500, homeWin: 0.170, draw: 0.126, awayWin: 0.704 },
  { low: -500, high: -400, homeWin: 0.178, draw: 0.145, awayWin: 0.676 },
  { low: -400, high: -300, homeWin: 0.186, draw: 0.161, awayWin: 0.654 },
  { low: -300, high: -250, homeWin: 0.205, draw: 0.176, awayWin: 0.619 },
  { low: -250, high: -200, homeWin: 0.272, draw: 0.198, awayWin: 0.530 },
  { low: -200, high: -150, homeWin: 0.294, draw: 0.194, awayWin: 0.511 },
  { low: -150, high: -100, homeWin: 0.295, draw: 0.228, awayWin: 0.477 },
  { low: -100, high: -50, homeWin: 0.364, draw: 0.201, awayWin: 0.435 },
  { low: -50, high: 0, homeWin: 0.389, draw: 0.225, awayWin: 0.387 },
  { low: 0, high: 50, homeWin: 0.438, draw: 0.179, awayWin: 0.382 },
  { low: 50, high: 100, homeWin: 0.492, draw: 0.188, awayWin: 0.321 },
  { low: 100, high: 150, homeWin: 0.532, draw: 0.205, awayWin: 0.263 },
  { low: 150, high: 200, homeWin: 0.568, draw: 0.167, awayWin: 0.266 },
  { low: 200, high: 250, homeWin: 0.592, draw: 0.172, awayWin: 0.236 },
  { low: 250, high: 300, homeWin: 0.692, draw: 0.159, awayWin: 0.150 },
  { low: 300, high: 400, homeWin: 0.699, draw: 0.144, awayWin: 0.156 },
  { low: 400, high: 500, homeWin: 0.714, draw: 0.135, awayWin: 0.151 },
  { low: 500, high: 600, homeWin: 0.711, draw: 0.127, awayWin: 0.162 },
  { low: 600, high: 800, homeWin: 0.754, draw: 0.102, awayWin: 0.143 },
  { low: 800, high: 3000, homeWin: 0.777, draw: 0.095, awayWin: 0.128 },
];

/**
 * Get win probabilities based on power score difference (from empirical data)
 */
function getWinProbabilitiesByPowerDiff(powerDiff) {
  for (const bucket of WIN_PROBABILITY_TABLE) {
    if (powerDiff >= bucket.low && powerDiff < bucket.high) {
      return {
        homeWin: bucket.homeWin,
        draw: bucket.draw,
        awayWin: bucket.awayWin
      };
    }
  }
  
  // Extreme cases
  if (powerDiff < -3000) {
    return { homeWin: 0.142, draw: 0.110, awayWin: 0.748 };
  }
  return { homeWin: 0.777, draw: 0.095, awayWin: 0.128 };
}

/**
 * Calculate expected goals using team's actual scoring/conceding rates
 * This method weights:
 * - 55% on the team's own scoring rate (GPG)
 * - 45% on the opponent's conceding rate (GAPG)
 * - Adjusted for off/def power differentials
 * - Adjusted for power score gap (includes age adjustment)
 *
 * IMPORTANT: For cross-age predictions, GPG/GAPG stats are adjusted because
 * a team's stats against their own age group don't translate directly to
 * playing older/younger teams.
 */
function calculateExpectedGoalsWithGPG(powerDiff, homeOff, homeDef, awayOff, awayDef,
                                        homeGPG, homeGAPG, awayGPG, awayGAPG,
                                        homeAge, awayAge) {
  // Configuration based on regression analysis
  const TEAM_GPG_WEIGHT = 0.55;
  const OPP_GAPG_WEIGHT = 0.45;
  const HOME_ADVANTAGE = 0.15;
  const POWER_ADJUSTMENT = 0.0025;  // Goals per power point difference
  const OFF_DEF_FACTOR = 0.015;     // Goals per off/def point from 50

  // Age-adjust GPG/GAPG stats for cross-age predictions
  // A younger team's low GAPG doesn't apply when playing older teams
  // A younger team's high GPG won't translate against older defenders
  const AGE_STAT_ADJUSTMENT = 0.25; // Goals per year of age difference
  const ageDiff = (homeAge && awayAge) ? (homeAge - awayAge) : 0;

  // Adjust stats based on age difference:
  // If home is older (ageDiff > 0): home scores more, away concedes more
  // If away is older (ageDiff < 0): away scores more, home concedes more
  const adjustedHomeGPG = homeGPG + (ageDiff * AGE_STAT_ADJUSTMENT * 0.5);
  const adjustedHomeGAPG = homeGAPG - (ageDiff * AGE_STAT_ADJUSTMENT * 0.5);
  const adjustedAwayGPG = awayGPG - (ageDiff * AGE_STAT_ADJUSTMENT * 0.5);
  const adjustedAwayGAPG = awayGAPG + (ageDiff * AGE_STAT_ADJUSTMENT * 0.5);

  // Home team expected goals
  // Weighted combination of home's scoring rate and away's concede rate
  const homeBase = (adjustedHomeGPG * TEAM_GPG_WEIGHT + adjustedAwayGAPG * OPP_GAPG_WEIGHT);

  // Adjust for offensive/defensive quality differential
  const offDefAdjHome = (homeOff - 50) * OFF_DEF_FACTOR - (awayDef - 50) * OFF_DEF_FACTOR;

  // Power score adjustment - accounts for age adjustments in cross-age predictions
  const powerAdjHome = powerDiff * POWER_ADJUSTMENT * 0.7;

  let expectedHome = homeBase + HOME_ADVANTAGE + offDefAdjHome + powerAdjHome;

  // Away team expected goals
  const awayBase = (adjustedAwayGPG * TEAM_GPG_WEIGHT + adjustedHomeGAPG * OPP_GAPG_WEIGHT);
  const offDefAdjAway = (awayOff - 50) * OFF_DEF_FACTOR - (homeDef - 50) * OFF_DEF_FACTOR;
  const powerAdjAway = -powerDiff * POWER_ADJUSTMENT * 0.7;

  let expectedAway = awayBase + offDefAdjAway + powerAdjAway;
  
  // Clamp to reasonable ranges
  expectedHome = Math.max(0.3, Math.min(8.0, expectedHome));
  expectedAway = Math.max(0.2, Math.min(7.0, expectedAway));
  
  return { expectedHome, expectedAway };
}

/**
 * Calculate expected goals using only off/def power ratings (fallback)
 * Used when GPG/GAPG stats aren't available
 */
function calculateExpectedGoalsBasic(powerDiff, homeOff, homeDef, awayOff, awayDef) {
  // Configuration
  const BASE_GOALS = 1.85;
  const HOME_ADVANTAGE = 0.15;
  const POWER_FACTOR = 0.0025;  // Goals per power point difference
  const OFF_DEF_FACTOR = 0.023; // Impact per point from 50

  // Home expected goals - increased multiplier for cross-age predictions
  const powerAdjHome = powerDiff * POWER_FACTOR * 0.7;
  const offDefHome = (homeOff - 50) * OFF_DEF_FACTOR - (awayDef - 50) * OFF_DEF_FACTOR;

  let expectedHome = BASE_GOALS + HOME_ADVANTAGE + powerAdjHome + offDefHome;

  // Away expected goals
  const powerAdjAway = -powerDiff * POWER_FACTOR * 0.7;
  const offDefAway = (awayOff - 50) * OFF_DEF_FACTOR - (homeDef - 50) * OFF_DEF_FACTOR;

  let expectedAway = BASE_GOALS - 0.05 + powerAdjAway + offDefAway;
  
  // Clamp
  expectedHome = Math.max(0.3, Math.min(6.0, expectedHome));
  expectedAway = Math.max(0.2, Math.min(5.5, expectedAway));
  
  return { expectedHome, expectedAway };
}

/**
 * Normalize team name for matching - strips league and age group suffixes
 */
function normalizeTeamNameForMatch(name) {
  if (!name) return '';
  return name.toLowerCase()
    .replace(/\s+(ga|ecnl|ecnl-rl|ecnl rl|aspire|rl)$/i, '')
    .replace(/\s+\d+\/?\d*g$/i, '')  // Remove age suffixes like "13G", "08/07G"
    .replace(/\s+aspire$/i, '')
    .trim();
}

/**
 * Extract base club name (remove everything after common suffixes)
 */
function getBaseClubName(name) {
  if (!name) return '';
  const normalized = normalizeTeamNameForMatch(name);
  // Remove common suffixes like "SC", "FC", "Soccer Club" etc for broader matching
  return normalized
    .replace(/\s+(sc|fc|soccer club|soccer|club|academy|united)$/i, '')
    .trim();
}

/**
 * Common generic words that shouldn't be used for fuzzy matching alone
 * These are too common across team names to be reliable identifiers
 */
const GENERIC_TEAM_WORDS = new Set([
  'united', 'fc', 'sc', 'soccer', 'club', 'academy', 'athletic', 'athletics',
  'city', 'county', 'youth', 'premier', 'elite', 'select', 'fire', 'heat',
  'storm', 'thunder', 'lightning', 'rush', 'force', 'spirit', 'pride'
]);

/**
 * Find opponent in teams data with smart matching
 * Tries multiple strategies: exact match, normalized match, fuzzy match
 * IMPORTANT: Only matches within the SAME age group to ensure accurate predictions
 */
export function findOpponentInData(opponentName, teamAgeGroup, teamsData) {
  if (!teamsData || !opponentName) {
    return createDefaultOpponent(opponentName, 1500);
  }

  const oppNormalized = normalizeTeamNameForMatch(opponentName);
  const oppBase = getBaseClubName(opponentName);

  // Strategy 1: Exact name match (same age group)
  let match = teamsData.find(t =>
    t.name?.toLowerCase() === opponentName.toLowerCase() && t.ageGroup === teamAgeGroup
  );
  if (match) return match;

  // Strategy 2: Normalized name match (same age group)
  match = teamsData.find(t => {
    const tNorm = normalizeTeamNameForMatch(t.name);
    return tNorm === oppNormalized && t.ageGroup === teamAgeGroup;
  });
  if (match) return match;

  // Strategy 3: Base club name match in same age group
  match = teamsData.find(t => {
    const tBase = getBaseClubName(t.name);
    return tBase === oppBase && t.ageGroup === teamAgeGroup;
  });
  if (match) return match;

  // Strategy 4: Partial match - opponent name contains team name or vice versa (same age group)
  // Only match if the shorter name is at least 8 characters to avoid false positives
  match = teamsData.find(t => {
    if (t.ageGroup !== teamAgeGroup) return false;
    const tNorm = normalizeTeamNameForMatch(t.name);
    const shorter = tNorm.length < oppNormalized.length ? tNorm : oppNormalized;
    if (shorter.length < 8) return false; // Require meaningful substring
    return tNorm.includes(oppNormalized) || oppNormalized.includes(tNorm);
  });
  if (match) return match;

  // Strategy 5: Word overlap matching (same age group)
  // Filter out generic words that are too common to be reliable
  const oppWords = oppNormalized.split(/\s+/)
    .filter(w => w.length > 2 && !GENERIC_TEAM_WORDS.has(w.toLowerCase()));

  // Only attempt word matching if we have meaningful (non-generic) words
  if (oppWords.length >= 1) {
    match = teamsData.find(t => {
      if (t.ageGroup !== teamAgeGroup) return false;
      const tNorm = normalizeTeamNameForMatch(t.name);
      const tWords = tNorm.split(/\s+/)
        .filter(w => w.length > 2 && !GENERIC_TEAM_WORDS.has(w.toLowerCase()));

      // Require at least 1 non-generic word to match
      // AND the matching words must be a significant portion of both names
      const matchingWords = oppWords.filter(w => tWords.includes(w));
      if (matchingWords.length === 0) return false;

      // For reliable matching, require either:
      // - At least 2 non-generic words match, OR
      // - 1 word matches AND it's at least 50% of the unique words in both names
      const minWords = Math.min(oppWords.length, tWords.length);
      return matchingWords.length >= 2 ||
             (matchingWords.length >= 1 && minWords === 1 && matchingWords[0].length >= 5);
    });
    if (match) return match;
  }

  // No match found in same age group - return default with estimated stats for unranked team
  return createDefaultOpponent(opponentName, 800);
}

/**
 * Create a default opponent object with estimated stats based on power level
 * Lower power = worse team = higher GAPG, lower GPG
 */
function createDefaultOpponent(name, powerScore) {
  // Estimate GPG and GAPG based on power score
  // League average is about 2.0 GPG and 2.0 GAPG
  // Better teams score more and concede less
  // Power 800 (weak) -> GPG ~1.3, GAPG ~2.8
  // Power 1500 (avg) -> GPG ~2.0, GAPG ~2.0
  // Power 2000 (elite) -> GPG ~3.5, GAPG ~0.8
  
  const powerFactor = (powerScore - 1500) / 1000; // Range roughly -0.7 to +0.5
  const gpg = Math.max(0.5, Math.min(5, 2.0 + powerFactor * 1.5));
  const gapg = Math.max(0.3, Math.min(4, 2.0 - powerFactor * 1.5));
  
  return { 
    name: name, 
    powerScore: powerScore,
    goalsPerGame: gpg,
    goalsAgainstPerGame: gapg,
    offensivePowerScore: 50 + powerFactor * 30,
    defensivePowerScore: 50 + powerFactor * 30,
    rank: null,
    isUnranked: true
  };
}

/**
 * Predict game outcome between two teams
 * Returns predicted scores and win/loss/draw probabilities
 * Handles cross-age-group predictions with appropriate adjustments
 *
 * @param {Object} homeTeam - Home team object with powerScore, offensivePowerScore, etc.
 * @param {Object} awayTeam - Away team object
 * @param {Array} teamsData - Full teams array for lookups
 */
export function predictGame(homeTeam, awayTeam, teamsData) {
  // Find full team data if only partial data provided
  const home = homeTeam.powerScore ? homeTeam : teamsData?.find(t =>
    t.name === homeTeam.name || t.id === homeTeam.id
  ) || homeTeam;

  const away = awayTeam.powerScore ? awayTeam : teamsData?.find(t =>
    t.name === awayTeam.name || t.id === awayTeam.id
  ) || awayTeam;

  // Extract team stats with defaults
  const homePower = home.powerScore || 1500;
  const awayPower = away.powerScore || 1500;
  const homeOff = home.offensivePowerScore || 50;
  const homeDef = home.defensivePowerScore || 50;
  const awayOff = away.offensivePowerScore || 50;
  const awayDef = away.defensivePowerScore || 50;

  // GPG and GAPG stats (may not always be available)
  const homeGPG = home.goalsPerGame || home.gpg;
  const homeGAPG = home.goalsAgainstPerGame || home.gapg;
  const awayGPG = away.goalsPerGame || away.gpg;
  const awayGAPG = away.goalsAgainstPerGame || away.gapg;

  // Parse age groups for cross-age-group adjustment
  const homeAge = parseAgeFromAgeGroup(home.ageGroup);
  const awayAge = parseAgeFromAgeGroup(away.ageGroup);

  // Calculate age adjustment (older teams get power boost vs younger teams)
  const ageAdjustment = calculateAgeGroupPowerAdjustment(homeAge, awayAge, homePower, awayPower);

  // Effective power difference includes age adjustment
  const powerDiff = (homePower - awayPower) + ageAdjustment;
  
  // Calculate expected goals
  let expectedHome, expectedAway;
  let confidence;
  
  if (homeGPG && homeGAPG && awayGPG && awayGAPG) {
    // Use the more accurate GPG-based model with age adjustment
    const result = calculateExpectedGoalsWithGPG(
      powerDiff, homeOff, homeDef, awayOff, awayDef,
      homeGPG, homeGAPG, awayGPG, awayGAPG,
      homeAge, awayAge
    );
    expectedHome = result.expectedHome;
    expectedAway = result.expectedAway;
    confidence = 85;
  } else {
    // Fallback to basic model
    const result = calculateExpectedGoalsBasic(
      powerDiff, homeOff, homeDef, awayOff, awayDef
    );
    expectedHome = result.expectedHome;
    expectedAway = result.expectedAway;
    confidence = 60;
  }
  
  // Get win probabilities from empirical table
  const probs = getWinProbabilitiesByPowerDiff(powerDiff);
  
  // Include age adjustment info for display
  const isCrossAgeGroup = homeAge !== null && awayAge !== null && homeAge !== awayAge;

  return {
    predictedHomeScore: Math.round(expectedHome),
    predictedAwayScore: Math.round(expectedAway),
    homeExpectedGoals: expectedHome.toFixed(2),
    awayExpectedGoals: expectedAway.toFixed(2),
    homeWinProbability: Math.round(probs.homeWin * 100),
    drawProbability: Math.round(probs.draw * 100),
    awayWinProbability: Math.round(probs.awayWin * 100),
    expectedGoalDiff: (expectedHome - expectedAway).toFixed(2),
    confidence,
    // Age adjustment info
    isCrossAgeGroup,
    homeAgeGroup: home.ageGroup,
    awayAgeGroup: away.ageGroup,
    ageAdjustment: isCrossAgeGroup ? Math.round(ageAdjustment) : 0
  };
}

/**
 * Analyze actual game result vs prediction
 * Returns performance rating and ranking value
 */
export function analyzeGamePerformance(game, team, prediction, isHome) {
  const teamScore = isHome ? game.homeScore : game.awayScore;
  const oppScore = isHome ? game.awayScore : game.homeScore;
  const predictedTeamScore = isHome ? prediction.predictedHomeScore : prediction.predictedAwayScore;
  const predictedOppScore = isHome ? prediction.predictedAwayScore : prediction.predictedHomeScore;
  
  // Actual result
  const actualGD = teamScore - oppScore;
  const predictedGD = predictedTeamScore - predictedOppScore;
  
  // Performance difference (positive = outperformed, negative = underperformed)
  const performanceDiff = actualGD - predictedGD;
  
  // Calculate performance score (0-100 scale)
  // Base on goal differential vs expected
  let performanceScore = 50 + (performanceDiff * 12);
  
  // Bonus for upsets
  if (actualGD > 0 && predictedGD <= 0) {
    // Won when expected to lose/draw
    performanceScore += 15;
  } else if (actualGD === 0 && predictedGD < 0) {
    // Drew when expected to lose
    performanceScore += 10;
  } else if (actualGD < 0 && predictedGD >= 0) {
    // Lost when expected to win/draw
    performanceScore -= 15;
  } else if (actualGD === 0 && predictedGD > 0) {
    // Drew when expected to win
    performanceScore -= 10;
  }
  
  // Clamp to 0-100
  performanceScore = Math.max(0, Math.min(100, performanceScore));
  
  // Determine label
  let performanceLabel;
  if (performanceDiff >= 2) {
    performanceLabel = 'Greatly Outperformed';
  } else if (performanceDiff >= 1) {
    performanceLabel = 'Outperformed';
  } else if (performanceDiff > -1) {
    performanceLabel = 'Met Expectations';
  } else if (performanceDiff > -2) {
    performanceLabel = 'Underperformed';
  } else {
    performanceLabel = 'Greatly Underperformed';
  }
  
  return {
    actualScore: `${teamScore}-${oppScore}`,
    predictedScore: `${predictedTeamScore}-${predictedOppScore}`,
    goalDiffActual: actualGD,
    goalDiffPredicted: predictedGD,
    performanceDiff,
    performanceScore,
    performanceLabel,
    outperformed: performanceDiff > 0
  };
}

/**
 * Rank all games for a team by performance
 * Returns games sorted from best to worst result
 */
export function rankGamesByPerformance(games, team, teamsData) {
  const normalizedTeamName = team.name?.toLowerCase()
    .replace(/\s+(ga|ecnl|ecnl-rl|ecnl rl|aspire)$/i, '')
    .replace(/\s+\d+g$/i, '')  // Remove age group suffix like "13G"
    .trim();
  
  const teamAgeGroup = team.ageGroup;
  
  const analyzedGames = games.map(game => {
    // Determine if team is home or away
    const gameHomeNorm = game.homeTeam?.toLowerCase()
      .replace(/\s+(ga|ecnl|ecnl-rl|ecnl rl|aspire)$/i, '')
      .replace(/\s+\d+g$/i, '')
      .trim();
    
    const isHome = gameHomeNorm === normalizedTeamName || 
                   game.homeTeam?.toLowerCase().includes(normalizedTeamName);
    
    const opponentName = isHome ? game.awayTeam : game.homeTeam;
    
    // Find opponent in teams data with improved matching
    const opponent = findOpponentInData(opponentName, teamAgeGroup, teamsData);
    
    // Get prediction
    const prediction = isHome 
      ? predictGame(team, opponent, teamsData)
      : predictGame(opponent, team, teamsData);
    
    // Analyze performance
    const analysis = analyzeGamePerformance(game, team, prediction, isHome);
    
    return {
      ...game,
      opponent: opponentName,
      opponentData: opponent,  // Include full opponent data for rank display
      isHome,
      prediction,
      analysis,
      performanceScore: analysis.performanceScore
    };
  });
  
  // Sort by performance score (highest = best result)
  const sorted = [...analyzedGames].sort((a, b) => b.performanceScore - a.performanceScore);
  
  // Assign ranks
  return sorted.map((game, index) => ({
    ...game,
    performanceRank: index + 1,
    totalGames: sorted.length
  }));
}

/**
 * Get prediction color based on probability
 */
export function getPredictionColor(probability, type) {
  if (type === 'win') {
    if (probability >= 70) return '#2e7d32';
    if (probability >= 50) return '#558b2f';
    if (probability >= 30) return '#827717';
    return '#666';
  }
  if (type === 'loss') {
    if (probability >= 70) return '#c62828';
    if (probability >= 50) return '#d84315';
    if (probability >= 30) return '#ef6c00';
    return '#666';
  }
  return '#666';
}

/**
 * Get performance color based on score
 */
export function getPerformanceColor(score) {
  if (score >= 70) return '#2e7d32';  // Great
  if (score >= 55) return '#558b2f';  // Good
  if (score >= 45) return '#827717';  // OK
  if (score >= 35) return '#ef6c00';  // Below
  return '#c62828';  // Poor
}

export default {
  predictGame,
  analyzeGamePerformance,
  rankGamesByPerformance,
  getPredictionColor,
  getPerformanceColor,
  getWinProbabilitiesByPowerDiff,
  findOpponentInData
};
