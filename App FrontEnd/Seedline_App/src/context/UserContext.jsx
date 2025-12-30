import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { storage } from '../data/sampleData';
import { firebaseSignOut, onFirebaseAuthStateChanged } from '../config/firebase';
import { api } from '../services/api';

// API Base URL - set to empty for now (backend features disabled in hosted version)
// Player claiming features require the local admin server
const API_BASE = '';

// Admin server API for account type lookup (local development only)
// Set VITE_ADMIN_API in .env for local dev, leave empty for production
const ADMIN_API = import.meta.env.VITE_ADMIN_API || '';

// Activity tracking enabled flag - temporarily disabled for performance testing
const ACTIVITY_TRACKING = false; // import.meta.env.VITE_ACTIVITY_TRACKING !== 'false';

// Account types
export const ACCOUNT_TYPES = {
  GUEST: 'guest',
  FREE: 'free',
  PAID: 'paid',
  COACH: 'coach',   // Can bypass removal confirmation for their teams
  ADMIN: 'admin'    // Can bypass removal confirmation for all teams
};

// Claim limits
export const CLAIM_LIMITS = {
  maxTotal: 8,
  maxPerTeam: 3
};

// Feature permissions by account type
export const PERMISSIONS = {
  [ACCOUNT_TYPES.GUEST]: {
    canBrowse: true,
    canSaveMyTeams: false,  // Guests cannot save teams
    canClaimPlayers: false,
    canAwardBadges: false,
    canSubmitScores: false,
    canVoteOnGames: false,
    canAddLinks: false,
    canBypassRemovalConfirmation: false,
    canTransferPlayers: false,
  },
  [ACCOUNT_TYPES.FREE]: {
    canBrowse: true,
    canSaveMyTeams: true,
    canClaimPlayers: false,
    canAwardBadges: false,
    canSubmitScores: false,
    canVoteOnGames: false,
    canAddLinks: false,
    canBypassRemovalConfirmation: false,
    canTransferPlayers: false,
  },
  [ACCOUNT_TYPES.PAID]: {
    canBrowse: true,
    canSaveMyTeams: true,
    canClaimPlayers: true,
    canAwardBadges: true,
    canSubmitScores: true,
    canVoteOnGames: true,
    canAddLinks: true,
    canBypassRemovalConfirmation: false,
    canTransferPlayers: true,
  },
  [ACCOUNT_TYPES.COACH]: {
    canBrowse: true,
    canSaveMyTeams: true,
    canClaimPlayers: true,
    canAwardBadges: true,
    canSubmitScores: true,
    canVoteOnGames: true,
    canAddLinks: true,
    canBypassRemovalConfirmation: true,  // For their teams only (checked separately)
    canTransferPlayers: true,
  },
  [ACCOUNT_TYPES.ADMIN]: {
    canBrowse: true,
    canSaveMyTeams: true,
    canClaimPlayers: true,
    canAwardBadges: true,
    canSubmitScores: true,
    canVoteOnGames: true,
    canAddLinks: true,
    canBypassRemovalConfirmation: true,  // For all teams
    canTransferPlayers: true,
  }
};

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [userDataReady, setUserDataReady] = useState(false); // True once user data has fully loaded
  const [claimedPlayers, setClaimedPlayers] = useState([]);
  const [claimLimits, setClaimLimits] = useState({ total: 0, maxTotal: CLAIM_LIMITS.maxTotal, teamCounts: {}, maxPerTeam: CLAIM_LIMITS.maxPerTeam });
  const [claimsLoading, setClaimsLoading] = useState(false);

  // Initialize activity tracking session on mount
  useEffect(() => {
    if (ACTIVITY_TRACKING) {
      api.initSession().then(() => {
        console.log('[Activity] Session initialized');
      }).catch(err => {
        console.warn('[Activity] Session init failed:', err);
      });
    }
  }, []);

  // Listen for Firebase auth state changes and sync with API
  useEffect(() => {
    if (typeof onFirebaseAuthStateChanged !== 'function') {
      return; // Firebase not configured
    }

    const unsubscribe = onFirebaseAuthStateChanged(async (firebaseUser) => {
      if (firebaseUser) {
        try {
          // Get fresh token and set on API client
          const token = await firebaseUser.getIdToken();
          api.setAuthToken(token);

          // Update session with authenticated user
          if (ACTIVITY_TRACKING) {
            await api.updateSessionUser();
          }

          // Set up token refresh (every 55 minutes)
          const refreshInterval = setInterval(async () => {
            try {
              const newToken = await firebaseUser.getIdToken(true);
              api.setAuthToken(newToken);
            } catch (err) {
              console.warn('[Auth] Token refresh failed:', err);
            }
          }, 55 * 60 * 1000);

          return () => clearInterval(refreshInterval);
        } catch (err) {
          console.warn('[Auth] Token setup failed:', err);
        }
      } else {
        api.setAuthToken(null);
      }
    });

    return () => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, []);

  useEffect(() => {
    // Load user from storage on mount (not for guests)
    const savedUser = storage.getUser();
    if (savedUser && savedUser.accountType !== ACCOUNT_TYPES.GUEST) {
      // Ensure user has a stable userId (for data persistence)
      const userWithId = storage.ensureUserId() || savedUser;

      // Migrate any orphaned data from old random userId keys
      // This recovers data that was "lost" due to the old bug where each login generated a new userId
      try {
        storage.migrateOrphanedData();
      } catch (e) {
        console.warn('[Migration] Failed to migrate orphaned data:', e);
      }

      // Refresh account type from admin server if user has email and API is configured
      if (userWithId.email && ADMIN_API) {
        // Add 3-second timeout to prevent slow app loads if admin server is down
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        fetch(`${ADMIN_API}/user/lookup?email=${encodeURIComponent(userWithId.email)}`, {
          signal: controller.signal
        })
          .then(res => {
            clearTimeout(timeoutId);
            return res.ok ? res.json() : null;
          })
          .then(data => {
            if (data?.found) {
              const typeMap = {
                'pro': ACCOUNT_TYPES.PAID,
                'paid': ACCOUNT_TYPES.PAID,
                'admin': ACCOUNT_TYPES.ADMIN,
                'coach': ACCOUNT_TYPES.COACH,
                'free': ACCOUNT_TYPES.FREE
              };
              const serverAccountType = typeMap[data.account_type] || ACCOUNT_TYPES.FREE;
              if (serverAccountType !== userWithId.accountType) {
                console.log(`Refreshed account type: ${userWithId.accountType} -> ${serverAccountType}`);
                const updatedUser = { ...userWithId, accountType: serverAccountType };
                storage.setUser(updatedUser);
                setUser(updatedUser);
                setUserDataReady(true);
                return;
              }
            }
            setUser(userWithId);
            setUserDataReady(true);
          })
          .catch(() => {
            clearTimeout(timeoutId);
            // Admin server not available or timed out, use cached user
            setUser(userWithId);
            setUserDataReady(true);
          });
      } else {
        setUser(userWithId);
        setUserDataReady(true);
      }
    } else {
      // No saved user or guest - mark data as ready immediately
      setUserDataReady(true);
    }
  }, []);

  // Load claimed players when user changes
  useEffect(() => {
    if (user?.id && user.accountType === ACCOUNT_TYPES.PAID) {
      loadClaimedPlayers();
    } else {
      setClaimedPlayers([]);
      setClaimLimits({ total: 0, maxTotal: CLAIM_LIMITS.maxTotal, teamCounts: {}, maxPerTeam: CLAIM_LIMITS.maxPerTeam });
    }
  }, [user?.id, user?.accountType]);

  const login = (userData) => {
    // Clear any guest data first
    storage.clearGuestData();

    // Add stable userId for non-guest users if not already present
    // Prefer Firebase UID (userData.id) for userId to ensure consistency
    let userToSave = userData;
    if (userData.accountType !== ACCOUNT_TYPES.GUEST && !userData.userId) {
      // Use Firebase UID as userId if available, otherwise generate one
      userToSave = { ...userData, userId: userData.id || storage.generateUserId() };
    }

    // Save user to storage (for all users so getCurrentUser works)
    storage.setUser(userToSave);

    // Migrate any orphaned data from old random userId keys to Firebase UID-based keys
    // This recovers data that was "lost" due to the bug where each login generated a new userId
    if (userData.accountType !== ACCOUNT_TYPES.GUEST) {
      try {
        storage.migrateOrphanedData();
      } catch (e) {
        console.warn('[Migration] Failed to migrate orphaned data:', e);
      }
    }

    setUser(userToSave);
  };

  const logout = async () => {
    try {
      await firebaseSignOut();
    } catch (error) {
      console.error('Firebase sign out error:', error);
    }
    storage.clearUser();
    storage.clearGuestData();
    setUser(null);
  };

  const updateUser = (updates) => {
    const updatedUser = { ...user, ...updates };
    if (updatedUser.accountType !== ACCOUNT_TYPES.GUEST) {
      storage.setUser(updatedUser);
    }
    setUser(updatedUser);
  };

  // Get permissions for current user
  const getPermissions = () => {
    if (!user) return PERMISSIONS[ACCOUNT_TYPES.GUEST];
    return PERMISSIONS[user.accountType] || PERMISSIONS[ACCOUNT_TYPES.GUEST];
  };

  // Check if user can perform a specific action
  const canPerform = (action) => {
    const perms = getPermissions();
    return perms[action] || false;
  };

  // Check if user is admin or coach
  const isAdminOrCoach = () => {
    if (!user) return false;
    return user.accountType === ACCOUNT_TYPES.ADMIN || user.accountType === ACCOUNT_TYPES.COACH;
  };

  // Check if user can bypass removal confirmation for a specific team
  // Admins can bypass for all teams, coaches only for their assigned teams
  const canBypassConfirmation = (teamId = null) => {
    if (!user) return false;

    // Admins can bypass for all teams
    if (user.accountType === ACCOUNT_TYPES.ADMIN) {
      return true;
    }

    // Coaches can only bypass for their assigned teams
    if (user.accountType === ACCOUNT_TYPES.COACH) {
      // Check if coach is assigned to this team
      const coachTeamIds = user.coachTeamIds || [];
      if (teamId === null) {
        // No team specified, return true if they have any teams
        return coachTeamIds.length > 0;
      }
      return coachTeamIds.includes(teamId);
    }

    return false;
  };

  // Get My Teams (returns empty for guests)
  const getMyTeams = useCallback(() => {
    if (!user || user.accountType === ACCOUNT_TYPES.GUEST) return [];
    return storage.getMyTeams();
  }, [user]);

  // Save My Teams (does nothing for guests)
  const saveMyTeams = (teams) => {
    if (!user || user.accountType === ACCOUNT_TYPES.GUEST) return false;
    storage.setMyTeams(teams);
    return true;
  };

  // Helper to create stable team key (survives JSON regeneration)
  const getTeamKey = (team) => {
    return `${team.name?.toLowerCase() || ''}_${team.ageGroup?.toLowerCase() || ''}`;
  };

  // Add a team to My Teams
  const addToMyTeams = (team) => {
    if (!canPerform('canSaveMyTeams')) return false;
    const current = getMyTeams();
    if (current.length >= 5) return false;
    
    // Check for duplicate using stable key (name + ageGroup)
    const teamKey = getTeamKey(team);
    if (current.some(t => getTeamKey(t) === teamKey)) return false;
    
    const teamData = {
      id: team.id,
      name: team.name,
      club: team.club,
      ageGroup: team.ageGroup,
      league: team.league,
      state: team.state,
      addedAt: new Date().toISOString()
    };
    
    storage.setMyTeams([...current, teamData]);
    return true;
  };

  // Remove a team from My Teams (by stable key OR id for backwards compatibility)
  const removeFromMyTeams = (teamOrId) => {
    if (!canPerform('canSaveMyTeams')) return false;
    const current = getMyTeams();
    
    // Support both object (new way) and id (old way)
    if (typeof teamOrId === 'object') {
      const keyToRemove = getTeamKey(teamOrId);
      storage.setMyTeams(current.filter(t => getTeamKey(t) !== keyToRemove));
    } else {
      // Legacy: remove by ID
      storage.setMyTeams(current.filter(t => t.id !== teamOrId));
    }
    return true;
  };

  // Check if a team is in My Teams (using stable key)
  const isInMyTeams = (team) => {
    const myTeams = getMyTeams();

    // Support both object (new way) and id (old way)
    if (typeof team === 'object' && team !== null) {
      const teamKey = getTeamKey(team);
      return myTeams.some(t => getTeamKey(t) === teamKey);
    } else {
      // Legacy: check by ID
      return myTeams.some(t => t.id === team);
    }
  };

  // ==================== FOLLOWED TEAMS ====================

  // Get Followed Teams (returns empty for guests)
  const getFollowedTeams = () => {
    if (!user || user.accountType === ACCOUNT_TYPES.GUEST) return [];
    return storage.getFollowedTeams();
  };

  // Follow a team (no limit)
  const followTeam = (team) => {
    if (!user || user.accountType === ACCOUNT_TYPES.GUEST) return false;
    const current = getFollowedTeams();

    // Check for duplicate using stable key
    const teamKey = getTeamKey(team);
    if (current.some(t => getTeamKey(t) === teamKey)) return false;

    const teamData = {
      id: team.id,
      name: team.name,
      club: team.club,
      ageGroup: team.ageGroup,
      league: team.league,
      state: team.state,
      followedAt: new Date().toISOString()
    };

    storage.setFollowedTeams([...current, teamData]);
    return true;
  };

  // Unfollow a team
  const unfollowTeam = (teamOrId) => {
    if (!user || user.accountType === ACCOUNT_TYPES.GUEST) return false;
    const current = getFollowedTeams();

    if (typeof teamOrId === 'object') {
      const keyToRemove = getTeamKey(teamOrId);
      storage.setFollowedTeams(current.filter(t => getTeamKey(t) !== keyToRemove));
    } else {
      storage.setFollowedTeams(current.filter(t => t.id !== teamOrId));
    }
    return true;
  };

  // Check if following a team
  const isFollowing = (team) => {
    const followed = getFollowedTeams();

    if (typeof team === 'object' && team !== null) {
      const teamKey = getTeamKey(team);
      return followed.some(t => getTeamKey(t) === teamKey);
    } else {
      return followed.some(t => t.id === team);
    }
  };

  // ==================== PLAYER CLAIMING ====================

  // Load claimed players from API
  const loadClaimedPlayers = useCallback(async () => {
    if (!user?.id) return;

    // Skip if no backend configured
    if (!API_BASE) {
      console.log('Player claiming requires local backend server');
      return;
    }

    setClaimsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/claims?user_id=${user.id}`);
      const data = await response.json();

      if (data.claims) {
        setClaimedPlayers(data.claims);
        setClaimLimits({
          total: data.total || 0,
          maxTotal: data.max_total || CLAIM_LIMITS.maxTotal,
          teamCounts: data.team_counts || {},
          maxPerTeam: data.max_per_team || CLAIM_LIMITS.maxPerTeam
        });
      }
    } catch (error) {
      console.error('Error loading claimed players:', error);
    } finally {
      setClaimsLoading(false);
    }
  }, [user?.id]);

  // Check if user can claim more players
  const canClaimMore = (teamId = null) => {
    if (!canPerform('canClaimPlayers')) {
      return { allowed: false, reason: 'Pro account required' };
    }

    if (claimLimits.total >= claimLimits.maxTotal) {
      return { allowed: false, reason: `Maximum ${claimLimits.maxTotal} players claimed` };
    }

    if (teamId) {
      const teamCount = claimLimits.teamCounts[teamId] || 0;
      if (teamCount >= claimLimits.maxPerTeam) {
        return { allowed: false, reason: `Maximum ${claimLimits.maxPerTeam} players per team` };
      }
    }

    return { allowed: true };
  };

  // Check if a specific player is claimed by current user
  const isClaimedByMe = (playerId) => {
    return claimedPlayers.some(c => c.player_id === playerId);
  };

  // Get claim info for a player owned by current user
  const getMyClaimForPlayer = (playerId) => {
    return claimedPlayers.find(c => c.player_id === playerId);
  };

  // Claim an existing player
  const claimPlayer = async (playerId, teamId) => {
    if (!user?.id) return { success: false, error: 'Not logged in' };
    if (!API_BASE) return { success: false, error: 'Player claiming not available in web version' };

    const canClaim = canClaimMore(teamId);
    if (!canClaim.allowed) {
      return { success: false, error: canClaim.reason };
    }

    try {
      const response = await fetch(`${API_BASE}/claims`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          player_id: playerId,
          team_id: teamId
        })
      });

      const data = await response.json();

      if (data.success) {
        await loadClaimedPlayers(); // Refresh claims
      }

      return data;
    } catch (error) {
      console.error('Error claiming player:', error);
      return { success: false, error: error.message };
    }
  };

  // Create and claim a new player
  const createAndClaimPlayer = async (playerData, teamId) => {
    if (!user?.id) return { success: false, error: 'Not logged in' };
    if (!API_BASE) return { success: false, error: 'Player claiming not available in web version' };

    const canClaim = canClaimMore(teamId);
    if (!canClaim.allowed) {
      return { success: false, error: canClaim.reason };
    }

    try {
      const response = await fetch(`${API_BASE}/claims`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          team_id: teamId,
          new_player: playerData
        })
      });

      const data = await response.json();

      if (data.success) {
        await loadClaimedPlayers();
      }

      return data;
    } catch (error) {
      console.error('Error creating player:', error);
      return { success: false, error: error.message };
    }
  };

  // Release a claim
  const releasePlayer = async (claimId) => {
    if (!user?.id) return { success: false, error: 'Not logged in' };
    if (!API_BASE) return { success: false, error: 'Not available in web version' };

    try {
      const response = await fetch(`${API_BASE}/claims/${claimId}?user_id=${user.id}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (data.success) {
        await loadClaimedPlayers();
      }

      return data;
    } catch (error) {
      console.error('Error releasing player:', error);
      return { success: false, error: error.message };
    }
  };

  // Update player profile
  const updatePlayerProfile = async (claimId, updates) => {
    if (!user?.id) return { success: false, error: 'Not logged in' };
    if (!API_BASE) return { success: false, error: 'Not available in web version' };

    try {
      const response = await fetch(`${API_BASE}/claims/${claimId}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          ...updates
        })
      });

      const data = await response.json();

      if (data.success) {
        await loadClaimedPlayers();
      }

      return data;
    } catch (error) {
      console.error('Error updating profile:', error);
      return { success: false, error: error.message };
    }
  };

  // Switch player's team
  const switchPlayerTeam = async (claimId, newTeamId) => {
    if (!user?.id) return { success: false, error: 'Not logged in' };
    if (!API_BASE) return { success: false, error: 'Not available in web version' };

    try {
      const response = await fetch(`${API_BASE}/claims/${claimId}/team`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          team_id: newTeamId
        })
      });

      const data = await response.json();

      if (data.success) {
        await loadClaimedPlayers();
      }

      return data;
    } catch (error) {
      console.error('Error switching team:', error);
      return { success: false, error: error.message };
    }
  };

  // ==================== CLAIM CHALLENGES ====================

  // Challenge someone else's claim
  const challengeClaim = async (claimId, reason, evidenceUrl = null) => {
    if (!user?.id) return { success: false, error: 'Not logged in' };
    if (!API_BASE) return { success: false, error: 'Not available in web version' };

    try {
      const response = await fetch(`${API_BASE}/challenges`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          claim_id: claimId,
          reason: reason,
          evidence_url: evidenceUrl
        })
      });

      return await response.json();
    } catch (error) {
      console.error('Error challenging claim:', error);
      return { success: false, error: error.message };
    }
  };

  // Get challenges submitted by current user
  const getMyChallenges = async () => {
    if (!user?.id) return { challenges: [] };
    if (!API_BASE) return { challenges: [], error: 'Not available in web version' };

    try {
      const response = await fetch(`${API_BASE}/user/challenges?user_id=${user.id}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching challenges:', error);
      return { challenges: [], error: error.message };
    }
  };

  // Check claim status for a player (is it claimed by someone?)
  const getPlayerClaimStatus = async (playerId) => {
    if (!API_BASE) return { claimed: false, error: 'Not available in web version' };
    try {
      const response = await fetch(`${API_BASE}/players/${playerId}/claim-status`);
      return await response.json();
    } catch (error) {
      console.error('Error checking claim status:', error);
      return { claimed: false, error: error.message };
    }
  };

  const value = {
    user,
    userDataReady, // True once user data has fully loaded from storage
    login,
    logout,
    updateUser,
    getPermissions,
    canPerform,
    getMyTeams,
    saveMyTeams,
    addToMyTeams,
    removeFromMyTeams,
    isInMyTeams,
    // Followed teams
    getFollowedTeams,
    followTeam,
    unfollowTeam,
    isFollowing,
    isGuest: user?.accountType === ACCOUNT_TYPES.GUEST,
    isFree: user?.accountType === ACCOUNT_TYPES.FREE,
    isPaid: user?.accountType === ACCOUNT_TYPES.PAID,
    isCoach: user?.accountType === ACCOUNT_TYPES.COACH,
    isAdmin: user?.accountType === ACCOUNT_TYPES.ADMIN,
    isAdminOrCoach,
    canBypassConfirmation,
    // Player claiming
    claimedPlayers,
    claimLimits,
    claimsLoading,
    loadClaimedPlayers,
    canClaimMore,
    isClaimedByMe,
    getMyClaimForPlayer,
    claimPlayer,
    createAndClaimPlayer,
    releasePlayer,
    updatePlayerProfile,
    switchPlayerTeam,
    // Challenges
    challengeClaim,
    getMyChallenges,
    getPlayerClaimStatus,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}

export default UserContext;
