// Static data for Seedline App
// Team rankings are now loaded dynamically from /public/rankings_for_react.json

// These are kept as defaults/fallbacks - actual values come from JSON
export const AGE_GROUPS = ['G13', 'G12', 'G11', 'G10', 'G09', 'G08/07'];
export const STATES = ['AZ', 'CA', 'CO', 'FL', 'GA', 'IL', 'MA', 'NC', 'NJ', 'NY', 'OH', 'PA', 'TX', 'VA', 'WA'];
export const LEAGUES = ['ECNL', 'GA'];

// Empty teamsData - will be loaded from JSON
export const teamsData = [];

// Clubs data - can be populated separately if needed
export const clubsData = [];

// Badge types
export const BADGE_TYPES = [
  { id: 'physical', name: 'Physical', emoji: '💪', description: 'Dominant in physical play' },
  { id: 'vocal', name: 'Vocal', emoji: '📣', description: 'Strong communicator' },
  { id: 'fearless', name: 'Fearless', emoji: '🔥', description: 'Brave in every challenge' },
  { id: 'stamina', name: 'Stamina', emoji: '⚡', description: 'Endless energy' },
  { id: 'consistent', name: 'Consistent', emoji: '🎯', description: 'Reliable every game' },
  { id: 'leader', name: 'Leader', emoji: '👑', description: 'Natural team leader' },
  { id: 'future_pro', name: 'Future Pro', emoji: '⭐', description: 'Professional potential' },
  { id: 'technical', name: 'Technical', emoji: '⚙️', description: 'Exceptional technical skills' },
  { id: 'tactical', name: 'Tactical', emoji: '🧠', description: 'Smart tactical awareness' },
  { id: 'creative', name: 'Creative', emoji: '🎨', description: 'Creative playmaker' },
  { id: 'clutch', name: 'Clutch', emoji: '🏆', description: 'Performs in big moments' },
  { id: 'resilient', name: 'Resilient', emoji: '🛡️', description: 'Bounces back from setbacks' },
  { id: 'team_first', name: 'Team First', emoji: '🤝', description: 'Puts team before self' },
];

// Link platform types with validation patterns
export const LINK_PLATFORMS = [
  { 
    id: 'veo', 
    name: 'VEO', 
    icon: '🎬', 
    color: '#00C853',
    pattern: /^https?:\/\/(www\.)?(app\.)?veo\.co\//i,
    placeholder: 'https://app.veo.co/...'
  },
  { 
    id: 'youtube', 
    name: 'YouTube', 
    icon: '📺', 
    color: '#FF0000',
    pattern: /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\//i,
    placeholder: 'https://youtube.com/...'
  },
  { 
    id: 'instagram', 
    name: 'Instagram', 
    icon: '📸', 
    color: '#E4405F',
    pattern: /^https?:\/\/(www\.)?instagram\.com\//i,
    placeholder: 'https://instagram.com/...'
  },
  { 
    id: 'facebook', 
    name: 'Facebook', 
    icon: '👤', 
    color: '#1877F2',
    pattern: /^https?:\/\/(www\.)?(facebook\.com|fb\.com)\//i,
    placeholder: 'https://facebook.com/...'
  },
  { 
    id: 'tiktok', 
    name: 'TikTok', 
    icon: '🎵', 
    color: '#000000',
    pattern: /^https?:\/\/(www\.)?(tiktok\.com|vm\.tiktok\.com)\//i,
    placeholder: 'https://tiktok.com/...'
  },
  { 
    id: 'snapchat', 
    name: 'Snapchat', 
    icon: '👻', 
    color: '#FFFC00',
    pattern: /^https?:\/\/(www\.)?(snapchat\.com|story\.snapchat\.com)\//i,
    placeholder: 'https://snapchat.com/...'
  },
  { 
    id: 'reddit', 
    name: 'Reddit', 
    icon: '🔶', 
    color: '#FF4500',
    pattern: /^https?:\/\/(www\.)?(reddit\.com|old\.reddit\.com)\//i,
    placeholder: 'https://reddit.com/...'
  },
  { 
    id: 'website', 
    name: 'Website', 
    icon: '🌐', 
    color: '#4CAF50',
    pattern: /^https?:\/\/.+/i,
    placeholder: 'https://...'
  },
];

// Blocked keywords for child safety (basic list - production would use API)
const BLOCKED_KEYWORDS = [
  'adult', 'xxx', 'porn', 'nsfw', 'gambling', 'casino', 'betting',
  'drugs', 'alcohol', 'tobacco', 'violence', 'gore', 'hate'
];

