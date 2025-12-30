import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import { storage, BADGE_TYPES, rosterHelpers, findTeamInRankings } from '../data/sampleData';
import LinkManager from './LinkManager';
import SubmitGameForm from './SubmitGameForm';
import PendingGames from './PendingGames';
import RankingsHistoryChart from './RankingsHistoryChart';
import { useUser } from '../context/UserContext';
import { PlayersIcon, BadgesIcon } from './PaperIcons';
import DailyUpdate from './DailyUpdate';
import { useClubLogo } from '../data/useClubLogo';
import TeamRatingForm from './TeamRatingForm';
import TeamReviews from './TeamReviews';
import { isElevenUpBrand } from '../config/brand';
import {
  predictGame,
  rankGamesByPerformance,
  getPredictionColor,
  getPerformanceColor,
  findOpponentInData
} from '../data/scorePredictions';

// Parse date string robustly - handles various formats including truncated years
const parseDate = (dateStr) => {
  if (!dateStr) return null;
  if (dateStr instanceof Date) return dateStr;
  const str = String(dateStr).trim();
  // Try ISO format first (YYYY-MM-DD)
  if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
    const d = new Date(str + 'T00:00:00');
    if (!isNaN(d.getTime())) return d;
  }
  // Handle "Mon DD, YYYY" format and truncated years like "Dec 8, 202"
  const monthMatch = str.match(/^([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{2,4})/);
  if (monthMatch) {
    const [, month, day, yearStr] = monthMatch;
    let year = parseInt(yearStr, 10);
    if (year < 100) year = 2000 + year; // 25 -> 2025
    else if (year >= 200 && year < 1000) year = year * 10; // 202 -> 2020, 203 -> 2030
    // Sanity check: if year is still unreasonable, default to current year
    if (year < 2020 || year > 2030) year = new Date().getFullYear();
    const d = new Date(`${month} ${day}, ${year}`);
    if (!isNaN(d.getTime())) return d;
  }
  const d = new Date(str);
  return !isNaN(d.getTime()) ? d : null;
};

// Convert date to ISO format for comparisons
const toISODateString = (dateStr) => {
  const d = parseDate(dateStr);
  return d ? d.toISOString().split('T')[0] : null;
};

// Helper function for league badge colors
function getLeagueBadgeStyle(league) {
  const styles = {
    'ECNL': { background: '#e3f2fd', color: '#1976d2' },
    'GA': { background: '#f3e5f5', color: '#7b1fa2' },
    'ECNL-RL': { background: '#ffebee', color: '#c62828' },
    'ASPIRE': { background: '#e8f5e9', color: '#2e7d32' },
    'NPL': { background: '#fff3e0', color: '#e65100' },
    'MLS NEXT HD': { background: '#006064', color: '#ffffff' },  // Dark Teal (MLS pro clubs - Homegrown Division)
    'MLS NEXT AD': { background: '#e0f7fa', color: '#00838f' },  // Light Teal (Academy Division)
  };
  return styles[league] || { background: '#f5f5f5', color: '#666' };
}

