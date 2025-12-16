import { createContext, useContext, useState, useEffect } from 'react';
import { storage } from '../data/sampleData';

// Account types
export const ACCOUNT_TYPES = {
  GUEST: 'guest',
  FREE: 'free',
  PAID: 'paid'
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
  },
  [ACCOUNT_TYPES.FREE]: {
    canBrowse: true,
    canSaveMyTeams: true,
    canClaimPlayers: false,
    canAwardBadges: false,
    canSubmitScores: false,
    canVoteOnGames: false,
    canAddLinks: false,
  },
  [ACCOUNT_TYPES.PAID]: {
    canBrowse: true,
    canSaveMyTeams: true,
    canClaimPlayers: true,
    canAwardBadges: true,
    canSubmitScores: true,
    canVoteOnGames: true,
    canAddLinks: true,
  }
};

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Load user from storage on mount (not for guests)
    const savedUser = storage.getUser();
    if (savedUser && savedUser.accountType !== ACCOUNT_TYPES.GUEST) {
      setUser(savedUser);
    }
  }, []);

  const login = (userData) => {
    // Clear any guest data first
    storage.clearGuestData();
    
    // Save user to storage (not for guests)
    if (userData.accountType !== ACCOUNT_TYPES.GUEST) {
      storage.setUser(userData);
    } else {
      // For guests, still save to storage so getCurrentUser works
      // but mark as guest so user-specific data returns empty
      storage.setUser(userData);
    }
    setUser(userData);
  };

  const logout = () => {
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

  // Get My Teams (returns empty for guests)
  const getMyTeams = () => {
    if (!user || user.accountType === ACCOUNT_TYPES.GUEST) return [];
    return storage.getMyTeams();
  };

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

  const value = {
    user,
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
    isGuest: user?.accountType === ACCOUNT_TYPES.GUEST,
    isFree: user?.accountType === ACCOUNT_TYPES.FREE,
    isPaid: user?.accountType === ACCOUNT_TYPES.PAID,
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
