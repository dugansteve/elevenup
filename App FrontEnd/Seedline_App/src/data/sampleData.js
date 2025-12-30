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

// =============================================================================
// CRITICAL: Team Matching Helper
// =============================================================================
// WARNING: Team IDs in rankings_for_react.json are UNSTABLE - they change every
// time the ranker runs. NEVER use team.id to match saved teams to current rankings.
// Always use this helper function instead.
//
// This bug has occurred MULTIPLE TIMES where saved teams (My Teams, Followed Teams)
// showed the wrong team because the code used ID fallback matching.
// =============================================================================

/**
 * Find a team in teamsData by name and ageGroup (stable matching)
 *
 * IMPORTANT: Do NOT add ID-based fallback here! IDs are regenerated when
 * rankings are updated and will match the WRONG team.
 *
 * @param {Object} savedTeam - The saved team object with name, ageGroup, club
 * @param {Array} teamsData - The current rankings data
 * @returns {Object|null} - The matched team from teamsData, or null if not found
 */
export function findTeamInRankings(savedTeam, teamsData) {
  if (!savedTeam || !teamsData || teamsData.length === 0) return null;

  const savedName = savedTeam.name?.toLowerCase() || '';
  const savedAgeGroup = savedTeam.ageGroup?.toLowerCase() || '';
  const savedClub = savedTeam.club?.toLowerCase() || '';

  // Strategy 1: Exact name + ageGroup match
  let match = teamsData.find(t =>
    t.name?.toLowerCase() === savedName &&
    t.ageGroup?.toLowerCase() === savedAgeGroup
  );
  if (match) return match;

  // Strategy 2: Partial name match (handles name variations)
  if (savedName.length >= 5) {
    match = teamsData.find(t => {
      if (t.ageGroup?.toLowerCase() !== savedAgeGroup) return false;
      const tName = t.name?.toLowerCase() || '';
      return tName.includes(savedName) || savedName.includes(tName);
    });
    if (match) return match;
  }

  // Strategy 3: Club name match (same club, same age group)
  if (savedClub && savedClub.length >= 3) {
    match = teamsData.find(t => {
      if (t.ageGroup?.toLowerCase() !== savedAgeGroup) return false;
      const tClub = t.club?.toLowerCase() || '';
      return tClub.includes(savedClub) || savedClub.includes(tClub);
    });
    if (match) return match;
  }

  // NO ID FALLBACK - this is intentional!
  // Team IDs change when rankings are regenerated
  return null;
}

// Badge types
export const BADGE_TYPES = [
  { id: 'physical', name: 'Physical', emoji: '💪', description: 'Dominant in physical play' },
  { id: 'vocal', name: 'Vocal', emoji: '📣', description: 'Strong communicator' },
  { id: 'fearless', name: 'Fearless', emoji: '🔥', description: 'Brave in every challenge' },
  { id: 'stamina', name: 'Stamina', emoji: '⚡', description: 'Endless energy' },
  { id: 'speed', name: 'Speed', emoji: '🏃', description: 'Exceptional pace and quickness' },
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
  PLAYERS: 'seedline_players',        // Will be prefixed with stable userId
  BADGES: 'seedline_badges',          // Will be prefixed with stable userId
  LINKS: 'seedline_links',            // Will be prefixed with stable userId
  LINK_CLICKS: 'seedline_link_clicks',
  BLOCKED_LINKS: 'seedline_blocked_links',
  USER_GAMES: 'seedline_user_games',  // Will be prefixed with stable userId
  GAME_VOTES: 'seedline_game_votes',
  MY_TEAMS: 'seedline_my_teams',      // Will be prefixed with stable userId
  FOLLOWED_TEAMS: 'seedline_followed_teams', // Will be prefixed with stable userId - unlimited teams
  URL_VALIDATIONS: 'seedline_url_validations',
  PENDING_REMOVALS: 'seedline_pending_removals',      // Global - tracks pending player removals
  PLAYER_TEAM_HISTORY: 'seedline_player_team_history', // Global - tracks player team history
  DAILY_UPDATES: 'seedline_daily_updates',            // Will be prefixed with stable userId
  DAILY_UPDATE_USAGE: 'seedline_daily_update_usage',  // Will be prefixed with stable userId - tracks daily generation limits
};

// Generate a stable user ID
const generateUserId = () => {
  return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Get current user from storage
const getCurrentUser = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.USER) || 'null');
  } catch {
    return null;
  }
};