// LocalStorage keys - user-specific keys use {userId} placeholder
const STORAGE_KEYS = {
  USER: 'seedline_user',
  PLAYERS: 'seedline_players',        // Will be prefixed with username
  BADGES: 'seedline_badges',          // Will be prefixed with username  
  LINKS: 'seedline_links',            // Will be prefixed with username
  LINK_CLICKS: 'seedline_link_clicks',
  BLOCKED_LINKS: 'seedline_blocked_links',
  USER_GAMES: 'seedline_user_games',  // Will be prefixed with username
  GAME_VOTES: 'seedline_game_votes',
  MY_TEAMS: 'seedline_my_teams',      // Will be prefixed with username
  URL_VALIDATIONS: 'seedline_url_validations',
};

// Get current user from storage
const getCurrentUser = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.USER) || 'null');
  } catch {
    return null;
  }
};

// Get user-specific storage key
const getUserKey = (baseKey) => {
  const user = getCurrentUser();
  if (!user || user.accountType === 'guest') {
    // Guests get a temporary key that won't persist
    return `guest_temp_${baseKey}`;
  }
  return `${user.username}_${baseKey}`;
};

// Event types for user-submitted games
export const EVENT_TYPES = [
  { id: 'league_play', name: 'League Play' },
  { id: 'league_tournament', name: 'League Tournament' },
  { id: 'outside_tournament', name: 'Outside Tournament' },
  { id: 'friendly', name: 'Friendly' },
  { id: 'other', name: 'Other' },
];

// Verification status for user-submitted games
export const VERIFICATION_STATUS = {
  PENDING: 'pending',
  URL_VERIFIED: 'url_verified',
  COMMUNITY_VERIFIED: 'community_verified',
  SCRAPED: 'scraped',
  REJECTED: 'rejected',
};

// Storage functions
export const storage = {
  // User storage (global - not user-specific)
  getUser: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.USER) || 'null'),
  setUser: (user) => localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user)),
  clearUser: () => localStorage.removeItem(STORAGE_KEYS.USER),
  
  // Clear all guest/temp data
  clearGuestData: () => {
    // Remove all guest_temp_ prefixed items
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('guest_temp_')) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
  },
  
  // Player storage (user-specific)
  getPlayers: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];
    return JSON.parse(localStorage.getItem(getUserKey(STORAGE_KEYS.PLAYERS)) || '[]');
  },
  setPlayers: (players) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    localStorage.setItem(getUserKey(STORAGE_KEYS.PLAYERS), JSON.stringify(players));
  },
  
  // Badge storage (user-specific)
  getBadges: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return {};
    return JSON.parse(localStorage.getItem(getUserKey(STORAGE_KEYS.BADGES)) || '{}');
  },
  setBadges: (badges) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    localStorage.setItem(getUserKey(STORAGE_KEYS.BADGES), JSON.stringify(badges));
  },
  
  // Link storage (user-specific)
  getLinks: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];
    return JSON.parse(localStorage.getItem(getUserKey(STORAGE_KEYS.LINKS)) || '[]');
  },
  setLinks: (links) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    localStorage.setItem(getUserKey(STORAGE_KEYS.LINKS), JSON.stringify(links));
  },
  
  // Link clicks storage (for popularity tracking - global)
  getLinkClicks: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.LINK_CLICKS) || '{}'),
  setLinkClicks: (clicks) => localStorage.setItem(STORAGE_KEYS.LINK_CLICKS, JSON.stringify(clicks)),
  
  // Blocked links storage (for player pages - global)
  getBlockedLinks: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.BLOCKED_LINKS) || '{}'),
  setBlockedLinks: (blocked) => localStorage.setItem(STORAGE_KEYS.BLOCKED_LINKS, JSON.stringify(blocked)),

  // User-submitted games storage (user-specific)
  getUserGames: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];
    return JSON.parse(localStorage.getItem(getUserKey(STORAGE_KEYS.USER_GAMES)) || '[]');
  },
  setUserGames: (games) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    localStorage.setItem(getUserKey(STORAGE_KEYS.USER_GAMES), JSON.stringify(games));
  },
  
  // Game votes storage (global)
  getGameVotes: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.GAME_VOTES) || '{}'),
  setGameVotes: (votes) => localStorage.setItem(STORAGE_KEYS.GAME_VOTES, JSON.stringify(votes)),

  // My Teams storage (user-specific, up to 5 teams)
  getMyTeams: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];
    return JSON.parse(localStorage.getItem(getUserKey(STORAGE_KEYS.MY_TEAMS)) || '[]');
  },
  setMyTeams: (teams) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    // Limit to 5 teams
    const limitedTeams = teams.slice(0, 5);
    localStorage.setItem(getUserKey(STORAGE_KEYS.MY_TEAMS), JSON.stringify(limitedTeams));
  },
  
  // URL validations storage (global)
  getUrlValidations: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.URL_VALIDATIONS) || '{}'),
  setUrlValidations: (validations) => localStorage.setItem(STORAGE_KEYS.URL_VALIDATIONS, JSON.stringify(validations)),
};

