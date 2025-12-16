import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';

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
    'MLS NEXT': { background: '#e0f7fa', color: '#00838f' },
  };
  return styles[league] || { background: '#f5f5f5', color: '#666' };
}

// League categorization
const NATIONAL_LEAGUES = ['ECNL', 'ECNL RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT'];
const REGIONAL_LEAGUES = [
  'Southeastern CCL Fall',
  'Southeastern CCL U11/U12',
  'Florida WFPL',
  'Florida NFPL',
  'Florida SEFPL',
  'Florida CFPL',
  'Chesapeake PSL YPL'
];

// Helper to extract actual club name by stripping age group suffixes
function extractClubName(teamName) {
  if (!teamName) return '';

  let name = teamName.trim();

  name = name
    .replace(/\s+[GB]?\d{2}[GB]?(\s+(Ga|RL|Gold|White|Blue|Red|Black|Premier|Elite|Academy|Select|Pre-Academy|Pre Academy))*\s*$/i, '')
    .replace(/\s+\d{2}\s*$/, '')
    .replace(/\s*\([A-Za-z]{2}\)\s*$/, '')
    .replace(/\s+/g, ' ')
    .trim();

  return name || teamName;
}

function Clubs() {
  const { teamsData, ageGroups, leagues, states, isLoading, error, lastUpdated } = useRankingsData();
  const tableContainerRef = useRef(null);

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
  const [selectedGender, setSelectedGender] = useState(savedFilters?.gender || 'ALL');
  const [selectedAgeGroup, setSelectedAgeGroup] = useState(savedFilters?.ageGroup || 'ALL');
  const [selectedLeague, setSelectedLeague] = useState(savedFilters?.league || 'ALL');
  const [selectedState, setSelectedState] = useState(savedFilters?.state || 'ALL');
  const [filterSearch, setFilterSearch] = useState(savedFilters?.search || '');
  const [minTeams, setMinTeams] = useState(savedFilters?.minTeams || 1);

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
      const bestTeams = Object.values(club.bestTeamPerAgeGroup);
      const ageGroupCount = bestTeams.length;

      // Club ranking = average of top team's powerScore from each age group
      const avgPowerScore = ageGroupCount > 0
        ? bestTeams.reduce((sum, bt) => sum + bt.powerScore, 0) / ageGroupCount
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
      const winPct = club.totalGamesPlayed > 0 ? club.totalWins / club.totalGamesPlayed : 0;

      // Average offensive/defensive scores from best teams
      const avgOffScore = ageGroupCount > 0
        ? bestTeams.reduce((sum, bt) => sum + (bt.team.offensivePowerScore || 50), 0) / ageGroupCount
        : 50;
      const avgDefScore = ageGroupCount > 0
        ? bestTeams.reduce((sum, bt) => sum + (bt.team.defensivePowerScore || 50), 0) / ageGroupCount
        : 50;

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
        winPct: winPct,
        totalGamesPlayed: club.totalGamesPlayed,
        avgOffScore: avgOffScore,
        avgDefScore: avgDefScore,
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
  }, [teamsData]);

  // Filter and sort clubs
  const filteredClubs = useMemo(() => {
    let filtered = [...clubs];

    // Search filter
    if (filterSearch) {
      const term = filterSearch.toLowerCase();
      filtered = filtered.filter(club => club.name.toLowerCase().includes(term));
    }

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
      filtered = filtered.filter(club => club.leagues.includes(selectedLeague));
    }

    // State filter
    if (selectedState !== 'ALL') {
      filtered = filtered.filter(club => club.states.includes(selectedState));
    }

    // Min teams filter
    filtered = filtered.filter(club => club.teamCount >= minTeams);

    // Sort
    return filtered.sort((a, b) => {
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
      {/* Header with last updated */}
      <div className="card rankings-header-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
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
          <div className="filter-group search-group">
            <label className="filter-label">Search Club</label>
            <input
              type="text"
              className="form-input"
              placeholder="Search by club name..."
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
            />
          </div>

          {/* Filter row */}
          <div className="filter-row">
            <div className="filter-group">
              <label className="filter-label">Gender/Age</label>
              <select
                className="filter-select"
                value={`${selectedGender}|${selectedAgeGroup}`}
                onChange={(e) => {
                  const [gender, age] = e.target.value.split('|');
                  setSelectedGender(gender);
                  setSelectedAgeGroup(age);
                }}
              >
                <option value="ALL|ALL">All</option>
                <optgroup label="Girls">
                  <option value="Girls|ALL">Girls - All Ages</option>
                  {ageGroups.filter(a => a.startsWith('G')).map(age => (
                    <option key={age} value={`Girls|${age}`}>Girls {age}</option>
                  ))}
                </optgroup>
                <optgroup label="Boys">
                  <option value="Boys|ALL">Boys - All Ages</option>
                  {ageGroups.filter(a => a.startsWith('B')).map(age => (
                    <option key={age} value={`Boys|${age}`}>Boys {age}</option>
                  ))}
                </optgroup>
              </select>
            </div>

            <div className="filter-group">
              <label className="filter-label">League</label>
              <select
                className="filter-select"
                value={selectedLeague}
                onChange={(e) => setSelectedLeague(e.target.value)}
              >
                <option value="ALL">All Leagues</option>
                <optgroup label="National Leagues">
                  {NATIONAL_LEAGUES.filter(l => leagues.includes(l)).map(league => (
                    <option key={league} value={league}>{league}</option>
                  ))}
                </optgroup>
                <optgroup label="Regional Leagues">
                  {REGIONAL_LEAGUES.filter(l => leagues.includes(l)).map(league => (
                    <option key={league} value={league}>{league}</option>
                  ))}
                </optgroup>
              </select>
            </div>

            <div className="filter-group">
              <label className="filter-label">State</label>
              <select
                className="filter-select"
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
              >
                <option value="ALL">All</option>
                {states.map(state => (
                  <option key={state} value={state}>{state}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label className="filter-label">Min Teams</label>
              <select
                className="filter-select"
                value={minTeams}
                onChange={(e) => setMinTeams(parseInt(e.target.value))}
              >
                <option value="1">1+</option>
                <option value="3">3+</option>
                <option value="5">5+</option>
                <option value="10">10+</option>
                <option value="15">15+</option>
              </select>
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
                setMinTeams(1);
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
            <table className="data-table rankings-table">
              <thead>
                <tr>
                  <th
                    className="col-rank sortable-header"
                    onClick={() => handleSort('power')}
                    style={{ cursor: 'pointer' }}
                    title="Sort by Average Power Score"
                  >
                    Rank{getSortIndicator('power')}
                  </th>
                  <th className="col-team">Club</th>
                  <th
                    className="sortable-header hide-mobile"
                    onClick={() => handleSort('ageGroups')}
                    style={{ cursor: 'pointer', textAlign: 'center' }}
                    title="Number of age groups"
                  >
                    Ages{getSortIndicator('ageGroups')}
                  </th>
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
                    className="sortable-header"
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
                  {showDetails && <th title="Average Offensive Power Score">Off</th>}
                  {showDetails && <th title="Average Defensive Power Score">Def</th>}
                  {showDetails && <th title="Best Win (from any team in club)">Best Win</th>}
                  {showDetails && <th title="2nd Best Win">2nd Best</th>}
                  {showDetails && <th title="Worst Loss">Worst Loss</th>}
                  {showDetails && <th title="2nd Worst Loss">2nd Worst</th>}
                  {showDetails && <th title="Win Percentage">Win %</th>}
                </tr>
              </thead>
              <tbody>
                {filteredClubs.slice(0, displayLimit).map((club, index) => (
                  <tr key={club.name}>
                    <td className="rank-cell col-rank">#{index + 1}</td>
                    <td className="col-team">
                      <Link
                        to={`/club/${encodeURIComponent(club.name)}`}
                        className="team-name-link"
                        onClick={saveScrollPosition}
                      >
                        {club.name}
                      </Link>
                    </td>
                    <td className="hide-mobile" style={{ textAlign: 'center', fontWeight: '500' }}>{club.ageGroupCount}</td>
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
                    <td>{club.totalWins}-{club.totalLosses}-{club.totalDraws}</td>
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
                    {showDetails && (
                      <td style={{ textAlign: 'center' }}>
                        {((club.winPct || 0) * 100).toFixed(0)}%
                      </td>
                    )}
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
    </div>
  );
}

export default Clubs;
