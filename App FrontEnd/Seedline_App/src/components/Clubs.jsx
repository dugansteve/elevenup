import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import BottomSheetSelect from './BottomSheetSelect';
import { isElevenUpBrand } from '../config/brand';

// Pagination constants
const CLUBS_PER_PAGE = 200;

// Truncated text component with tap-to-expand for mobile
function TruncatedCell({ text, subText, color, maxWidth = '150px' }) {
  const [expanded, setExpanded] = useState(false);

  if (!text || text === '-') return <span>-</span>;

  const fullText = subText ? `${text} (by ${subText})` : text;

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
        title={fullText}
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
          {fullText}
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

// Session storage keys for preserving state
const STORAGE_KEYS = {
  scrollPosition: 'clubs_scroll_position',
  filters: 'clubs_filters',
  showDetails: 'clubs_show_details'
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

// Helper to extract actual club name by stripping age group suffixes
function extractClubName(teamName) {
  if (!teamName) return '';

  let name = teamName.trim();

  // Match age patterns: "08G", "08/07G", "G08", "2008", "07/06G", etc.
  // Followed by optional tier words: Gold, Navy, Aspire, White, Blue, etc.
  const tierWords = 'Ga|RL|Gold|White|Blue|Red|Black|Navy|Aspire|Premier|Elite|Academy|Select|Pre-Academy|Pre Academy|I|II|III';

  // Pattern for combined age groups like "08/07G" or "07/06G"
  name = name.replace(new RegExp(`\\s+\\d{2}/\\d{2}[GB]?(\\s+(${tierWords}))*\\s*$`, 'i'), '');

  // Pattern for simple age groups like "08G", "G08", "13G"
  name = name.replace(new RegExp(`\\s+[GB]?\\d{2}[GB]?(\\s+(${tierWords}))*\\s*$`, 'i'), '');

  // Pattern for just tier words at end (after age was already in club name)
  name = name.replace(new RegExp(`\\s+(${tierWords})\\s*$`, 'i'), '');

  // Clean up year patterns like "2008"
  name = name.replace(/\s+\d{4}\s*$/, '');

  // Clean up state abbreviations in parens
  name = name.replace(/\s*\([A-Za-z]{2}\)\s*$/, '');

  // Normalize whitespace
  name = name.replace(/\s+/g, ' ').trim();

  return name || teamName;
}

// Helper to check if age group is academy-aged (08/07 through 13)
function isAcademyAge(ageGroup) {
  if (!ageGroup) return false;
  // Extract the numeric part (e.g., "G13" -> 13, "B08/07" -> 8, "G08" -> 8)
  const match = ageGroup.match(/(\d+)/);
  if (!match) return false;
  const age = parseInt(match[1], 10);
  // Academy ages: 8, 9, 10, 11, 12, 13 (and 07 in combined groups like 08/07)
  return age >= 7 && age <= 13;
}

function Clubs() {
  const { teamsData, ageGroups, leagues, states, isLoading, error, lastUpdated } = useRankingsData();
  const tableContainerRef = useRef(null);

  // Mobile bottom sheet for Gender/Age filter
  const [showGenderAgeSheet, setShowGenderAgeSheet] = useState(false);

  // Mobile info tooltip
  const [showInfoTooltip, setShowInfoTooltip] = useState(false);

  // Drag scrolling state
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeftStart, setScrollLeftStart] = useState(0);

  // Track horizontal scroll for shrinking rank column
  const [isScrolled, setIsScrolled] = useState(false);

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
    const walk = (x - startX) * 1.5;
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

  // Filter state
  const [selectedGender, setSelectedGender] = useState(savedFilters?.gender || 'Girls');
  const [selectedAgeGroup, setSelectedAgeGroup] = useState(savedFilters?.ageGroup || 'ALL');
  const [selectedLeague, setSelectedLeague] = useState(savedFilters?.league || 'ALL');
  const [selectedState, setSelectedState] = useState(savedFilters?.state || 'ALL');
  const [filterSearch, setFilterSearch] = useState(savedFilters?.search || '');
  const [minTeams, setMinTeams] = useState(savedFilters?.minTeams || 5);

  // Sort state
  const [sortField, setSortField] = useState('power');
  const [sortDirection, setSortDirection] = useState('desc');

  // UI state
  const [displayLimit, setDisplayLimit] = useState(savedFilters?.displayLimit || CLUBS_PER_PAGE);
  const [showDetails, setShowDetails] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.showDetails);
      return saved === 'true';
    } catch { return false; }
  });

  // Save filters to sessionStorage whenever they change
  useEffect(() => {
    const filters = {
      gender: selectedGender,
      ageGroup: selectedAgeGroup,
      league: selectedLeague,
      state: selectedState,
      search: filterSearch,
      minTeams: minTeams,
      displayLimit: displayLimit
    };
    sessionStorage.setItem(STORAGE_KEYS.filters, JSON.stringify(filters));
  }, [selectedGender, selectedAgeGroup, selectedLeague, selectedState, filterSearch, minTeams, displayLimit]);

  // Save showDetails state
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEYS.showDetails, showDetails.toString());
  }, [showDetails]);

  // Restore scroll position when component mounts
  useEffect(() => {
    const savedScrollPos = sessionStorage.getItem(STORAGE_KEYS.scrollPosition);
    if (savedScrollPos && !isLoading) {
      setTimeout(() => {
        window.scrollTo(0, parseInt(savedScrollPos, 10));
        sessionStorage.removeItem(STORAGE_KEYS.scrollPosition);
      }, 100);
    }
  }, [isLoading]);

  // Track horizontal scroll to shrink rank column
  useEffect(() => {
    const container = tableContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      setIsScrolled(container.scrollLeft > 10);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

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
    setDisplayLimit(CLUBS_PER_PAGE);
  }, [selectedGender, selectedAgeGroup, selectedLeague, selectedState, filterSearch, minTeams]);

  // Calculate national ranks by age group (rank within each age group)
  const nationalRanks = useMemo(() => {
    const rankMap = {};
    // Group teams by age group
    const groupedTeams = {};
    teamsData.forEach(team => {
      if (!team.ageGroup) return;
      const key = team.ageGroup;
      if (!groupedTeams[key]) groupedTeams[key] = [];
      groupedTeams[key].push(team);
    });
    // Sort each group by power score and assign ranks
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

  // Derive clubs from teams data with ranking calculations
  const clubs = useMemo(() => {
    const clubMap = {};

    teamsData.forEach(team => {
      const clubName = extractClubName(team.club || team.name);
      if (!clubName) return;

      if (!clubMap[clubName]) {
        clubMap[clubName] = {
          name: clubName,
          states: new Set(),
          leagues: new Set(),
          ageGroups: new Set(),
          genders: new Set(),
          teams: [],
          totalWins: 0,
          totalLosses: 0,
          totalDraws: 0,
          totalGoalsFor: 0,
          totalGoalsAgainst: 0,
          totalGamesPlayed: 0,
          allBestWins: [],
          allSecondBestWins: [],
          allWorstLosses: [],
          allSecondWorstLosses: [],
          bestTeamPerAgeGroup: {}
        };
      }

      const club = clubMap[clubName];
      if (team.state) club.states.add(team.state);
      club.leagues.add(team.league);
      club.ageGroups.add(team.ageGroup);
      if (team.gender) club.genders.add(team.gender);
      else if (team.ageGroup) {
        club.genders.add(team.ageGroup.startsWith('G') ? 'Girls' : 'Boys');
      }
      club.teams.push(team);

      club.totalWins += team.wins || 0;
      club.totalLosses += team.losses || 0;
      club.totalDraws += team.draws || 0;
      club.totalGoalsFor += team.goalsFor || 0;
      club.totalGoalsAgainst += team.goalsAgainst || 0;
      club.totalGamesPlayed += team.gamesPlayed || ((team.wins || 0) + (team.losses || 0) + (team.draws || 0));

      if (team.bestWin) club.allBestWins.push({ win: team.bestWin, team: team.name });
      if (team.secondBestWin) club.allSecondBestWins.push({ win: team.secondBestWin, team: team.name });
      if (team.worstLoss) club.allWorstLosses.push({ win: team.worstLoss, team: team.name });
      if (team.secondWorstLoss) club.allSecondWorstLosses.push({ win: team.secondWorstLoss, team: team.name });

      const ageGroup = team.ageGroup;
      if (ageGroup) {
        const existingBest = club.bestTeamPerAgeGroup[ageGroup];
        if (!existingBest || (team.powerScore || 0) > (existingBest.powerScore || 0)) {
          club.bestTeamPerAgeGroup[ageGroup] = {
            team: team,
            powerScore: team.powerScore || 0,
            rank: team.rank
          };
        }
      }
    });

    // Calculate derived values for each club
    return Object.values(clubMap).map(club => {
      // Filter to only academy-aged teams (G08/07 through G13, B08/07 through B13)
      const academyBestTeams = Object.entries(club.bestTeamPerAgeGroup)
        .filter(([ageGroup]) => isAcademyAge(ageGroup))
        .map(([, teamData]) => teamData);

      const bestTeams = Object.values(club.bestTeamPerAgeGroup);
      const ageGroupCount = academyBestTeams.length; // Use academy count for ranking

      // Club ranking = average of top team's powerScore from each ACADEMY age group
      const avgPowerScore = ageGroupCount > 0
        ? academyBestTeams.reduce((sum, bt) => sum + bt.powerScore, 0) / ageGroupCount
        : 0;

      // Helper to find best/worst result from array (lower rank = better for wins, higher rank = worse for losses)
      const findBestWin = (winsArray) => {
        if (winsArray.length === 0) return null;
        return winsArray.reduce((best, current) => {
          const currentRank = parseInt((current.win.match(/^#(\d+)/) || [])[1]) || 9999;
          const bestRank = parseInt((best.win.match(/^#(\d+)/) || [])[1]) || 9999;
          return currentRank < bestRank ? current : best;
        });
      };

      const findWorstLoss = (lossesArray) => {
        if (lossesArray.length === 0) return null;
        return lossesArray.reduce((worst, current) => {
          const currentRank = parseInt((current.win.match(/^#(\d+)/) || [])[1]) || 0;
          const worstRank = parseInt((worst.win.match(/^#(\d+)/) || [])[1]) || 0;
          return currentRank > worstRank ? current : worst;
        });
      };

      const bestOverallWin = findBestWin(club.allBestWins);
      const secondBestOverallWin = findBestWin(club.allSecondBestWins);
      const worstOverallLoss = findWorstLoss(club.allWorstLosses);
      const secondWorstOverallLoss = findWorstLoss(club.allSecondWorstLosses);

      const goalDiff = club.totalGoalsFor - club.totalGoalsAgainst;
      const avgGD = club.totalGamesPlayed > 0 ? goalDiff / club.totalGamesPlayed : 0;

      // Calculate Avg PPG using only top team at each age group
      let topTeamWins = 0;
      let topTeamLosses = 0;
      let topTeamDraws = 0;
      academyBestTeams.forEach(bt => {
        topTeamWins += bt.team.wins || 0;
        topTeamLosses += bt.team.losses || 0;
        topTeamDraws += bt.team.draws || 0;
      });
      const topTeamGames = topTeamWins + topTeamLosses + topTeamDraws;
      const topTeamPoints = (topTeamWins * 3) + (topTeamDraws * 1);
      const avgPPG = topTeamGames > 0 ? topTeamPoints / topTeamGames : 0;

      // Average offensive/defensive scores from best ACADEMY teams
      const avgOffScore = ageGroupCount > 0
        ? academyBestTeams.reduce((sum, bt) => sum + (bt.team.offensivePowerScore || 50), 0) / ageGroupCount
        : 50;
      const avgDefScore = ageGroupCount > 0
        ? academyBestTeams.reduce((sum, bt) => sum + (bt.team.defensivePowerScore || 50), 0) / ageGroupCount
        : 50;

      // Average rank of best team per ACADEMY age group (matches club ranking methodology)
      const bestRankPerAgeGroup = {};
      club.teams.forEach(t => {
        const ag = t.ageGroup;
        const rank = nationalRanks[t.id];
        // Only include academy-aged teams (G08/07 through G13, B08/07 through B13)
        if (ag && rank && isAcademyAge(ag)) {
          // Keep the best (lowest) rank for each age group
          if (!bestRankPerAgeGroup[ag] || rank < bestRankPerAgeGroup[ag]) {
            bestRankPerAgeGroup[ag] = rank;
          }
        }
      });

      const bestRanks = Object.values(bestRankPerAgeGroup);
      const avgTeamRank = bestRanks.length > 0
        ? bestRanks.reduce((sum, r) => sum + r, 0) / bestRanks.length
        : null;

      return {
        name: club.name,
        states: [...club.states],
        leagues: [...club.leagues].sort(),
        ageGroups: [...club.ageGroups].sort(),
        genders: [...club.genders],
        teamCount: club.teams.length,
        ageGroupCount: ageGroupCount,
        avgPowerScore: avgPowerScore,
        totalWins: club.totalWins,
        totalLosses: club.totalLosses,
        totalDraws: club.totalDraws,
        goalDiff: goalDiff,
        avgGD: avgGD,
        avgPPG: avgPPG,
        totalGamesPlayed: club.totalGamesPlayed,
        avgOffScore: avgOffScore,
        avgDefScore: avgDefScore,
        avgTeamRank: avgTeamRank,
        bestWin: bestOverallWin ? bestOverallWin.win : null,
        bestWinTeam: bestOverallWin ? bestOverallWin.team : null,
        secondBestWin: secondBestOverallWin ? secondBestOverallWin.win : null,
        secondBestWinTeam: secondBestOverallWin ? secondBestOverallWin.team : null,
        worstLoss: worstOverallLoss ? worstOverallLoss.win : null,
        worstLossTeam: worstOverallLoss ? worstOverallLoss.team : null,
        secondWorstLoss: secondWorstOverallLoss ? secondWorstOverallLoss.win : null,
        secondWorstLossTeam: secondWorstOverallLoss ? secondWorstOverallLoss.team : null
      };
    });
  }, [teamsData, nationalRanks]);

  // Filter and sort clubs - rankings are assigned BEFORE search filter is applied
  const filteredClubs = useMemo(() => {
    let filtered = [...clubs];

    // Apply all filters EXCEPT search first (these affect ranking)
    // Gender filter - club must have teams in selected gender
    if (selectedGender !== 'ALL') {
      filtered = filtered.filter(club => club.genders.includes(selectedGender));
    }

    // Age group filter - club must have teams in selected age group
    if (selectedAgeGroup !== 'ALL') {
      filtered = filtered.filter(club => club.ageGroups.includes(selectedAgeGroup));
    }

    // League filter
    if (selectedLeague !== 'ALL') {
      if (selectedLeague === 'ALL_NATIONAL') {
        filtered = filtered.filter(club => club.leagues.some(l => NATIONAL_LEAGUES.includes(l)));
      } else if (selectedLeague === 'ALL_REGIONAL') {
        filtered = filtered.filter(club => club.leagues.some(l => REGIONAL_LEAGUES.includes(l)));
      } else {
        filtered = filtered.filter(club => club.leagues.includes(selectedLeague));
      }
    }

    // State filter
    if (selectedState !== 'ALL') {
      filtered = filtered.filter(club => club.states.includes(selectedState));
    }

    // Min teams filter
    filtered = filtered.filter(club => club.teamCount >= minTeams);

    // Sort to determine rankings
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'power':
          comparison = (b.avgPowerScore || 0) - (a.avgPowerScore || 0);
          break;
        case 'record':
          const aPPG = a.totalGamesPlayed > 0
            ? (a.totalWins * 3 + a.totalDraws) / a.totalGamesPlayed : 0;
          const bPPG = b.totalGamesPlayed > 0
            ? (b.totalWins * 3 + b.totalDraws) / b.totalGamesPlayed : 0;
          comparison = bPPG - aPPG;
          break;
        case 'gd':
          comparison = (b.avgGD || 0) - (a.avgGD || 0);
          break;
        case 'teams':
          comparison = b.teamCount - a.teamCount;
          break;
        case 'ageGroups':
          comparison = b.ageGroupCount - a.ageGroupCount;
          break;
        default:
          comparison = (b.avgPowerScore || 0) - (a.avgPowerScore || 0);
      }

      return sortDirection === 'asc' ? -comparison : comparison;
    });

    // Assign rankings AFTER sorting but BEFORE search filter
    // This ensures rankings stay consistent regardless of search
    const totalClubsBeforeSearch = filtered.length;
    filtered = filtered.map((club, index) => ({
      ...club,
      displayRank: index + 1,
      totalRanked: totalClubsBeforeSearch
    }));

    // NOW apply search filter (this only filters display, doesn't affect rankings)
    if (filterSearch) {
      const term = filterSearch.toLowerCase();
      filtered = filtered.filter(club => club.name.toLowerCase().includes(term));
    }

    return filtered;
  }, [clubs, filterSearch, selectedGender, selectedAgeGroup, selectedLeague, selectedState, minTeams, sortField, sortDirection]);

  // Handle column header click for sorting
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Get sort indicator
  const getSortIndicator = (field) => {
    if (sortField !== field) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

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

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">Loading clubs data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">⚠️</div>
          <div className="empty-state-text">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header with last updated - hidden on mobile */}
      <div className="card rankings-header-card hide-mobile" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h1 style={{ fontSize: '1.25rem', margin: 0, fontWeight: '700', color: 'var(--primary-green)' }}>
              Club Rankings
            </h1>
            <p style={{ fontSize: '0.85rem', margin: '0.25rem 0 0 0', color: '#666' }}>
              Rankings based on average power score of top team per age group
            </p>
          </div>
          {lastUpdated && (
            <span style={{ fontSize: '0.75rem', color: '#888' }}>
              Updated: {formatDate(lastUpdated)}
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="card filters-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
        <div className="filters-compact">
          {/* Club Name Search */}
          <div className="filter-group search-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="text"
              className="form-input"
              placeholder="Search by club name..."
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              style={{ flex: 1 }}
            />
            {/* Info tooltip - mobile only */}
            <div style={{ position: 'relative' }} className="mobile-info-tooltip">
              <button
                onClick={() => setShowInfoTooltip(!showInfoTooltip)}
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  border: '1px solid #ccc',
                  background: showInfoTooltip ? 'var(--primary-green)' : '#f5f5f5',
                  color: showInfoTooltip ? 'white' : '#666',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
                aria-label="Rankings info"
              >
                i
              </button>
              {showInfoTooltip && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '8px',
                    background: '#333',
                    color: 'white',
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    fontSize: '0.8rem',
                    lineHeight: 1.4,
                    width: '220px',
                    zIndex: 1000,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                  }}
                >
                  <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>Club Rankings</div>
                  <div style={{ marginBottom: '0.5rem' }}>Rankings based on average power score of top team per age group</div>
                  {lastUpdated && (
                    <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>
                      Updated: {formatDate(lastUpdated)}
                    </div>
                  )}
                  {/* Arrow pointing up */}
                  <div style={{
                    position: 'absolute',
                    top: '-6px',
                    right: '8px',
                    width: 0,
                    height: 0,
                    borderLeft: '6px solid transparent',
                    borderRight: '6px solid transparent',
                    borderBottom: '6px solid #333'
                  }} />
                </div>
              )}
            </div>
          </div>

          {/* Filter row */}
          <div className="filter-row">
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

            <div className="filter-group">
              <BottomSheetSelect
                label="Min Teams"
                value={minTeams}
                onChange={(val) => setMinTeams(parseInt(val))}
                options={[
                  { value: '1', label: '1+' },
                  { value: '3', label: '3+' },
                  { value: '5', label: '5+' },
                  { value: '10', label: '10+' },
                  { value: '15', label: '15+' }
                ]}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <span className="card-title" style={{ fontSize: '0.9rem' }}>
            {displayLimit < filteredClubs.length
              ? `${displayLimit} of ${filteredClubs.length} clubs`
              : `${filteredClubs.length} clubs`}
          </span>
          <button
            onClick={() => setShowDetails(!showDetails)}
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: '6px',
              border: '1px solid #ddd',
              background: showDetails ? 'var(--primary-green)' : '#f8f9fa',
              color: showDetails ? 'white' : '#666',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s ease'
            }}
          >
            {showDetails ? '◀ Hide details' : '▶ See more details'}
          </button>
        </div>

        {filteredClubs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-text">No clubs found matching your filters</div>
            <button
              onClick={() => {
                setFilterSearch('');
                setSelectedGender('ALL');
                setSelectedAgeGroup('ALL');
                setSelectedState('ALL');
                setSelectedLeague('ALL');
                setMinTeams(5);
              }}
              className="btn btn-secondary"
              style={{ marginTop: '1rem' }}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          <div
            className="table-scroll-container"
            ref={tableContainerRef}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ cursor: 'grab' }}
          >
            <table className={`data-table rankings-table clubs-table ${!showDetails ? 'compact-view' : ''} ${isScrolled ? 'scrolled' : ''}`}>
              <thead>
                <tr>
                  <th
                    className="col-rank sortable-header sticky-col sticky-col-1"
                    onClick={() => handleSort('power')}
                    style={{ cursor: 'pointer' }}
                    title="Sort by Average Power Score"
                  >
                    <span className="hide-mobile">Rank</span>{getSortIndicator('power')}
                  </th>
                  <th className="col-team sticky-col sticky-col-2">Club</th>
                  {showDetails && (
                    <th
                      className="sortable-header"
                      onClick={() => handleSort('ageGroups')}
                      style={{ cursor: 'pointer', textAlign: 'center' }}
                      title="Age group range"
                    >
                      Age{getSortIndicator('ageGroups')}
                    </th>
                  )}
                  <th
                    className="sortable-header hide-mobile"
                    onClick={() => handleSort('teams')}
                    style={{ cursor: 'pointer', textAlign: 'center' }}
                    title="Total teams"
                  >
                    Teams{getSortIndicator('teams')}
                  </th>
                  <th className="col-league">Leagues</th>
                  <th className="col-state hide-mobile">ST</th>
                  <th
                    className="col-power sortable-header hide-mobile"
                    onClick={() => handleSort('power')}
                    style={{ cursor: 'pointer' }}
                    title="Average Power Score (top team per age group)"
                  >
                    Power{getSortIndicator('power')}
                  </th>
                  <th
                    className={`sortable-header ${!showDetails ? 'hide-mobile' : ''}`}
                    onClick={() => handleSort('record')}
                    style={{ cursor: 'pointer' }}
                    title="Sort by Record (3 pts/win, 1 pt/draw)"
                  >
                    Record{getSortIndicator('record')}
                  </th>
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
                  {showDetails && <th title="Average Team Rank across all age groups">Avg Rank</th>}
                  {showDetails && <th title="Average Offensive Power Score">Off</th>}
                  {showDetails && <th title="Average Defensive Power Score">Def</th>}
                  {showDetails && <th title="Best Win (from any team in club)">Best Win</th>}
                  {showDetails && <th title="2nd Best Win">2nd Best</th>}
                  {showDetails && <th title="Worst Loss">Worst Loss</th>}
                  {showDetails && <th title="2nd Worst Loss">2nd Worst</th>}
                  <th className={!showDetails ? 'show-mobile-only' : ''} title="Average Points Per Game (top team per age group)">Avg PPG</th>
                </tr>
              </thead>
              <tbody>
                {filteredClubs.slice(0, displayLimit).map((club, index) => (
                  <tr key={club.name}>
                    <td className="rank-cell col-rank sticky-col sticky-col-1">#{club.displayRank}</td>
                    <td className="col-team sticky-col sticky-col-2">
                      <Link
                        to={`/club/${encodeURIComponent(club.name)}`}
                        className="team-name-link"
                        onClick={saveScrollPosition}
                      >
                        {club.name}
                      </Link>
                    </td>
                    {showDetails && (
                      <td style={{ textAlign: 'center', fontWeight: '500', fontSize: '0.75rem' }}>
                        {(() => {
                          // Show age range like "G08-G13" instead of just count
                          const sortedAges = sortAgeGroupsNumerically(club.ageGroups);
                          if (sortedAges.length === 0) return '-';
                          if (sortedAges.length === 1) return sortedAges[0];
                          // Get first and last age groups
                          const first = sortedAges[0];
                          const last = sortedAges[sortedAges.length - 1];
                          return `${first}-${last}`;
                        })()}
                      </td>
                    )}
                    <td className="hide-mobile" style={{ textAlign: 'center', fontWeight: '500' }}>{club.teamCount}</td>
                    <td className="col-league">
                      {club.leagues.length <= 2 ? (
                        club.leagues.map(league => (
                          <span
                            key={league}
                            className="league-badge-sm"
                            style={{ ...getLeagueBadgeStyle(league), marginRight: '0.25rem' }}
                          >
                            {league}
                          </span>
                        ))
                      ) : (
                        <span
                          title={club.leagues.join(', ')}
                          style={{
                            fontSize: '0.8rem',
                            color: '#666',
                            cursor: 'help'
                          }}
                        >
                          {club.leagues.length} leagues
                        </span>
                      )}
                    </td>
                    <td className="col-state hide-mobile">
                      {club.states.length === 1 ? club.states[0] :
                       club.states.length > 1 ? (
                        <span title={club.states.join(', ')} style={{ cursor: 'help' }}>
                          {club.states.length}
                        </span>
                       ) : '-'}
                    </td>
                    <td className="col-power power-score hide-mobile">{club.avgPowerScore?.toFixed(1) || '0.0'}</td>
                    <td className={!showDetails ? 'hide-mobile' : ''}>{club.totalWins}-{club.totalLosses}-{club.totalDraws}</td>
                    {showDetails && (
                      <td style={{
                        color: club.avgGD > 0 ? '#2e7d32' : club.avgGD < 0 ? '#c62828' : '#666',
                        fontWeight: '600',
                        textAlign: 'center'
                      }}>
                        {club.avgGD > 0 ? '+' : ''}{club.avgGD.toFixed(2)}
                      </td>
                    )}
                    {showDetails && (
                      <td style={{
                        textAlign: 'center',
                        fontWeight: '600',
                        color: '#555'
                      }}>
                        {club.avgTeamRank ? `#${Math.round(club.avgTeamRank)}` : '-'}
                      </td>
                    )}
                    {showDetails && (
                      <td style={{
                        textAlign: 'center',
                        color: '#1976d2',
                        fontWeight: '600'
                      }}>
                        {club.avgOffScore?.toFixed(0) || '-'}
                      </td>
                    )}
                    {showDetails && (
                      <td style={{
                        textAlign: 'center',
                        color: '#7b1fa2',
                        fontWeight: '600'
                      }}>
                        {club.avgDefScore?.toFixed(0) || '-'}
                      </td>
                    )}
                    {showDetails && (
                      <td>
                        <TruncatedCell
                          text={club.bestWin}
                          subText={club.bestWinTeam}
                          color="#2e7d32"
                        />
                      </td>
                    )}
                    {showDetails && (
                      <td>
                        <TruncatedCell
                          text={club.secondBestWin}
                          subText={club.secondBestWinTeam}
                          color="#2e7d32"
                        />
                      </td>
                    )}
                    {showDetails && (
                      <td>
                        <TruncatedCell
                          text={club.worstLoss}
                          subText={club.worstLossTeam}
                          color="#c62828"
                        />
                      </td>
                    )}
                    {showDetails && (
                      <td>
                        <TruncatedCell
                          text={club.secondWorstLoss}
                          subText={club.secondWorstLossTeam}
                          color="#c62828"
                        />
                      </td>
                    )}
                    <td className={!showDetails ? 'show-mobile-only' : ''} style={{ textAlign: 'center' }}>
                      {(club.avgPPG || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Load More button for pagination */}
            {displayLimit < filteredClubs.length && (
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
                  onClick={() => setDisplayLimit(prev => Math.min(prev + CLUBS_PER_PAGE, filteredClubs.length))}
                  className="btn btn-primary"
                  style={{ padding: '0.75rem 2rem' }}
                >
                  Load {Math.min(CLUBS_PER_PAGE, filteredClubs.length - displayLimit)} More Clubs
                </button>
                <button
                  onClick={() => setDisplayLimit(filteredClubs.length)}
                  className="btn btn-secondary"
                  style={{ padding: '0.75rem 1.5rem' }}
                >
                  Load All ({filteredClubs.length})
                </button>
              </div>
            )}
          </div>
        )}
      </div>

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

export default Clubs;