// Get user-specific storage key using stable userId
const getUserKey = (baseKey) => {
  const user = getCurrentUser();
  if (!user || user.accountType === 'guest') {
    // Guests get a temporary key that won't persist
    return `guest_temp_${baseKey}`;
  }
  // Priority: Firebase UID (user.id) > legacy userId > username
  // user.id is the Firebase UID which is guaranteed stable across logins
  const userIdentifier = user.id || user.userId || user.username;
  return `${userIdentifier}_${baseKey}`;
};

// Get legacy key (username-based) for data migration
const getLegacyUserKey = (baseKey) => {
  const user = getCurrentUser();
  if (!user || user.accountType === 'guest' || !user.username) {
    return null;
  }
  return `${user.username}_${baseKey}`;
};

// Migrate data from legacy username-based key to new userId-based key
const migrateUserData = (baseKey) => {
  const user = getCurrentUser();
  if (!user || !user.userId || !user.username) return;

  const legacyKey = `${user.username}_${baseKey}`;
  const newKey = `${user.userId}_${baseKey}`;

  // Only migrate if legacy data exists and new key doesn't have data
  const legacyData = localStorage.getItem(legacyKey);
  const newData = localStorage.getItem(newKey);

  if (legacyData && !newData) {
    localStorage.setItem(newKey, legacyData);
    // Keep legacy data as backup, don't delete it
  }
};

