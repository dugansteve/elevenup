import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import { useUser } from '../context/UserContext';
import { dailyUpdateHelpers, findTeamInRankings } from '../data/sampleData';
import BottomSheetSelect from './BottomSheetSelect';
import { TeamsIcon, TournamentIcon } from './PaperIcons';
import { isElevenUpBrand } from '../config/brand';

import RankingsMap from './RankingsMap';
// Pagination constants
const TEAMS_PER_PAGE = 200;

// Session storage keys for preserving state
const STORAGE_KEYS = {
  scrollPosition: 'rankings_scroll_position',
  filters: 'rankings_filters',
  showDetails: 'rankings_show_details',
  viewMode: 'rankings_view_mode'
};

// Helper function for league badge colors
function getLeagueBadgeStyle(league) {
  const styles = {
    'ECNL': { background: '#e3f2fd', color: '#1976d2' },      // Blue
    'GA': { background: '#f3e5f5', color: '#7b1fa2' },        // Purple
    'ECNL-RL': { background: '#ffebee', color: '#c62828' },   // Red
    'ASPIRE': { background: '#e8f5e9', color: '#2e7d32' },    // Green
    'NPL': { background: '#fff3e0', color: '#e65100' },       // Orange
    'MLS NEXT HD': { background: '#006064', color: '#ffffff' },  // Dark Teal (MLS pro clubs - Homegrown Division)
    'MLS NEXT AD': { background: '#e0f7fa', color: '#00838f' },  // Light Teal (Academy Division)
  };
  return styles[league] || { background: '#f5f5f5', color: '#666' };
}

// Helper function to strip age/gender suffix from team names for cleaner display
function stripAgeFromName(name) {
  if (!name) return name;
  // Remove patterns like " G13", " B12", " 2012G", " 2013B", " 12G", " 13B" at end
  // Also handles "08/07G", "08/07B" combo age groups
  return name
    .replace(/\s+\d{2}\/\d{2}[GB]\s*$/i, '')  // " 08/07G" combo ages
    .replace(/\s+[GB]\d{1,2}\s*$/i, '')        // " G13", " B12"
    .replace(/\s+\d{4}[GB]\s*$/i, '')          // " 2012G", " 2013B"
    .replace(/\s+\d{2}[GB]\s*$/i, '')          // " 12G", " 13B"
    .trim();
}

// League categorization
const NATIONAL_LEAGUES = ['ECNL', 'ECNL-RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT', 'MLS NEXT HD', 'MLS NEXT AD'];
// Girls-only leagues (no boys teams)
const GIRLS_ONLY_LEAGUES = ['GA', 'ASPIRE'];
// Boys-only leagues (no girls teams)
const BOYS_ONLY_LEAGUES = ['MLS NEXT', 'MLS NEXT HD', 'MLS NEXT AD'];
const REGIONAL_LEAGUES = [
  'Baltimore Mania',
  'Chesapeake PSL YPL',
  'Eastern PA Challenge Cup',
  'Florida CFPL',
  'Florida NFPL',
  'Florida SEFPL',
  'Florida WFPL',
  'ICSL',
  'Illinois Cup',
  'Mid South Conference',
  'MSPSP',
  'Northwest Conference',
  'Presidents Cup',
  'Real CO Cup',
  'SEFPL',
  'SLYSA',
  'SOCAL',
  'Southeastern CCL Fall',
  'Southeastern CCL U11/U12',
  'State Cup',
  'Virginia Cup',
  'WFPL',
  'WVFC Capital Cup'
];

// Helper function to sort age groups numerically (G06, G07, G08/07, G09...G19)
function sortAgeGroupsNumerically(ageGroups) {
  return [...ageGroups].sort((a, b) => {
    // Extract number from age group (e.g., "G13" -> 13, "G08/07" -> 8)
    const getNum = (ag) => {
      const match = ag.match(/\d+/);
      return match ? parseInt(match[0], 10) : 0;
    };
    return getNum(a) - getNum(b);
  });
}

// Truncated text component with tap-to-expand for mobile
function TruncatedCell({ text, color, maxWidth = '150px' }) {
  const [expanded, setExpanded] = useState(false);

  if (!text || text === '-') return <span>-</span>;

  return (
    <div style={{ position: 'relative' }}>
      <span
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        style={{
          fontSize: '0.8rem',
          color: color,
          maxWidth: maxWidth,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: 'block',
          cursor: 'pointer'
        }}
        title={text}
      >
        {text}
      </span>
      {expanded && (
        <div
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(false);
          }}
          style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#333',
            color: '#fff',
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            fontSize: '0.8rem',
            whiteSpace: 'nowrap',
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            marginTop: '4px'
          }}
        >
          {text}
          <div style={{
            position: 'absolute',
            top: '-6px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: 0,
            height: 0,
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderBottom: '6px solid #333'
          }} />
        </div>
      )}
    </div>
  );
}