// User game helper functions
export const userGameHelpers = {
  // Generate unique ID for user-submitted game
  generateGameId: () => `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  
  // Get user's device/browser fingerprint for anonymous voting
  getUserFingerprint: () => {
    let fingerprint = localStorage.getItem('seedline_fingerprint');
    if (!fingerprint) {
      fingerprint = `fp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('seedline_fingerprint', fingerprint);
    }
    return fingerprint;
  },

  // Submit a new user game
  submitGame: (gameData) => {
    const games = storage.getUserGames();
    const newGame = {
      id: userGameHelpers.generateGameId(),
      ...gameData,
      submittedAt: new Date().toISOString(),
      submittedBy: userGameHelpers.getUserFingerprint(),
      status: 'pending',
      verificationStatus: VERIFICATION_STATUS.PENDING,
      urlVerified: false,
      urlVerificationMessage: null,
      isUserGenerated: true,
      confirmations: 0,
      denials: 0,
    };
    games.push(newGame);
    storage.setUserGames(games);
    return newGame;
  },

  // Get all user games for a specific team (by name and age group)
  getGamesForTeam: (teamName, ageGroup) => {
    const games = storage.getUserGames();
    const teamLower = teamName.toLowerCase();
    return games.filter(game => {
      const homeMatch = game.homeTeam.toLowerCase() === teamLower;
      const awayMatch = game.awayTeam.toLowerCase() === teamLower;
      const ageMatch = game.ageGroup === ageGroup;
      return (homeMatch || awayMatch) && ageMatch;
    });
  },

  // Vote on a user-submitted game
  voteOnGame: (gameId, isValid) => {
    const fingerprint = userGameHelpers.getUserFingerprint();
    const votes = storage.getGameVotes();
    const games = storage.getUserGames();
    
    // Initialize votes for this game if needed
    if (!votes[gameId]) {
      votes[gameId] = { confirmations: {}, denials: {} };
    }
    
    // Remove any existing vote from this user
    delete votes[gameId].confirmations[fingerprint];
    delete votes[gameId].denials[fingerprint];
    
    // Add new vote
    if (isValid) {
      votes[gameId].confirmations[fingerprint] = new Date().toISOString();
    } else {
      votes[gameId].denials[fingerprint] = new Date().toISOString();
    }
    
    storage.setGameVotes(votes);
    
    // Update game counts
    const game = games.find(g => g.id === gameId);
    if (game) {
      game.confirmations = Object.keys(votes[gameId].confirmations).length;
      game.denials = Object.keys(votes[gameId].denials).length;
      
      // Check if game should be community verified (5 confirmations, 0 denials)
      if (game.confirmations >= 5 && game.denials === 0 && game.verificationStatus === VERIFICATION_STATUS.PENDING) {
        game.verificationStatus = VERIFICATION_STATUS.COMMUNITY_VERIFIED;
        game.status = 'verified';
      }
      
      storage.setUserGames(games);
    }
    
    return votes[gameId];
  },

  // Get user's vote on a specific game
  getUserVote: (gameId) => {
    const fingerprint = userGameHelpers.getUserFingerprint();
    const votes = storage.getGameVotes();
    
    if (!votes[gameId]) return null;
    
    if (votes[gameId].confirmations[fingerprint]) return 'confirmed';
    if (votes[gameId].denials[fingerprint]) return 'denied';
    return null;
  },

  // Mark game as URL verified (would be called by Claude verification)
  markUrlVerified: (gameId, isVerified, message) => {
    const games = storage.getUserGames();
    const game = games.find(g => g.id === gameId);
    if (game) {
      game.urlVerified = isVerified;
      game.urlVerificationMessage = message;
      if (isVerified) {
        game.verificationStatus = VERIFICATION_STATUS.URL_VERIFIED;
        game.status = 'verified';
      }
      storage.setUserGames(games);
    }
  },

  // Delete a user-submitted game (for moderation)
  deleteGame: (gameId) => {
    const games = storage.getUserGames();
    const filtered = games.filter(g => g.id !== gameId);
    storage.setUserGames(filtered);
    
    // Also remove votes
    const votes = storage.getGameVotes();
    delete votes[gameId];
    storage.setGameVotes(votes);
  },

  // Check if a similar game already exists (to detect duplicates)
  checkDuplicate: (homeTeam, awayTeam, date, ageGroup) => {
    const games = storage.getUserGames();
    const homeLower = homeTeam.toLowerCase();
    const awayLower = awayTeam.toLowerCase();
    
    return games.find(g => 
      g.homeTeam.toLowerCase() === homeLower &&
      g.awayTeam.toLowerCase() === awayLower &&
      g.date === date &&
      g.ageGroup === ageGroup
    );
  },

  // Save URL validation result for a game
  saveValidationResult: (gameId, validationResult) => {
    const validations = storage.getUrlValidations();
    validations[gameId] = {
      ...validationResult,
      validatedAt: new Date().toISOString()
    };
    storage.setUrlValidations(validations);

    // Also update the game record
    const games = storage.getUserGames();
    const game = games.find(g => g.id === gameId);
    if (game) {
      game.urlVerified = validationResult.verified;
      game.urlVerificationMessage = validationResult.message;
      game.urlValidationConfidence = validationResult.confidence || 0;
      game.urlValidationDetails = validationResult.details || {};
      
      // Auto-verify if AI verification is confident enough (80%+)
      if (validationResult.verified && validationResult.confidence >= 80) {
        game.verificationStatus = VERIFICATION_STATUS.URL_VERIFIED;
        game.status = 'verified';
      }
      
      storage.setUserGames(games);
    }

    return validationResult;
  },

  // Get validation result for a game
  getValidationResult: (gameId) => {
    const validations = storage.getUrlValidations();
    return validations[gameId] || null;
  },

  // Get all games that need validation (have URL but not yet validated)
  getGamesNeedingValidation: () => {
    const games = storage.getUserGames();
    const validations = storage.getUrlValidations();
    
    return games.filter(g => 
      g.scoreUrl && 
      !validations[g.id] &&
      g.verificationStatus === VERIFICATION_STATUS.PENDING
    );
  },
};