function TeamProfile() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const { teamsData, gamesData, playersData, rankingsHistory, isLoading } = useRankingsData();
  const { user, canPerform, addToMyTeams, removeFromMyTeams, isInMyTeams, getMyTeams, canBypassConfirmation, isPaid } = useUser();
  const canSubmitScores = canPerform('canSubmitScores');
  const canSaveMyTeams = canPerform('canSaveMyTeams');
  const canClaimPlayers = canPerform('canClaimPlayers');

  const [activeTab, setActiveTab] = useState('games');
  const [showAddPlayerModal, setShowAddPlayerModal] = useState(false);
  const [newPlayer, setNewPlayer] = useState({
    name: '',
    position: '',
    jerseyNumber: '',
    gradYear: ''
  });
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [pendingGamesKey, setPendingGamesKey] = useState(0);
  const [myTeamsRefreshKey, setMyTeamsRefreshKey] = useState(0);
  const [showPredictions, setShowPredictions] = useState(false);
  const [showUpcoming, setShowUpcoming] = useState(true);
  const [showPredictPanel, setShowPredictPanel] = useState(false);
  const [customOpponentSearch, setCustomOpponentSearch] = useState('');
  const [selectedCustomOpponent, setSelectedCustomOpponent] = useState(null);
  const [showRosterDetails, setShowRosterDetails] = useState(true);
  const [rosterSortField, setRosterSortField] = useState('name');
  const [rosterSortDirection, setRosterSortDirection] = useState('asc');
  const [showRemoveMode, setShowRemoveMode] = useState(false);
  const [rosterRefreshKey, setRosterRefreshKey] = useState(0);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [playerToTransfer, setPlayerToTransfer] = useState(null);
  const [transferSearch, setTransferSearch] = useState('');
  const [showRatingForm, setShowRatingForm] = useState(false);
  const [reviewsRefreshKey, setReviewsRefreshKey] = useState(0);
  const [selectedTransferTeam, setSelectedTransferTeam] = useState(null);

  // Track mobile view for layout adjustments
  const [isMobile, setIsMobile] = useState(window.innerWidth < 500);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 500);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Callback to refresh pending games after submission
  const handleGameSubmitted = useCallback(() => {
    setShowSubmitForm(false);
    setPendingGamesKey(prev => prev + 1);
  }, []);

  // Find the team - use ref to maintain stable reference
  // This prevents cascading recalculations when teamsData updates but the team itself hasn't changed
  const teamRef = useRef(null);
  const team = useMemo(() => {
    const found = teamsData.find(t => t.id === parseInt(teamId));
    // Only update ref if we found a team and it's different from current
    if (found) {
      // Use the existing ref if it's the same team (same id)
      if (teamRef.current && teamRef.current.id === found.id) {
        // Update the ref with new data but return same reference structure
        // to prevent unnecessary downstream recalculations
        Object.assign(teamRef.current, found);
        return teamRef.current;
      }
      teamRef.current = found;
    }
    return found;
  }, [teamsData, teamId]);

  // Get club logo
  const { logoUrl } = useClubLogo(team?.club || team?.name);

  // Helper to normalize team names for comparison
  // Strips league suffixes and age patterns for matching
  // This allows "Lamorinda SC" (display name) to match "Lamorinda SC 13G" (game name)
  const normalizeTeamName = (name) => {
    if (!name) return '';
    return name.toLowerCase()
      // Remove league suffixes (can appear anywhere, not just end)
      .replace(/\s+(ga|ecnl|ecnl-rl|ecnl rl|aspire|npl|mls next)(?:\s|$)/gi, ' ')
      // Remove age patterns: "13G", "G13", "11B", "B11", etc.
      .replace(/\s+\d{1,2}[gb](?:\s|$)/gi, ' ')  // "13G", "11B"
      .replace(/\s+[gb]\d{1,2}(?:\s|$)/gi, ' ')  // "G13", "B11"
      // Remove birth year patterns: "2013", "2012", "2013G", "2012B"
      .replace(/\s+20\d{2}[gb]?(?:\s|$)/gi, ' ')  // "2013", "2012", "2013G"
      // Remove combo age patterns: "08/07G", "07/06B"
      .replace(/\s+\d{2}\/\d{2}[gb]?(?:\s|$)/gi, ' ')
      // Clean up extra whitespace
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Get games for this team (past and future)
  const teamGames = useMemo(() => {
    if (!team || !gamesData) return { past: [], upcoming: [] };

    const normalizedTeamName = normalizeTeamName(team.name);
    const teamLeague = (team.league || '').toUpperCase();
    const today = new Date().toISOString().split('T')[0];

    // Find all games where this team played (home or away)
    // Must match BOTH team name AND league to avoid cross-league confusion
    const allGames = gamesData.filter(game => {
      const normalizedHome = normalizeTeamName(game.homeTeam);
      const normalizedAway = normalizeTeamName(game.awayTeam);
      const gameLeague = (game.league || '').toUpperCase();

      // Normalize league names for comparison
      const normalizeLeague = (lg) => {
        if (!lg) return '';
        lg = lg.toUpperCase();
        if (lg === 'ECNL-RL' || lg === 'ECNL RL') return 'ECNL-RL';
        if (lg === 'GIRLS ACADEMY') return 'GA';
        // MLS NEXT variants (HD = Homegrown Division, AD = Academy Division)
        if (lg.startsWith('MLS NEXT')) return 'MLS NEXT';
        return lg;
      };

      const normalizedGameLeague = normalizeLeague(gameLeague);
      const normalizedTeamLeague = normalizeLeague(teamLeague);

      // Exact match after normalization
      const homeMatch = normalizedHome === normalizedTeamName;
      const awayMatch = normalizedAway === normalizedTeamName;

      // Must match league too (same team name can exist in different leagues)
      const leagueMatch = normalizedGameLeague === normalizedTeamLeague;

      // Also check age group if available
      const ageMatch = !game.ageGroup || game.ageGroup === team.ageGroup;

      return (homeMatch || awayMatch) && leagueMatch && ageMatch;
    });

    // Sort by date using robust date parsing
    const sortedGames = allGames.sort((a, b) => {
      const dateA = parseDate(a.date);
      const dateB = parseDate(b.date);
      if (!dateA && !dateB) return 0;
      if (!dateA) return 1;
      if (!dateB) return -1;
      return dateB - dateA;
    });

    // Split into past and upcoming using ISO date comparison
    // Upcoming = future date OR scheduled status (even if date comparison fails)
    // Past = past date AND has scores (completed games)
    const past = sortedGames.filter(g => {
      const gameDate = toISODateString(g.date);
      const isPastDate = gameDate && gameDate <= today;
      const hasScores = g.homeScore !== null && g.awayScore !== null;
      return isPastDate && hasScores;
    });

    const upcoming = sortedGames.filter(g => {
      const gameDate = toISODateString(g.date);
      const isFutureDate = gameDate && gameDate > today;
      const isScheduled = g.status === 'scheduled' || (g.homeScore === null || g.awayScore === null);
      return isFutureDate || isScheduled;
    }).reverse(); // Oldest upcoming first

    return { past, upcoming };
  }, [team, gamesData]);

  // Games with predictions and performance rankings
  const rankedGames = useMemo(() => {
    if (!team || !teamGames.past.length) return [];
    return rankGamesByPerformance(teamGames.past, team, teamsData);
  }, [team, teamGames.past, teamsData]);

  // Get prediction for upcoming games
  const upcomingWithPredictions = useMemo(() => {
    if (!team || !teamGames.upcoming.length) return [];

    const normalizedTeamName = normalizeTeamName(team.name);

    return teamGames.upcoming.map(game => {
      const isHome = normalizeTeamName(game.homeTeam) === normalizedTeamName;
      const opponentName = isHome ? game.awayTeam : game.homeTeam;

      // Find opponent using improved matching
      const opponent = findOpponentInData(opponentName, team.ageGroup, teamsData);

      // Get prediction
      const prediction = isHome
        ? predictGame(team, opponent, teamsData)
        : predictGame(opponent, team, teamsData);

      return {
        ...game,
        opponent: opponentName,
        opponentData: opponent,  // Include full opponent data for rank display
        isHome,
        prediction,
        teamWinProb: isHome ? prediction.homeWinProbability : prediction.awayWinProbability,
        teamLossProb: isHome ? prediction.awayWinProbability : prediction.homeWinProbability,
        drawProb: prediction.drawProbability,
        predictedTeamScore: isHome ? prediction.predictedHomeScore : prediction.predictedAwayScore,
        predictedOppScore: isHome ? prediction.predictedAwayScore : prediction.predictedHomeScore
      };
    });
  }, [team, teamGames.upcoming, teamsData]);

  // Get players on this team's roster
  // Includes both database players (matched by teamName) and user-created players (matched by teamId)
  const roster = useMemo(() => {
    if (!team) return [];

    // Get user-created players from localStorage (have teamId)
    const localPlayers = storage.getPlayers();
    const localRoster = localPlayers.filter(p => p.teamId === parseInt(teamId));

    // Get database players that match this team's name, age group, AND league
    // Database players have teamName but not teamId
    const teamNameLower = team.name.toLowerCase();
    const normalizedTeamName = normalizeTeamName(team.name);

    // Normalize league for comparison (handle "ECNL-RL" vs "ECNL RL" differences)
    const normalizeLeague = (league) => (league || '').toLowerCase().replace(/[-\s]/g, '');
    const teamLeagueNormalized = normalizeLeague(team.league);

    // ============================================================================
    // WARNING: DO NOT WEAKEN THE AGE GROUP FILTER BELOW!
    // This bug has been fixed multiple times. Without strict age group matching,
    // teams like "Solar SC G11" end up with 400+ players from ALL age groups
    // because players match on club name alone. The age group check MUST require
    // both player AND team to have age group data, and they MUST match exactly.
    // ============================================================================
    const databaseRoster = (playersData || []).filter(p => {
      if (!p.teamName) return false;

      // REQUIRE age group match - players without age group data should not appear on team pages
      // This prevents hundreds of players from matching based on club name alone
      // DO NOT CHANGE THIS TO OPTIONAL - see warning above
      if (!p.ageGroup || !team.ageGroup || p.ageGroup !== team.ageGroup) {
        return false;
      }

      // Must match league (critical for separating ECNL vs ECNL-RL rosters)
      if (p.league && team.league) {
        const playerLeagueNormalized = normalizeLeague(p.league);
        if (playerLeagueNormalized !== teamLeagueNormalized) {
          return false;
        }
      }

      const playerTeamLower = p.teamName.toLowerCase();
      const normalizedPlayerTeam = normalizeTeamName(p.teamName);

      // Check for exact or normalized match
      if (p.teamName === team.name || normalizedPlayerTeam === normalizedTeamName) {
        return true;
      }

      // Allow substring match since we already verified age group matches
      if (playerTeamLower.length >= 8 && teamNameLower.includes(playerTeamLower)) {
        return true;
      }

      return false;
    });

    // Combine both sources, avoiding duplicates by player id AND name
    // When duplicates exist, prefer the one with a jersey number
    const seenIds = new Set();
    const seenNames = new Map(); // Map of normalized name -> player index in combined array
    const combined = [];

    const normalizeName = (name) => (name || '').toLowerCase().trim();
    const hasJerseyNumber = (p) => !!(p.number || p.jerseyNumber);

    const addPlayer = (player) => {
      const normalizedName = normalizeName(player.name);

      // Check if we already have this exact ID
      if (seenIds.has(player.id)) {
        return;
      }

      // Check if we already have a player with the same name
      if (seenNames.has(normalizedName)) {
        const existingIndex = seenNames.get(normalizedName);
        const existing = combined[existingIndex];

        // Replace if new player has jersey number and existing doesn't
        if (hasJerseyNumber(player) && !hasJerseyNumber(existing)) {
          combined[existingIndex] = player;
          seenIds.add(player.id);
        }
        return;
      }

      // New player - add to combined
      seenIds.add(player.id);
      seenNames.set(normalizedName, combined.length);
      combined.push(player);
    };

    // Add local players first (user-managed take priority)
    for (const player of localRoster) {
      addPlayer(player);
    }

    // Add database players
    for (const player of databaseRoster) {
      addPlayer(player);
    }

    return combined;
  }, [teamId, team, playersData, rosterRefreshKey]);

  // Get all badges for roster players (needed for sorting)
  const badges = storage.getBadges();

  // Sort the roster based on current sort settings
  const sortedRoster = useMemo(() => {
    if (!roster.length) return roster;

    return [...roster].sort((a, b) => {
      let aVal, bVal;

      switch (rosterSortField) {
        case 'name':
          aVal = (a.name || '').toLowerCase();
          bVal = (b.name || '').toLowerCase();
          break;
        case 'position':
          aVal = (a.position || '').toLowerCase();
          bVal = (b.position || '').toLowerCase();
          break;
        case 'number':
          aVal = parseInt(a.number || a.jerseyNumber || '999') || 999;
          bVal = parseInt(b.number || b.jerseyNumber || '999') || 999;
          break;
        case 'badges':
          const aBadges = badges[a.id] || {};
          const bBadges = badges[b.id] || {};
          aVal = Object.values(aBadges).reduce((sum, count) => sum + count, 0);
          bVal = Object.values(bBadges).reduce((sum, count) => sum + count, 0);
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return rosterSortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return rosterSortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [roster, rosterSortField, rosterSortDirection, badges]);

  // Handle roster sort
  const handleRosterSort = (field) => {
    if (rosterSortField === field) {
      setRosterSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setRosterSortField(field);
      setRosterSortDirection('asc');
    }
  };

  // Get sort indicator for roster columns
  const getRosterSortIndicator = (field) => {
    if (rosterSortField !== field) return '';
    return rosterSortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  // Handler to add a player to this team
  const handleAddPlayer = (e) => {
    e.preventDefault();
    if (!team || !newPlayer.name || !newPlayer.position) return;

    // Check for duplicate player with same first and last name on this team
    const normalizeName = (name) => (name || '').toLowerCase().trim();
    const newPlayerNameNormalized = normalizeName(newPlayer.name);

    const duplicatePlayer = roster.find(player => {
      const existingNameNormalized = normalizeName(player.name);
      return existingNameNormalized === newPlayerNameNormalized;
    });

    if (duplicatePlayer) {
      alert(`A player named "${newPlayer.name}" already exists on this team's roster. Please use a different name or edit the existing player.`);
      return;
    }

    // Check for conflict - was this player removed from this team within 6 months?
    const conflict = rosterHelpers.checkReaddConflict(newPlayer.name, team.id);
    if (conflict) {
      const confirmAdd = window.confirm(
        `Warning: A player named "${newPlayer.name}" was removed from this team on ${new Date(conflict.removedAt).toLocaleDateString()}.\n\n` +
        `Removed by: ${conflict.removedBy}\n` +
        `Confirmed by: ${conflict.confirmedBy}\n\n` +
        `If this is the same player, please contact both users to resolve the conflict. ` +
        `Do you still want to add this player?`
      );
      if (!confirmAdd) return;
    }

    const player = {
      id: Date.now(),
      name: newPlayer.name,
      position: newPlayer.position,
      teamId: team.id,
      teamName: team.name,
      club: team.club || team.name,
      ageGroup: team.ageGroup,
      gender: team.ageGroup?.startsWith('G') ? 'Female' : 'Male',
      state: team.state,
      league: team.league,
      number: newPlayer.jerseyNumber || null,
      jerseyNumber: newPlayer.jerseyNumber || null,
      gradYear: newPlayer.gradYear || null,
      removalStatus: 'active'
    };

    const allPlayers = storage.getPlayers();
    const updatedPlayers = [...allPlayers, player];
    storage.setPlayers(updatedPlayers);

    // Initialize team history for this player
    rosterHelpers.initializeTeamHistory(
      player.id,
      team.id,
      team.name,
      user?.userId || user?.id,
      user?.username || 'Unknown'
    );

    setNewPlayer({ name: '', position: '', jerseyNumber: '', gradYear: '' });
    setShowAddPlayerModal(false);
    setRosterRefreshKey(prev => prev + 1);
  };

  // Handler to request player removal (soft delete)
  const handleRemovePlayer = (playerId) => {
    if (!team || !user) return;

    const isAdmin = canBypassConfirmation(team.id);

    if (isAdmin) {
      // Admin/coach can remove immediately
      if (!window.confirm('Remove this player immediately? (Admin action)')) {
        return;
      }
    }

    const result = rosterHelpers.requestRemoval(
      playerId,
      team.id,
      team.name,
      user.userId || user.id,
      user.username || 'Unknown',
      isAdmin
    );

    if (result.success) {
      setRosterRefreshKey(prev => prev + 1);
      if (result.immediate) {
        // Admin removed immediately
      } else {
        // Regular user - now pending confirmation
        alert('Removal requested. Another user must confirm this removal.');
      }
    } else {
      alert(result.error || 'Failed to request removal');
    }
  };

  // Handler to confirm a pending removal (second person)
  const handleConfirmRemoval = (player) => {
    if (!user) return;

    const isAdmin = canBypassConfirmation(team?.id);

    const result = rosterHelpers.confirmRemoval(
      player.id,
      user.userId || user.id,
      user.username || 'Unknown',
      isAdmin
    );

    if (result.success) {
      setRosterRefreshKey(prev => prev + 1);
    } else {
      alert(result.error || 'Failed to confirm removal');
    }
  };

  // Handler to cancel removal / put back player
  const handlePutBack = (player) => {
    if (!user || !team) return;

    const isAdmin = canBypassConfirmation(team.id);

    const result = rosterHelpers.cancelRemoval(
      player.id,
      user.userId || user.id,
      user.username || 'Unknown',
      isAdmin
    );

    if (result.success) {
      setRosterRefreshKey(prev => prev + 1);
      if (result.conflict) {
        alert('Conflict created: You want to keep this player, but someone else wants to remove them. The player will stay on the roster until resolved.');
      }
    } else {
      alert(result.error || 'Failed to restore player');
    }
  };

  // Handler to open transfer modal
  const handleOpenTransfer = (player) => {
    setPlayerToTransfer(player);
    setTransferSearch('');
    setSelectedTransferTeam(null);
    setShowTransferModal(true);
  };

  // Handler to complete transfer
  const handleTransfer = () => {
    if (!playerToTransfer || !selectedTransferTeam || !user || !team) return;

    const result = rosterHelpers.transferPlayer(
      playerToTransfer.id,
      team.id,
      team.name,
      selectedTransferTeam.id,
      selectedTransferTeam.name,
      user.userId || user.id,
      user.username || 'Unknown'
    );

    if (result.success) {
      setRosterRefreshKey(prev => prev + 1);
      setShowTransferModal(false);
      setPlayerToTransfer(null);
      alert(`${playerToTransfer.name} has been transferred to ${selectedTransferTeam.name}`);
    } else {
      alert(result.error || 'Failed to transfer player');
    }
  };

  // Search results for transfer destination team
  const transferTeamResults = useMemo(() => {
    if (!transferSearch || transferSearch.length < 2) return [];
    const searchTerms = transferSearch.toLowerCase().split(/\s+/).filter(t => t.length > 0);
    if (searchTerms.length === 0) return [];

    return teamsData
      .filter(t => {
        if (t.id === team?.id) return false; // Can't transfer to same team
        const searchableText = `${t.name || ''} ${t.club || ''} ${t.ageGroup || ''}`.toLowerCase();
        return searchTerms.every(term => searchableText.includes(term));
      })
      .slice(0, 10);
  }, [transferSearch, teamsData, team]);

  // Find rank within the team's age group and league
  const rankInCategory = useMemo(() => {
    if (!team) return null;
    const sameCategory = teamsData
      .filter(t => t.ageGroup === team.ageGroup && t.league === team.league)
      .sort((a, b) => b.powerScore - a.powerScore);
    return sameCategory.findIndex(t => t.id === team.id) + 1;
  }, [team, teamsData]);

  const totalInCategory = useMemo(() => {
    if (!team) return 0;
    return teamsData.filter(t => t.ageGroup === team.ageGroup && t.league === team.league).length;
  }, [team, teamsData]);

  // Find NATIONAL rank within age group (across ALL leagues) - matches history data
  const nationalRank = useMemo(() => {
    if (!team) return null;
    const sameAgeGroup = teamsData
      .filter(t => t.ageGroup === team.ageGroup)
      .sort((a, b) => (b.powerScore || 0) - (a.powerScore || 0));
    return sameAgeGroup.findIndex(t => t.id === team.id) + 1;
  }, [team, teamsData]);

  const totalInAgeGroup = useMemo(() => {
    if (!team) return 0;
    return teamsData.filter(t => t.ageGroup === team.ageGroup).length;
  }, [team, teamsData]);

  // Find STATE rank within age group (same state only)
  const stateRank = useMemo(() => {
    if (!team || !team.state) return null;
    const sameStateAndAge = teamsData
      .filter(t => t.ageGroup === team.ageGroup && t.state === team.state)
      .sort((a, b) => (b.powerScore || 0) - (a.powerScore || 0));
    return sameStateAndAge.findIndex(t => t.id === team.id) + 1;
  }, [team, teamsData]);

  // Get ranking history for this team
  const teamRankingHistory = useMemo(() => {
    if (!team || !rankingsHistory) return [];
    return rankingsHistory[team.id] || [];
  }, [team, rankingsHistory]);

  // Get myTeams - use storage directly to avoid function reference issues
  // The myTeamsRefreshKey forces recalculation when teams are added/removed
  const myTeamsSnapshot = useMemo(() => {
    if (!user || user.accountType === 'guest') return [];
    return storage.getMyTeams();
  }, [user?.accountType, myTeamsRefreshKey]);

  // Predictions against My Teams
  // CRITICAL: Uses findTeamInRankings() helper which does NOT use ID fallback
  // Team IDs are regenerated when rankings are updated and will match wrong teams if used
  const myTeamsPredictions = useMemo(() => {
    // Guard: need team, loaded teamsData, and myTeams to compute predictions
    if (!team || !teamsData || teamsData.length === 0 || myTeamsSnapshot.length === 0) return [];

    // Helper to create stable team key for self-matching check
    const getTeamKey = (t) => `${t.name?.toLowerCase() || ''}_${t.ageGroup?.toLowerCase() || ''}`;
    const currentTeamKey = getTeamKey(team);

    return myTeamsSnapshot
      .filter(t => getTeamKey(t) !== currentTeamKey) // Don't predict against self
      .map(savedTeam => {
        // Use the central helper function - it matches by name/ageGroup/club only
        const opponentData = findTeamInRankings(savedTeam, teamsData);

        // Skip if we couldn't find full team data in rankings (no match = can't predict)
        if (!opponentData || !opponentData.powerScore) return null;

        // Skip if resolved opponent is the same as current team (prevents self-prediction)
        // This catches cases where saved team name differs but findTeamInRankings resolves to same team
        if (opponentData.id === team.id || getTeamKey(opponentData) === currentTeamKey) return null;

        const prediction = predictGame(team, opponentData, teamsData);
        return {
          opponent: opponentData,
          prediction,
          homeWinProb: prediction.homeWinProbability,
          awayWinProb: prediction.awayWinProbability,
          drawProb: prediction.drawProbability,
          predictedHomeScore: prediction.predictedHomeScore,
          predictedAwayScore: prediction.predictedAwayScore
        };
      })
      .filter(Boolean); // Remove nulls from teams we couldn't match
  }, [team, teamsData, myTeamsSnapshot]);

  // Search results for custom opponent - matches all search terms
  const searchResults = useMemo(() => {
    if (!customOpponentSearch || customOpponentSearch.length < 2) return [];
    // Split search into individual terms and filter out empty strings
    const searchTerms = customOpponentSearch.toLowerCase().split(/\s+/).filter(t => t.length > 0);
    if (searchTerms.length === 0) return [];

    return teamsData
      .filter(t => {
        if (t.id === team?.id) return false;
        // Combine searchable fields
        const searchableText = `${t.name || ''} ${t.club || ''} ${t.ageGroup || ''}`.toLowerCase();
        // All search terms must match somewhere in the combined text
        return searchTerms.every(term => searchableText.includes(term));
      })
      .slice(0, 10);
  }, [customOpponentSearch, teamsData, team]);

  // Custom opponent prediction
  const customPrediction = useMemo(() => {
    if (!team || !selectedCustomOpponent) return null;
    const prediction = predictGame(team, selectedCustomOpponent, teamsData);
    return {
      opponent: selectedCustomOpponent,
      prediction,
      homeWinProb: prediction.homeWinProbability,
      awayWinProb: prediction.awayWinProbability,
      drawProb: prediction.drawProbability,
      predictedHomeScore: prediction.predictedHomeScore,
      predictedAwayScore: prediction.predictedAwayScore
    };
  }, [team, selectedCustomOpponent, teamsData]);

  // Helper to determine if team won/lost/tied a game
  const getGameResult = (game) => {
    const normalizedTeamName = normalizeTeamName(team.name);
    const isHome = normalizeTeamName(game.homeTeam) === normalizedTeamName;
    const teamScore = isHome ? game.homeScore : game.awayScore;
    const oppScore = isHome ? game.awayScore : game.homeScore;

    if (teamScore > oppScore) return 'win';
    if (teamScore < oppScore) return 'loss';
    return 'draw';
  };

  // Format date nicely for display
  const formatDate = (dateStr) => {
    const date = parseDate(dateStr);
    if (!date) return 'Invalid Date';
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">Loading team data...</div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-text">Team not found</div>
          <button
            onClick={() => navigate('/rankings')}
            className="btn btn-primary"
            style={{ marginTop: '1rem' }}
          >
            Back to Rankings
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{
        background: '#ffffff',
        borderRadius: '12px',
        padding: '1rem 1.25rem',
        marginBottom: '0.75rem',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--primary-green)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem'
            }}
          >
            ← Back
          </button>
          <span style={{ fontSize: '0.9rem', color: '#666', fontWeight: '500' }}>
            {team.ageGroup} • {team.league}
          </span>
        </div>
        {/* Team name row with logo */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.5rem' }}>
          {logoUrl && (
            <img
              src={logoUrl}
              alt={`${team.club || team.name} logo`}
              style={{
                width: '75px',
                height: '75px',
                objectFit: 'contain',
                marginTop: '0.25rem'
              }}
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          )}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h1 className="page-title" style={{ marginBottom: '0' }}>{team.name} {team.ageGroup}</h1>
            {/* Rankings inline on desktop only */}
            {!isMobile && (
              team.isRanked === false ? (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginLeft: '1rem' }}>
                  <span style={{
                    padding: '0.25rem 0.75rem',
                    backgroundColor: '#f5f5f5',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    color: '#888'
                  }}>
                    Unranked
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#999' }}>
                    ({team.gamesPlayed || 0} game{(team.gamesPlayed || 0) !== 1 ? 's' : ''} — needs 5 to rank)
                  </span>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'baseline', marginLeft: '1rem' }}>
                  <span style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--primary-green)' }}>
                    #{nationalRank}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: '500' }}>Nat'l</span>
                  {stateRank && team.state && (
                    <>
                      <span style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--primary-green)' }}>
                        #{stateRank}
                      </span>
                      <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: '500' }}>{team.state}</span>
                    </>
                  )}
                </div>
              )
            )}
          </div>
        </div>
        {/* Rankings row - shows on far left on mobile */}
        {isMobile && (
          team.isRanked === false ? (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <span style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#f5f5f5',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '0.9rem',
                fontWeight: '600',
                color: '#888'
              }}>
                Unranked
              </span>
              <span style={{ fontSize: '0.8rem', color: '#999' }}>
                ({team.gamesPlayed || 0} game{(team.gamesPlayed || 0) !== 1 ? 's' : ''} — needs 5 to rank)
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'baseline', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--primary-green)' }}>
                #{nationalRank}
              </span>
              <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: '500' }}>Nat'l</span>
              {stateRank && team.state && (
                <>
                  <span style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--primary-green)' }}>
                    #{stateRank}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#666', fontWeight: '500' }}>{team.state}</span>
                </>
              )}
            </div>
          )
        )}
        {/* Address line */}
        {(team.city || team.state || team.zipCode || team.streetAddress) && (
          <div style={{ marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#666' }}>
              {team.streetAddress && <span>{team.streetAddress}, </span>}
              {[team.city, team.state, team.zipCode].filter(Boolean).join(', ')}
            </span>
          </div>
        )}
        {/* Buttons row - Add, Club, Crystal Ball */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {/* My Teams Button */}
              {canSaveMyTeams && (
                <>
                  {isInMyTeams(team) ? (
                    <button
                      onClick={() => {
                        removeFromMyTeams(team);
                        setMyTeamsRefreshKey(prev => prev + 1);
                      }}
                      style={{
                        padding: '0.4rem 0.75rem',
                        borderRadius: '6px',
                        border: '2px solid var(--accent-green)',
                        background: '#f0f7ed',
                        color: 'var(--primary-green)',
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        lineHeight: '1',
                        boxSizing: 'border-box'
                      }}
                    >
                      {isElevenUpBrand ? '★' : '⭐'} My Team
                    </button>
                  ) : getMyTeams().length < 5 ? (
                    <button
                      onClick={() => {
                        addToMyTeams(team);
                        setMyTeamsRefreshKey(prev => prev + 1);
                      }}
                      style={{
                        padding: '0.4rem 0.75rem',
                        borderRadius: '6px',
                        border: 'none',
                        background: 'var(--primary-green)',
                        color: 'white',
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        lineHeight: '1',
                        boxSizing: 'border-box'
                      }}
                    >
                      ☆ Add
                    </button>
                  ) : (
                    <span style={{
                      padding: '0.4rem 0.75rem',
                      borderRadius: '6px',
                      background: '#f5f5f5',
                      color: '#888',
                      fontSize: '0.75rem'
                    }}>
                      Full (5/5)
                    </span>
                  )}
                </>
              )}
              {/* Club Button */}
              <Link
                to={`/club/${encodeURIComponent(team.club)}`}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: '6px',
                  border: 'none',
                  background: 'var(--primary-green)',
                  color: 'white',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  textDecoration: 'none',
                  lineHeight: '1',
                  boxSizing: 'border-box'
                }}
              >
                Club →
              </Link>
              {/* Crystal Ball Predict Button */}
              <button
                onClick={() => setShowPredictPanel(!showPredictPanel)}
                className="crystal-ball-btn"
                style={{
                  padding: '0',
                  border: 'none',
                  background: 'transparent',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  opacity: showPredictPanel ? 0.6 : 1,
                  position: 'relative',
                  lineHeight: 1,
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="Predict Results"
              >
                <span className="crystal-ball-icon">🔮</span>
              </button>
        </div>
      </div>

      {/* Prediction Panel */}
      {showPredictPanel && (
        <div className="card" style={{ padding: '1rem', background: '#faf5ff', border: '1px solid #e1bee7', position: 'relative' }}>
          <button
            onClick={() => setShowPredictPanel(false)}
            style={{
              position: 'absolute',
              top: '0.5rem',
              right: '0.5rem',
              background: 'transparent',
              border: 'none',
              fontSize: '1.2rem',
              color: '#7b1fa2',
              cursor: 'pointer',
              padding: '0.25rem',
              lineHeight: 1
            }}
            title="Close"
          >
            ✕
          </button>
          <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#7b1fa2', marginBottom: '1rem' }}>
            Predict Results vs...
          </h3>

          {/* Predictions vs My Teams */}
          {myTeamsPredictions.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', fontWeight: '500' }}>
                vs My Teams
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {myTeamsPredictions.map(({ opponent, prediction, homeWinProb, drawProb, awayWinProb, predictedHomeScore, predictedAwayScore }) => (
                  <div
                    key={opponent.id}
                    style={{
                      padding: '0.6rem 0.75rem',
                      background: 'white',
                      borderRadius: '6px',
                      border: prediction?.isCrossAgeGroup ? '2px solid #ff9800' : '1px solid #e0e0e0'
                    }}
                  >
                    {/* Cross-age-group indicator */}
                    {prediction?.isCrossAgeGroup && (
                      <div style={{
                        fontSize: '0.65rem',
                        color: '#e65100',
                        textAlign: 'center',
                        marginBottom: '0.3rem',
                        fontWeight: '500'
                      }}>
                        Cross-age: {team.ageGroup} vs {opponent.ageGroup}
                      </div>
                    )}
                    {/* Score display with team names */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                      marginBottom: '0.4rem'
                    }}>
                      <span style={{
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        color: '#333',
                        textAlign: 'right',
                        flex: 1
                      }}>
                        {team.name} {team.ageGroup}
                      </span>
                      <span style={{
                        fontWeight: '700',
                        color: '#7b1fa2',
                        fontSize: '1.1rem',
                        padding: '0.2rem 0.5rem',
                        background: '#f3e5f5',
                        borderRadius: '4px'
                      }}>
                        {predictedHomeScore} - {predictedAwayScore}
                      </span>
                      <Link
                        to={`/team/${opponent.id}`}
                        style={{
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          color: '#7b1fa2',
                          textDecoration: 'none',
                          textAlign: 'left',
                          flex: 1
                        }}
                        onClick={() => setShowPredictPanel(false)}
                      >
                        {opponent.name} {opponent.ageGroup}
                      </Link>
                    </div>
                    {/* Win probabilities - labeled with team names */}
                    <div style={{
                      display: 'flex',
                      justifyContent: 'center',
                      gap: '0.4rem',
                      fontSize: '0.65rem'
                    }}>
                      <span style={{
                        padding: '0.15rem 0.4rem',
                        borderRadius: '3px',
                        background: getPredictionColor(homeWinProb, 'win'),
                        color: 'white',
                        fontWeight: '600'
                      }}>
                        {team.name?.split(' ')[0]} {homeWinProb}%
                      </span>
                      <span style={{
                        padding: '0.15rem 0.4rem',
                        borderRadius: '3px',
                        background: '#888',
                        color: 'white',
                        fontWeight: '600'
                      }}>
                        Draw {drawProb}%
                      </span>
                      <span style={{
                        padding: '0.15rem 0.4rem',
                        borderRadius: '3px',
                        background: getPredictionColor(awayWinProb, 'loss'),
                        color: 'white',
                        fontWeight: '600'
                      }}>
                        {opponent.name?.split(' ')[0]} {awayWinProb}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {myTeamsPredictions.length === 0 && !selectedCustomOpponent && (
            <p style={{ fontSize: '0.85rem', color: '#888', marginBottom: '1rem' }}>
              No teams in My Teams to predict against. Search for a team below.
            </p>
          )}

          {/* Custom Opponent Search */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', fontWeight: '500' }}>
              Search Any Team
            </div>
            <input
              type="text"
              placeholder="Search by team or club name..."
              value={customOpponentSearch}
              onChange={(e) => {
                setCustomOpponentSearch(e.target.value);
                setSelectedCustomOpponent(null);
              }}
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                border: '1px solid #ddd',
                fontSize: '0.85rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && !selectedCustomOpponent && (
            <div style={{
              maxHeight: '200px',
              overflowY: 'auto',
              border: '1px solid #e0e0e0',
              borderRadius: '6px',
              marginBottom: '0.75rem'
            }}>
              {searchResults.map(t => (
                <div
                  key={t.id}
                  onClick={() => {
                    setSelectedCustomOpponent(t);
                    setCustomOpponentSearch(t.name);
                  }}
                  style={{
                    padding: '0.5rem 0.75rem',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f0f0f0',
                    fontSize: '0.85rem',
                    background: 'white'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                >
                  <div style={{ fontWeight: '500', color: '#333' }}>{t.name} {t.ageGroup}</div>
                  <div style={{ fontSize: '0.75rem', color: '#888' }}>
                    {t.club} • {t.league} • #{t.rank || '?'}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Custom Prediction Result */}
          {customPrediction && (
            <div style={{
              padding: '0.75rem',
              background: 'white',
              borderRadius: '8px',
              border: customPrediction.prediction?.isCrossAgeGroup ? '2px solid #ff9800' : '2px solid #7b1fa2'
            }}>
              <div style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.5rem', textAlign: 'center' }}>
                Predicted Result
                {customPrediction.prediction?.isCrossAgeGroup && (
                  <span style={{ color: '#e65100', fontWeight: '500' }}>
                    {' '}(Cross-age: {team.ageGroup} vs {customPrediction.opponent.ageGroup})
                  </span>
                )}
              </div>
              {/* Score display with team names on either side */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.75rem',
                marginBottom: '0.75rem'
              }}>
                <span style={{
                  fontSize: '0.9rem',
                  fontWeight: '600',
                  color: '#333',
                  textAlign: 'right',
                  flex: 1
                }}>
                  {team.name} {team.ageGroup}
                </span>
                <span style={{
                  fontSize: '1.5rem',
                  fontWeight: '700',
                  color: customPrediction.prediction?.isCrossAgeGroup ? '#e65100' : '#7b1fa2',
                  padding: '0.25rem 0.75rem',
                  background: customPrediction.prediction?.isCrossAgeGroup ? '#fff3e0' : '#f3e5f5',
                  borderRadius: '6px'
                }}>
                  {customPrediction.predictedHomeScore} - {customPrediction.predictedAwayScore}
                </span>
                <Link
                  to={`/team/${customPrediction.opponent.id}`}
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    color: '#7b1fa2',
                    textDecoration: 'none',
                    textAlign: 'left',
                    flex: 1
                  }}
                  onClick={() => setShowPredictPanel(false)}
                >
                  {customPrediction.opponent.name} {customPrediction.opponent.ageGroup}
                </Link>
              </div>
              {/* Win/Draw/Loss probabilities - labeled with team names */}
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '0.5rem',
                flexWrap: 'wrap',
                fontSize: '0.75rem',
                marginBottom: '0.75rem'
              }}>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  background: getPredictionColor(customPrediction.homeWinProb, 'win'),
                  color: 'white',
                  fontWeight: '600'
                }}>
                  {team.name?.split(' ')[0]} {customPrediction.homeWinProb}%
                </span>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  background: '#666',
                  color: 'white',
                  fontWeight: '600'
                }}>
                  Draw {customPrediction.drawProb}%
                </span>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  background: getPredictionColor(customPrediction.awayWinProb, 'loss'),
                  color: 'white',
                  fontWeight: '600'
                }}>
                  {customPrediction.opponent.name?.split(' ')[0]} {customPrediction.awayWinProb}%
                </span>
              </div>
              <div style={{ textAlign: 'center' }}>
                <button
                  onClick={() => {
                    setSelectedCustomOpponent(null);
                    setCustomOpponentSearch('');
                  }}
                  style={{
                    padding: '0.35rem 0.7rem',
                    borderRadius: '4px',
                    border: '1px solid #ddd',
                    background: '#f8f9fa',
                    color: '#666',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  Search Another Team
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Team Stats Overview - Compact */}
      <div className="card" style={{ padding: '1rem' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))',
          gap: '0.5rem',
          padding: '0.75rem',
          background: '#f8f9fa',
          borderRadius: '8px'
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--primary-green)' }}>{team.powerScore?.toFixed(0)}</div>
            <div style={{ fontSize: '0.65rem', color: '#888', textTransform: 'uppercase' }}>PWR</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: '700' }}>{team.wins}-{team.losses}-{team.draws}</div>
            <div style={{ fontSize: '0.65rem', color: '#888', textTransform: 'uppercase' }}>W-L-D</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: '700' }}>{(team.sos * 100).toFixed(0)}%</div>
            <div style={{ fontSize: '0.65rem', color: '#888', textTransform: 'uppercase' }}>SOS</div>
          </div>
        </div>
      </div>

      {/* Rankings History Chart - Always visible */}
      <div className="card" style={{ padding: '1rem' }}>
        <RankingsHistoryChart
          history={teamRankingHistory}
          currentRank={nationalRank}
          currentOffensiveRank={team.offensiveRank}
          currentDefensiveRank={team.defensiveRank}
          teamName={team.name}
        />
      </div>

      {/* Tabs */}
      <div className="card">
        <div className="team-profile-tabs">
          <button
            className={`team-profile-tab ${activeTab === 'games' ? 'active' : ''}`}
            onClick={() => setActiveTab('games')}
          >
            <span className="tab-icon">📅 </span>Games ({teamGames.past.length + teamGames.upcoming.length})
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'roster' ? 'active' : ''}`}
            onClick={() => setActiveTab('roster')}
          >
            <span className="tab-icon"><PlayersIcon size={16} color="green" /></span>Roster ({roster.length})
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'links' ? 'active' : ''}`}
            onClick={() => setActiveTab('links')}
          >
            <span className="tab-icon">🔗 </span>Links
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'dailyUpdate' ? 'active' : ''}`}
            onClick={() => setActiveTab('dailyUpdate')}
          >
            <span className="tab-icon">...</span>Daily Update
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'reviews' ? 'active' : ''}`}
            onClick={() => setActiveTab('reviews')}
          >
            <span className="tab-icon">{'\u2605'} </span>Reviews
          </button>
        </div>

        {activeTab === 'reviews' && (
          <TeamReviews
            key={reviewsRefreshKey}
            teamId={team.id}
            teamName={team.name}
            onAddRating={() => setShowRatingForm(true)}
          />
        )}

        {activeTab === 'dailyUpdate' && (
          <DailyUpdate team={{ ...team, nationalRank }} teamGames={teamGames} />
        )}

        {activeTab === 'links' && (
          <LinkManager
            entityType="team"
            entityId={team.id}
            entityName={team.name}
            isOwner={false}
          />
        )}

        {activeTab === 'games' && (
          <div>

            {/* Submit Game Form - Pro users only */}
            {canSubmitScores && showSubmitForm && (
              <div style={{
                marginBottom: '1.5rem',
                background: '#fafafa',
                borderRadius: '12px',
                border: '1px solid #e0e0e0'
              }}>
                <SubmitGameForm
                  team={team}
                  onSubmit={handleGameSubmitted}
                  onCancel={() => setShowSubmitForm(false)}
                />
              </div>
            )}

            {teamGames.past.length === 0 && teamGames.upcoming.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📅</div>
                <div className="empty-state-text">No official games found</div>
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  Game data for this team is not yet available.
                  Use the "Report Missing Game" button above to submit games.
                </p>
              </div>
            ) : (
              <div>
                {/* Toggle Options */}
                <div style={{
                  display: 'flex',
                  gap: '0.4rem',
                  marginBottom: '0.75rem',
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {!isMobile && (
                      <button
                        onClick={() => setShowUpcoming(!showUpcoming)}
                        style={{
                          padding: '0.35rem 0.7rem',
                          borderRadius: '4px',
                          border: '1px solid #ddd',
                          background: showUpcoming ? 'var(--primary-green)' : '#f8f9fa',
                          color: showUpcoming ? 'white' : '#666',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          fontWeight: '500'
                        }}
                      >
                        {showUpcoming ? 'Hide' : 'Show'} Upcoming
                      </button>
                    )}
                    <button
                      onClick={() => setShowPredictions(!showPredictions)}
                      style={{
                        padding: '0.35rem 0.7rem',
                        borderRadius: '4px',
                        border: '1px solid #ddd',
                        background: showPredictions ? '#7b1fa2' : '#f8f9fa',
                        color: showPredictions ? 'white' : '#666',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: '500'
                      }}
                    >
                      {showPredictions ? 'Hide' : 'Show'} Predictions
                    </button>
                  </div>
                  {canSubmitScores && (
                    <button
                      onClick={() => setShowSubmitForm(!showSubmitForm)}
                      style={{
                        padding: '0.35rem 0.7rem',
                        borderRadius: '4px',
                        border: '1px solid #ddd',
                        background: showSubmitForm ? '#f5f5f5' : 'var(--primary-green)',
                        color: showSubmitForm ? '#666' : 'white',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: '500'
                      }}
                    >
                      {showSubmitForm ? '✕ Cancel' : '+ Report Game'}
                    </button>
                  )}
                </div>

                {/* Upcoming Games */}
                {showUpcoming && upcomingWithPredictions.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      marginBottom: '0.5rem'
                    }}>
                      <h3 style={{
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        color: 'var(--primary-green)',
                        margin: 0
                      }}>
                        Upcoming ({upcomingWithPredictions.length})
                      </h3>
                      {isMobile && (
                        <button
                          onClick={() => setShowUpcoming(false)}
                          style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            border: '1px solid #ddd',
                            background: '#f8f9fa',
                            color: '#666',
                            cursor: 'pointer',
                            fontSize: '0.65rem',
                            fontWeight: '500'
                          }}
                        >
                          Hide Upcoming
                        </button>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {upcomingWithPredictions.map(game => {
                        // Find opponent team for linking - use existing opponentData or look up with smart matching
                        const opponentTeam = game.opponentData?.id
                          ? game.opponentData
                          : findOpponentInData(game.opponent, team.ageGroup, teamsData);

                        return (
                        <div
                          key={game.id}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: '#f0f7ff',
                            borderRadius: '6px',
                            borderLeft: '3px solid #2196f3'
                          }}
                        >
                          {/* Single row: Date, opponent, prediction */}
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            flexWrap: 'wrap',
                            fontSize: '0.85rem'
                          }}>
                            <span style={{ color: '#666', fontSize: '0.75rem', minWidth: '100px' }}>
                              {parseDate(game.date)?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            </span>
                            <span style={{ fontWeight: '500', color: '#333', flex: 1, minWidth: '150px' }}>
                              {game.isHome ? 'vs' : '@'}{' '}
                              {opponentTeam?.id ? (
                                <Link
                                  to={`/team/${opponentTeam.id}`}
                                  style={{ color: '#1976d2', textDecoration: 'none' }}
                                >
                                  {game.opponent} {opponentTeam.ageGroup}
                                </Link>
                              ) : (
                                game.opponent
                              )}
                            </span>
                            {showPredictions && game.opponentData && (
                              <span style={{
                                fontSize: '0.7rem',
                                color: (game.opponentData.isUnranked || !game.opponentData.rank) ? '#999' : '#7b1fa2',
                                fontWeight: '600'
                              }}>
                                {(game.opponentData.isUnranked || !game.opponentData.rank) ? 'NR' : `#${game.opponentData.rank}`}
                              </span>
                            )}
                            {showPredictions && (
                              <span style={{
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                padding: '0.15rem 0.4rem',
                                borderRadius: '4px',
                                background: getPredictionColor(game.teamWinProb, 'win'),
                                color: 'white'
                              }}>
                                {game.predictedTeamScore}-{game.predictedOppScore}
                              </span>
                            )}
                          </div>
                        </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Past Games */}
                {teamGames.past.length > 0 && (
                  <div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      marginBottom: '0.5rem',
                      flexWrap: 'wrap'
                    }}>
                      <h3 style={{
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        color: 'var(--primary-green)',
                        margin: 0
                      }}>
                        Results ({teamGames.past.length})
                      </h3>
                      {showPredictions && (
                        <span style={{
                          fontSize: '0.75rem',
                          color: '#7b1fa2',
                          fontWeight: '500'
                        }}>
                          • by Performance
                        </span>
                      )}
                      {isMobile && !showUpcoming && upcomingWithPredictions.length > 0 && (
                        <button
                          onClick={() => setShowUpcoming(true)}
                          style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            border: '1px solid #ddd',
                            background: '#f8f9fa',
                            color: '#666',
                            cursor: 'pointer',
                            fontSize: '0.65rem',
                            fontWeight: '500',
                            marginLeft: 'auto'
                          }}
                        >
                          Show Upcoming ({upcomingWithPredictions.length})
                        </button>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      {(showPredictions ? rankedGames : teamGames.past).map(game => {
                        const isHome = showPredictions ? game.isHome : normalizeTeamName(game.homeTeam) === normalizeTeamName(team.name);
                        const opponent = showPredictions ? game.opponent : (isHome ? game.awayTeam : game.homeTeam);
                        const teamScore = isHome ? game.homeScore : game.awayScore;
                        const oppScore = isHome ? game.awayScore : game.homeScore;
                        const result = getGameResult(game);

                        // Find opponent team for linking - use existing opponentData or look up with smart matching
                        const opponentTeam = game.opponentData?.id
                          ? game.opponentData
                          : findOpponentInData(opponent, team.ageGroup, teamsData);

                        const resultColors = {
                          win: { bg: '#e8f5e9', border: '#4caf50', text: '#2e7d32' },
                          loss: { bg: '#ffebee', border: '#f44336', text: '#c62828' },
                          draw: { bg: '#fff3e0', border: '#ff9800', text: '#e65100' }
                        };
                        const colors = resultColors[result];

                        return (
                          <div
                            key={game.id}
                            className="past-game-card"
                            style={{
                              padding: '0.4rem 0.6rem',
                              background: colors.bg,
                              borderRadius: '4px',
                              borderLeft: `3px solid ${colors.border}`,
                              fontSize: '0.85rem'
                            }}
                          >
                            {/* Single compact row */}
                            <div style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.4rem',
                              flexWrap: 'wrap'
                            }}>
                              {/* Date */}
                              <span style={{ color: '#666', fontSize: '0.75rem', minWidth: '85px' }}>
                                {parseDate(game.date)?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                              </span>
                              {/* Result badge */}
                              <span style={{
                                fontWeight: '700',
                                color: 'white',
                                background: colors.border,
                                padding: '0.1rem 0.35rem',
                                borderRadius: '3px',
                                fontSize: '0.7rem',
                                minWidth: '18px',
                                textAlign: 'center'
                              }}>
                                {result === 'win' ? 'W' : result === 'loss' ? 'L' : 'D'}
                              </span>
                              {/* Score */}
                              <span style={{
                                fontWeight: '600',
                                color: '#333',
                                minWidth: '32px'
                              }}>
                                {teamScore}-{oppScore}
                              </span>
                              {/* Opponent */}
                              <span style={{
                                fontWeight: '500',
                                color: '#333',
                                flex: 1,
                                minWidth: '100px',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis'
                              }}>
                                {isHome ? 'vs' : '@'}{' '}
                                {opponentTeam?.id ? (
                                  <Link
                                    to={`/team/${opponentTeam.id}`}
                                    style={{ color: '#1976d2', textDecoration: 'none' }}
                                  >
                                    {opponent} {opponentTeam.ageGroup}
                                  </Link>
                                ) : (
                                  opponent
                                )}
                              </span>
                              {/* Opponent rank if predictions on */}
                              {showPredictions && game.opponentData && (
                                <span style={{
                                  fontSize: '0.7rem',
                                  color: (game.opponentData.isUnranked || !game.opponentData.rank) ? '#999' : '#7b1fa2',
                                  fontWeight: '600'
                                }}>
                                  {(game.opponentData.isUnranked || !game.opponentData.rank) ? 'NR' : `#${game.opponentData.rank}`}
                                </span>
                              )}
                              {/* Performance indicator if predictions on */}
                              {showPredictions && game.analysis && (
                                <span style={{
                                  fontSize: '0.65rem',
                                  fontWeight: '600',
                                  padding: '0.1rem 0.3rem',
                                  borderRadius: '3px',
                                  background: game.analysis.outperformed ? '#2e7d32' : '#e65100',
                                  color: 'white'
                                }}>
                                  {game.analysis.performanceDiff > 0 ? '+' : ''}{game.analysis.performanceDiff}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* User-Submitted Pending Games */}
            <PendingGames
              key={pendingGamesKey}
              team={team}
              onRefresh={() => setPendingGamesKey(prev => prev + 1)}
            />
          </div>
        )}

        {activeTab === 'roster' && (
          <div>
            {/* Add/Remove Player Buttons */}
            {canClaimPlayers && (
              <div style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '0.5rem',
                marginBottom: '1rem'
              }}>
                <button
                  onClick={() => setShowAddPlayerModal(true)}
                  style={{
                    padding: '0.6rem 1rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--primary-green)',
                    color: '#fff',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  + Add Player
                </button>
                {roster.length > 0 && (
                  <button
                    onClick={() => setShowRemoveMode(!showRemoveMode)}
                    style={{
                      padding: '0.6rem 1rem',
                      borderRadius: '8px',
                      border: showRemoveMode ? '2px solid #c62828' : 'none',
                      background: showRemoveMode ? '#ffebee' : '#c62828',
                      color: showRemoveMode ? '#c62828' : '#fff',
                      fontSize: '0.9rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {showRemoveMode ? '✕ Cancel' : '- Remove Player'}
                  </button>
                )}
              </div>
            )}

            {!canClaimPlayers && (
              <div style={{
                padding: '0.75rem 1rem',
                background: '#f8f9fa',
                borderRadius: '8px',
                marginBottom: '1rem',
                border: '1px solid #e0e0e0'
              }}>
                <span style={{ color: '#666', fontSize: '0.9rem' }}>
                  Pro account required to add players
                </span>
              </div>
            )}

            {roster.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon"><PlayersIcon size={48} color="gray" /></div>
                <div className="empty-state-text">No players on roster yet</div>
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  {canClaimPlayers ? 'Click "Add Player" above to add players to this team.' : 'Upgrade to Pro to add players to this team.'}
                </p>
                {canClaimPlayers ? (
                  <button
                    onClick={() => setShowAddPlayerModal(true)}
                    className="btn btn-primary"
                    style={{ marginTop: '1rem' }}
                  >
                    Add Your First Player
                  </button>
                ) : (
                  <button
                    onClick={() => navigate('/players')}
                    className="btn btn-secondary"
                    style={{ marginTop: '1rem' }}
                  >
                    Go to Players
                  </button>
                )}
              </div>
            ) : (
              <div>
                {/* Toggle Details Button */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
                  <button
                    onClick={() => setShowRosterDetails(!showRosterDetails)}
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      border: '1px solid #ddd',
                      background: showRosterDetails ? 'var(--primary-green)' : '#f8f9fa',
                      color: showRosterDetails ? 'white' : '#666',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: '500'
                    }}
                  >
                    {showRosterDetails ? 'Hide Details' : 'Show Details'}
                  </button>
                </div>

                {/* Roster Table */}
                <div className="table-container" style={{ overflowX: 'auto' }}>
                  <table className="data-table rankings-table">
                    <thead>
                      <tr>
                        <th
                          className="sortable-header"
                          onClick={() => handleRosterSort('name')}
                          style={{ cursor: 'pointer' }}
                        >
                          Name{getRosterSortIndicator('name')}
                        </th>
                        <th
                          className="sortable-header"
                          onClick={() => handleRosterSort('position')}
                          style={{ cursor: 'pointer' }}
                        >
                          Pos{getRosterSortIndicator('position')}
                        </th>
                        <th
                          className="col-age sortable-header"
                          onClick={() => handleRosterSort('number')}
                          style={{ cursor: 'pointer' }}
                        >
                          {showRosterDetails ? 'Age' : '#'}{!showRosterDetails && getRosterSortIndicator('number')}
                        </th>
                        <th
                          className="sortable-header"
                          onClick={() => handleRosterSort('badges')}
                          style={{ cursor: 'pointer' }}
                        >
                          {showRosterDetails ? 'Team' : 'Badges'}{!showRosterDetails && getRosterSortIndicator('badges')}
                        </th>
                        <th className={`col-league${!showRosterDetails ? ' hide-mobile' : ''}`}>League</th>
                        <th className={`col-state${!showRosterDetails ? ' hide-mobile' : ''}`}>ST</th>
                        <th className={!showRosterDetails ? 'hide-mobile' : ''}>Coll. Commit</th>
                        {showRosterDetails && <th>Grad</th>}
                        {showRosterDetails && <th>Jersey</th>}
                        {(showRemoveMode || canClaimPlayers) && <th style={{ width: showRemoveMode ? '180px' : '80px' }}>Actions</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {sortedRoster
                        .filter(player => {
                          // Hide removed players unless in remove mode
                          if (player.removalStatus === 'hidden' && !showRemoveMode) return false;
                          return true;
                        })
                        .map(player => {
                        const playerBadges = badges[player.id] || {};
                        const totalBadges = Object.values(playerBadges).reduce((sum, count) => sum + count, 0);
                        const isPendingRemoval = player.removalStatus === 'pending_removal';
                        const isHidden = player.removalStatus === 'hidden';
                        const isConflict = player.removalStatus === 'conflict';
                        const canConfirm = isPaid && player.removalRequestedBy !== (user?.userId || user?.id);
                        const isRequester = player.removalRequestedBy === (user?.userId || user?.id);

                        return (
                          <tr
                            key={player.id}
                            style={isPendingRemoval || isConflict ? {
                              opacity: 0.6,
                              background: isConflict ? '#fff3e0' : '#f5f5f5'
                            } : isHidden ? {
                              opacity: 0.4,
                              background: '#ffebee',
                              textDecoration: 'line-through'
                            } : {}}
                          >
                            <td>
                              <Link
                                to={`/player/${player.id}`}
                                className="team-name-link"
                              >
                                {player.name}
                              </Link>
                            </td>
                            <td>{player.position || '-'}</td>
                            <td className="col-age">
                              {showRosterDetails
                                ? (player.ageGroup || '-')
                                : (player.number || player.jerseyNumber || '-')
                              }
                            </td>
                            <td>
                              {showRosterDetails ? (
                                player.teamName ? (
                                  <span
                                    style={{
                                      fontSize: '0.85rem',
                                      maxWidth: '200px',
                                      display: 'block',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap'
                                    }}
                                    title={player.teamName}
                                  >
                                    {player.teamName}
                                  </span>
                                ) : '-'
                              ) : (
                                (() => {
                                  // Get badge types that have counts > 0
                                  const earnedBadgeIds = Object.entries(playerBadges)
                                    .filter(([_, count]) => count > 0)
                                    .map(([badgeId]) => badgeId);

                                  if (earnedBadgeIds.length === 0) return '-';

                                  // If more than 3 different badge types, show total count
                                  if (earnedBadgeIds.length > 3) {
                                    return (
                                      <span style={{
                                        background: 'var(--accent-green)',
                                        color: 'white',
                                        padding: '0.2rem 0.5rem',
                                        borderRadius: '4px',
                                        fontSize: '0.8rem',
                                        fontWeight: '600'
                                      }}>
                                        {totalBadges}
                                      </span>
                                    );
                                  }

                                  // Show badge icons
                                  return (
                                    <span style={{ display: 'flex', gap: '2px', flexWrap: 'wrap' }}>
                                      {earnedBadgeIds.map(badgeId => {
                                        const badgeType = BADGE_TYPES.find(b => b.id === badgeId);
                                        if (!badgeType) return null;
                                        const count = playerBadges[badgeId];
                                        return (
                                          <span
                                            key={badgeId}
                                            title={`${badgeType.name}${count > 1 ? ` x${count}` : ''}`}
                                            style={{ fontSize: '1rem' }}
                                          >
                                            {badgeType.emoji}
                                          </span>
                                        );
                                      })}
                                    </span>
                                  );
                                })()
                              )}
                            </td>
                            <td className={`col-league${!showRosterDetails ? ' hide-mobile' : ''}`}>
                              {player.league ? (
                                <span className="league-badge-sm" style={getLeagueBadgeStyle(player.league)}>
                                  {player.league}
                                </span>
                              ) : '-'}
                            </td>
                            <td className={`col-state${!showRosterDetails ? ' hide-mobile' : ''}`}>{player.state || '-'}</td>
                            <td className={!showRosterDetails ? 'hide-mobile' : ''}>{player.collegeCommitment || player.college_commitment || '-'}</td>
                            {showRosterDetails && <td>{player.gradYear || player.graduationYear || player.graduation_year || '-'}</td>}
                            {showRosterDetails && <td>{player.number || player.jerseyNumber || '-'}</td>}
                            {(showRemoveMode || canClaimPlayers) && (
                              <td>
                                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                  {/* Transfer button - show when not hidden and not in pending removal */}
                                  {canClaimPlayers && !isHidden && !isPendingRemoval && !isConflict && (
                                    <button
                                      onClick={() => handleOpenTransfer(player)}
                                      style={{
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '4px',
                                        border: '1px solid #1976d2',
                                        background: '#e3f2fd',
                                        color: '#1976d2',
                                        fontSize: '0.7rem',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      Transfer
                                    </button>
                                  )}

                                  {/* Pending removal status indicator */}
                                  {(isPendingRemoval || isConflict) && (
                                    <span style={{
                                      fontSize: '0.65rem',
                                      color: isConflict ? '#e65100' : '#666',
                                      fontStyle: 'italic'
                                    }}>
                                      {isConflict ? 'Conflict' : `by ${player.removalRequestedByName || 'user'}`}
                                    </span>
                                  )}

                                  {/* Confirm removal button - for second person (only in remove mode) */}
                                  {showRemoveMode && isPendingRemoval && canConfirm && (
                                    <button
                                      onClick={() => handleConfirmRemoval(player)}
                                      style={{
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '4px',
                                        border: 'none',
                                        background: '#c62828',
                                        color: 'white',
                                        fontSize: '0.7rem',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      Confirm
                                    </button>
                                  )}

                                  {/* Put back button - always visible for pending removals (requester can undo without confirmation) */}
                                  {(isPendingRemoval || isConflict) && (
                                    <button
                                      onClick={() => handlePutBack(player)}
                                      style={{
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '4px',
                                        border: '1px solid #2e7d32',
                                        background: '#e8f5e9',
                                        color: '#2e7d32',
                                        fontSize: '0.7rem',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      Put Back
                                    </button>
                                  )}

                                  {/* Remove button - for active players */}
                                  {showRemoveMode && !isPendingRemoval && !isHidden && !isConflict && (
                                    <button
                                      onClick={() => handleRemovePlayer(player.id)}
                                      style={{
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '4px',
                                        border: 'none',
                                        background: '#c62828',
                                        color: 'white',
                                        fontSize: '0.7rem',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      Remove
                                    </button>
                                  )}

                                  {/* Hidden player indicator */}
                                  {isHidden && showRemoveMode && (
                                    <span style={{ fontSize: '0.65rem', color: '#c62828' }}>Removed</span>
                                  )}
                                </div>
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add Player Modal */}
      {showAddPlayerModal && (
        <div
          className="modal-overlay"
          onClick={() => setShowAddPlayerModal(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'white',
              borderRadius: '16px',
              width: '100%',
              maxWidth: '450px',
              padding: '1.5rem',
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
            }}
          >
            <h2 style={{
              fontSize: '1.25rem',
              fontWeight: '600',
              color: 'var(--primary-green)',
              marginBottom: '1rem'
            }}>
              Add Player to {team?.name}
            </h2>

            <form onSubmit={handleAddPlayer}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem' }}>
                  Player Name *
                </label>
                <input
                  type="text"
                  className="form-input"
                  value={newPlayer.name}
                  onChange={(e) => setNewPlayer({...newPlayer, name: e.target.value})}
                  placeholder="Enter player name"
                  required
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #ddd' }}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem' }}>
                  Position *
                </label>
                <select
                  className="form-select"
                  value={newPlayer.position}
                  onChange={(e) => setNewPlayer({...newPlayer, position: e.target.value})}
                  required
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #ddd' }}
                >
                  <option value="">Select position</option>
                  <option value="Goalkeeper">Goalkeeper</option>
                  <option value="Defender">Defender</option>
                  <option value="Midfielder">Midfielder</option>
                  <option value="Forward">Forward</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem' }}>
                    Jersey #
                  </label>
                  <input
                    type="text"
                    value={newPlayer.jerseyNumber}
                    onChange={(e) => setNewPlayer({...newPlayer, jerseyNumber: e.target.value})}
                    placeholder="e.g., 10"
                    maxLength="3"
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #ddd' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem' }}>
                    Grad Year
                  </label>
                  <input
                    type="text"
                    value={newPlayer.gradYear}
                    onChange={(e) => setNewPlayer({...newPlayer, gradYear: e.target.value})}
                    placeholder="e.g., 2028"
                    maxLength="4"
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #ddd' }}
                  />
                </div>
              </div>

              <div style={{
                padding: '0.75rem',
                background: '#f8f9fa',
                borderRadius: '8px',
                marginBottom: '1.5rem',
                fontSize: '0.85rem',
                color: '#666'
              }}>
                Team: <strong>{team?.name}</strong> • {team?.ageGroup} • {team?.league}
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setShowAddPlayerModal(false)}
                  style={{
                    padding: '0.75rem 1.25rem',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    background: '#f5f5f5',
                    color: '#666',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '0.75rem 1.25rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--primary-green)',
                    color: 'white',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  Add Player
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Transfer Player Modal */}
      {showTransferModal && playerToTransfer && (
        <div
          className="modal-overlay"
          onClick={() => setShowTransferModal(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
        >
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'white',
              borderRadius: '12px',
              padding: '1.5rem',
              maxWidth: '450px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto'
            }}
          >
            <h3 style={{ marginBottom: '1rem', color: 'var(--dark-green)' }}>
              Transfer Player
            </h3>

            <div style={{
              padding: '0.75rem',
              background: '#f8f9fa',
              borderRadius: '8px',
              marginBottom: '1rem',
              fontSize: '0.9rem'
            }}>
              <strong>{playerToTransfer.name}</strong>
              <div style={{ color: '#666', fontSize: '0.85rem' }}>
                From: {team?.name} ({team?.ageGroup})
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem' }}>
                Search Destination Team
              </label>
              <input
                type="text"
                value={transferSearch}
                onChange={(e) => {
                  setTransferSearch(e.target.value);
                  setSelectedTransferTeam(null);
                }}
                placeholder="Type team name, club, or age group..."
                style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #ddd' }}
              />
            </div>

            {/* Search Results */}
            {transferSearch.length >= 2 && !selectedTransferTeam && (
              <div style={{
                maxHeight: '200px',
                overflowY: 'auto',
                border: '1px solid #ddd',
                borderRadius: '8px',
                marginBottom: '1rem'
              }}>
                {transferTeamResults.length === 0 ? (
                  <div style={{ padding: '1rem', color: '#666', textAlign: 'center' }}>
                    No teams found
                  </div>
                ) : (
                  transferTeamResults.map(t => (
                    <div
                      key={t.id}
                      onClick={() => {
                        setSelectedTransferTeam(t);
                        setTransferSearch(t.name);
                      }}
                      style={{
                        padding: '0.75rem',
                        borderBottom: '1px solid #eee',
                        cursor: 'pointer',
                        transition: 'background 0.2s'
                      }}
                      onMouseOver={(e) => e.currentTarget.style.background = '#f5f5f5'}
                      onMouseOut={(e) => e.currentTarget.style.background = 'white'}
                    >
                      <div style={{ fontWeight: '500' }}>{t.name} {t.ageGroup}</div>
                      <div style={{ fontSize: '0.8rem', color: '#666' }}>
                        {t.club} • {t.league} • {t.state}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Selected Team Display */}
            {selectedTransferTeam && (
              <div style={{
                padding: '0.75rem',
                background: '#e8f5e9',
                borderRadius: '8px',
                marginBottom: '1rem',
                border: '1px solid #2e7d32'
              }}>
                <div style={{ fontWeight: '500', color: '#2e7d32' }}>
                  To: {selectedTransferTeam.name}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#666' }}>
                  {selectedTransferTeam.club} • {selectedTransferTeam.ageGroup} • {selectedTransferTeam.league}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => {
                  setShowTransferModal(false);
                  setPlayerToTransfer(null);
                }}
                style={{
                  padding: '0.75rem 1.25rem',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  background: '#f5f5f5',
                  color: '#666',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleTransfer}
                disabled={!selectedTransferTeam}
                style={{
                  padding: '0.75rem 1.25rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: selectedTransferTeam ? '#1976d2' : '#ccc',
                  color: 'white',
                  fontWeight: '600',
                  cursor: selectedTransferTeam ? 'pointer' : 'not-allowed'
                }}
              >
                Transfer Player
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rating Form Modal */}
      {showRatingForm && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 16
        }}>
          <div style={{
            background: 'white',
            borderRadius: 12,
            maxWidth: 560,
            width: '100%',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.2)'
          }}>
            <TeamRatingForm
              team={team}
              onSubmit={() => {
                setShowRatingForm(false);
                setReviewsRefreshKey(prev => prev + 1);
                setActiveTab('reviews');
              }}
              onCancel={() => setShowRatingForm(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default TeamProfile;