function Rankings() {
  const navigate = useNavigate();
  const location = useLocation();
  const { teamsData, gamesData, ageGroups, leagues, states, genders, isLoading, error, lastUpdated } = useRankingsData();
  const { canPerform, getMyTeams, addToMyTeams, removeFromMyTeams, isInMyTeams, isGuest, getFollowedTeams, followTeam, unfollowTeam, isFollowing, userDataReady } = useUser();
  const tableContainerRef = useRef(null);

  // Mobile bottom sheet for Gender/Age filter
  const [showGenderAgeSheet, setShowGenderAgeSheet] = useState(false);

  // Drag scrolling state
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeftStart, setScrollLeftStart] = useState(0);
  
  // Drag scroll handlers
  const handleMouseDown = useCallback((e) => {
    if (!tableContainerRef.current) return;
    setIsDragging(true);
    setStartX(e.pageX - tableContainerRef.current.offsetLeft);
    setScrollLeftStart(tableContainerRef.current.scrollLeft);
    tableContainerRef.current.style.cursor = 'grabbing';
    tableContainerRef.current.style.userSelect = 'none';
  }, []);
  
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    if (tableContainerRef.current) {
      tableContainerRef.current.style.cursor = 'grab';
      tableContainerRef.current.style.userSelect = '';
    }
  }, []);
  
  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !tableContainerRef.current) return;
    e.preventDefault();
    const x = e.pageX - tableContainerRef.current.offsetLeft;
    const walk = (x - startX) * 1.5; // Scroll speed multiplier
    tableContainerRef.current.scrollLeft = scrollLeftStart - walk;
  }, [isDragging, startX, scrollLeftStart]);
  
  const handleMouseLeave = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      if (tableContainerRef.current) {
        tableContainerRef.current.style.cursor = 'grab';
        tableContainerRef.current.style.userSelect = '';
      }
    }
  }, [isDragging]);
  
  // Try to restore saved filters from sessionStorage
  const getSavedFilters = () => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.filters);
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  };
  
  const savedFilters = getSavedFilters();
  
  const [selectedAgeGroup, setSelectedAgeGroup] = useState(savedFilters?.ageGroup || 'ALL');
  const [selectedLeague, setSelectedLeague] = useState(savedFilters?.league || 'ALL');
  const [selectedState, setSelectedState] = useState(savedFilters?.state || 'ALL');
  const [selectedGender, setSelectedGender] = useState(savedFilters?.gender || 'Girls');
  const [viewMode, setViewMode] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.viewMode);
      return saved || 'rankings';
    } catch { return 'rankings'; }
  }); // 'rankings', 'myteams', or 'following'
  const [filterSearch, setFilterSearch] = useState(savedFilters?.search || ''); // For rankings table filter
  const [modalSearch, setModalSearch] = useState('');   // For Add Team modal
  const [showAddTeamModal, setShowAddTeamModal] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [myTeamsRefreshKey, setMyTeamsRefreshKey] = useState(0);
  const [followedTeamsRefreshKey, setFollowedTeamsRefreshKey] = useState(0);
  const [followingQuickView, setFollowingQuickView] = useState(false);
  const [displayLimit, setDisplayLimit] = useState(savedFilters?.displayLimit || TEAMS_PER_PAGE); // Pagination
  const [showDetails, setShowDetails] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.showDetails);
      // If no saved preference, default based on screen size (desktop = true, mobile = false)
      if (saved === null) {
        return window.innerWidth >= 768;
      }
      return saved === 'true';
    } catch { return false; }
  });
  
  // Sorting state
  const [sortField, setSortField] = useState('power'); // 'power', 'record', 'gd', 'offRank', 'defRank'
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc' or 'desc'

  // Save filters to sessionStorage whenever they change
  useEffect(() => {
    const filters = {
      ageGroup: selectedAgeGroup,
      league: selectedLeague,
      state: selectedState,
      gender: selectedGender,
      search: filterSearch,
      displayLimit: displayLimit
    };
    sessionStorage.setItem(STORAGE_KEYS.filters, JSON.stringify(filters));
  }, [selectedAgeGroup, selectedLeague, selectedState, selectedGender, filterSearch, displayLimit]);

  // Save showDetails state
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEYS.showDetails, showDetails.toString());
  }, [showDetails]);

  // Save viewMode state
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEYS.viewMode, viewMode);
  }, [viewMode]);

  // Restore scroll position when component mounts
  useEffect(() => {
    const savedScrollPos = sessionStorage.getItem(STORAGE_KEYS.scrollPosition);
    if (savedScrollPos && !isLoading) {
      // Small delay to ensure content is rendered
      setTimeout(() => {
        window.scrollTo(0, parseInt(savedScrollPos, 10));
        // Clear the saved position after restoring
        sessionStorage.removeItem(STORAGE_KEYS.scrollPosition);
      }, 100);
    }
  }, [isLoading]);

  // Function to save scroll position before navigating
  const saveScrollPosition = () => {
    sessionStorage.setItem(STORAGE_KEYS.scrollPosition, window.scrollY.toString());
  };

  // Reset display limit when filters change (but not on initial load)
  const isInitialMount = useRef(true);
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    setDisplayLimit(TEAMS_PER_PAGE);
  }, [selectedAgeGroup, selectedLeague, selectedState, selectedGender, filterSearch]);

  // Get current My Teams
  const myTeams = useMemo(() => {
    // Force refresh when key changes
    const _ = myTeamsRefreshKey;
    return getMyTeams();
  }, [getMyTeams, myTeamsRefreshKey]);

  // Get current Followed Teams
  const followedTeams = useMemo(() => {
    const _ = followedTeamsRefreshKey;
    return getFollowedTeams();
  }, [getFollowedTeams, followedTeamsRefreshKey]);

  // Calculate national ranks by gender+age group (based on power score)
  const nationalRanks = useMemo(() => {
    const rankMap = {};

    // Group teams by gender+age group
    const groupedTeams = {};
    teamsData.forEach(team => {
      if (!team.ageGroup) return;
      const key = team.ageGroup; // e.g., "G13", "B14" - already includes gender
      if (!groupedTeams[key]) groupedTeams[key] = [];
      groupedTeams[key].push(team);
    });

    // Sort each group by power score and assign national ranks
    Object.keys(groupedTeams).forEach(ageGroup => {
      const sorted = [...groupedTeams[ageGroup]].sort((a, b) =>
        (b.powerScore || 0) - (a.powerScore || 0)
      );
      sorted.forEach((team, index) => {
        rankMap[team.id] = index + 1;
      });
    });

    return rankMap;
  }, [teamsData]);

  // Filter teams based on selections - rankings are assigned BEFORE search filter is applied
  const filteredTeams = useMemo(() => {
    let filtered = [...teamsData];

    // Apply all filters EXCEPT search first (these affect ranking)
    // Filter by gender (based on age group prefix G or B)
    if (selectedGender !== 'ALL') {
      const genderPrefix = selectedGender === 'Girls' ? 'G' : 'B';
      filtered = filtered.filter(team =>
        team.ageGroup && team.ageGroup.charAt(0).toUpperCase() === genderPrefix
      );
    }

    if (selectedAgeGroup !== 'ALL') {
      filtered = filtered.filter(team => team.ageGroup === selectedAgeGroup);
    }

    if (selectedLeague !== 'ALL') {
      if (selectedLeague === 'ALL_NATIONAL') {
        filtered = filtered.filter(team => NATIONAL_LEAGUES.includes(team.league));
      } else if (selectedLeague === 'ALL_REGIONAL') {
        filtered = filtered.filter(team => REGIONAL_LEAGUES.includes(team.league));
      } else {
        filtered = filtered.filter(team => team.league === selectedLeague);
      }
    }

    if (selectedState !== 'ALL') {
      filtered = filtered.filter(team => team.state === selectedState);
    }

    // Calculate points per game for record sorting (3 pts for win, 1 pt for draw, 0 for loss)
    const getPointsPerGame = (team) => {
      const gamesPlayed = (team.wins || 0) + (team.losses || 0) + (team.draws || 0);
      if (gamesPlayed === 0) return 0;
      const points = (team.wins || 0) * 3 + (team.draws || 0) * 1;
      return points / gamesPlayed;
    };

    // Calculate average goal diff per game
    const getAvgGD = (team) => {
      const gamesPlayed = (team.wins || 0) + (team.losses || 0) + (team.draws || 0);
      if (gamesPlayed === 0) return 0;
      return (team.goalDiff || 0) / gamesPlayed;
    };

    // Sort to determine rankings
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'record':
          const aPPG = getPointsPerGame(a);
          const bPPG = getPointsPerGame(b);
          comparison = bPPG - aPPG;
          // Tiebreaker: team with more games played first
          if (comparison === 0) {
            const aGames = (a.wins || 0) + (a.losses || 0) + (a.draws || 0);
            const bGames = (b.wins || 0) + (b.losses || 0) + (b.draws || 0);
            comparison = bGames - aGames;
          }
          break;
        case 'gd':
          comparison = getAvgGD(b) - getAvgGD(a);
          break;
        case 'offRank':
          // Lower rank is better, handle missing ranks
          const aOffRank = a.offensiveRank || 9999;
          const bOffRank = b.offensiveRank || 9999;
          comparison = aOffRank - bOffRank; // ascending (lower rank first)
          break;
        case 'defRank':
          // Lower rank is better, handle missing ranks
          const aDefRank = a.defensiveRank || 9999;
          const bDefRank = b.defensiveRank || 9999;
          comparison = aDefRank - bDefRank; // ascending (lower rank first)
          break;
        case 'power':
        default:
          comparison = (b.powerScore || 0) - (a.powerScore || 0);
          break;
      }

      // Apply direction (ranks are already in proper direction)
      if (sortField !== 'offRank' && sortField !== 'defRank') {
        return sortDirection === 'asc' ? -comparison : comparison;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    // V43: Separate ranked and unranked teams
    const rankedTeams = filtered.filter(team => team.isRanked !== false);
    const unrankedTeams = filtered.filter(team => team.isRanked === false);

    // Assign rankings AFTER sorting but BEFORE search filter
    // This ensures rankings stay consistent regardless of search
    const totalRankedBeforeSearch = rankedTeams.length;
    const rankedWithDisplayRank = rankedTeams.map((team, index) => ({
      ...team,
      displayRank: index + 1,
      totalRanked: totalRankedBeforeSearch
    }));

    // Unranked teams don't get a display rank - they appear at the bottom
    const unrankedWithFlag = unrankedTeams.map(team => ({
      ...team,
      displayRank: null,
      totalRanked: totalRankedBeforeSearch
    }));

    // Combine: ranked first, then unranked
    let combined = [...rankedWithDisplayRank, ...unrankedWithFlag];

    // NOW apply search filter (this only filters display, doesn't affect rankings)
    if (filterSearch) {
      const term = filterSearch.toLowerCase();
      combined = combined.filter(team =>
        team.name.toLowerCase().includes(term) ||
        (team.club && team.club.toLowerCase().includes(term))
      );
    }

    return combined;
  }, [teamsData, selectedAgeGroup, selectedLeague, selectedState, selectedGender, filterSearch, sortField, sortDirection]);
  
  // Handle column header click for sorting
  const handleSort = (field) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      // New field: set appropriate default direction
      setSortField(field);
      setSortDirection(field === 'offRank' || field === 'defRank' ? 'asc' : 'desc');
    }
  };
  
  // Get sort indicator
  const getSortIndicator = (field) => {
    if (sortField !== field) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  // Filter age groups based on selected gender
  const filteredAgeGroups = useMemo(() => {
    if (selectedGender === 'ALL') return ageGroups;
    const genderPrefix = selectedGender === 'Girls' ? 'G' : 'B';
    return ageGroups.filter(ag => ag.charAt(0).toUpperCase() === genderPrefix);
  }, [ageGroups, selectedGender]);

  // Get full team data for My Teams
  // CRITICAL: Uses findTeamInRankings() helper which does NOT use ID fallback
  // Team IDs are regenerated when rankings are updated and will match wrong teams if used
  const myTeamsFullData = useMemo(() => {
    return myTeams.map(savedTeam => {
      // Use the central helper function - it matches by name/ageGroup/club only
      const fullTeam = findTeamInRankings(savedTeam, teamsData);

      if (fullTeam) {
        return { ...fullTeam, savedId: savedTeam.id };
      }
      // Team not found in current rankings - return saved data with flag
      return { ...savedTeam, notInRankings: true };
    }).filter(Boolean);
  }, [myTeams, teamsData]);

  // Get full team data for Followed Teams
  // CRITICAL: Uses findTeamInRankings() helper which does NOT use ID fallback
  const followedTeamsFullData = useMemo(() => {
    return followedTeams.map(savedTeam => {
      // Use the central helper function - it matches by name/ageGroup/club only
      const fullTeam = findTeamInRankings(savedTeam, teamsData);

      if (fullTeam) {
        return { ...fullTeam, savedId: savedTeam.id, followedAt: savedTeam.followedAt };
      }
      return { ...savedTeam, notInRankings: true };
    }).filter(Boolean);
  }, [followedTeams, teamsData]);

  // Helper to normalize team names for comparison
  const normalizeTeamName = (name) => {
    if (!name) return '';
    return name.toLowerCase()
      .replace(/\s+(ga|ecnl|ecnl-rl|ecnl rl|aspire|npl)$/i, '')
      .trim();
  };

  // Helper to get most recent and next game for a team
  const getTeamGames = useCallback((team) => {
    if (!team || !gamesData) return { recentGame: null, nextGame: null };

    const normalizedTeamName = normalizeTeamName(team.name);
    const teamLeague = (team.league || '').toUpperCase();
    const teamAgeGroup = team.ageGroup || '';
    const today = new Date().toISOString().split('T')[0];

    // Find all games for this team
    const teamGamesFiltered = gamesData.filter(game => {
      const normalizedHome = normalizeTeamName(game.homeTeam);
      const normalizedAway = normalizeTeamName(game.awayTeam);
      const gameLeague = (game.league || '').toUpperCase();

      // Check if team name matches
      const homeMatch = normalizedHome === normalizedTeamName;
      const awayMatch = normalizedAway === normalizedTeamName;

      // Check league match (normalize common variants)
      const normalizeLeague = (lg) => {
        if (!lg) return '';
        lg = lg.toUpperCase();
        if (lg === 'ECNL-RL' || lg === 'ECNL RL') return 'ECNL-RL';
        if (lg === 'GIRLS ACADEMY') return 'GA';
        if (lg.startsWith('MLS NEXT')) return 'MLS NEXT';
        return lg;
      };
      const leagueMatch = normalizeLeague(gameLeague) === normalizeLeague(teamLeague);

      // Check age group if available
      const ageMatch = !game.ageGroup || game.ageGroup === teamAgeGroup;

      return (homeMatch || awayMatch) && leagueMatch && ageMatch;
    });

    // Separate past and future games
    const pastGames = [];
    const futureGames = [];

    teamGamesFiltered.forEach(game => {
      const gameDate = game.date || '';
      const hasScore = game.homeScore !== null && game.homeScore !== undefined &&
                       game.awayScore !== null && game.awayScore !== undefined;

      if (gameDate <= today && hasScore) {
        pastGames.push({ ...game, dateStr: gameDate });
      } else if (gameDate > today) {
        futureGames.push({ ...game, dateStr: gameDate });
      }
    });

    // Sort past games (most recent first) and future games (soonest first)
    pastGames.sort((a, b) => b.dateStr.localeCompare(a.dateStr));
    futureGames.sort((a, b) => a.dateStr.localeCompare(b.dateStr));

    return {
      recentGame: pastGames[0] || null,
      nextGame: futureGames[0] || null
    };
  }, [gamesData]);

  // Teams for the add modal (filtered by search)
  const searchableTeams = useMemo(() => {
    if (!modalSearch) return [];
    const term = modalSearch.toLowerCase();
    return teamsData
      .filter(team => 
        team.name.toLowerCase().includes(term) ||
        (team.club && team.club.toLowerCase().includes(term))
      )
      .slice(0, 20);
  }, [teamsData, modalSearch]);

  // Format the last updated date
  const formatDate = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  // Handle adding team to My Teams
  const handleAddTeam = (team) => {
    if (addToMyTeams(team)) {
      setMyTeamsRefreshKey(prev => prev + 1);
      setModalSearch('');
      setShowAddTeamModal(false);
    }
  };

  // Handle removing team from My Teams
  const handleRemoveTeam = (team) => {
    if (window.confirm('Remove this team from My Teams?')) {
      removeFromMyTeams(team);
      setMyTeamsRefreshKey(prev => prev + 1);
    }
  };

  // Find rank for a team (overall rank, not filtered)
  const getTeamRank = (team) => {
    // First try to find the team in the full data by ID
    const fullTeam = teamsData.find(t => t.id === team.id);
    if (fullTeam && fullTeam.rank) {
      return fullTeam.rank;
    }
    
    // If not found by ID, try to find by name
    const byName = teamsData.find(t => t.name === team.name);
    if (byName && byName.rank) {
      return byName.rank;
    }
    
    // Fallback: calculate rank by sorting
    const sorted = [...teamsData].sort((a, b) => b.powerScore - a.powerScore);
    const idx = sorted.findIndex(t => t.id === team.id || t.name === team.name);
    return idx >= 0 ? idx + 1 : '—';
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">
          Loading rankings data...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">⚠️</div>
          <div className="empty-state-text">{error}</div>
          <p style={{ color: '#666', marginTop: '1rem' }}>
            Make sure <code>rankings_for_react.json</code> is in the <code>public/</code> folder.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* View Mode Toggle and Last Updated - compact header (hidden on mobile) */}
      <div className="card rankings-header-card hide-on-mobile" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setViewMode('rankings')}
              className="view-toggle-btn"
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                background: viewMode === 'rankings' 
                  ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)' 
                  : '#f5f5f5',
                color: viewMode === 'rankings' ? 'white' : '#666',
                transition: 'all 0.2s ease'
              }}
            >
              <TeamsIcon size={16} color="green" /> All Teams
            </button>
            <button
              onClick={() => setViewMode('myteams')}
              className="view-toggle-btn"
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                background: viewMode === 'myteams' 
                  ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)' 
                  : '#f5f5f5',
                color: viewMode === 'myteams' ? 'white' : '#666',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}
            >
              My Teams
              {myTeams.length > 0 && (
              <span style={{
                background: viewMode === 'myteams' ? 'rgba(255,255,255,0.3)' : 'var(--accent-green)',
                color: viewMode === 'myteams' ? 'white' : 'white',
                padding: '0.125rem 0.5rem',
                borderRadius: '10px',
                fontSize: '0.75rem'
              }}>
                {myTeams.length}
              </span>
            )}
          </button>
          </div>
          {lastUpdated && (
            <span style={{ fontSize: '0.75rem', color: '#888' }}>
              Updated: {formatDate(lastUpdated)}
            </span>
          )}
        </div>
      </div>

      {/* Rankings View */}
      {viewMode === 'rankings' && (
        <>
          <div className="card filters-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
            <div className="filters-compact">
              {/* Filter row - Gender/Age, League, State on single row (ABOVE search) */}
              <div className="filter-row" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'nowrap', marginBottom: '0.5rem' }}>
                <div className="filter-group">
                  {/* Mobile: button that opens bottom sheet */}
                  <button
                    className="filter-select mobile-filter-btn"
                    onClick={() => setShowGenderAgeSheet(true)}
                    style={{
                      textAlign: 'left',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <span>
                      {selectedGender === 'ALL' && selectedAgeGroup === 'ALL'
                        ? 'All'
                        : selectedAgeGroup === 'ALL'
                          ? `${selectedGender} - All`
                          : `${selectedGender === 'Girls' ? 'Girls' : 'Boys'} ${selectedAgeGroup}`}
                    </span>
                    <span style={{ marginLeft: '0.5rem', opacity: 0.6 }}>▼</span>
                  </button>
                </div>
                
                <div className="filter-group">
                  <BottomSheetSelect
                    label="League"
                    value={selectedLeague}
                    onChange={setSelectedLeague}
                    options={(() => {
                      // Determine effective gender from selection or age group
                      let effectiveGender = selectedGender;
                      if (selectedGender === 'ALL' && selectedAgeGroup !== 'ALL') {
                        effectiveGender = selectedAgeGroup.startsWith('G') ? 'Girls' : 'Boys';
                      }

                      // Filter leagues based on gender
                      const filterByGender = (league) => {
                        if (effectiveGender === 'Boys' && GIRLS_ONLY_LEAGUES.includes(league)) return false;
                        if (effectiveGender === 'Girls' && BOYS_ONLY_LEAGUES.includes(league)) return false;
                        return true;
                      };

                      const nationalOptions = NATIONAL_LEAGUES
                        .filter(l => leagues.includes(l) && filterByGender(l))
                        .map(league => ({ value: league, label: league }));
                      const regionalOptions = REGIONAL_LEAGUES
                        .filter(l => leagues.includes(l) && filterByGender(l))
                        .map(league => ({ value: league, label: league }));

                      return [
                        { value: 'ALL', label: 'All Leagues' },
                        {
                          group: 'National Leagues',
                          options: [
                            ...(nationalOptions.length > 1 ? [{ value: 'ALL_NATIONAL', label: isElevenUpBrand ? '★ All National Leagues' : '⭐ All National Leagues' }] : []),
                            ...nationalOptions
                          ]
                        },
                        {
                          group: 'Regional Leagues',
                          options: [
                            ...(regionalOptions.length > 1 ? [{ value: 'ALL_REGIONAL', label: isElevenUpBrand ? '★ All Regional Leagues' : '⭐ All Regional Leagues' }] : []),
                            ...regionalOptions
                          ]
                        }
                      ].filter(opt => !opt.group || opt.options.length > 0);
                    })()}
                  />
                </div>

                <div className="filter-group">
                  <BottomSheetSelect
                    label="State"
                    value={selectedState}
                    onChange={setSelectedState}
                    options={[
                      { value: 'ALL', label: 'All States' },
                      { group: 'States', options: states.map(state => ({ value: state, label: state })) }
                    ]}
                  />
                </div>
              </div>

              {/* Search row with Map, My Teams and Following icons (BELOW filters) */}
              <div className="search-row" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <div className="filter-group search-group" style={{ flex: '1', minWidth: '120px', maxWidth: '200px' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Search team or club..."
                    value={filterSearch}
                    onChange={(e) => setFilterSearch(e.target.value)}
                  />
                </div>

                {/* Map - Trifold map with pin */}
                <span
                  onClick={() => setShowMap(true)}
                  title="Show Map"
                  style={{
                    cursor: filteredTeams.length > 0 ? 'pointer' : 'not-allowed',
                    fontSize: '1.4rem',
                    opacity: filteredTeams.length > 0 ? 0.8 : 0.4,
                    transition: 'opacity 0.2s'
                  }}
                >
                  🗺️
                </span>

                {/* My Teams - Teal Heart with count to the right */}
                <span
                  onClick={() => setViewMode(viewMode === 'myteams' ? 'rankings' : 'myteams')}
                  title="My Teams"
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '2px',
                    opacity: viewMode === 'myteams' ? 1 : 0.7,
                    transition: 'opacity 0.2s'
                  }}
                >
                  {isElevenUpBrand ? (
                    <svg width="22" height="22" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))' }}>
                      <defs>
                        <linearGradient id="heartGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#00E676" />
                          <stop offset="50%" stopColor="#1DE9B6" />
                          <stop offset="100%" stopColor="#00BCD4" />
                        </linearGradient>
                        <linearGradient id="heartHighlight" x1="0%" y1="0%" x2="0%" y2="100%">
                          <stop offset="0%" stopColor="#FFFFFF" />
                          <stop offset="100%" stopColor="#69F0AE" />
                        </linearGradient>
                      </defs>
                      <path fill="url(#heartGradient)" stroke="#00ACC1" strokeWidth="0.5" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
                      <path fill="url(#heartHighlight)" opacity="0.4" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" clipPath="inset(0 50% 50% 0)"/>
                    </svg>
                  ) : (
                    <span style={{ fontSize: '1.3rem' }}>❤️</span>
                  )}
                  {myTeams.length > 0 && (
                    <span style={{
                      color: isElevenUpBrand ? '#1DE9B6' : '#e91e63',
                      fontSize: '0.75rem',
                      fontWeight: '700'
                    }}>
                      {myTeams.length}
                    </span>
                  )}
                </span>

                {/* Following - Star with count to the right */}
                <span
                  onClick={() => setViewMode(viewMode === 'following' ? 'rankings' : 'following')}
                  title="Following"
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '2px',
                    opacity: viewMode === 'following' ? 1 : 0.7,
                    transition: 'opacity 0.2s'
                  }}
                >
                  {isElevenUpBrand ? (
                    <svg width="22" height="22" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))' }}>
                      <defs>
                        <linearGradient id="starGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#B2FF59" />
                          <stop offset="50%" stopColor="#76FF03" />
                          <stop offset="100%" stopColor="#00E676" />
                        </linearGradient>
                        <linearGradient id="starHighlight" x1="0%" y1="0%" x2="0%" y2="100%">
                          <stop offset="0%" stopColor="#FFFFFF" />
                          <stop offset="100%" stopColor="#CCFF90" />
                        </linearGradient>
                      </defs>
                      <path fill="url(#starGradient)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                      <path fill="url(#starHighlight)" opacity="0.4" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" clipPath="inset(0 50% 50% 0)"/>
                    </svg>
                  ) : (
                    <span style={{ fontSize: '1.3rem' }}>⭐</span>
                  )}
                  {followedTeams.length > 0 && (
                    <span style={{
                      color: isElevenUpBrand ? '#76FF03' : '#FFD700',
                      fontSize: '0.75rem',
                      fontWeight: '700'
                    }}>
                      {followedTeams.length}
                    </span>
                  )}
                </span>

                {/* Spacer to push details button right */}
                <span style={{ flex: '1' }}></span>

                {/* Details toggle - text with arrow, green to match table */}
                <span
                  onClick={() => setShowDetails(!showDetails)}
                  title={showDetails ? 'Hide details' : 'Show details'}
                  style={{
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    color: '#00C853',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.2rem',
                    whiteSpace: 'nowrap'
                  }}
                >
                  details {showDetails ? '◀' : '▶'}
                </span>
              </div>
            </div>
          </div>

          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {filteredTeams.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem' }}>
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-text">No teams found matching your filters</div>
              </div>
            ) : (
              <div
                className="table-scroll-container"
                ref={tableContainerRef}
                onMouseDown={handleMouseDown}
                onMouseUp={handleMouseUp}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                style={{
                  cursor: 'grab',
                  overflowX: 'auto',
                  touchAction: 'auto'
                }}
              >
                <table className={`data-table rankings-table ${!showDetails ? 'compact-view' : ''}`}>
                  <thead>
                    <tr>
                      <th
                        className="col-rank"
                        onClick={() => handleSort('power')}
                        style={{ cursor: 'pointer' }}
                        title="Sort by Power Score (default ranking)"
                      >
                        {getSortIndicator('power')}
                      </th>
                      <th className="col-natl-rank sticky-col sticky-col-1" style={{ color: 'white', whiteSpace: 'normal', lineHeight: '1.1' }} title="National rank within gender and age group">Nat'l<br/>Rank</th>
                      <th className="col-team sticky-col sticky-col-2" style={{ whiteSpace: 'normal', lineHeight: '1.1' }}>
                        Team<br/>
                        <span style={{ fontWeight: '400', fontSize: '0.7rem', color: '#555' }}>
                          ({filteredTeams.length})
                        </span>
                      </th>
                      {selectedAgeGroup === 'ALL' && <th className="col-age">Age</th>}
                      <th className="col-league">League</th>
                      <th className="col-state">ST</th>
                      {showDetails && <th className="col-power">Power</th>}
                      {showDetails && (
                        <th 
                          className="sortable-header"
                          onClick={() => handleSort('record')}
                          style={{ cursor: 'pointer' }}
                          title="Sort by Record (3 pts/win, 1 pt/draw)"
                        >
                          Record{getSortIndicator('record')}
                        </th>
                      )}
                      {showDetails && (
                        <th 
                          className="sortable-header"
                          onClick={() => handleSort('gd')}
                          style={{ cursor: 'pointer' }}
                          title="Sort by Avg Goal Differential per game"
                        >
                          GD{getSortIndicator('gd')}
                        </th>
                      )}
                      {showDetails && (
                        <th 
                          className="sortable-header col-narrow"
                          onClick={() => handleSort('offRank')}
                          style={{ cursor: 'pointer', whiteSpace: 'normal', lineHeight: '1.1' }}
                          title="Sort by Offensive Rank"
                        >
                          Off<br/>Rank{getSortIndicator('offRank')}
                        </th>
                      )}
                      {showDetails && <th className="col-narrow" style={{ whiteSpace: 'normal', lineHeight: '1.1' }} title="Offensive Power Score">Off<br/>Score</th>}
                      {showDetails && (
                        <th 
                          className="sortable-header col-narrow"
                          onClick={() => handleSort('defRank')}
                          style={{ cursor: 'pointer', whiteSpace: 'normal', lineHeight: '1.1' }}
                          title="Sort by Defensive Rank"
                        >
                          Def<br/>Rank{getSortIndicator('defRank')}
                        </th>
                      )}
                      {showDetails && <th className="col-narrow" style={{ whiteSpace: 'normal', lineHeight: '1.1' }} title="Defensive Power Score">Def<br/>Score</th>}
                      {showDetails && <th className="col-win-loss" title="Best Win">Best Win</th>}
                      {showDetails && <th className="col-win-loss" title="2nd Best Win">2nd Best</th>}
                      {showDetails && <th className="col-win-loss" title="Worst Loss">Worst Loss</th>}
                      {showDetails && <th className="col-win-loss" title="2nd Worst Loss">2nd Worst</th>}
                      <th style={{ width: '40px' }} title="Follow Team">
                        {isElevenUpBrand ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 1px 1px rgba(0,0,0,0.2))' }}>
                            <defs>
                              <linearGradient id="headerStarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stopColor="#B2FF59" />
                                <stop offset="50%" stopColor="#76FF03" />
                                <stop offset="100%" stopColor="#00E676" />
                              </linearGradient>
                            </defs>
                            <path fill="url(#headerStarGrad)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                          </svg>
                        ) : '⭐'}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTeams.slice(0, displayLimit).map((team, index) => {
                      // Calculate average GD per game
                      const gamesPlayed = (team.wins || 0) + (team.losses || 0) + (team.draws || 0);
                      const avgGD = gamesPlayed > 0 ? (team.goalDiff || 0) / gamesPlayed : 0;
                      const isUnranked = team.isRanked === false;

                      return (
                      <tr key={team.id} style={isUnranked ? { opacity: 0.7, backgroundColor: '#f9f9f9' } : {}}>
                        <td className="rank-cell col-rank">{isUnranked ? '—' : `#${team.displayRank}`}</td>
                        <td className="col-natl-rank sticky-col sticky-col-1">{isUnranked ? '—' : `#${nationalRanks[team.id] || '—'}`}</td>
                        <td className="col-team sticky-col sticky-col-2">
                          <Link
                            to={`/team/${team.id}`}
                            className="team-name-link"
                            onClick={saveScrollPosition}
                          >
                            {team.name} {team.ageGroup}{isUnranked ? ' (unranked)' : ''}
                          </Link>
                        </td>
                        {selectedAgeGroup === 'ALL' && <td className="col-age">{team.ageGroup}</td>}
                        <td className="col-league">
                          <span className="league-badge-sm" style={getLeagueBadgeStyle(team.league)}>
                            {team.league}
                          </span>
                        </td>
                        <td className="col-state">{team.state || '-'}</td>
                        {showDetails && <td className="col-power power-score" style={{ fontWeight: '600' }}>{team.powerScore?.toFixed(1) || '0.0'}</td>}
                        {showDetails && <td>{team.wins}-{team.losses}-{team.draws}</td>}
                        {showDetails && (
                          <td style={{ 
                            color: avgGD > 0 ? '#66bb6a' : avgGD < 0 ? '#ef5350' : '#888',
                            fontWeight: '600',
                            textAlign: 'center'
                          }}>
                            {avgGD > 0 ? '+' : ''}{avgGD.toFixed(1)}
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-narrow" style={{ textAlign: 'center', fontWeight: '500' }}>
                            {team.offensiveRank ? `#${team.offensiveRank}` : '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-narrow" style={{
                            textAlign: 'center',
                            fontWeight: '600'
                          }}>
                            {team.offensivePowerScore?.toFixed(0) || '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-narrow" style={{ textAlign: 'center', fontWeight: '500' }}>
                            {team.defensiveRank ? `#${team.defensiveRank}` : '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-narrow" style={{
                            textAlign: 'center',
                            fontWeight: '600'
                          }}>
                            {team.defensivePowerScore?.toFixed(0) || '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-win-loss">
                            <TruncatedCell text={team.bestWin} color="#66bb6a" maxWidth="200px" />
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-win-loss">
                            <TruncatedCell text={team.secondBestWin} color="#66bb6a" maxWidth="200px" />
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-win-loss">
                            <TruncatedCell text={team.worstLoss} color="#ef5350" maxWidth="200px" />
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-win-loss">
                            <TruncatedCell text={team.secondWorstLoss} color="#ef5350" maxWidth="200px" />
                          </td>
                        )}
                        {showDetails && (
                          <td className="col-league">
                            <span className="league-badge-sm" style={getLeagueBadgeStyle(team.league)}>
                              {team.league}
                            </span>
                          </td>
                        )}
                        <td>
                          <button
                            onClick={() => {
                              if (isFollowing(team)) {
                                unfollowTeam(team);
                              } else {
                                followTeam(team);
                              }
                              setFollowedTeamsRefreshKey(prev => prev + 1);
                            }}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              padding: '0.25rem',
                              opacity: isFollowing(team) ? 1 : 0.3,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}
                            title={isFollowing(team) ? 'Unfollow Team' : 'Follow Team'}
                            onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                            onMouseLeave={(e) => e.currentTarget.style.opacity = isFollowing(team) ? 1 : 0.3}
                          >
                            {isFollowing(team) ? (
                              isElevenUpBrand ? (
                                <svg width="20" height="20" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 1px 1px rgba(0,0,0,0.2))' }}>
                                  <defs>
                                    <linearGradient id={`rowStarGrad${team.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                                      <stop offset="0%" stopColor="#B2FF59" />
                                      <stop offset="50%" stopColor="#76FF03" />
                                      <stop offset="100%" stopColor="#00E676" />
                                    </linearGradient>
                                  </defs>
                                  <path fill={`url(#rowStarGrad${team.id})`} stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                                </svg>
                              ) : <span style={{ fontSize: '1.2rem' }}>⭐</span>
                            ) : (
                              isElevenUpBrand ? (
                                <svg width="20" height="20" viewBox="0 0 24 24">
                                  <path fill="none" stroke="#999" strokeWidth="1.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                                </svg>
                              ) : <span style={{ fontSize: '1.2rem' }}>☆</span>
                            )}
                          </button>
                        </td>
                      </tr>
                    );
                    })}
                  </tbody>
                </table>
                
                {/* Load More button for pagination */}
                {displayLimit < filteredTeams.length && (
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    gap: '1rem',
                    marginTop: '1.5rem',
                    padding: '1rem',
                    background: '#f8f9fa',
                    borderRadius: '8px'
                  }}>
                    <button
                      onClick={() => setDisplayLimit(prev => Math.min(prev + TEAMS_PER_PAGE, filteredTeams.length))}
                      className="btn btn-primary"
                      style={{ padding: '0.75rem 2rem' }}
                    >
                      Load {Math.min(TEAMS_PER_PAGE, filteredTeams.length - displayLimit)} More Teams
                    </button>
                    <button
                      onClick={() => setDisplayLimit(filteredTeams.length)}
                      className="btn btn-secondary"
                      style={{ padding: '0.75rem 1.5rem' }}
                    >
                      Load All ({filteredTeams.length})
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* My Teams View */}
      {viewMode === 'myteams' && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {/* All Teams button - mobile only */}
              <button
                className="all-teams-btn-mobile show-on-mobile"
                onClick={() => setViewMode('rankings')}
                style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  background: '#f5f5f5',
                  color: '#666',
                  display: 'none', // hidden by default, shown on mobile via CSS
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                ← All Teams
              </button>
              <h2 className="card-title" style={{ margin: 0 }}>
                My Teams ({myTeams.length}/5)
              </h2>
            </div>
            {canPerform('canSaveMyTeams') && myTeams.length < 5 && (
              <button
                onClick={() => setShowAddTeamModal(true)}
                className="btn btn-primary"
              >
                + Add Team
              </button>
            )}
          </div>

          {/* Guest/Free account notice */}
          {isGuest && (
            <div style={{
              padding: '1rem',
              background: '#fff3e0',
              borderRadius: '8px',
              marginBottom: '1rem',
              border: '1px solid #ffcc80'
            }}>
              <p style={{ margin: 0, color: '#e65100', fontWeight: '500' }}>
                👤 You're browsing as a Guest. Create a free account to save your favorite teams!
              </p>
            </div>
          )}

          {/* Show loading while user data is loading */}
          {!userDataReady && !isGuest ? (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ animation: 'pulse 1.5s ease-in-out infinite', fontSize: '3rem' }}>
                {isElevenUpBrand ? (
                  <svg width="48" height="48" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }}>
                    <defs>
                      <linearGradient id="loadingStarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#B2FF59" />
                        <stop offset="50%" stopColor="#76FF03" />
                        <stop offset="100%" stopColor="#00E676" />
                      </linearGradient>
                    </defs>
                    <path fill="url(#loadingStarGrad)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ) : '⭐'}
              </div>
              <div className="empty-state-text">Loading your teams...</div>
            </div>
          ) : myTeams.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ fontSize: '3rem' }}>
                {isElevenUpBrand ? (
                  <svg width="48" height="48" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }}>
                    <defs>
                      <linearGradient id="emptyStateStarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#B2FF59" />
                        <stop offset="50%" stopColor="#76FF03" />
                        <stop offset="100%" stopColor="#00E676" />
                      </linearGradient>
                    </defs>
                    <path fill="url(#emptyStateStarGrad)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ) : '⭐'}
              </div>
              <div className="empty-state-text">
                {canPerform('canSaveMyTeams') 
                  ? "You haven't added any teams yet" 
                  : "Create a free account to save your favorite teams"}
              </div>
              <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                {canPerform('canSaveMyTeams') 
                  ? "Add up to 5 teams to quickly track their rankings and stats"
                  : "As a guest, you can browse all rankings but can't save teams"}
              </p>
              {canPerform('canSaveMyTeams') && (
                <button 
                  onClick={() => setShowAddTeamModal(true)}
                  className="btn btn-primary"
                  style={{ marginTop: '1rem' }}
                >
                  + Add Your First Team
                </button>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {myTeamsFullData.map((team, idx) => {
                const rank = getTeamRank(team);
                return (
                  <div
                    key={team.id}
                    style={{
                      background: 'linear-gradient(135deg, #fff 0%, #f8f9fa 100%)',
                      borderRadius: '16px',
                      padding: '1.5rem',
                      border: '2px solid #e0e0e0',
                      position: 'relative'
                    }}
                  >
                    {/* Remove button */}
                    {canPerform('canSaveMyTeams') && (
                      <button
                        onClick={() => handleRemoveTeam(team)}
                        style={{
                          position: 'absolute',
                          top: '1rem',
                          right: '1rem',
                          background: '#fee',
                          border: '1px solid #fcc',
                          color: '#c33',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          fontWeight: '600'
                        }}
                      >
                        Remove
                      </button>
                    )}

                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem', flexWrap: 'wrap' }}>
                      {/* Rank Badge */}
                      <div style={{
                        background: 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)',
                        color: 'white',
                        width: '70px',
                        height: '70px',
                        borderRadius: '12px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        <div style={{ fontSize: '0.7rem', opacity: 0.9 }}>RANK</div>
                        <div style={{ fontSize: '1.75rem', fontWeight: '700' }}>#{rank}</div>
                      </div>

                      {/* Team Info */}
                      <div style={{ flex: 1, minWidth: '200px', paddingRight: '5rem' }}>
                        <Link
                          to={`/team/${team.id}`}
                          style={{
                            fontSize: '1.35rem',
                            fontWeight: '700',
                            color: 'var(--primary-green)',
                            textDecoration: 'none'
                          }}
                        >
                          {team.name} {team.ageGroup} →
                        </Link>
                        <div style={{
                          display: 'flex',
                          gap: '0.75rem',
                          marginTop: '0.5rem',
                          flexWrap: 'wrap',
                          alignItems: 'center'
                        }}>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            ...getLeagueBadgeStyle(team.league)
                          }}>
                            {team.league}
                          </span>
                          <span style={{ color: '#666', fontSize: '0.9rem' }}>
                            {team.ageGroup}
                          </span>
                          {team.state && (
                            <span style={{ color: '#888', fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                              <TournamentIcon size={14} color="gray" /> {team.state}
                            </span>
                          )}
                        </div>
                        <Link 
                          to={`/club/${encodeURIComponent(team.club)}`}
                          style={{ 
                            display: 'block',
                            marginTop: '0.5rem',
                            color: '#666',
                            fontSize: '0.9rem',
                            textDecoration: 'none'
                          }}
                        >
                          {team.club} →
                        </Link>
                      </div>

                      {/* Stats */}
                      <div className="my-teams-stats-grid">
                        <div style={{ textAlign: 'center' }}>
                          <div style={{
                            fontSize: '1.5rem',
                            fontWeight: '700',
                            color: 'var(--primary-green)'
                          }}>
                            {team.powerScore?.toFixed(1) || '—'}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>
                            Power
                          </div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{
                            fontSize: '1.5rem',
                            fontWeight: '700',
                            color: '#333'
                          }}>
                            {team.wins || 0}-{team.losses || 0}-{team.draws || 0}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>
                            Record
                          </div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{
                            fontSize: '1.5rem',
                            fontWeight: '700',
                            color: team.goalDiff > 0 ? '#2e7d32' : team.goalDiff < 0 ? '#c62828' : '#666'
                          }}>
                            {team.goalDiff > 0 ? '+' : ''}{team.goalDiff || 0}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>
                            Goal Diff
                          </div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{
                            fontSize: '1.5rem',
                            fontWeight: '700',
                            color: '#333'
                          }}>
                            {((team.winPct || 0) * 100).toFixed(0)}%
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>
                            Win %
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Daily Update Preview (Pro users only) */}
                    {(() => {
                      const teamKey = `${team.name?.toLowerCase() || ''}_${team.ageGroup?.toLowerCase() || ''}`;
                      const latestUpdate = dailyUpdateHelpers.getLatestUpdate(teamKey);
                      const updateCount = dailyUpdateHelpers.getUpdatesForTeam(teamKey).length;

                      if (latestUpdate) {
                        // Extract first section (before first double newline)
                        const preview = latestUpdate.content?.split('\n\n')[0]?.replace(/\*\*/g, '') || '';
                        const updateDate = new Date(latestUpdate.generatedAt);
                        const isToday = updateDate.toDateString() === new Date().toDateString();

                        return (
                          <div style={{
                            marginTop: '1rem',
                            padding: '0.75rem',
                            background: 'linear-gradient(135deg, #f0f7ff 0%, #e3f2fd 100%)',
                            borderRadius: '8px',
                            borderLeft: '3px solid var(--primary-green)'
                          }}>
                            <div style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginBottom: '0.5rem'
                            }}>
                              <span style={{
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                color: 'var(--primary-green)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem'
                              }}>
                                ... Daily Update
                                {isToday && (
                                  <span style={{
                                    background: 'var(--primary-green)',
                                    color: 'white',
                                    padding: '0.1rem 0.4rem',
                                    borderRadius: '10px',
                                    fontSize: '0.65rem'
                                  }}>NEW</span>
                                )}
                              </span>
                              <span style={{
                                fontSize: '0.65rem',
                                color: '#888'
                              }}>
                                {updateCount} update{updateCount > 1 ? 's' : ''}
                              </span>
                            </div>
                            <p style={{
                              fontSize: '0.8rem',
                              color: '#555',
                              margin: 0,
                              lineHeight: '1.4',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {preview}
                            </p>
                            <Link
                              to={`/team/${team.id}`}
                              style={{
                                display: 'inline-block',
                                marginTop: '0.5rem',
                                fontSize: '0.75rem',
                                color: 'var(--primary-green)',
                                fontWeight: '600',
                                textDecoration: 'none'
                              }}
                            >
                              View Full Update →
                            </Link>
                          </div>
                        );
                      }

                      return null;
                    })()}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Following View */}
      {viewMode === 'following' && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <button
                className="all-teams-btn-mobile show-on-mobile"
                onClick={() => setViewMode('rankings')}
                style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  background: '#f5f5f5',
                  color: '#666',
                  display: 'none',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                ← All Teams
              </button>
              <h2 className="card-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {isElevenUpBrand ? (
                  <svg width="24" height="24" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))' }}>
                    <defs>
                      <linearGradient id="followingTitleStarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#B2FF59" />
                        <stop offset="50%" stopColor="#76FF03" />
                        <stop offset="100%" stopColor="#00E676" />
                      </linearGradient>
                    </defs>
                    <path fill="url(#followingTitleStarGrad)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ) : <span style={{ fontSize: '1.5rem' }}>⭐</span>}
                Following ({followedTeams.length})
              </h2>
            </div>
            {followedTeams.length > 0 && (
              <button
                onClick={() => setFollowingQuickView(!followingQuickView)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  background: followingQuickView
                    ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)'
                    : '#f5f5f5',
                  color: followingQuickView ? 'white' : '#666',
                  transition: 'all 0.2s ease'
                }}
              >
                {followingQuickView ? 'Detailed View' : 'Quick View'}
              </button>
            )}
          </div>

          {isGuest && (
            <div style={{
              padding: '1rem',
              background: '#fff3e0',
              borderRadius: '8px',
              marginBottom: '1rem',
              border: '1px solid #ffcc80'
            }}>
              <p style={{ margin: 0, color: '#e65100', fontWeight: '500' }}>
                👤 You're browsing as a Guest. Create a free account to follow teams!
              </p>
            </div>
          )}

          {/* Show loading while user data is loading */}
          {!userDataReady && !isGuest ? (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ animation: 'pulse 1.5s ease-in-out infinite', fontSize: '3rem' }}>
                {isElevenUpBrand ? (
                  <svg width="48" height="48" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }}>
                    <defs>
                      <linearGradient id="loadingStarGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#B2FF59" />
                        <stop offset="50%" stopColor="#76FF03" />
                        <stop offset="100%" stopColor="#00E676" />
                      </linearGradient>
                    </defs>
                    <path fill="url(#loadingStarGrad2)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ) : '⭐'}
              </div>
              <div className="empty-state-text">Loading followed teams...</div>
            </div>
          ) : followedTeams.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ fontSize: '3rem' }}>
                {isElevenUpBrand ? (
                  <svg width="48" height="48" viewBox="0 0 24 24" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }}>
                    <defs>
                      <linearGradient id="emptyStateStarGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#B2FF59" />
                        <stop offset="50%" stopColor="#76FF03" />
                        <stop offset="100%" stopColor="#00E676" />
                      </linearGradient>
                    </defs>
                    <path fill="url(#emptyStateStarGrad2)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ) : '⭐'}
              </div>
              <div className="empty-state-text">
                {!isGuest
                  ? "You're not following any teams yet"
                  : "Create a free account to follow teams"}
              </div>
              <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                {!isGuest
                  ? "Click the star ☆ next to any team in the rankings to follow them"
                  : "As a guest, you can browse all rankings but can't follow teams"}
              </p>
            </div>
          ) : followingQuickView ? (
            /* Quick View - All Games Consolidated */
            (() => {
              // Gather all games from all followed teams
              const allRecentGames = [];
              const allUpcomingGames = [];

              followedTeamsFullData.forEach(team => {
                const { recentGame, nextGame } = getTeamGames(team);
                const normalizedTeam = normalizeTeamName(team.name);

                if (recentGame) {
                  const isHome = normalizeTeamName(recentGame.homeTeam) === normalizedTeam;
                  const teamScore = isHome ? recentGame.homeScore : recentGame.awayScore;
                  const oppScore = isHome ? recentGame.awayScore : recentGame.homeScore;
                  const opponent = isHome ? recentGame.awayTeam : recentGame.homeTeam;
                  let result = 'D';
                  let resultColor = '#666';
                  if (teamScore > oppScore) { result = 'W'; resultColor = '#2e7d32'; }
                  else if (teamScore < oppScore) { result = 'L'; resultColor = '#c62828'; }

                  allRecentGames.push({
                    team,
                    game: recentGame,
                    opponent,
                    teamScore,
                    oppScore,
                    result,
                    resultColor,
                    date: recentGame.date
                  });
                }

                if (nextGame) {
                  const isHome = normalizeTeamName(nextGame.homeTeam) === normalizedTeam;
                  const opponent = isHome ? nextGame.awayTeam : nextGame.homeTeam;

                  allUpcomingGames.push({
                    team,
                    game: nextGame,
                    opponent,
                    date: nextGame.date
                  });
                }
              });

              // Sort recent games by date (most recent first)
              allRecentGames.sort((a, b) => b.date.localeCompare(a.date));
              // Sort upcoming games by date (soonest first)
              allUpcomingGames.sort((a, b) => a.date.localeCompare(b.date));

              const formatGameDate = (dateStr) => {
                if (!dateStr) return '';
                const date = new Date(dateStr + 'T12:00:00');
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              };

              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  {/* Recent Games Section */}
                  <div>
                    <h3 style={{
                      margin: '0 0 0.75rem 0',
                      fontSize: '1rem',
                      fontWeight: '600',
                      color: '#333',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      📊 Recent Results
                      <span style={{
                        background: '#e8f5e9',
                        color: 'var(--primary-green)',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '10px',
                        fontSize: '0.75rem'
                      }}>
                        {allRecentGames.length}
                      </span>
                    </h3>
                    {allRecentGames.length === 0 ? (
                      <div style={{
                        padding: '1rem',
                        background: '#f5f5f5',
                        borderRadius: '8px',
                        color: '#888',
                        textAlign: 'center'
                      }}>
                        No recent games found
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {allRecentGames.map((item, idx) => (
                          <div
                            key={`recent-${idx}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.75rem',
                              padding: '0.75rem',
                              background: '#fff',
                              border: '1px solid #e0e0e0',
                              borderRadius: '8px'
                            }}
                          >
                            <div style={{
                              fontWeight: '700',
                              fontSize: '1rem',
                              color: item.resultColor,
                              width: '50px',
                              textAlign: 'center'
                            }}>
                              {item.result} {item.teamScore}-{item.oppScore}
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Link
                                to={`/team/${item.team.id}`}
                                style={{
                                  fontWeight: '600',
                                  color: 'var(--primary-green)',
                                  textDecoration: 'none',
                                  fontSize: '0.9rem'
                                }}
                              >
                                {item.team.name} {item.team.ageGroup}
                              </Link>
                              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                                vs {item.opponent} {item.opponentAgeGroup || ''}
                              </div>
                            </div>
                            <div style={{
                              fontSize: '0.75rem',
                              color: '#888',
                              textAlign: 'right',
                              flexShrink: 0
                            }}>
                              {formatGameDate(item.date)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Upcoming Games Section */}
                  <div>
                    <h3 style={{
                      margin: '0 0 0.75rem 0',
                      fontSize: '1rem',
                      fontWeight: '600',
                      color: '#333',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      📅 Upcoming Games
                      <span style={{
                        background: '#e3f2fd',
                        color: '#1565c0',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '10px',
                        fontSize: '0.75rem'
                      }}>
                        {allUpcomingGames.length}
                      </span>
                    </h3>
                    {allUpcomingGames.length === 0 ? (
                      <div style={{
                        padding: '1rem',
                        background: '#e3f2fd',
                        borderRadius: '8px',
                        color: '#888',
                        textAlign: 'center'
                      }}>
                        No upcoming games scheduled
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {allUpcomingGames.map((item, idx) => (
                          <div
                            key={`upcoming-${idx}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.75rem',
                              padding: '0.75rem',
                              background: '#e3f2fd',
                              border: '1px solid #bbdefb',
                              borderRadius: '8px'
                            }}
                          >
                            <div style={{
                              fontWeight: '600',
                              fontSize: '0.85rem',
                              color: '#1565c0',
                              width: '50px',
                              textAlign: 'center'
                            }}>
                              {formatGameDate(item.date)}
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Link
                                to={`/team/${item.team.id}`}
                                style={{
                                  fontWeight: '600',
                                  color: 'var(--primary-green)',
                                  textDecoration: 'none',
                                  fontSize: '0.9rem'
                                }}
                              >
                                {item.team.name} {item.team.ageGroup}
                              </Link>
                              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                                vs {item.opponent} {item.opponentAgeGroup || ''}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })()
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {followedTeamsFullData.map((team) => {
                const rank = getTeamRank(team);
                return (
                  <div
                    key={team.id}
                    style={{
                      background: '#fff',
                      borderRadius: '12px',
                      padding: '1rem',
                      border: '1px solid #e0e0e0',
                      position: 'relative'
                    }}
                  >
                    {/* Unfollow button */}
                    <button
                      onClick={() => {
                        unfollowTeam(team);
                        setFollowedTeamsRefreshKey(prev => prev + 1);
                      }}
                      style={{
                        position: 'absolute',
                        top: '0.75rem',
                        right: '0.75rem',
                        background: '#fee',
                        border: '1px solid #fcc',
                        color: '#c33',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: '600'
                      }}
                    >
                      Unfollow
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingRight: '5rem' }}>
                      {/* Rank Badge */}
                      <div style={{
                        background: 'var(--primary-green)',
                        color: 'white',
                        width: '50px',
                        height: '50px',
                        borderRadius: '8px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        <div style={{ fontSize: '0.6rem', opacity: 0.9 }}>RANK</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: '700' }}>#{rank}</div>
                      </div>

                      {/* Team Info */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Link
                          to={`/team/${team.id}`}
                          style={{
                            fontSize: '1.1rem',
                            fontWeight: '700',
                            color: 'var(--primary-green)',
                            textDecoration: 'none',
                            display: 'block',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {team.name} {team.ageGroup} →
                        </Link>
                        <div style={{
                          display: 'flex',
                          gap: '0.5rem',
                          marginTop: '0.25rem',
                          flexWrap: 'wrap',
                          alignItems: 'center'
                        }}>
                          <span style={{
                            padding: '0.15rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            ...getLeagueBadgeStyle(team.league)
                          }}>
                            {team.league}
                          </span>
                          <span style={{ color: '#666', fontSize: '0.8rem' }}>
                            {team.ageGroup}
                          </span>
                          {team.state && (
                            <span style={{ color: '#888', fontSize: '0.8rem' }}>
                              {team.state}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Stats Row */}
                    <div style={{
                      display: 'flex',
                      gap: '1rem',
                      marginTop: '0.75rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid #eee',
                      justifyContent: 'space-around',
                      flexWrap: 'wrap'
                    }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#333' }}>
                          {team.powerScore?.toFixed(1) || '—'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>
                          Power
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#333' }}>
                          {team.wins || 0}-{team.losses || 0}-{team.draws || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>
                          Record
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{
                          fontSize: '1.1rem',
                          fontWeight: '700',
                          color: team.goalDiff > 0 ? '#2e7d32' : team.goalDiff < 0 ? '#c62828' : '#666'
                        }}>
                          {team.goalDiff > 0 ? '+' : ''}{team.goalDiff || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>
                          Goal Diff
                        </div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#333' }}>
                          {((team.winPct || 0) * 100).toFixed(0)}%
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>
                          Win %
                        </div>
                      </div>
                    </div>

                    {/* Recent & Upcoming Games */}
                    {(() => {
                      const { recentGame, nextGame } = getTeamGames(team);
                      const normalizedTeam = normalizeTeamName(team.name);

                      const formatGameDate = (game) => {
                        if (!game.date) return '';
                        const date = new Date(game.date + 'T12:00:00');
                        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                      };

                      const getOpponent = (game) => {
                        const isHome = normalizeTeamName(game.homeTeam) === normalizedTeam;
                        return isHome ? game.awayTeam : game.homeTeam;
                      };

                      const getResult = (game) => {
                        const isHome = normalizeTeamName(game.homeTeam) === normalizedTeam;
                        const teamScore = isHome ? game.homeScore : game.awayScore;
                        const oppScore = isHome ? game.awayScore : game.homeScore;
                        if (teamScore > oppScore) return { text: 'W', color: '#2e7d32' };
                        if (teamScore < oppScore) return { text: 'L', color: '#c62828' };
                        return { text: 'D', color: '#666' };
                      };

                      const getScore = (game) => {
                        const isHome = normalizeTeamName(game.homeTeam) === normalizedTeam;
                        const teamScore = isHome ? game.homeScore : game.awayScore;
                        const oppScore = isHome ? game.awayScore : game.homeScore;
                        return `${teamScore}-${oppScore}`;
                      };

                      return (
                        <div style={{
                          display: 'flex',
                          gap: '1rem',
                          marginTop: '0.75rem',
                          flexWrap: 'wrap'
                        }}>
                          {recentGame ? (
                            <div style={{
                              flex: '1 1 200px',
                              padding: '0.5rem',
                              background: '#f5f5f5',
                              borderRadius: '6px',
                              fontSize: '0.8rem'
                            }}>
                              <div style={{ fontWeight: '600', color: '#555', marginBottom: '0.25rem' }}>
                                Last Result
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{
                                  fontWeight: '700',
                                  color: getResult(recentGame).color,
                                  fontSize: '0.9rem'
                                }}>
                                  {getResult(recentGame).text} {getScore(recentGame)}
                                </span>
                                <span style={{ color: '#666' }}>vs {getOpponent(recentGame)}</span>
                              </div>
                              <div style={{ color: '#888', fontSize: '0.7rem', marginTop: '0.25rem' }}>
                                {formatGameDate(recentGame)}
                              </div>
                            </div>
                          ) : (
                            <div style={{
                              flex: '1 1 200px',
                              padding: '0.5rem',
                              background: '#f5f5f5',
                              borderRadius: '6px',
                              fontSize: '0.8rem',
                              color: '#888'
                            }}>
                              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>Last Result</div>
                              <div>No recent games</div>
                            </div>
                          )}
                          {nextGame ? (
                            <div style={{
                              flex: '1 1 200px',
                              padding: '0.5rem',
                              background: '#e3f2fd',
                              borderRadius: '6px',
                              fontSize: '0.8rem'
                            }}>
                              <div style={{ fontWeight: '600', color: '#1565c0', marginBottom: '0.25rem' }}>
                                Next Game
                              </div>
                              <div style={{ color: '#333' }}>
                                vs {getOpponent(nextGame)}
                              </div>
                              <div style={{ color: '#1565c0', fontSize: '0.7rem', marginTop: '0.25rem' }}>
                                {formatGameDate(nextGame)}
                                {nextGame.game_time && ` at ${nextGame.game_time}`}
                              </div>
                            </div>
                          ) : (
                            <div style={{
                              flex: '1 1 200px',
                              padding: '0.5rem',
                              background: '#e3f2fd',
                              borderRadius: '6px',
                              fontSize: '0.8rem',
                              color: '#888'
                            }}>
                              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>Next Game</div>
                              <div>No scheduled games</div>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Add Team Modal */}
      {showAddTeamModal && (
        <div 
          className="modal-overlay" 
          onClick={() => {
            setShowAddTeamModal(false);
            setModalSearch('');
          }}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Add Team to My Teams</h2>
              <p style={{ color: '#666', margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>
                {myTeams.length}/5 teams added
              </p>
            </div>
            
            <div className="form-group">
              <label className="form-label">Search for a team</label>
              <input
                type="text"
                className="form-input"
                value={modalSearch}
                onChange={(e) => setModalSearch(e.target.value)}
                placeholder="Type team or club name..."
                autoFocus
              />
            </div>

            {modalSearch && (
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {searchableTeams.length === 0 ? (
                  <div style={{ 
                    padding: '2rem', 
                    textAlign: 'center', 
                    color: '#888' 
                  }}>
                    No teams found matching "{modalSearch}"
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {searchableTeams.map(team => {
                      const alreadyAdded = isInMyTeams(team);
                      return (
                        <div
                          key={team.id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '0.75rem 1rem',
                            background: alreadyAdded ? '#f0f7ed' : '#f8f9fa',
                            borderRadius: '8px',
                            border: alreadyAdded ? '2px solid var(--accent-green)' : '2px solid transparent'
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: '600', color: '#333' }}>
                              {team.name} {team.ageGroup}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#666' }}>
                              {team.club} • {team.league}
                              {team.state && ` • ${team.state}`}
                            </div>
                          </div>
                          {alreadyAdded ? (
                            <span style={{
                              padding: '0.25rem 0.75rem',
                              background: 'var(--accent-green)',
                              color: 'white',
                              borderRadius: '6px',
                              fontSize: '0.85rem',
                              fontWeight: '600',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.35rem'
                            }}>
                              {isElevenUpBrand ? (
                                <svg width="16" height="16" viewBox="0 0 24 24">
                                  <defs>
                                    <linearGradient id="addedStarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                      <stop offset="0%" stopColor="#B2FF59" />
                                      <stop offset="50%" stopColor="#76FF03" />
                                      <stop offset="100%" stopColor="#00E676" />
                                    </linearGradient>
                                  </defs>
                                  <path fill="url(#addedStarGrad)" stroke="#00C853" strokeWidth="0.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                                </svg>
                              ) : '⭐'}
                              Added
                            </span>
                          ) : (
                            <button
                              onClick={() => handleAddTeam(team)}
                              className="btn btn-primary"
                              style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                            >
                              + Add
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {!modalSearch && (
              <div style={{ 
                padding: '2rem', 
                textAlign: 'center', 
                color: '#888' 
              }}>
                Start typing to search for teams
              </div>
            )}

            <div className="modal-actions">
              <button 
                onClick={() => {
                  setShowAddTeamModal(false);
                  setModalSearch('');
                }}
                className="btn btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rankings Map Modal */}
      {showMap && (
        <RankingsMap
          teams={filteredTeams}
          onClose={() => setShowMap(false)}
        />
      )}

      {/* Gender/Age Bottom Sheet */}
      {showGenderAgeSheet && (
        <div
          className="bottom-sheet-overlay"
          onClick={() => setShowGenderAgeSheet(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 3000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'white',
              borderRadius: '16px',
              width: '100%',
              maxWidth: '600px',
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
            }}
          >
            {/* Header */}
            <div style={{
              padding: '1rem 1.25rem',
              borderBottom: '1px solid #e0e0e0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexShrink: 0
            }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: 'var(--primary-green)' }}>
                Select Gender/Age
              </h3>
              <button
                onClick={() => setShowGenderAgeSheet(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: '#666',
                  padding: '0.25rem',
                  lineHeight: 1
                }}
              >
                ×
              </button>
            </div>

            {/* Options */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '1rem 1.25rem'
            }}>
              {/* All Option */}
              <button
                onClick={() => {
                  setSelectedGender('ALL');
                  setSelectedAgeGroup('ALL');
                  setShowGenderAgeSheet(false);
                }}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  marginBottom: '1rem',
                  border: selectedGender === 'ALL' && selectedAgeGroup === 'ALL' ? '2px solid var(--primary-green)' : '1px solid #ddd',
                  borderRadius: '8px',
                  background: selectedGender === 'ALL' && selectedAgeGroup === 'ALL' ? '#e8f5e9' : '#f0f0f0',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  color: selectedGender === 'ALL' && selectedAgeGroup === 'ALL' ? 'var(--primary-green)' : '#333'
                }}
              >
                All Genders & Ages
              </button>

              {/* Two-column layout for Girls and Boys */}
              <div style={{
                display: 'flex',
                gap: '1rem'
              }}>
                {/* Girls Column */}
                <div style={{ flex: 1 }}>
                  <div style={{
                    padding: '0.5rem 0',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    color: '#888',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid #eee',
                    marginBottom: '0.5rem'
                  }}>
                    Girls
                  </div>
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem'
                  }}>
                    <button
                      onClick={() => {
                        setSelectedGender('Girls');
                        setSelectedAgeGroup('ALL');
                        setShowGenderAgeSheet(false);
                      }}
                      style={{
                        padding: '0.5rem 0.75rem',
                        border: selectedGender === 'Girls' && selectedAgeGroup === 'ALL' ? '2px solid var(--primary-green)' : '1px solid #ddd',
                        borderRadius: '8px',
                        background: selectedGender === 'Girls' && selectedAgeGroup === 'ALL' ? '#e8f5e9' : 'white',
                        fontSize: '0.85rem',
                        cursor: 'pointer',
                        fontWeight: selectedGender === 'Girls' && selectedAgeGroup === 'ALL' ? '600' : '400',
                        color: selectedGender === 'Girls' && selectedAgeGroup === 'ALL' ? 'var(--primary-green)' : '#333',
                        textAlign: 'center'
                      }}
                    >
                      All Girls
                    </button>
                    {sortAgeGroupsNumerically(ageGroups.filter(a => a.startsWith('G'))).map(age => (
                      <button
                        key={age}
                        onClick={() => {
                          setSelectedGender('Girls');
                          setSelectedAgeGroup(age);
                          setShowGenderAgeSheet(false);
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          border: selectedGender === 'Girls' && selectedAgeGroup === age ? '2px solid var(--primary-green)' : '1px solid #ddd',
                          borderRadius: '8px',
                          background: selectedGender === 'Girls' && selectedAgeGroup === age ? '#e8f5e9' : 'white',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          fontWeight: selectedGender === 'Girls' && selectedAgeGroup === age ? '600' : '400',
                          color: selectedGender === 'Girls' && selectedAgeGroup === age ? 'var(--primary-green)' : '#333',
                          textAlign: 'center'
                        }}
                      >
                        {age}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Boys Column */}
                <div style={{ flex: 1 }}>
                  <div style={{
                    padding: '0.5rem 0',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    color: '#888',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid #eee',
                    marginBottom: '0.5rem'
                  }}>
                    Boys
                  </div>
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem'
                  }}>
                    <button
                      onClick={() => {
                        setSelectedGender('Boys');
                        setSelectedAgeGroup('ALL');
                        setShowGenderAgeSheet(false);
                      }}
                      style={{
                        padding: '0.5rem 0.75rem',
                        border: selectedGender === 'Boys' && selectedAgeGroup === 'ALL' ? '2px solid var(--primary-green)' : '1px solid #ddd',
                        borderRadius: '8px',
                        background: selectedGender === 'Boys' && selectedAgeGroup === 'ALL' ? '#e8f5e9' : 'white',
                        fontSize: '0.85rem',
                        cursor: 'pointer',
                        fontWeight: selectedGender === 'Boys' && selectedAgeGroup === 'ALL' ? '600' : '400',
                        color: selectedGender === 'Boys' && selectedAgeGroup === 'ALL' ? 'var(--primary-green)' : '#333',
                        textAlign: 'center'
                      }}
                    >
                      All Boys
                    </button>
                    {sortAgeGroupsNumerically(ageGroups.filter(a => a.startsWith('B'))).map(age => (
                      <button
                        key={age}
                        onClick={() => {
                          setSelectedGender('Boys');
                          setSelectedAgeGroup(age);
                          setShowGenderAgeSheet(false);
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          border: selectedGender === 'Boys' && selectedAgeGroup === age ? '2px solid var(--primary-green)' : '1px solid #ddd',
                          borderRadius: '8px',
                          background: selectedGender === 'Boys' && selectedAgeGroup === age ? '#e8f5e9' : 'white',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          fontWeight: selectedGender === 'Boys' && selectedAgeGroup === age ? '600' : '400',
                          color: selectedGender === 'Boys' && selectedAgeGroup === age ? 'var(--primary-green)' : '#333',
                          textAlign: 'center'
                        }}
                      >
                        {age}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Rankings;