// Find and migrate orphaned user data from old random userId keys
// This handles the bug where every login generated a new random userId
const migrateOrphanedData = () => {
  const user = getCurrentUser();
  if (!user || !user.id || user.accountType === 'guest') return;

  // First, log all localStorage keys that look like user data for debugging
  console.log('[Migration] Scanning localStorage for user data...');
  const allUserDataKeys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.includes('seedline_')) {
      try {
        const data = localStorage.getItem(key);
        const parsed = JSON.parse(data);
        const size = Array.isArray(parsed) ? parsed.length : Object.keys(parsed).length;
        if (size > 0) {
          allUserDataKeys.push({ key, size, sample: JSON.stringify(parsed).substring(0, 100) });
        }
      } catch (e) {
        // Skip
      }
    }
  }
  console.log('[Migration] Found user data keys:', allUserDataKeys);

  const correctKey = `${user.id}_${STORAGE_KEYS.MY_TEAMS}`;
  const existingData = localStorage.getItem(correctKey);

  // Log current state
  console.log('[Migration] Current user id:', user.id);
  console.log('[Migration] Correct key would be:', correctKey);
  console.log('[Migration] Data at correct key:', existingData);

  // DON'T skip if data exists - we need to find ALL orphaned data to help recover
  // The user may have correct data under an old key that we need to find

  // Keys to migrate (user-specific data)
  const dataKeys = [
    STORAGE_KEYS.MY_TEAMS,
    STORAGE_KEYS.FOLLOWED_TEAMS,
    STORAGE_KEYS.PLAYERS,
    STORAGE_KEYS.BADGES,
    STORAGE_KEYS.LINKS,
    STORAGE_KEYS.USER_GAMES,
    STORAGE_KEYS.DAILY_UPDATES,
    STORAGE_KEYS.DAILY_UPDATE_USAGE
  ];

  // Scan localStorage for keys matching pattern: *_seedline_*
  const orphanedKeyMap = {}; // Maps baseKey -> list of orphaned keys with data

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key) continue;

    // Check each data type
    for (const baseKey of dataKeys) {
      if (key.endsWith(`_${baseKey}`)) {
        const prefix = key.replace(`_${baseKey}`, '');

        // Skip if this is the correct key or guest key
        if (prefix === user.id || prefix === 'guest_temp') continue;

        // Skip if this looks like another user's Firebase UID (they start with letters)
        // But include old random userIds (start with "user_")
        // Also include username-based keys

        try {
          const data = localStorage.getItem(key);
          if (data) {
            const parsed = JSON.parse(data);
            // Only consider keys with actual data
            if ((Array.isArray(parsed) && parsed.length > 0) ||
                (typeof parsed === 'object' && Object.keys(parsed).length > 0)) {
              if (!orphanedKeyMap[baseKey]) {
                orphanedKeyMap[baseKey] = [];
              }
              orphanedKeyMap[baseKey].push({ key, prefix, data: parsed });
            }
          }
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }
  }

  // Log all orphaned data found
  console.log('[Migration] Orphaned data found:', orphanedKeyMap);

  // For MY_TEAMS specifically, log ALL versions found so user can see what's available
  if (orphanedKeyMap[STORAGE_KEYS.MY_TEAMS]) {
    console.log('[Migration] === MY_TEAMS data across all keys ===');
    for (const orphan of orphanedKeyMap[STORAGE_KEYS.MY_TEAMS]) {
      console.log(`[Migration] Key "${orphan.key}":`, orphan.data);
    }
  }

  // Migrate orphaned data - prefer the one with most data
  let migratedCount = 0;
  for (const [baseKey, orphanedKeys] of Object.entries(orphanedKeyMap)) {
    if (orphanedKeys.length === 0) continue;

    const correctKey = `${user.id}_${baseKey}`;
    const existingCorrectData = localStorage.getItem(correctKey);

    // Log what we found vs what's at correct key
    console.log(`[Migration] For ${baseKey}: found ${orphanedKeys.length} orphaned keys, correct key has:`, existingCorrectData);

    // Skip if correct key already has data
    if (existingCorrectData) {
      try {
        const parsed = JSON.parse(existingCorrectData);
        if ((Array.isArray(parsed) && parsed.length > 0) ||
            (typeof parsed === 'object' && Object.keys(parsed).length > 0)) {
          console.log(`[Migration] Skipping ${baseKey} - correct key already has ${Array.isArray(parsed) ? parsed.length : Object.keys(parsed).length} items`);
          continue;
        }
      } catch (e) {
        // Continue with migration
      }
    }

    // Find the orphaned key with the most data
    let bestOrphan = orphanedKeys[0];
    for (const orphan of orphanedKeys) {
      const orphanSize = Array.isArray(orphan.data) ? orphan.data.length : Object.keys(orphan.data).length;
      const bestSize = Array.isArray(bestOrphan.data) ? bestOrphan.data.length : Object.keys(bestOrphan.data).length;
      if (orphanSize > bestSize) {
        bestOrphan = orphan;
      }
    }

    // Migrate the data
    console.log(`[Migration] Migrating ${baseKey} from "${bestOrphan.prefix}" to "${user.id}"`);
    localStorage.setItem(correctKey, JSON.stringify(bestOrphan.data));
    migratedCount++;
  }

  if (migratedCount > 0) {
    console.log(`[Migration] Successfully migrated ${migratedCount} data types to Firebase UID-based keys`);
  } else {
    console.log('[Migration] No data needed to be migrated');
  }
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

  // Generate a stable user ID (exported for use in UserContext)
  generateUserId,

  // Ensure user has a stable userId (adds one if missing, for migration)
  ensureUserId: () => {
    const user = getCurrentUser();
    if (user && user.accountType !== 'guest' && !user.userId) {
      user.userId = generateUserId();
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
      // Migrate all user data to new userId-based keys
      migrateUserData(STORAGE_KEYS.PLAYERS);
      migrateUserData(STORAGE_KEYS.BADGES);
      migrateUserData(STORAGE_KEYS.LINKS);
      migrateUserData(STORAGE_KEYS.USER_GAMES);
      migrateUserData(STORAGE_KEYS.MY_TEAMS);
      return user;
    }
    return user;
  },

  // Migrate orphaned data from old random userId keys to Firebase UID-based keys
  migrateOrphanedData,

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

  // Player storage (user-specific) - with legacy data recovery
  getPlayers: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];

    // First, try the current key (userId-based or username-based)
    const currentKey = getUserKey(STORAGE_KEYS.PLAYERS);
    let players = JSON.parse(localStorage.getItem(currentKey) || '[]');

    // If empty and user has both userId and username, check legacy key
    if (players.length === 0 && user.userId && user.username) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.PLAYERS}`;
      if (legacyKey !== currentKey) {
        const legacyPlayers = JSON.parse(localStorage.getItem(legacyKey) || '[]');
        if (legacyPlayers.length > 0) {
          // Migrate the data
          localStorage.setItem(currentKey, JSON.stringify(legacyPlayers));
          players = legacyPlayers;
        }
      }
    }

    return players;
  },
  setPlayers: (players) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    const currentKey = getUserKey(STORAGE_KEYS.PLAYERS);
    localStorage.setItem(currentKey, JSON.stringify(players));

    // Also save to legacy key as backup if user has username
    if (user.username && user.userId) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.PLAYERS}`;
      if (legacyKey !== currentKey) {
        localStorage.setItem(legacyKey, JSON.stringify(players));
      }
    }
  },
  
  // Badge storage (user-specific) - with legacy data recovery
  getBadges: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return {};

    const currentKey = getUserKey(STORAGE_KEYS.BADGES);
    let badges = JSON.parse(localStorage.getItem(currentKey) || '{}');

    // Check legacy key if empty
    if (Object.keys(badges).length === 0 && user.userId && user.username) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.BADGES}`;
      if (legacyKey !== currentKey) {
        const legacyBadges = JSON.parse(localStorage.getItem(legacyKey) || '{}');
        if (Object.keys(legacyBadges).length > 0) {
          localStorage.setItem(currentKey, JSON.stringify(legacyBadges));
          badges = legacyBadges;
        }
      }
    }

    return badges;
  },
  setBadges: (badges) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    const currentKey = getUserKey(STORAGE_KEYS.BADGES);
    localStorage.setItem(currentKey, JSON.stringify(badges));

    // Also save to legacy key as backup
    if (user.username && user.userId) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.BADGES}`;
      if (legacyKey !== currentKey) {
        localStorage.setItem(legacyKey, JSON.stringify(badges));
      }
    }
  },

  // Link storage (user-specific) - with legacy data recovery
  getLinks: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];

    const currentKey = getUserKey(STORAGE_KEYS.LINKS);
    let links = JSON.parse(localStorage.getItem(currentKey) || '[]');

    // Check legacy key if empty
    if (links.length === 0 && user.userId && user.username) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.LINKS}`;
      if (legacyKey !== currentKey) {
        const legacyLinks = JSON.parse(localStorage.getItem(legacyKey) || '[]');
        if (legacyLinks.length > 0) {
          localStorage.setItem(currentKey, JSON.stringify(legacyLinks));
          links = legacyLinks;
        }
      }
    }

    return links;
  },
  setLinks: (links) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    const currentKey = getUserKey(STORAGE_KEYS.LINKS);
    localStorage.setItem(currentKey, JSON.stringify(links));

    // Also save to legacy key as backup
    if (user.username && user.userId) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.LINKS}`;
      if (legacyKey !== currentKey) {
        localStorage.setItem(legacyKey, JSON.stringify(links));
      }
    }
  },
  
  // Link clicks storage (for popularity tracking - global)
  getLinkClicks: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.LINK_CLICKS) || '{}'),
  setLinkClicks: (clicks) => localStorage.setItem(STORAGE_KEYS.LINK_CLICKS, JSON.stringify(clicks)),
  
  // Blocked links storage (for player pages - global)
  getBlockedLinks: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.BLOCKED_LINKS) || '{}'),
  setBlockedLinks: (blocked) => localStorage.setItem(STORAGE_KEYS.BLOCKED_LINKS, JSON.stringify(blocked)),

  // User-submitted games storage (user-specific) - with legacy data recovery
  getUserGames: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];

    const currentKey = getUserKey(STORAGE_KEYS.USER_GAMES);
    let games = JSON.parse(localStorage.getItem(currentKey) || '[]');

    // Check legacy key if empty
    if (games.length === 0 && user.userId && user.username) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.USER_GAMES}`;
      if (legacyKey !== currentKey) {
        const legacyGames = JSON.parse(localStorage.getItem(legacyKey) || '[]');
        if (legacyGames.length > 0) {
          localStorage.setItem(currentKey, JSON.stringify(legacyGames));
          games = legacyGames;
        }
      }
    }

    return games;
  },
  setUserGames: (games) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    const currentKey = getUserKey(STORAGE_KEYS.USER_GAMES);
    localStorage.setItem(currentKey, JSON.stringify(games));

    // Also save to legacy key as backup
    if (user.username && user.userId) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.USER_GAMES}`;
      if (legacyKey !== currentKey) {
        localStorage.setItem(legacyKey, JSON.stringify(games));
      }
    }
  },

  // Game votes storage (global)
  getGameVotes: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.GAME_VOTES) || '{}'),
  setGameVotes: (votes) => localStorage.setItem(STORAGE_KEYS.GAME_VOTES, JSON.stringify(votes)),

  // My Teams storage (user-specific, up to 5 teams) - with legacy data recovery
  getMyTeams: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];

    const currentKey = getUserKey(STORAGE_KEYS.MY_TEAMS);
    console.log('[getMyTeams] User object:', { id: user.id, userId: user.userId, username: user.username });
    console.log('[getMyTeams] Reading from key:', currentKey);
    let teams = JSON.parse(localStorage.getItem(currentKey) || '[]');
    console.log('[getMyTeams] Found teams:', teams);

    // Check legacy key if empty
    if (teams.length === 0 && user.userId && user.username) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.MY_TEAMS}`;
      if (legacyKey !== currentKey) {
        const legacyTeams = JSON.parse(localStorage.getItem(legacyKey) || '[]');
        if (legacyTeams.length > 0) {
          localStorage.setItem(currentKey, JSON.stringify(legacyTeams));
          teams = legacyTeams;
        }
      }
    }

    return teams;
  },
  setMyTeams: (teams) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    // Limit to 5 teams
    const limitedTeams = teams.slice(0, 5);
    const currentKey = getUserKey(STORAGE_KEYS.MY_TEAMS);
    localStorage.setItem(currentKey, JSON.stringify(limitedTeams));

    // Also save to legacy key as backup
    if (user.username && user.userId) {
      const legacyKey = `${user.username}_${STORAGE_KEYS.MY_TEAMS}`;
      if (legacyKey !== currentKey) {
        localStorage.setItem(legacyKey, JSON.stringify(limitedTeams));
      }
    }
  },
  
  // URL validations storage (global)
  getUrlValidations: () => JSON.parse(localStorage.getItem(STORAGE_KEYS.URL_VALIDATIONS) || '{}'),
  setUrlValidations: (validations) => localStorage.setItem(STORAGE_KEYS.URL_VALIDATIONS, JSON.stringify(validations)),

  // Followed Teams storage (user-specific, unlimited teams)
  getFollowedTeams: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];
    const currentKey = getUserKey(STORAGE_KEYS.FOLLOWED_TEAMS);
    return JSON.parse(localStorage.getItem(currentKey) || '[]');
  },
  setFollowedTeams: (teams) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;
    const currentKey = getUserKey(STORAGE_KEYS.FOLLOWED_TEAMS);
    localStorage.setItem(currentKey, JSON.stringify(teams));
  },
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

// Roster management helpers (removal, transfer, team history)
export const rosterHelpers = {
  // Get all pending removals
  getPendingRemovals: () => {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.PENDING_REMOVALS) || '[]');
  },

  // Save pending removals
  setPendingRemovals: (removals) => {
    localStorage.setItem(STORAGE_KEYS.PENDING_REMOVALS, JSON.stringify(removals));
  },

  // Get team history for all players
  getAllTeamHistory: () => {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.PLAYER_TEAM_HISTORY) || '{}');
  },

  // Save all team history
  setAllTeamHistory: (history) => {
    localStorage.setItem(STORAGE_KEYS.PLAYER_TEAM_HISTORY, JSON.stringify(history));
  },

  // Request player removal (soft delete)
  // Returns: { success: boolean, removalId?: string, error?: string }
  requestRemoval: (playerId, teamId, teamName, userId, userName, isAdminOrCoach = false) => {
    const players = storage.getPlayers();
    const player = players.find(p => p.id === playerId);

    if (!player) {
      return { success: false, error: 'Player not found' };
    }

    // Check if there's already a pending removal for this player
    const removals = rosterHelpers.getPendingRemovals();
    const existingRemoval = removals.find(r => r.playerId === playerId && r.status === 'pending');
    if (existingRemoval) {
      return { success: false, error: 'Removal already pending for this player' };
    }

    const removalId = `removal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = new Date().toISOString();

    if (isAdminOrCoach) {
      // Admin/coach can remove immediately without confirmation
      player.removalStatus = 'hidden';
      player.removalRequestedBy = userId;
      player.removalRequestedAt = now;
      player.removalConfirmedBy = userId;
      player.removalConfirmedAt = now;
      storage.setPlayers(players);

      // Add to team history
      rosterHelpers.addTeamHistoryEntry(playerId, teamId, teamName, 'removed', userId, userName);

      return { success: true, removalId, immediate: true };
    } else {
      // Regular user - set to pending removal
      player.removalStatus = 'pending_removal';
      player.removalRequestedBy = userId;
      player.removalRequestedByName = userName;
      player.removalRequestedAt = now;
      storage.setPlayers(players);

      // Add to pending removals list
      removals.push({
        removalId,
        playerId,
        playerName: player.name,
        teamId,
        teamName,
        requestedBy: userId,
        requestedByName: userName,
        requestedAt: now,
        status: 'pending',
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days
      });
      rosterHelpers.setPendingRemovals(removals);

      return { success: true, removalId, immediate: false };
    }
  },

  // Confirm removal (second person)
  // Returns: { success: boolean, error?: string }
  confirmRemoval: (playerId, confirmerId, confirmerName, isAdminOrCoach = false) => {
    const players = storage.getPlayers();
    const player = players.find(p => p.id === playerId);

    if (!player) {
      return { success: false, error: 'Player not found' };
    }

    if (player.removalStatus !== 'pending_removal') {
      return { success: false, error: 'Player is not pending removal' };
    }

    // Prevent same user from confirming their own removal (unless admin/coach)
    if (!isAdminOrCoach && player.removalRequestedBy === confirmerId) {
      return { success: false, error: 'You cannot confirm your own removal request' };
    }

    const now = new Date().toISOString();

    // Complete the removal
    player.removalStatus = 'hidden';
    player.removalConfirmedBy = confirmerId;
    player.removalConfirmedByName = confirmerName;
    player.removalConfirmedAt = now;
    storage.setPlayers(players);

    // Update pending removals list
    const removals = rosterHelpers.getPendingRemovals();
    const removal = removals.find(r => r.playerId === playerId && r.status === 'pending');
    if (removal) {
      removal.status = 'confirmed';
      removal.confirmedBy = confirmerId;
      removal.confirmedByName = confirmerName;
      removal.confirmedAt = now;
      rosterHelpers.setPendingRemovals(removals);
    }

    // Add to team history
    rosterHelpers.addTeamHistoryEntry(
      playerId,
      player.teamId,
      player.teamName,
      'removed',
      confirmerId,
      confirmerName
    );

    return { success: true };
  },

  // Cancel removal / put back player
  // Returns: { success: boolean, conflict?: boolean, error?: string }
  cancelRemoval: (playerId, userId, userName, isAdminOrCoach = false) => {
    const players = storage.getPlayers();
    const player = players.find(p => p.id === playerId);

    if (!player) {
      return { success: false, error: 'Player not found' };
    }

    if (player.removalStatus !== 'pending_removal') {
      return { success: false, error: 'Player is not pending removal' };
    }

    // Check if same user is cancelling (allowed) or different user (conflict)
    const isSameUser = player.removalRequestedBy === userId;

    if (isSameUser || isAdminOrCoach) {
      // Same user or admin can cancel outright
      player.removalStatus = 'active';
      delete player.removalRequestedBy;
      delete player.removalRequestedByName;
      delete player.removalRequestedAt;
      storage.setPlayers(players);

      // Remove from pending removals list
      const removals = rosterHelpers.getPendingRemovals();
      const filtered = removals.filter(r => !(r.playerId === playerId && r.status === 'pending'));
      rosterHelpers.setPendingRemovals(filtered);

      return { success: true, conflict: false };
    } else {
      // Different user wants to restore - this creates a conflict
      const removals = rosterHelpers.getPendingRemovals();
      const removal = removals.find(r => r.playerId === playerId && r.status === 'pending');
      if (removal) {
        removal.status = 'conflict';
        removal.conflictBy = userId;
        removal.conflictByName = userName;
        removal.conflictAt = new Date().toISOString();
        rosterHelpers.setPendingRemovals(removals);
      }

      return { success: true, conflict: true, message: 'Conflict created - player stays on roster until resolved' };
    }
  },

  // Transfer player to a different team
  // Returns: { success: boolean, error?: string }
  transferPlayer: (playerId, fromTeamId, fromTeamName, toTeamId, toTeamName, userId, userName) => {
    const players = storage.getPlayers();
    const player = players.find(p => p.id === playerId);

    if (!player) {
      return { success: false, error: 'Player not found' };
    }

    if (player.removalStatus === 'pending_removal') {
      return { success: false, error: 'Cannot transfer a player with pending removal' };
    }

    // Check for re-add conflict (transferred to a team they were removed from within 6 months)
    const conflict = rosterHelpers.checkReaddConflict(player.name, toTeamId);
    if (conflict) {
      return {
        success: false,
        error: 'This player was removed from the destination team within the last 6 months',
        conflict: true,
        conflictDetails: conflict
      };
    }

    const now = new Date().toISOString();

    // Add team history entry for leaving old team
    rosterHelpers.addTeamHistoryEntry(playerId, fromTeamId, fromTeamName, 'transferred_out', userId, userName);

    // Update player's team
    player.teamId = toTeamId;
    player.teamName = toTeamName;
    player.transferredAt = now;
    player.transferredBy = userId;
    storage.setPlayers(players);

    // Add team history entry for joining new team
    rosterHelpers.addTeamHistoryEntry(playerId, toTeamId, toTeamName, 'transferred_in', userId, userName);

    return { success: true };
  },

  // Get team history for a specific player
  getPlayerTeamHistory: (playerId) => {
    const allHistory = rosterHelpers.getAllTeamHistory();
    return allHistory[playerId] || [];
  },

  // Add a team history entry
  addTeamHistoryEntry: (playerId, teamId, teamName, action, userId, userName) => {
    const allHistory = rosterHelpers.getAllTeamHistory();

    if (!allHistory[playerId]) {
      allHistory[playerId] = [];
    }

    const now = new Date().toISOString();

    // If action is leaving (removed, transferred_out), update the previous entry's leftAt
    if (action === 'removed' || action === 'transferred_out') {
      const lastEntry = allHistory[playerId].find(
        e => e.teamId === teamId && !e.leftAt
      );
      if (lastEntry) {
        lastEntry.leftAt = now;
        lastEntry.leftAction = action;
      }
    }

    // Add new entry for joining actions
    if (action === 'added' || action === 'transferred_in' || action === 'restored') {
      allHistory[playerId].push({
        teamId,
        teamName,
        joinedAt: now,
        leftAt: null,
        action,
        actionBy: userId,
        actionByName: userName,
      });
    }

    rosterHelpers.setAllTeamHistory(allHistory);
  },

  // Initialize team history for a player when first added
  initializeTeamHistory: (playerId, teamId, teamName, userId, userName) => {
    const allHistory = rosterHelpers.getAllTeamHistory();

    if (!allHistory[playerId]) {
      allHistory[playerId] = [{
        teamId,
        teamName,
        joinedAt: new Date().toISOString(),
        leftAt: null,
        action: 'added',
        actionBy: userId,
        actionByName: userName,
      }];
      rosterHelpers.setAllTeamHistory(allHistory);
    }
  },

  // Check if re-adding a player would conflict (removed within 6 months)
  checkReaddConflict: (playerName, teamId) => {
    const removals = rosterHelpers.getPendingRemovals();
    const sixMonthsAgo = new Date(Date.now() - 6 * 30 * 24 * 60 * 60 * 1000).toISOString();

    // Check confirmed removals within 6 months
    const recentRemoval = removals.find(r =>
      r.teamId === teamId &&
      r.playerName?.toLowerCase() === playerName?.toLowerCase() &&
      r.status === 'confirmed' &&
      r.confirmedAt > sixMonthsAgo
    );

    if (recentRemoval) {
      return {
        removedAt: recentRemoval.confirmedAt,
        removedBy: recentRemoval.requestedByName,
        confirmedBy: recentRemoval.confirmedByName,
      };
    }

    return null;
  },

  // Get pending removal for a specific player
  getPendingRemovalForPlayer: (playerId) => {
    const removals = rosterHelpers.getPendingRemovals();
    return removals.find(r => r.playerId === playerId && (r.status === 'pending' || r.status === 'conflict'));
  },

  // Clean up expired pending removals (auto-cancel after 7 days)
  cleanupExpiredRemovals: () => {
    const removals = rosterHelpers.getPendingRemovals();
    const players = storage.getPlayers();
    const now = new Date().toISOString();

    const expiredRemovals = removals.filter(r => r.status === 'pending' && r.expiresAt < now);

    expiredRemovals.forEach(removal => {
      // Restore player
      const player = players.find(p => p.id === removal.playerId);
      if (player && player.removalStatus === 'pending_removal') {
        player.removalStatus = 'active';
        delete player.removalRequestedBy;
        delete player.removalRequestedByName;
        delete player.removalRequestedAt;
      }
      // Mark removal as expired
      removal.status = 'expired';
    });

    if (expiredRemovals.length > 0) {
      storage.setPlayers(players);
      rosterHelpers.setPendingRemovals(removals);
    }

    return expiredRemovals.length;
  },

  // Restore a hidden player (undo confirmed removal)
  restorePlayer: (playerId, teamId, teamName, userId, userName) => {
    const players = storage.getPlayers();
    const player = players.find(p => p.id === playerId);

    if (!player) {
      return { success: false, error: 'Player not found' };
    }

    if (player.removalStatus !== 'hidden') {
      return { success: false, error: 'Player is not hidden' };
    }

    // Restore the player
    player.removalStatus = 'active';
    delete player.removalRequestedBy;
    delete player.removalRequestedByName;
    delete player.removalRequestedAt;
    delete player.removalConfirmedBy;
    delete player.removalConfirmedByName;
    delete player.removalConfirmedAt;
    storage.setPlayers(players);

    // Add to team history
    rosterHelpers.addTeamHistoryEntry(playerId, teamId, teamName, 'restored', userId, userName);

    return { success: true };
  },
};