// Link helper functions
export const linkHelpers = {
  // Validate URL format
  isValidUrl: (url) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },

  // Check if URL matches platform pattern
  matchesPlatform: (url, platformId) => {
    const platform = LINK_PLATFORMS.find(p => p.id === platformId);
    if (!platform) return false;
    return platform.pattern.test(url);
  },

  // Basic child safety check (production would use real API)
  isChildSafe: (url) => {
    const lowerUrl = url.toLowerCase();
    return !BLOCKED_KEYWORDS.some(keyword => lowerUrl.includes(keyword));
  },

  // Verify link is accessible (simulated - real implementation needs backend)
  verifyLink: async (url) => {
    // In production, this would make a server-side request to verify the URL
    // For now, we do basic validation
    if (!linkHelpers.isValidUrl(url)) {
      return { valid: false, reason: 'Invalid URL format' };
    }
    if (!linkHelpers.isChildSafe(url)) {
      return { valid: false, reason: 'URL contains inappropriate content' };
    }
    // Simulate async verification
    return new Promise(resolve => {
      setTimeout(() => {
        resolve({ valid: true, reason: 'Link verified' });
      }, 500);
    });
  },

  // Get links for an entity (team, club, or player)
  getLinksForEntity: (entityType, entityId) => {
    const links = storage.getLinks();
    return links.filter(l => 
      l.entityType === entityType && 
      String(l.entityId) === String(entityId) &&
      l.status === 'approved'
    );
  },

  // Add a new link
  addLink: async (linkData) => {
    const verification = await linkHelpers.verifyLink(linkData.url);
    if (!verification.valid) {
      return { success: false, error: verification.reason };
    }

    const links = storage.getLinks();
    const newLink = {
      id: Date.now(),
      ...linkData,
      addedAt: new Date().toISOString(),
      status: 'approved', // In production, might be 'pending' for moderation
      ratings: {},
      averageRating: 0,
      totalRatings: 0,
      popularityScore: 0,
    };
    
    links.push(newLink);
    storage.setLinks(links);
    return { success: true, link: newLink };
  },

  // Delete a link
  deleteLink: (linkId) => {
    const links = storage.getLinks();
    const filtered = links.filter(l => l.id !== linkId);
    storage.setLinks(filtered);
  },

  // Rate a link
  rateLink: (linkId, userId, rating) => {
    const links = storage.getLinks();
    const link = links.find(l => l.id === linkId);
    if (!link) return false;

    link.ratings[userId] = rating;
    
    // Recalculate average
    const ratings = Object.values(link.ratings);
    link.totalRatings = ratings.length;
    link.averageRating = ratings.reduce((a, b) => a + b, 0) / ratings.length;
    
    storage.setLinks(links);
    return true;
  },

  // Record a click (max 3 per day per user for points)
  recordClick: (linkId, userId) => {
    const clicks = storage.getLinkClicks();
    const today = new Date().toISOString().split('T')[0];
    const key = `${linkId}_${userId}`;
    
    if (!clicks[key]) {
      clicks[key] = { dates: {}, totalClicks: 0 };
    }
    
    if (!clicks[key].dates[today]) {
      clicks[key].dates[today] = 0;
    }
    
    clicks[key].dates[today]++;
    clicks[key].totalClicks++;
    
    storage.setLinkClicks(clicks);
    
    // Update popularity score on the link
    linkHelpers.updatePopularityScore(linkId);
    
    // Return points earned (max 3 per day)
    return Math.min(clicks[key].dates[today], 3);
  },

  // Calculate and update popularity score
  updatePopularityScore: (linkId) => {
    const clicks = storage.getLinkClicks();
    const links = storage.getLinks();
    const link = links.find(l => l.id === linkId);
    if (!link) return;

    let score = 0;
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    // Calculate score from all users' clicks on this link
    Object.keys(clicks).forEach(key => {
      if (key.startsWith(`${linkId}_`)) {
        const userData = clicks[key];
        Object.entries(userData.dates).forEach(([date, count]) => {
          const clickDate = new Date(date);
          if (clickDate >= thirtyDaysAgo) {
            // Max 3 points per user per day
            score += Math.min(count, 3);
          }
        });
      }
    });

    link.popularityScore = score;
    storage.setLinks(links);
  },

  // Block a link from appearing on a player's page
  blockLinkForPlayer: (playerId, linkId) => {
    const blocked = storage.getBlockedLinks();
    if (!blocked[playerId]) {
      blocked[playerId] = { blockedLinkIds: [], blockAllNew: false };
    }
    if (!blocked[playerId].blockedLinkIds.includes(linkId)) {
      blocked[playerId].blockedLinkIds.push(linkId);
    }
    storage.setBlockedLinks(blocked);
  },

  // Unblock a link
  unblockLinkForPlayer: (playerId, linkId) => {
    const blocked = storage.getBlockedLinks();
    if (blocked[playerId]) {
      blocked[playerId].blockedLinkIds = blocked[playerId].blockedLinkIds.filter(id => id !== linkId);
      storage.setBlockedLinks(blocked);
    }
  },

  // Toggle block all new links for a player
  setBlockAllNewLinks: (playerId, blockAll) => {
    const blocked = storage.getBlockedLinks();
    if (!blocked[playerId]) {
      blocked[playerId] = { blockedLinkIds: [], blockAllNew: false };
    }
    blocked[playerId].blockAllNew = blockAll;
    storage.setBlockedLinks(blocked);
  },

  // Check if a link is blocked for a player
  isLinkBlockedForPlayer: (playerId, linkId) => {
    const blocked = storage.getBlockedLinks();
    if (!blocked[playerId]) return false;
    return blocked[playerId].blockedLinkIds.includes(linkId);
  },

  // Check if new links are blocked for a player
  areNewLinksBlocked: (playerId) => {
    const blocked = storage.getBlockedLinks();
    return blocked[playerId]?.blockAllNew || false;
  },

  // Get visible links for a player (respecting blocks)
  getVisibleLinksForPlayer: (playerId) => {
    const allLinks = linkHelpers.getLinksForEntity('player', playerId);
    const blocked = storage.getBlockedLinks();
    const playerBlocks = blocked[playerId];
    
    if (!playerBlocks) return allLinks;
    
    return allLinks.filter(link => !playerBlocks.blockedLinkIds.includes(link.id));
  },
};

export default {
  AGE_GROUPS,
  STATES,
  LEAGUES,
  teamsData,
  clubsData,
  BADGE_TYPES,
  LINK_PLATFORMS,
  EVENT_TYPES,
  VERIFICATION_STATUS,
  storage,
  linkHelpers,
  userGameHelpers,
};
