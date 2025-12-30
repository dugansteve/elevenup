import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { storage, AGE_GROUPS, LEAGUES, STATES } from '../data/sampleData';
import { useRankingsData } from '../data/useRankingsData';
import { useUser } from '../context/UserContext';
import BottomSheetSelect from './BottomSheetSelect';

// API Base URL - empty for web version (display modes require local backend)
const API_BASE = '';

// Pagination constants
const PLAYERS_PER_PAGE = 200;
const MAX_SAFE_DISPLAY = 5000;

// Session storage keys for preserving state
const STORAGE_KEYS = {
  scrollPosition: 'players_scroll_position',
  filters: 'players_filters',
  showDetails: 'players_show_details'
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

// Helper function to sort age groups numerically
function sortAgeGroupsNumerically(ageGroups) {
  return [...ageGroups].sort((a, b) => {
    const getNum = (ag) => {
      const match = ag.match(/\d+/);
      return match ? parseInt(match[0], 10) : 0;
    };
    return getNum(a) - getNum(b);
  });
}

function Players() {
  const navigate = useNavigate();
  const { teamsData, playersData, ageGroups, isLoading, lastUpdated } = useRankingsData();
  const { canPerform } = useUser();
  const canClaimPlayers = canPerform('canClaimPlayers');
  const tableContainerRef = useRef(null);

  // Display modes for claimed players (player_id -> 'full' | 'initial')
  const [displayModes, setDisplayModes] = useState({});

  // Fetch display modes for all claimed players
  useEffect(() => {
    async function fetchDisplayModes() {
      if (!API_BASE) return; // Skip if no backend configured
      try {
        const response = await fetch(`${API_BASE}/claims/display-modes`);
        const data = await response.json();
        if (data.display_modes) {
          setDisplayModes(data.display_modes);
        }
      } catch (error) {
        console.error('Error fetching display modes:', error);
      }
    }
    fetchDisplayModes();
  }, []);

  // Helper function to format player name based on display mode
  const getDisplayName = useCallback((player) => {
    const fullName = player.name || `${player.firstName || ''} ${player.lastName || ''}`.trim();
    const displayMode = displayModes[player.id];

    if (displayMode === 'initial') {
      const parts = fullName.trim().split(/\s+/);
      if (parts.length >= 2) {
        const firstName = parts[0];
        const lastInitial = parts[parts.length - 1].charAt(0).toUpperCase();
        return `${firstName} ${lastInitial}.`;
      }
    }

    return fullName;
  }, [displayModes]);

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

  const [viewMode, setViewMode] = useState('allplayers');
  const [localPlayers, setLocalPlayers] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [displayLimit, setDisplayLimit] = useState(savedFilters?.displayLimit || PLAYERS_PER_PAGE);
  const [showDetails, setShowDetails] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.showDetails);
      return saved === 'true';
    } catch { return false; }
  });

  const [newPlayer, setNewPlayer] = useState({
    name: '',
    position: '',
    ageGroup: 'G13',
    teamId: '',
    gender: 'Female',
    jerseyNumber: '',
    gradYear: ''
  });
  const [searchTerm, setSearchTerm] = useState('');

  // Filter state
  const [selectedGender, setSelectedGender] = useState(savedFilters?.gender || 'Girls');
  const [selectedAgeGroup, setSelectedAgeGroup] = useState(savedFilters?.ageGroup || 'ALL');
  const [selectedLeague, setSelectedLeague] = useState(savedFilters?.league || 'ALL');
  const [selectedState, setSelectedState] = useState(savedFilters?.state || 'ALL');
  const [filterSearch, setFilterSearch] = useState(savedFilters?.search || '');
  const [teamSearch, setTeamSearch] = useState(savedFilters?.teamSearch || '');

  // Sort state
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');

  // Save filters to sessionStorage whenever they change
  useEffect(() => {
    const filters = {
      gender: selectedGender,
      ageGroup: selectedAgeGroup,
      league: selectedLeague,
      state: selectedState,
      search: filterSearch,
      teamSearch: teamSearch,
      displayLimit: displayLimit
    };
    sessionStorage.setItem(STORAGE_KEYS.filters, JSON.stringify(filters));
  }, [selectedGender, selectedAgeGroup, selectedLeague, selectedState, filterSearch, teamSearch, displayLimit]);

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

  // Reset display limit when filters change
  const isInitialMount = useRef(true);
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    setDisplayLimit(PLAYERS_PER_PAGE);
  }, [selectedGender, selectedAgeGroup, selectedLeague, selectedState, filterSearch, teamSearch]);

  useEffect(() => {
    loadPlayers();
  }, []);

  const loadPlayers = () => {
    const savedPlayers = storage.getPlayers();
    setLocalPlayers(savedPlayers);
  };

  // Combine localStorage players with database players
  const players = useMemo(() => {
    const userPlayers = localPlayers.map(p => ({ ...p, source: 'local' }));
    const dbPlayers = (playersData || []).map(p => ({ ...p, source: 'database' }));

    const allPlayers = [...userPlayers];
    const existingKeys = new Set(userPlayers.map(p => `${p.name}-${p.teamName}`.toLowerCase()));

    for (const dbPlayer of dbPlayers) {
      const key = `${dbPlayer.name}-${dbPlayer.teamName}`.toLowerCase();
      if (!existingKeys.has(key)) {
        allPlayers.push(dbPlayer);
        existingKeys.add(key);
      }
    }

    return allPlayers;
  }, [localPlayers, playersData]);

  // Get unique leagues from players data
  const uniqueLeagues = useMemo(() => {
    const leagues = [...new Set(players.map(p => p.league).filter(Boolean))];
    return leagues.sort();
  }, [players]);

  // Get unique states from players data
  const uniqueStates = useMemo(() => {
    const states = [...new Set(players.map(p => p.state).filter(Boolean))];
    return states.sort();
  }, [players]);

  // Get unique age groups from players data
  const uniqueAgeGroups = useMemo(() => {
    const ages = [...new Set(players.map(p => p.ageGroup).filter(Boolean))];
    return sortAgeGroupsNumerically(ages);
  }, [players]);

  // Filter and sort players
  const filteredPlayers = useMemo(() => {
    let filtered = [...players];

    // Gender filter
    if (selectedGender !== 'ALL') {
      filtered = filtered.filter(player => {
        if (selectedGender === 'Girls') {
          return player.gender === 'Female' || (player.ageGroup && player.ageGroup.startsWith('G'));
        } else {
          return player.gender === 'Male' || (player.ageGroup && player.ageGroup.startsWith('B'));
        }
      });
    }

    // Age group filter
    if (selectedAgeGroup !== 'ALL') {
      filtered = filtered.filter(player => player.ageGroup === selectedAgeGroup);
    }

    // League filter
    if (selectedLeague !== 'ALL') {
      filtered = filtered.filter(player => player.league === selectedLeague);
    }

    // State filter
    if (selectedState !== 'ALL') {
      filtered = filtered.filter(player => player.state === selectedState);
    }

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'name':
          comparison = (a.name || '').localeCompare(b.name || '');
          break;
        case 'team':
          comparison = (a.teamName || '').localeCompare(b.teamName || '');
          break;
        case 'club':
          comparison = (a.club || '').localeCompare(b.club || '');
          break;
        case 'position':
          comparison = (a.position || '').localeCompare(b.position || '');
          break;
        case 'gradYear':
          comparison = (a.gradYear || a.graduationYear || a.graduation_year || '9999').localeCompare(b.gradYear || b.graduationYear || b.graduation_year || '9999');
          break;
        default:
          comparison = (a.name || '').localeCompare(b.name || '');
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

    // Player name search filter
    if (filterSearch) {
      const term = filterSearch.toLowerCase();
      filtered = filtered.filter(player =>
        player.name?.toLowerCase().includes(term)
      );
    }

    // Team/club search filter
    if (teamSearch) {
      const term = teamSearch.toLowerCase();
      filtered = filtered.filter(player =>
        player.teamName?.toLowerCase().includes(term) ||
        player.club?.toLowerCase().includes(term)
      );
    }

    return filtered;
  }, [players, selectedGender, selectedAgeGroup, selectedLeague, selectedState, filterSearch, teamSearch, sortField, sortDirection]);

  // Handle column header click for sorting
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Get sort indicator
  const getSortIndicator = (field) => {
    if (sortField !== field) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  const handleAddPlayer = (e) => {
    e.preventDefault();

    const team = teamsData.find(t => t.id === parseInt(newPlayer.teamId));
    if (!team) return;

    // Check for duplicate player with same name on this team
    const normalizeName = (name) => (name || '').toLowerCase().trim();
    const newPlayerNameNormalized = normalizeName(newPlayer.name);
    const selectedTeamId = parseInt(newPlayer.teamId);

    // Check both local players and database players for this team
    const existingOnTeam = players.filter(p => {
      // Match by teamId or teamName
      const matchesTeam = p.teamId === selectedTeamId ||
        (p.teamName && p.teamName.toLowerCase() === team.name.toLowerCase());
      return matchesTeam;
    });

    const duplicatePlayer = existingOnTeam.find(p =>
      normalizeName(p.name) === newPlayerNameNormalized
    );

    if (duplicatePlayer) {
      alert(`A player named "${newPlayer.name}" already exists on ${team.name}'s roster. Please use a different name or edit the existing player.`);
      return;
    }

    const player = {
      id: Date.now(),
      ...newPlayer,
      teamId: parseInt(newPlayer.teamId),
      teamName: team.name,
      club: team.club || team.name,
      state: team.state,
      league: team.league,
      number: newPlayer.jerseyNumber || null,
      gradYear: newPlayer.gradYear || null
    };

    const updatedPlayers = [...localPlayers, player];
    storage.setPlayers(updatedPlayers);
    setLocalPlayers(updatedPlayers);

    setNewPlayer({
      name: '',
      position: '',
      ageGroup: 'G13',
      teamId: '',
      gender: 'Female',
      jerseyNumber: '',
      gradYear: ''
    });
    setShowAddModal(false);
  };

  const handleDeletePlayer = (playerId) => {
    if (window.confirm('Are you sure you want to remove this player?')) {
      const updatedPlayers = localPlayers.filter(p => p.id !== playerId);
      storage.setPlayers(updatedPlayers);
      setLocalPlayers(updatedPlayers);
    }
  };

  // Helper function to normalize age group for comparison
  const normalizeAgeGroup = (ag) => {
    if (!ag) return '';
    const match = ag.match(/^(\d{2}(?:\/\d{2})?)([GB])$/);
    if (match) {
      return `${match[2]}${match[1]}`;
    }
    return ag;
  };

  const ageGroupsMatch = (ag1, ag2) => {
    if (!ag1 || !ag2) return false;
    return normalizeAgeGroup(ag1) === normalizeAgeGroup(ag2);
  };

  const availableTeams = teamsData.filter(team =>
    ageGroupsMatch(team.ageGroup, newPlayer.ageGroup) &&
    (!searchTerm ||
      team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (team.club && team.club.toLowerCase().includes(searchTerm.toLowerCase())))
  );

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

  const PlayerCard = ({ player, showDelete = false }) => (
    <div
      style={{
        background: 'linear-gradient(135deg, #fff 0%, #f8f9fa 100%)',
        borderRadius: '12px',
        padding: '1.5rem',
        border: '2px solid #e0e0e0',
        cursor: 'pointer',
        transition: 'all 0.2s ease'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)';
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          <h3
            onClick={() => navigate(`/player/${player.id}`)}
            style={{
              fontSize: '1.25rem',
              fontWeight: '700',
              color: 'var(--primary-green)',
              marginBottom: '0.25rem',
              cursor: 'pointer'
            }}
          >
            {getDisplayName(player)}
          </h3>
          <div style={{ fontSize: '0.9rem', color: '#666' }}>
            {player.position} {player.ageGroup && `• ${player.ageGroup}`}
          </div>
        </div>
        {showDelete && (
          <button
            onClick={() => handleDeletePlayer(player.id)}
            style={{
              background: '#fee',
              border: '1px solid #fcc',
              color: '#c33',
              padding: '0.5rem 0.75rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '600'
            }}
          >
            Remove
          </button>
        )}
      </div>

      <div style={{
        background: 'white',
        padding: '1rem',
        borderRadius: '8px',
        marginBottom: '0.75rem'
      }}>
        <div style={{ fontSize: '0.85rem', color: '#888', marginBottom: '0.25rem' }}>Team</div>
        <div style={{ fontWeight: '600', color: 'var(--text-dark)' }}>{player.teamName}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Club</div>
          <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>{player.club}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>League</div>
          <div>
            <span className="league-badge-sm" style={getLeagueBadgeStyle(player.league)}>
              {player.league}
            </span>
          </div>
        </div>
        {(player.number || player.jerseyNumber) && (
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Jersey #</div>
            <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>{player.number || player.jerseyNumber}</div>
          </div>
        )}
        {(player.gradYear || player.graduationYear || player.graduation_year) && (
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Grad Year</div>
            <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>{player.gradYear || player.graduationYear || player.graduation_year}</div>
          </div>
        )}
        {player.state && (
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>State</div>
            <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>{player.state}</div>
          </div>
        )}
      </div>

      <button
        onClick={() => navigate(`/player/${player.id}`)}
        className="btn btn-secondary"
        style={{ width: '100%', marginTop: '1rem' }}
      >
        View Profile
      </button>
    </div>
  );

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">Loading players data...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="card rankings-header-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setViewMode('allplayers')}
              className="view-toggle-btn"
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                background: viewMode === 'allplayers'
                  ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)'
                  : '#f5f5f5',
                color: viewMode === 'allplayers' ? 'white' : '#666',
                transition: 'all 0.2s ease'
              }}
            >
              All Players
            </button>
            <button
              onClick={() => setViewMode('myplayers')}
              className="view-toggle-btn"
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                background: viewMode === 'myplayers'
                  ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)'
                  : '#f5f5f5',
                color: viewMode === 'myplayers' ? 'white' : '#666',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}
            >
              My Players
              {localPlayers.length > 0 && (
                <span style={{
                  background: viewMode === 'myplayers' ? 'rgba(255,255,255,0.3)' : 'var(--accent-green)',
                  color: 'white',
                  padding: '0.125rem 0.5rem',
                  borderRadius: '10px',
                  fontSize: '0.75rem'
                }}>
                  {localPlayers.length}
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

      {/* All Players View */}
      {viewMode === 'allplayers' && (
        <>
          {/* Filters */}
          <div className="card filters-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
            <div className="filters-compact">
              {/* Search Fields Row */}
              <div className="search-fields-row">
                <div className="filter-group search-group search-player-group">
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Player name..."
                    value={filterSearch}
                    onChange={(e) => setFilterSearch(e.target.value)}
                  />
                </div>
                <div className="filter-group search-group search-team-group">
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Team or club..."
                    value={teamSearch}
                    onChange={(e) => setTeamSearch(e.target.value)}
                  />
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
                    options={[
                      { value: 'ALL', label: 'All Leagues' },
                      {
                        group: 'National Leagues',
                        options: NATIONAL_LEAGUES.filter(l => uniqueLeagues.includes(l)).map(league => ({
                          value: league,
                          label: league
                        }))
                      },
                      {
                        group: 'Regional Leagues',
                        options: REGIONAL_LEAGUES.filter(l => uniqueLeagues.includes(l)).map(league => ({
                          value: league,
                          label: league
                        }))
                      }
                    ].filter(opt => !opt.group || opt.options.length > 0)}
                  />
                </div>

                <div className="filter-group">
                  <BottomSheetSelect
                    label="State"
                    value={selectedState}
                    onChange={setSelectedState}
                    options={[
                      { value: 'ALL', label: 'All States' },
                      { group: 'States', options: uniqueStates.map(state => ({ value: state, label: state })) }
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
                {displayLimit < filteredPlayers.length
                  ? `${displayLimit} of ${filteredPlayers.length} players`
                  : `${filteredPlayers.length} players`}
              </span>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                {canClaimPlayers && (
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="btn btn-primary"
                    style={{ padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
                  >
                    + Add Player
                  </button>
                )}
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
            </div>

            {filteredPlayers.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-text">No players found matching your filters</div>
                <button
                  onClick={() => {
                    setFilterSearch('');
                    setTeamSearch('');
                    setSelectedGender('ALL');
                    setSelectedAgeGroup('ALL');
                    setSelectedLeague('ALL');
                    setSelectedState('ALL');
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
                        className="sortable-header"
                        onClick={() => handleSort('name')}
                        style={{ cursor: 'pointer' }}
                      >
                        Name{getSortIndicator('name')}
                      </th>
                      <th
                        className="sortable-header"
                        onClick={() => handleSort('position')}
                        style={{ cursor: 'pointer' }}
                      >
                        Pos{getSortIndicator('position')}
                      </th>
                      <th className="col-age">Age</th>
                      <th
                        className="sortable-header"
                        onClick={() => handleSort('team')}
                        style={{ cursor: 'pointer' }}
                      >
                        Team{getSortIndicator('team')}
                      </th>
                      <th className="col-league">League</th>
                      <th className="col-state">ST</th>
                      <th>Coll. Commit</th>
                      {showDetails && (
                        <th
                          className="sortable-header"
                          onClick={() => handleSort('gradYear')}
                          style={{ cursor: 'pointer' }}
                        >
                          Grad{getSortIndicator('gradYear')}
                        </th>
                      )}
                      {showDetails && <th>Jersey</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPlayers.slice(0, displayLimit).map((player) => (
                      <tr key={player.id}>
                        <td>
                          <Link
                            to={`/player/${player.id}`}
                            className="team-name-link"
                            onClick={saveScrollPosition}
                          >
                            {getDisplayName(player)}
                          </Link>
                        </td>
                        <td>{player.position || '-'}</td>
                        <td className="col-age">{player.ageGroup || '-'}</td>
                        <td>
                          {player.teamName ? (
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
                          ) : '-'}
                        </td>
                        <td className="col-league">
                          {player.league ? (
                            <span className="league-badge-sm" style={getLeagueBadgeStyle(player.league)}>
                              {player.league}
                            </span>
                          ) : '-'}
                        </td>
                        <td className="col-state">{player.state || '-'}</td>
                        <td>{player.collegeCommitment || player.college_commitment || '-'}</td>
                        {showDetails && <td>{player.gradYear || player.graduationYear || player.graduation_year || '-'}</td>}
                        {showDetails && <td>{player.number || player.jerseyNumber || '-'}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Load More button */}
                {displayLimit < filteredPlayers.length && (
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
                      onClick={() => setDisplayLimit(prev => Math.min(prev + PLAYERS_PER_PAGE, filteredPlayers.length))}
                      className="btn btn-primary"
                      style={{ padding: '0.75rem 2rem' }}
                    >
                      Load {Math.min(PLAYERS_PER_PAGE, filteredPlayers.length - displayLimit)} More Players
                    </button>
                    {filteredPlayers.length <= MAX_SAFE_DISPLAY && (
                      <button
                        onClick={() => setDisplayLimit(filteredPlayers.length)}
                        className="btn btn-secondary"
                        style={{ padding: '0.75rem 1.5rem' }}
                      >
                        Load All ({filteredPlayers.length})
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* My Players View */}
      {viewMode === 'myplayers' && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 className="card-title">My Players ({localPlayers.length})</h2>
            {canClaimPlayers && (
              <button
                onClick={() => setShowAddModal(true)}
                className="btn btn-primary"
              >
                + Add Player
              </button>
            )}
          </div>

          {!canClaimPlayers && (
            <div style={{
              padding: '1rem',
              background: '#fff3e0',
              borderRadius: '8px',
              marginBottom: '1rem',
              border: '1px solid #ffcc80'
            }}>
              <p style={{ margin: 0, color: '#e65100', fontWeight: '500' }}>
                Pro account required to add/claim players. Upgrade to manage your players' profiles and badges.
              </p>
            </div>
          )}

          {localPlayers.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">👤</div>
              <div className="empty-state-text">No players yet</div>
              {canClaimPlayers ? (
                <button
                  onClick={() => setShowAddModal(true)}
                  className="btn btn-primary"
                  style={{ marginTop: '1rem' }}
                >
                  Add Your First Player
                </button>
              ) : (
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  Upgrade to Pro to add and manage players
                </p>
              )}
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
              {localPlayers.map(player => (
                <PlayerCard key={player.id} player={player} showDelete={canClaimPlayers} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Player Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Add New Player</h2>
            </div>

            {isLoading ? (
              <div className="loading">Loading teams...</div>
            ) : (
              <form onSubmit={handleAddPlayer}>
                <div className="form-group">
                  <label className="form-label">Player Name *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={newPlayer.name}
                    onChange={(e) => setNewPlayer({...newPlayer, name: e.target.value})}
                    placeholder="Enter player name"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Gender *</label>
                  <select
                    className="form-select"
                    value={newPlayer.gender}
                    onChange={(e) => setNewPlayer({...newPlayer, gender: e.target.value})}
                    required
                  >
                    <option value="Female">Female</option>
                    <option value="Male">Male</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Position *</label>
                  <select
                    className="form-select"
                    value={newPlayer.position}
                    onChange={(e) => setNewPlayer({...newPlayer, position: e.target.value})}
                    required
                  >
                    <option value="">Select position</option>
                    <option value="Goalkeeper">Goalkeeper</option>
                    <option value="Defender">Defender</option>
                    <option value="Midfielder">Midfielder</option>
                    <option value="Forward">Forward</option>
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Jersey Number</label>
                    <input
                      type="text"
                      className="form-input"
                      value={newPlayer.jerseyNumber}
                      onChange={(e) => setNewPlayer({...newPlayer, jerseyNumber: e.target.value})}
                      placeholder="e.g., 10"
                      maxLength="3"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Graduation Year</label>
                    <input
                      type="text"
                      className="form-input"
                      value={newPlayer.gradYear}
                      onChange={(e) => setNewPlayer({...newPlayer, gradYear: e.target.value})}
                      placeholder="e.g., 2028"
                      maxLength="4"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Age Group *</label>
                  <select
                    className="form-select"
                    value={newPlayer.ageGroup}
                    onChange={(e) => setNewPlayer({...newPlayer, ageGroup: e.target.value, teamId: ''})}
                    required
                  >
                    {ageGroups.map(age => (
                      <option key={age} value={age}>{age}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Search Team</label>
                  <input
                    type="text"
                    className="form-input"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by team or club name..."
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Team * ({availableTeams.length} available)</label>
                  <select
                    className="form-select"
                    value={newPlayer.teamId}
                    onChange={(e) => setNewPlayer({...newPlayer, teamId: e.target.value})}
                    required
                  >
                    <option value="">Select team</option>
                    {availableTeams.slice(0, 100).map(team => (
                      <option key={team.id} value={team.id}>
                        {team.name} {team.ageGroup} ({team.league})
                      </option>
                    ))}
                    {availableTeams.length > 100 && (
                      <option disabled>... Use search to find more teams</option>
                    )}
                  </select>
                </div>

                <div className="modal-actions">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Add Player
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
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
                    {sortAgeGroupsNumerically(uniqueAgeGroups.filter(a => a.startsWith('G'))).map(age => (
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
                    {sortAgeGroupsNumerically(uniqueAgeGroups.filter(a => a.startsWith('B'))).map(age => (
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

export default Players;
