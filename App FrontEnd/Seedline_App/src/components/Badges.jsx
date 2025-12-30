import { useState, useMemo, useRef, useCallback } from 'react';
import BadgeLeaderboard from './BadgeLeaderboard';
import { storage, BADGE_TYPES } from '../data/sampleData';
import { useRankingsData } from '../data/useRankingsData';
import { useUser } from '../context/UserContext';
import BottomSheetSelect from './BottomSheetSelect';
import { BadgesIcon, TeamsIcon } from './PaperIcons';
import { isElevenUpBrand } from '../config/brand';

// League categorization
const NATIONAL_LEAGUES = ['ECNL', 'ECNL-RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT', 'MLS NEXT HD', 'MLS NEXT AD'];

// Pagination constant
const PLAYERS_PER_PAGE = 200;

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

// Helper function to sort age groups numerically (G06, G07, G08/07, G09...G19)
function sortAgeGroupsNumerically(ageGroups) {
  return [...ageGroups].sort((a, b) => {
    const getNum = (ag) => {
      const match = ag.match(/\d+/);
      return match ? parseInt(match[0], 10) : 0;
    };
    return getNum(a) - getNum(b);
  });
}

function Badges() {
  const { canPerform, isPaid } = useUser();
  const canAwardBadges = canPerform('canAwardBadges');
  const { playersData, isLoading } = useRankingsData();
  const tableContainerRef = useRef(null);

  const [activeTab, setActiveTab] = useState(canAwardBadges ? 'award' : 'leaderboard');
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [displayLimit, setDisplayLimit] = useState(PLAYERS_PER_PAGE);

  // Search filters
  const [nameSearch, setNameSearch] = useState('');
  const [teamSearch, setTeamSearch] = useState('');
  const [selectedGender, setSelectedGender] = useState('Girls');
  const [selectedAgeGroup, setSelectedAgeGroup] = useState('ALL');
  const [selectedLeague, setSelectedLeague] = useState('ALL');
  const [selectedState, setSelectedState] = useState('ALL');
  const [showGenderAgeSheet, setShowGenderAgeSheet] = useState(false);

  // Sort state
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');

  // Drag scrolling state
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeftStart, setScrollLeftStart] = useState(0);

  const badges = storage.getBadges();

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

  // Get unique leagues from players data
  const uniqueLeagues = useMemo(() => {
    if (!playersData) return [];
    const leagues = [...new Set(playersData.map(p => p.league).filter(Boolean))];
    return leagues.sort();
  }, [playersData]);

  // Get unique states from players data
  const uniqueStates = useMemo(() => {
    if (!playersData) return [];
    const states = [...new Set(playersData.map(p => p.state).filter(Boolean))];
    return states.sort();
  }, [playersData]);

  // Get unique age groups from players data (for the gender/age sheet)
  const uniqueAgeGroups = useMemo(() => {
    if (!playersData) return [];
    const ages = [...new Set(playersData.map(p => p.ageGroup).filter(Boolean))];
    return sortAgeGroupsNumerically(ages);
  }, [playersData]);

  // Filter players based on search criteria
  const filteredPlayers = useMemo(() => {
    if (!playersData || playersData.length === 0) return [];

    let filtered = playersData.filter(player => {
      // Gender filter (always applied unless ALL)
      if (selectedGender !== 'ALL') {
        const playerGender = player.ageGroup ? player.ageGroup.charAt(0).toUpperCase() : '';
        const expectedPrefix = selectedGender === 'Girls' ? 'G' : 'B';
        if (playerGender !== expectedPrefix) return false;
      }

      // Age group filter
      if (selectedAgeGroup !== 'ALL') {
        if (player.ageGroup !== selectedAgeGroup) return false;
      }

      // League filter
      if (selectedLeague !== 'ALL') {
        if (player.league !== selectedLeague) return false;
      }

      // State filter
      if (selectedState !== 'ALL') {
        if (player.state !== selectedState) return false;
      }

      // Name filter
      if (nameSearch.length >= 2) {
        const searchLower = nameSearch.toLowerCase();
        const nameMatch = (player.name || '').toLowerCase().includes(searchLower) ||
                         (player.firstName || '').toLowerCase().includes(searchLower) ||
                         (player.lastName || '').toLowerCase().includes(searchLower);
        if (!nameMatch) return false;
      }

      // Team filter
      if (teamSearch.length >= 2) {
        const teamLower = teamSearch.toLowerCase();
        const teamMatch = (player.teamName || '').toLowerCase().includes(teamLower) ||
                         (player.club || '').toLowerCase().includes(teamLower);
        if (!teamMatch) return false;
      }

      return true;
    });

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
        case 'position':
          comparison = (a.position || '').localeCompare(b.position || '');
          break;
        default:
          comparison = (a.name || '').localeCompare(b.name || '');
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [playersData, nameSearch, teamSearch, selectedGender, selectedAgeGroup, selectedLeague, selectedState, sortField, sortDirection]);

  // Create a unique key for storing badges (use db id or name+team combo)
  const getPlayerBadgeKey = (player) => {
    if (player.id) return `db_${player.id}`;
    return `${player.name}_${player.teamName}`.toLowerCase().replace(/\s+/g, '_');
  };

  // Handle clicking a badge - award if not awarded, unaward if already awarded
  const handleBadgeClick = (badge) => {
    if (!selectedPlayer) return;

    const playerKey = getPlayerBadgeKey(selectedPlayer);
    const currentBadges = storage.getBadges();
    const playerBadges = currentBadges[playerKey] || {};
    const badgeType = badge.id;
    const currentCount = playerBadges[badgeType] || 0;

    if (currentCount > 0) {
      // Unaward: remove the badge completely
      delete playerBadges[badgeType];
    } else {
      // Award: add 1 (max 1 per type per user)
      playerBadges[badgeType] = 1;
    }

    // Store player info along with badges for display later
    if (Object.keys(playerBadges).filter(k => k !== '_playerInfo').length > 0) {
      playerBadges._playerInfo = {
        name: selectedPlayer.name,
        teamName: selectedPlayer.teamName,
        position: selectedPlayer.position,
        ageGroup: selectedPlayer.ageGroup,
        league: selectedPlayer.league,
        jerseyNumber: selectedPlayer.jerseyNumber
      };
    }

    currentBadges[playerKey] = playerBadges;
    storage.setBadges(currentBadges);
    setRefreshKey(prev => prev + 1);
  };

  // Get all players with badges for "My Badges" tab
  const getPlayerBadgeSummary = () => {
    const summary = [];
    const allBadges = storage.getBadges();
    const localPlayers = storage.getPlayers(); // Get localStorage players

    Object.entries(allBadges).forEach(([playerKey, playerBadges]) => {
      const badgeList = Object.entries(playerBadges)
        .filter(([key, count]) => key !== '_playerInfo' && count > 0)
        .map(([badgeId, count]) => {
          const badgeInfo = BADGE_TYPES.find(b => b.id === badgeId);
          return badgeInfo ? { ...badgeInfo, count } : null;
        })
        .filter(Boolean);

      if (badgeList.length > 0) {
        // Get player info from stored data
        let playerInfo = playerBadges._playerInfo || {};

        // If no _playerInfo, try to look up from available player data
        if (!playerInfo.name) {
          // Try localStorage players first (playerKey might be the ID)
          const numericKey = parseInt(playerKey);
          if (!isNaN(numericKey)) {
            const localPlayer = localPlayers.find(p => p.id === numericKey);
            if (localPlayer) {
              playerInfo = {
                name: localPlayer.name,
                teamName: localPlayer.teamName,
                position: localPlayer.position,
                ageGroup: localPlayer.ageGroup,
                league: localPlayer.league
              };
              // Also update storage so this lookup isn't needed again
              playerBadges._playerInfo = playerInfo;
              storage.setBadges(allBadges);
            }
          }

          // Try database players (playerKey format: db_123)
          if (!playerInfo.name && playerKey.startsWith('db_')) {
            const dbId = parseInt(playerKey.replace('db_', ''));
            const dbPlayer = playersData?.find(p => p.id === dbId);
            if (dbPlayer) {
              playerInfo = {
                name: dbPlayer.name,
                teamName: dbPlayer.teamName,
                position: dbPlayer.position,
                ageGroup: dbPlayer.ageGroup,
                league: dbPlayer.league
              };
              playerBadges._playerInfo = playerInfo;
              storage.setBadges(allBadges);
            }
          }
        }

        summary.push({
          playerKey,
          player: {
            name: playerInfo.name || playerKey,
            teamName: playerInfo.teamName || '',
            position: playerInfo.position || '',
            league: playerInfo.league || '',
            ageGroup: playerInfo.ageGroup || ''
          },
          badges: badgeList,
          totalBadges: badgeList.reduce((sum, b) => sum + b.count, 0)
        });
      }
    });

    return summary.sort((a, b) => b.totalBadges - a.totalBadges);
  };

  const playerBadgeSummary = useMemo(() => getPlayerBadgeSummary(), [badges, refreshKey]);

  // Get current badges for selected player
  const selectedPlayerBadges = useMemo(() => {
    if (!selectedPlayer) return {};
    const playerKey = getPlayerBadgeKey(selectedPlayer);
    const allBadges = storage.getBadges();
    return allBadges[playerKey] || {};
  }, [selectedPlayer, refreshKey]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Badges</h1>
        <p className="page-description">
          Award badges to any player and view the leaderboard
        </p>
      </div>

      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'award' ? 'active' : ''}`}
            onClick={() => setActiveTab('award')}
          >
            <BadgesIcon size={16} color="green" /> Award Badges
          </button>
          <button
            className={`tab ${activeTab === 'mybadges' ? 'active' : ''}`}
            onClick={() => setActiveTab('mybadges')}
          >
            {isElevenUpBrand ? '★' : '⭐'} My Badges
          </button>
          <button
            className={`tab ${activeTab === 'leaderboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('leaderboard')}
          >
            <TeamsIcon size={16} color="green" /> Leaderboard
          </button>
        </div>

        {activeTab === 'award' ? (
          <div>
            {!canAwardBadges ? (
              <div className="empty-state">
                <div className="empty-state-icon">🔒</div>
                <div className="empty-state-text">Pro Account Required</div>
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem', maxWidth: '400px', margin: '0.5rem auto 0' }}>
                  Upgrade to a Pro account to award badges to players. You can still view the leaderboard and existing badges.
                </p>
              </div>
            ) : (
              <>
                {/* Selected Player & Badge Awards - Show at top when player selected */}
                {selectedPlayer && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{
                      padding: '1rem',
                      background: '#f0f7ed',
                      borderRadius: '8px',
                      marginBottom: '1rem',
                      border: '2px solid var(--accent-green)'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <strong style={{ color: 'var(--primary-green)', fontSize: '1.1rem' }}>
                            {selectedPlayer.name}
                          </strong>
                          {selectedPlayer.jerseyNumber && (
                            <span style={{ marginLeft: '0.5rem', color: '#666' }}>
                              #{selectedPlayer.jerseyNumber}
                            </span>
                          )}
                          <div style={{ fontSize: '0.85rem', color: '#666' }}>
                            {selectedPlayer.teamName} • {selectedPlayer.ageGroup}
                          </div>
                        </div>
                        <button
                          onClick={() => setSelectedPlayer(null)}
                          style={{
                            background: 'none',
                            border: '1px solid #ccc',
                            padding: '0.25rem 0.75rem',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.85rem'
                          }}
                        >
                          Clear
                        </button>
                      </div>
                      <p style={{ margin: '0.75rem 0 0', color: 'var(--primary-green)', fontSize: '0.9rem' }}>
                        Click a badge to award it. Click an awarded badge to remove it.
                      </p>
                    </div>

                    <div className="badge-grid">
                      {BADGE_TYPES.map(badge => {
                        const count = selectedPlayerBadges[badge.id] || 0;
                        const isAwarded = count > 0;

                        return (
                          <div
                            key={badge.id}
                            className="badge-card"
                            onClick={() => handleBadgeClick(badge)}
                            style={{
                              borderColor: isAwarded ? 'var(--accent-green)' : 'transparent',
                              background: isAwarded
                                ? 'linear-gradient(135deg, #f0f7ed 0%, #e8f5e0 100%)'
                                : 'white',
                              position: 'relative',
                              cursor: 'pointer'
                            }}
                          >
                            {isAwarded && (
                              <div style={{
                                position: 'absolute',
                                top: '10px',
                                right: '10px',
                                background: 'var(--accent-green)',
                                color: 'white',
                                borderRadius: '50%',
                                width: '24px',
                                height: '24px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '14px',
                                fontWeight: '700'
                              }}>
                                ✓
                              </div>
                            )}
                            <div className="badge-emoji">{badge.emoji}</div>
                            <div className="badge-name">{badge.name}</div>
                            <div className="badge-description">{badge.description}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Filters Section - Same as Players page */}
                <div className="filters-compact" style={{ marginBottom: '1rem' }}>
                  {/* Search Fields Row */}
                  <div className="search-fields-row">
                    <div className="filter-group search-group search-player-group">
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Player name..."
                        value={nameSearch}
                        onChange={(e) => setNameSearch(e.target.value)}
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
                          ...(uniqueLeagues.filter(l => !NATIONAL_LEAGUES.includes(l)).length > 0 ? [{
                            group: 'Other Leagues',
                            options: uniqueLeagues.filter(l => !NATIONAL_LEAGUES.includes(l)).map(league => ({
                              value: league,
                              label: league
                            }))
                          }] : [])
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

                {/* Player count */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '0.5rem',
                  padding: '0.5rem 0'
                }}>
                  <span style={{ fontSize: '0.9rem', color: '#666' }}>
                    {displayLimit < filteredPlayers.length
                      ? `${displayLimit} of ${filteredPlayers.length.toLocaleString()} players`
                      : `${filteredPlayers.length.toLocaleString()} players`}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#888' }}>
                    Click a row to select player
                  </span>
                </div>

                {/* Players Table */}
                {filteredPlayers.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">🔍</div>
                    <div className="empty-state-text">No players found matching your filters</div>
                    <button
                      onClick={() => {
                        setNameSearch('');
                        setTeamSearch('');
                        setSelectedGender('Girls');
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
                    <table className="data-table rankings-table" style={{ tableLayout: 'fixed', width: '100%' }}>
                      <thead>
                        <tr>
                          <th
                            className="sortable-header"
                            onClick={() => handleSort('name')}
                            style={{ cursor: 'pointer', width: '54px', maxWidth: '54px' }}
                          >
                            Name{getSortIndicator('name')}
                          </th>
                          <th
                            className="sortable-header"
                            onClick={() => handleSort('position')}
                            style={{ cursor: 'pointer', width: '20px', maxWidth: '20px', textAlign: 'center' }}
                          >
                            Pos{getSortIndicator('position')}
                          </th>
                          <th className="col-age" style={{ width: '36px', maxWidth: '36px' }}>Age</th>
                          <th
                            className="sortable-header"
                            onClick={() => handleSort('team')}
                            style={{ cursor: 'pointer' }}
                          >
                            Team{getSortIndicator('team')}
                          </th>
                          <th className="col-league" style={{ width: '33px', maxWidth: '33px' }}>League</th>
                          <th className="col-state" style={{ width: '28px', maxWidth: '28px' }}>ST</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredPlayers.slice(0, displayLimit).map((player, idx) => {
                          const isSelected = selectedPlayer && getPlayerBadgeKey(selectedPlayer) === getPlayerBadgeKey(player);
                          return (
                            <tr
                              key={`${player.id || idx}-${player.name}`}
                              onClick={() => setSelectedPlayer(player)}
                              style={{
                                cursor: 'pointer',
                                background: isSelected ? '#f0f7ed' : undefined
                              }}
                            >
                              <td style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                <span
                                  className="team-name-link"
                                  style={{
                                    fontWeight: isSelected ? '700' : undefined,
                                    color: isSelected ? 'var(--primary-green)' : undefined
                                  }}
                                  title={player.name}
                                >
                                  {player.name}
                                  {isSelected && <span style={{ marginLeft: '0.25rem' }}>✓</span>}
                                </span>
                              </td>
                              <td style={{ fontSize: '0.8rem', textAlign: 'center' }}>
                                {player.position ? player.position.charAt(0) : '-'}
                              </td>
                              <td className="col-age" style={{ fontSize: '0.8rem' }}>{player.ageGroup || '-'}</td>
                              <td style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {player.teamName ? (
                                  <span
                                    style={{ fontSize: '0.8rem' }}
                                    title={player.teamName}
                                  >
                                    {player.teamName}
                                  </span>
                                ) : '-'}
                              </td>
                              <td className="col-league">
                                {player.league ? (
                                  <span className="league-badge-sm" style={{ ...getLeagueBadgeStyle(player.league), fontSize: '0.65rem', padding: '0.1rem 0.2rem' }}>
                                    {player.league}
                                  </span>
                                ) : '-'}
                              </td>
                              <td className="col-state" style={{ fontSize: '0.8rem' }}>{player.state || '-'}</td>
                            </tr>
                          );
                        })}
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
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        ) : activeTab === 'mybadges' ? (
          <div>
            {playerBadgeSummary.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon"><BadgesIcon size={48} color="gray" /></div>
                <div className="empty-state-text">No badges awarded yet</div>
                <button 
                  onClick={() => setActiveTab('award')} 
                  className="btn btn-primary"
                  style={{ marginTop: '1rem' }}
                >
                  Award Your First Badge
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {playerBadgeSummary.map(({ playerKey, player, badges: playerBadges, totalBadges }) => (
                  <div
                    key={playerKey}
                    style={{
                      background: 'linear-gradient(135deg, #fff 0%, #f8f9fa 100%)',
                      borderRadius: '12px',
                      padding: '1.5rem',
                      border: '2px solid #e0e0e0'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ 
                          fontSize: '1.25rem', 
                          fontWeight: '700', 
                          color: 'var(--primary-green)',
                          marginBottom: '0.25rem'
                        }}>
                          {player.name}
                        </h3>
                        <div style={{ fontSize: '0.9rem', color: '#666' }}>
                          {player.position && `${player.position} • `}{player.teamName} {player.league && `(${player.league})`}
                        </div>
                      </div>
                      <div style={{
                        background: 'var(--accent-green)',
                        color: 'white',
                        padding: '0.5rem 1rem',
                        borderRadius: '8px',
                        fontWeight: '700'
                      }}>
                        {totalBadges} Total
                      </div>
                    </div>
                    
                    <div style={{ 
                      display: 'flex', 
                      flexWrap: 'wrap', 
                      gap: '0.75rem' 
                    }}>
                      {playerBadges.map(badge => (
                        <div
                          key={badge.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 0.75rem',
                            background: '#f0f7ed',
                            borderRadius: '8px',
                            border: '1px solid var(--light-green)'
                          }}
                        >
                          <span style={{ fontSize: '1.25rem' }}>{badge.emoji}</span>
                          <span style={{ fontWeight: '600', color: 'var(--primary-green)' }}>
                            {badge.name}
                          </span>
                          <span style={{
                            background: 'var(--accent-green)',
                            color: 'white',
                            padding: '0.125rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            fontWeight: '600'
                          }}>
                            ×{badge.count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <BadgeLeaderboard key={refreshKey} />
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

export default Badges;