// Daily Update helpers (Pro users only - max 2 per day, stores up to 5 per team)
export const dailyUpdateHelpers = {
  // Get today's date string for usage tracking
  getTodayString: () => new Date().toISOString().split('T')[0],

  // Get all daily updates for a specific team (user-specific)
  getUpdatesForTeam: (teamKey) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return [];

    const currentKey = getUserKey(STORAGE_KEYS.DAILY_UPDATES);
    const allUpdates = JSON.parse(localStorage.getItem(currentKey) || '{}');
    return allUpdates[teamKey] || [];
  },

  // Get all daily updates across all teams
  getAllUpdates: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return {};

    const currentKey = getUserKey(STORAGE_KEYS.DAILY_UPDATES);
    return JSON.parse(localStorage.getItem(currentKey) || '{}');
  },

  // Save a daily update for a team (max 5 stored, oldest removed)
  saveUpdate: (teamKey, teamName, teamAgeGroup, teamLeague, updateContent) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return { success: false, error: 'Must be logged in' };

    const currentKey = getUserKey(STORAGE_KEYS.DAILY_UPDATES);
    const allUpdates = JSON.parse(localStorage.getItem(currentKey) || '{}');

    if (!allUpdates[teamKey]) {
      allUpdates[teamKey] = [];
    }

    const newUpdate = {
      id: `update_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      teamKey,
      teamName,
      teamAgeGroup,
      teamLeague,
      content: updateContent,
      generatedAt: new Date().toISOString(),
    };

    // Add to beginning (newest first)
    allUpdates[teamKey].unshift(newUpdate);

    // Keep only the 5 most recent updates
    if (allUpdates[teamKey].length > 5) {
      allUpdates[teamKey] = allUpdates[teamKey].slice(0, 5);
    }

    localStorage.setItem(currentKey, JSON.stringify(allUpdates));

    return { success: true, update: newUpdate };
  },

  // Get daily usage (how many teams have had updates generated today)
  getDailyUsage: () => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return { teamsUsedToday: [], count: 0 };

    const currentKey = getUserKey(STORAGE_KEYS.DAILY_UPDATE_USAGE);
    const usage = JSON.parse(localStorage.getItem(currentKey) || '{}');
    const today = dailyUpdateHelpers.getTodayString();

    if (!usage[today]) {
      return { teamsUsedToday: [], count: 0 };
    }

    return { teamsUsedToday: usage[today], count: usage[today].length };
  },

  // Record that a team had an update generated today
  recordUsage: (teamKey) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return;

    const currentKey = getUserKey(STORAGE_KEYS.DAILY_UPDATE_USAGE);
    const usage = JSON.parse(localStorage.getItem(currentKey) || '{}');
    const today = dailyUpdateHelpers.getTodayString();

    if (!usage[today]) {
      usage[today] = [];
    }

    if (!usage[today].includes(teamKey)) {
      usage[today].push(teamKey);
    }

    // Clean up old dates (keep only last 7 days)
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const cutoff = sevenDaysAgo.toISOString().split('T')[0];

    Object.keys(usage).forEach(date => {
      if (date < cutoff) {
        delete usage[date];
      }
    });

    localStorage.setItem(currentKey, JSON.stringify(usage));
  },

  // Check if user can generate update for a team today
  // All logged-in users get unlimited updates
  canGenerateUpdate: (teamKey) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') {
      return { allowed: false, reason: 'Must be logged in' };
    }

    // All logged-in users get unlimited updates
    return { allowed: true, unlimited: true };
  },

  // Check if team already has update generated today
  hasUpdateToday: (teamKey) => {
    const { teamsUsedToday } = dailyUpdateHelpers.getDailyUsage();
    return teamsUsedToday.includes(teamKey);
  },

  // Get the most recent update for a team
  getLatestUpdate: (teamKey) => {
    const updates = dailyUpdateHelpers.getUpdatesForTeam(teamKey);
    return updates.length > 0 ? updates[0] : null;
  },

  // Delete a specific update
  deleteUpdate: (teamKey, updateId) => {
    const user = getCurrentUser();
    if (!user || user.accountType === 'guest') return false;

    const currentKey = getUserKey(STORAGE_KEYS.DAILY_UPDATES);
    const allUpdates = JSON.parse(localStorage.getItem(currentKey) || '{}');

    if (!allUpdates[teamKey]) return false;

    allUpdates[teamKey] = allUpdates[teamKey].filter(u => u.id !== updateId);

    if (allUpdates[teamKey].length === 0) {
      delete allUpdates[teamKey];
    }

    localStorage.setItem(currentKey, JSON.stringify(allUpdates));
    return true;
  },

  // Get all teams with updates (for My Teams section)
  getTeamsWithUpdates: () => {
    const allUpdates = dailyUpdateHelpers.getAllUpdates();
    return Object.keys(allUpdates).map(teamKey => {
      const updates = allUpdates[teamKey];
      const latest = updates[0];
      return {
        teamKey,
        teamName: latest?.teamName,
        teamAgeGroup: latest?.teamAgeGroup,
        teamLeague: latest?.teamLeague,
        updateCount: updates.length,
        latestUpdate: latest,
      };
    });
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
  rosterHelpers,
  dailyUpdateHelpers,
};
