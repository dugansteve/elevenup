import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import { useUser } from '../context/UserContext';

// Pagination constants
const TEAMS_PER_PAGE = 200;

// Session storage keys for preserving state
const STORAGE_KEYS = {
  scrollPosition: 'rankings_scroll_position',
  filters: 'rankings_filters',
  showDetails: 'rankings_show_details'
};

// Helper function for league badge colors
function getLeagueBadgeStyle(league) {
  const styles = {
    'ECNL': { background: '#e3f2fd', color: '#1976d2' },      // Blue
    'GA': { background: '#f3e5f5', color: '#7b1fa2' },        // Purple
    'ECNL-RL': { background: '#ffebee', color: '#c62828' },   // Red
    'ASPIRE': { background: '#e8f5e9', color: '#2e7d32' },    // Green
    'NPL': { background: '#fff3e0', color: '#e65100' },       // Orange
  };
  return styles[league] || { background: '#f5f5f5', color: '#666' };
}

function Rankings() {
  const navigate = useNavigate();
  const location = useLocation();
  const { teamsData, ageGroups, leagues, states, genders, isLoading, error, lastUpdated } = useRankingsData();
  const { canPerform, getMyTeams, addToMyTeams, removeFromMyTeams, isInMyTeams, isGuest } = useUser();
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
  const [selectedGender, setSelectedGender] = useState(savedFilters?.gender || 'ALL');
  const [viewMode, setViewMode] = useState('rankings'); // 'rankings' or 'myteams'
  const [filterSearch, setFilterSearch] = useState(savedFilters?.search || ''); // For rankings table filter
  const [modalSearch, setModalSearch] = useState('');   // For Add Team modal
  const [showAddTeamModal, setShowAddTeamModal] = useState(false);
  const [myTeamsRefreshKey, setMyTeamsRefreshKey] = useState(0);
  const [displayLimit, setDisplayLimit] = useState(savedFilters?.displayLimit || TEAMS_PER_PAGE); // Pagination
  const [showDetails, setShowDetails] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.showDetails);
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

  // Filter teams based on selections
  const filteredTeams = useMemo(() => {
    let filtered = [...teamsData];
    
    // Filter by search term (team name or club name)
    if (filterSearch) {
      const term = filterSearch.toLowerCase();
      filtered = filtered.filter(team =>
        team.name.toLowerCase().includes(term) ||
        (team.club && team.club.toLowerCase().includes(term))
      );
    }
    
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
      filtered = filtered.filter(team => team.league === selectedLeague);
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
    
    // Sort based on selected field
    return filtered.sort((a, b) => {
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

  // Get full team data for My Teams (match by ID first, then by name)
  const myTeamsFullData = useMemo(() => {
    return myTeams.map(savedTeam => {
      // Match by name + ageGroup (stable across JSON regeneration)
      let fullTeam = teamsData.find(t => 
        t.name?.toLowerCase() === savedTeam.name?.toLowerCase() && 
        t.ageGroup?.toLowerCase() === savedTeam.ageGroup?.toLowerCase()
      );
      
      // Fallback: try ID match (legacy support)
      if (!fullTeam) {
        fullTeam = teamsData.find(t => t.id === savedTeam.id);
      }
      
      // Return the full team data if found, otherwise return saved data with flag
      if (fullTeam) {
        return { ...fullTeam, savedId: savedTeam.id };
      }
      return { ...savedTeam, notInRankings: true };
    }).filter(Boolean);
  }, [myTeams, teamsData]);

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
      {/* View Mode Toggle and Last Updated - compact header */}
      <div className="card rankings-header-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
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
              🏆 All Rankings
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
              ⭐ My Teams
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
              {/* Team Name Search */}
              <div className="filter-group search-group">
                <label className="filter-label">Search Team</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Search by team or club name..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                />
              </div>
              
              {/* Filter row - Gender/Age, League, State */}
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
                    <option value="ALL">All</option>
                    {leagues.map(league => (
                      <option key={league} value={league}>{league}</option>
                    ))}
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
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
              <span className="card-title" style={{ fontSize: '0.9rem' }}>
                {displayLimit < filteredTeams.length 
                  ? `${displayLimit} of ${filteredTeams.length} teams`
                  : `${filteredTeams.length} teams`}
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
            
            {filteredTeams.length === 0 ? (
              <div className="empty-state">
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
                style={{ cursor: 'grab' }}
              >
                <table className="data-table rankings-table">
                  <thead>
                    <tr>
                      <th 
                        className="col-rank sortable-header"
                        onClick={() => handleSort('power')}
                        style={{ cursor: 'pointer' }}
                        title="Sort by Power Score (default ranking)"
                      >
                        Rank{getSortIndicator('power')}
                      </th>
                      <th className="col-team">Team</th>
                      <th className="col-age">Age</th>
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
                      {showDetails && <th title="Best Win">Best Win</th>}
                      {showDetails && <th title="2nd Best Win">2nd Best</th>}
                      {showDetails && <th title="Worst Loss">Worst Loss</th>}
                      {showDetails && <th title="2nd Worst Loss">2nd Worst</th>}
                      {canPerform('canSaveMyTeams') && <th style={{ width: '40px' }}></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTeams.slice(0, displayLimit).map((team, index) => {
                      // Calculate average GD per game
                      const gamesPlayed = (team.wins || 0) + (team.losses || 0) + (team.draws || 0);
                      const avgGD = gamesPlayed > 0 ? (team.goalDiff || 0) / gamesPlayed : 0;
                      
                      return (
                      <tr key={team.id}>
                        <td className="rank-cell col-rank">#{index + 1}</td>
                        <td className="col-team">
                          <Link 
                            to={`/team/${team.id}`}
                            className="team-name-link"
                            onClick={saveScrollPosition}
                          >
                            {team.name}
                          </Link>
                        </td>
                        <td className="col-age">{team.ageGroup}</td>
                        <td className="col-league">
                          <span className="league-badge-sm" style={getLeagueBadgeStyle(team.league)}>
                            {team.league}
                          </span>
                        </td>
                        <td className="col-state">{team.state || '-'}</td>
                        {showDetails && <td className="col-power power-score">{team.powerScore?.toFixed(1) || '0.0'}</td>}
                        {showDetails && <td>{team.wins}-{team.losses}-{team.draws}</td>}
                        {showDetails && (
                          <td style={{ 
                            color: avgGD > 0 ? '#2e7d32' : avgGD < 0 ? '#c62828' : '#666',
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
                            color: '#1976d2',
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
                            color: '#7b1fa2',
                            fontWeight: '600'
                          }}>
                            {team.defensivePowerScore?.toFixed(0) || '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td style={{ 
                            fontSize: '0.8rem',
                            color: '#2e7d32',
                            maxWidth: '150px',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }} title={team.bestWin || ''}>
                            {team.bestWin || '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td style={{ 
                            fontSize: '0.8rem',
                            color: '#2e7d32',
                            maxWidth: '150px',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }} title={team.secondBestWin || ''}>
                            {team.secondBestWin || '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td style={{ 
                            fontSize: '0.8rem',
                            color: '#c62828',
                            maxWidth: '150px',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }} title={team.worstLoss || ''}>
                            {team.worstLoss || '-'}
                          </td>
                        )}
                        {showDetails && (
                          <td style={{ 
                            fontSize: '0.8rem',
                            color: '#c62828',
                            maxWidth: '150px',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }} title={team.secondWorstLoss || ''}>
                            {team.secondWorstLoss || '-'}
                          </td>
                        )}
                        {canPerform('canSaveMyTeams') && (
                          <td>
                            {isInMyTeams(team) ? (
                              <button
                                onClick={() => handleRemoveTeam(team)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  fontSize: '1.2rem',
                                  padding: '0.25rem'
                                }}
                                title="Remove from My Teams"
                              >
                                ⭐
                              </button>
                            ) : myTeams.length < 5 ? (
                              <button
                                onClick={() => handleAddTeam(team)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  fontSize: '1.2rem',
                                  padding: '0.25rem',
                                  opacity: 0.3
                                }}
                                title="Add to My Teams"
                                onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                                onMouseLeave={(e) => e.currentTarget.style.opacity = 0.3}
                              >
                                ☆
                              </button>
                            ) : (
                              <span style={{ 
                                fontSize: '0.75rem', 
                                color: '#999',
                                display: 'block',
                                textAlign: 'center'
                              }}>
                                Max 5
                              </span>
                            )}
                          </td>
                        )}
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
            <h2 className="card-title">
              ⭐ My Teams ({myTeams.length}/5)
            </h2>
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

          {myTeams.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">⭐</div>
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
                      <div style={{ flex: 1, minWidth: '200px' }}>
                        <Link 
                          to={`/team/${team.id}`}
                          style={{ 
                            fontSize: '1.35rem', 
                            fontWeight: '700', 
                            color: 'var(--primary-green)',
                            textDecoration: 'none'
                          }}
                        >
                          {team.name} →
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
                            <span style={{ color: '#888', fontSize: '0.9rem' }}>
                              📍 {team.state}
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
                      <div style={{ 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(4, 1fr)', 
                        gap: '1rem',
                        minWidth: '300px'
                      }}>
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
                              {team.name}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#666' }}>
                              {team.club} • {team.ageGroup} • {team.league}
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
                              fontWeight: '600'
                            }}>
                              ⭐ Added
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
    </div>
  );
}

export default Rankings;
