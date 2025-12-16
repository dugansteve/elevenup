import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { storage, AGE_GROUPS, LEAGUES, STATES } from '../data/sampleData';
import { useRankingsData } from '../data/useRankingsData';
import { useUser } from '../context/UserContext';

// Max players to display at once to prevent browser freeze
const PLAYERS_PER_PAGE = 100;
const MAX_SAFE_DISPLAY = 5000;

function Players() {
  const navigate = useNavigate();
  const { teamsData, playersData, ageGroups, isLoading } = useRankingsData();
  const { canPerform } = useUser();
  const canClaimPlayers = canPerform('canClaimPlayers');
  
  const [activeTab, setActiveTab] = useState('myplayers');
  const [localPlayers, setLocalPlayers] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [displayLimit, setDisplayLimit] = useState(PLAYERS_PER_PAGE);
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
  
  // All Players filters
  const [allPlayersFilters, setAllPlayersFilters] = useState({
    gender: 'ALL',
    ageGroup: 'ALL',
    league: 'ALL',
    state: 'ALL',
    nameSearch: ''
  });

  // Reset display limit when filters change
  useEffect(() => {
    setDisplayLimit(PLAYERS_PER_PAGE);
  }, [allPlayersFilters]);

  useEffect(() => {
    loadPlayers();
  }, []);

  const loadPlayers = () => {
    const savedPlayers = storage.getPlayers();
    setLocalPlayers(savedPlayers);
  };

  // Combine localStorage players with database players
  const players = useMemo(() => {
    // localStorage players (user-created)
    const userPlayers = localPlayers.map(p => ({ ...p, source: 'local' }));
    
    // Database players (from export)
    const dbPlayers = (playersData || []).map(p => ({ ...p, source: 'database' }));
    
    // Merge and deduplicate by name + team
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

  const handleAddPlayer = (e) => {
    e.preventDefault();
    
    const team = teamsData.find(t => t.id === parseInt(newPlayer.teamId));
    if (!team) return;

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
  // Handles both G13 and 13G formats
  const normalizeAgeGroup = (ag) => {
    if (!ag) return '';
    // If format is XXG or XXB (e.g., 13G, 08B), convert to GXX or BXX
    const match = ag.match(/^(\d{2}(?:\/\d{2})?)([GB])$/);
    if (match) {
      return `${match[2]}${match[1]}`; // Convert 13G -> G13
    }
    return ag;
  };

  // Check if two age groups match (handles G13 vs 13G)
  const ageGroupsMatch = (ag1, ag2) => {
    if (!ag1 || !ag2) return false;
    return normalizeAgeGroup(ag1) === normalizeAgeGroup(ag2);
  };

  // Filter teams based on selected age group for the dropdown
  // Uses flexible matching to handle both G13 and 13G formats
  const availableTeams = teamsData.filter(team => 
    ageGroupsMatch(team.ageGroup, newPlayer.ageGroup) &&
    (!searchTerm || 
      team.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
      (team.club && team.club.toLowerCase().includes(searchTerm.toLowerCase())))
  );

  // Get unique values for filters from all players
  const uniqueGenders = useMemo(() => {
    const genders = [...new Set(players.map(p => p.gender).filter(Boolean))];
    return genders.length > 0 ? genders : ['Female', 'Male'];
  }, [players]);

  const uniqueAgeGroups = useMemo(() => {
    const ages = [...new Set(players.map(p => p.ageGroup).filter(Boolean))];
    return ages.length > 0 ? ages.sort() : AGE_GROUPS;
  }, [players]);

  const uniqueLeagues = useMemo(() => {
    const leagues = [...new Set(players.map(p => p.league).filter(Boolean))];
    return leagues.length > 0 ? leagues.sort() : LEAGUES;
  }, [players]);

  const uniqueStates = useMemo(() => {
    const states = [...new Set(players.map(p => p.state).filter(Boolean))];
    return states.length > 0 ? states.sort() : STATES;
  }, [players]);

  // Filter all players based on filters
  const filteredAllPlayers = useMemo(() => {
    return players.filter(player => {
      if (allPlayersFilters.gender !== 'ALL' && player.gender !== allPlayersFilters.gender) return false;
      if (allPlayersFilters.ageGroup !== 'ALL' && player.ageGroup !== allPlayersFilters.ageGroup) return false;
      if (allPlayersFilters.league !== 'ALL' && player.league !== allPlayersFilters.league) return false;
      if (allPlayersFilters.state !== 'ALL' && player.state !== allPlayersFilters.state) return false;
      if (allPlayersFilters.nameSearch && !player.name.toLowerCase().includes(allPlayersFilters.nameSearch.toLowerCase())) return false;
      return true;
    });
  }, [players, allPlayersFilters]);

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
            {player.name}
          </h3>
          <div style={{ fontSize: '0.9rem', color: '#666' }}>
            {player.position} • {player.ageGroup}
            {player.gender && ` • ${player.gender}`}
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
            <span style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: '600',
              background: player.league === 'ECNL' ? '#e3f2fd' : 
                         player.league === 'GA' ? '#f3e5f5' :
                         player.league === 'ECNL-RL' ? '#ffebee' :
                         player.league === 'ASPIRE' ? '#e8f5e9' : '#f5f5f5',
              color: player.league === 'ECNL' ? '#1976d2' : 
                    player.league === 'GA' ? '#7b1fa2' :
                    player.league === 'ECNL-RL' ? '#c62828' :
                    player.league === 'ASPIRE' ? '#2e7d32' : '#666'
            }}>
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
        {(player.gradYear || player.graduation_year) && (
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Grad Year</div>
            <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>{player.gradYear || player.graduation_year}</div>
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
        View Profile →
      </button>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Players</h1>
        <p className="page-description">
          Manage your players and view all players in the system
          {playersData && playersData.length > 0 && (
            <span style={{ marginLeft: '0.5rem', color: '#666' }}>
              • {playersData.length.toLocaleString()} players loaded from database
            </span>
          )}
        </p>
      </div>

      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'myplayers' ? 'active' : ''}`}
            onClick={() => setActiveTab('myplayers')}
          >
            👤 My Players
          </button>
          <button
            className={`tab ${activeTab === 'allplayers' ? 'active' : ''}`}
            onClick={() => setActiveTab('allplayers')}
          >
            👥 All Players
          </button>
        </div>

        {activeTab === 'myplayers' ? (
          <>
            <div className="card-header" style={{ borderBottom: 'none', paddingBottom: 0, marginBottom: '1rem' }}>
              <h2 className="card-title">My Players ({localPlayers.length})</h2>
              {canClaimPlayers && (
                <button 
                  onClick={() => setShowAddModal(true)} 
                  className="btn btn-primary"
                >
                  ➕ Add Player
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
                  🔒 Pro account required to add/claim players. Upgrade to manage your players' profiles and badges.
                </p>
              </div>
            )}

            {localPlayers.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">👥</div>
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
          </>
        ) : (
          <>
            {/* All Players Filters */}
            <div style={{ 
              padding: '1rem', 
              background: '#f8f9fa', 
              borderRadius: '12px', 
              marginBottom: '1.5rem',
              border: '2px solid #e0e0e0'
            }}>
              {/* All filters on one line */}
              <div style={{ 
                display: 'flex', 
                flexWrap: 'wrap',
                gap: '0.5rem',
                alignItems: 'flex-end'
              }}>
                {/* Name Search */}
                <div style={{ flex: '1 1 150px', minWidth: '120px' }}>
                  <label style={{ fontSize: '0.7rem', color: '#666', display: 'block', marginBottom: '0.2rem' }}>Name</label>
                  <input
                    type="text"
                    placeholder="Search..."
                    value={allPlayersFilters.nameSearch}
                    onChange={(e) => setAllPlayersFilters({...allPlayersFilters, nameSearch: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div style={{ flex: '0 0 70px' }}>
                  <label style={{ fontSize: '0.7rem', color: '#666', display: 'block', marginBottom: '0.2rem' }}>B/G</label>
                  <select
                    value={allPlayersFilters.gender}
                    onChange={(e) => setAllPlayersFilters({...allPlayersFilters, gender: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem',
                      background: 'white'
                    }}
                  >
                    <option value="ALL">All</option>
                    {uniqueGenders.map(g => (
                      <option key={g} value={g}>{g === 'Female' ? 'G' : g === 'Male' ? 'B' : g}</option>
                    ))}
                  </select>
                </div>

                <div style={{ flex: '0 0 70px' }}>
                  <label style={{ fontSize: '0.7rem', color: '#666', display: 'block', marginBottom: '0.2rem' }}>Age</label>
                  <select
                    value={allPlayersFilters.ageGroup}
                    onChange={(e) => setAllPlayersFilters({...allPlayersFilters, ageGroup: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem',
                      background: 'white'
                    }}
                  >
                    <option value="ALL">All</option>
                    {uniqueAges.map(age => (
                      <option key={age} value={age}>{age}</option>
                    ))}
                  </select>
                </div>

                <div style={{ flex: '0 0 80px' }}>
                  <label style={{ fontSize: '0.7rem', color: '#666', display: 'block', marginBottom: '0.2rem' }}>League</label>
                  <select
                    value={allPlayersFilters.league}
                    onChange={(e) => setAllPlayersFilters({...allPlayersFilters, league: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem',
                      background: 'white'
                    }}
                  >
                    <option value="ALL">All</option>
                    {uniqueLeagues.map(league => (
                      <option key={league} value={league}>{league}</option>
                    ))}
                  </select>
                </div>

                <div style={{ flex: '0 0 60px' }}>
                  <label style={{ fontSize: '0.7rem', color: '#666', display: 'block', marginBottom: '0.2rem' }}>ST</label>
                  <select
                    value={allPlayersFilters.state}
                    onChange={(e) => setAllPlayersFilters({...allPlayersFilters, state: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem',
                      background: 'white'
                    }}
                  >
                    <option value="ALL">All</option>
                    {uniqueStates.map(state => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => setAllPlayersFilters({ 
                    gender: 'ALL', 
                    ageGroup: 'ALL', 
                    league: 'ALL', 
                    state: 'ALL',
                    nameSearch: ''
                  })}
                  style={{
                    padding: '0.4rem 0.6rem',
                    borderRadius: '4px',
                    border: '1px solid #ddd',
                    background: '#fff',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    color: '#666'
                  }}
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="card-header" style={{ borderBottom: 'none', paddingBottom: 0, marginBottom: '1rem' }}>
              <h2 className="card-title">
                All Players ({filteredAllPlayers.length}{filteredAllPlayers.length !== players.length ? ` of ${players.length}` : ''})
              </h2>
            </div>

            {players.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">👥</div>
                <div className="empty-state-text">No players in the system yet</div>
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem', maxWidth: '400px' }}>
                  To load players from your database, run:<br/>
                  <code style={{ background: '#f5f5f5', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>
                    python export_players.py
                  </code>
                </p>
                {canClaimPlayers && (
                  <button 
                    onClick={() => { setActiveTab('myplayers'); setShowAddModal(true); }} 
                    className="btn btn-primary"
                    style={{ marginTop: '1rem' }}
                  >
                    Or Add a Player Manually
                  </button>
                )}
              </div>
            ) : filteredAllPlayers.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-text">No players match your filters</div>
                <button 
                  onClick={() => setAllPlayersFilters({ 
                    gender: 'ALL', 
                    ageGroup: 'ALL', 
                    league: 'ALL', 
                    state: 'ALL',
                    nameSearch: ''
                  })}
                  className="btn btn-secondary"
                  style={{ marginTop: '1rem' }}
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <>
                {/* Display info and warning for large datasets */}
                {filteredAllPlayers.length > PLAYERS_PER_PAGE && (
                  <div style={{
                    padding: '0.75rem 1rem',
                    background: filteredAllPlayers.length > MAX_SAFE_DISPLAY ? '#fff3e0' : '#e3f2fd',
                    borderRadius: '8px',
                    marginBottom: '1rem',
                    border: `1px solid ${filteredAllPlayers.length > MAX_SAFE_DISPLAY ? '#ffcc80' : '#90caf9'}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.5rem'
                  }}>
                    <span style={{ color: filteredAllPlayers.length > MAX_SAFE_DISPLAY ? '#e65100' : '#1565c0' }}>
                      {filteredAllPlayers.length > MAX_SAFE_DISPLAY ? '⚠️' : 'ℹ️'} Showing {Math.min(displayLimit, filteredAllPlayers.length).toLocaleString()} of {filteredAllPlayers.length.toLocaleString()} players
                      {filteredAllPlayers.length > MAX_SAFE_DISPLAY && ' (use filters to narrow results)'}
                    </span>
                    <span style={{ fontSize: '0.85rem', color: '#666' }}>
                      💡 Tip: Use name search or filters above to find specific players
                    </span>
                  </div>
                )}
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
                  {filteredAllPlayers.slice(0, displayLimit).map(player => (
                    <PlayerCard key={player.id} player={player} showDelete={false} />
                  ))}
                </div>
                
                {/* Load More / Load All buttons */}
                {displayLimit < filteredAllPlayers.length && (
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    gap: '1rem',
                    marginTop: '2rem',
                    padding: '1rem',
                    background: '#f8f9fa',
                    borderRadius: '8px'
                  }}>
                    <button
                      onClick={() => setDisplayLimit(prev => Math.min(prev + PLAYERS_PER_PAGE, filteredAllPlayers.length))}
                      className="btn btn-primary"
                    >
                      Load {Math.min(PLAYERS_PER_PAGE, filteredAllPlayers.length - displayLimit).toLocaleString()} More
                    </button>
                    {filteredAllPlayers.length <= MAX_SAFE_DISPLAY && (
                      <button
                        onClick={() => setDisplayLimit(filteredAllPlayers.length)}
                        className="btn btn-secondary"
                      >
                        Load All ({filteredAllPlayers.length.toLocaleString()})
                      </button>
                    )}
                    {filteredAllPlayers.length > MAX_SAFE_DISPLAY && (
                      <span style={{ color: '#666', fontSize: '0.85rem', alignSelf: 'center' }}>
                        Use filters to load all players
                      </span>
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>

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
                        {team.name} ({team.league})
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
    </div>
  );
}

export default Players;
