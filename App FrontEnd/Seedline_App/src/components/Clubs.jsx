import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';

// Helper to extract actual club name by stripping age group suffixes
function extractClubName(teamName) {
  if (!teamName) return '';
  
  // Common patterns to remove from end of team name:
  // - Age groups like: 13G, G13, 12G, G12, 11G, G11, etc.
  // - With optional prefixes like: GA, RL, etc.
  // - Examples: "Cincinnati United 13G", "Tophat 13G Ga Gold", "Beach FC (Ca) G11"
  
  let name = teamName.trim();
  
  // Remove trailing age group patterns
  // Pattern matches: space + optional word + age indicator at end
  // Examples: " 13G", " G13", " 12G Ga Gold", " G11 RL"
  name = name
    // Remove " 13G", " G13", " 12G", etc at end
    .replace(/\s+[GB]?\d{2}[GB]?(\s+(Ga|RL|Gold|White|Blue|Red|Black|Premier|Elite|Academy|Select|Pre-Academy|Pre Academy))*\s*$/i, '')
    // Remove standalone age at end like " 13", " 12", " 11"
    .replace(/\s+\d{2}\s*$/, '')
    // Remove trailing parenthetical state like "(Ca)", "(Tx)"
    .replace(/\s*\([A-Za-z]{2}\)\s*$/, '')
    // Clean up any double spaces
    .replace(/\s+/g, ' ')
    .trim();
  
  return name || teamName;
}

function Clubs() {
  const { teamsData, states, leagues, isLoading, error } = useRankingsData();
  const [selectedState, setSelectedState] = useState('ALL');
  const [selectedLeague, setSelectedLeague] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Derive clubs from teams data - properly aggregate by extracted club name
  const clubs = useMemo(() => {
    const clubMap = {};
    
    teamsData.forEach(team => {
      // Extract the actual club name (strip age group)
      const clubName = extractClubName(team.club || team.name);
      if (!clubName) return;
      
      if (!clubMap[clubName]) {
        clubMap[clubName] = {
          name: clubName,
          states: new Set(),
          leagues: new Set(),
          ageGroups: new Set(),
          teams: [],
          totalWins: 0,
          totalLosses: 0,
          totalDraws: 0,
          totalGoalsFor: 0,
          totalGoalsAgainst: 0
        };
      }
      
      const club = clubMap[clubName];
      if (team.state) club.states.add(team.state);
      club.leagues.add(team.league);
      club.ageGroups.add(team.ageGroup);
      club.teams.push(team);
      club.totalWins += team.wins || 0;
      club.totalLosses += team.losses || 0;
      club.totalDraws += team.draws || 0;
      club.totalGoalsFor += team.goalsFor || 0;
      club.totalGoalsAgainst += team.goalsAgainst || 0;
    });

    // Convert to array and sort alphabetically
    return Object.values(clubMap)
      .map(club => ({
        ...club,
        states: [...club.states],
        leagues: [...club.leagues].sort(),
        ageGroups: [...club.ageGroups].sort(),
        goalDiff: club.totalGoalsFor - club.totalGoalsAgainst,
        teamCount: club.teams.length
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [teamsData]);

  // Filter clubs
  const filteredClubs = useMemo(() => {
    let filtered = clubs;
    
    if (selectedState !== 'ALL') {
      filtered = filtered.filter(club => club.states.includes(selectedState));
    }
    
    if (selectedLeague !== 'ALL') {
      filtered = filtered.filter(club => club.leagues.includes(selectedLeague));
    }
    
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(club => club.name.toLowerCase().includes(search));
    }
    
    return filtered;
  }, [clubs, selectedState, selectedLeague, searchTerm]);

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
      <div className="page-header">
        <h1 className="page-title">Clubs Directory</h1>
        <p className="page-description">
          Browse {clubs.length} youth soccer clubs • Click any club to see all their teams
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Search & Filter</h2>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div className="filter-group">
            <label className="filter-label">Search Club Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="Type to search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div className="filter-group">
            <label className="filter-label">League</label>
            <select 
              className="filter-select"
              value={selectedLeague}
              onChange={(e) => setSelectedLeague(e.target.value)}
            >
              <option value="ALL">All Leagues</option>
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
              <option value="ALL">All States</option>
              {states.map(state => (
                <option key={state} value={state}>{state}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {filteredClubs.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-text">No clubs found</div>
            {(searchTerm || selectedState !== 'ALL' || selectedLeague !== 'ALL') && (
              <button 
                onClick={() => { setSearchTerm(''); setSelectedState('ALL'); setSelectedLeague('ALL'); }}
                className="btn btn-secondary"
                style={{ marginTop: '1rem' }}
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <p style={{ color: '#666', marginBottom: '0' }}>
              Showing {filteredClubs.length} club{filteredClubs.length !== 1 ? 's' : ''}
              {selectedLeague !== 'ALL' && ` in ${selectedLeague}`}
              {selectedState !== 'ALL' && ` in ${selectedState}`}
              {searchTerm && ` matching "${searchTerm}"`}
            </p>
          </div>

          <div className="card">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
              {filteredClubs.map(club => (
                <Link
                  key={club.name}
                  to={`/club/${encodeURIComponent(club.name)}`}
                  style={{
                    padding: '1.25rem',
                    background: '#f8f9fa',
                    borderRadius: '10px',
                    borderLeft: '4px solid var(--accent-green)',
                    textDecoration: 'none',
                    color: 'inherit',
                    transition: 'all 0.2s ease',
                    display: 'block'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateX(4px)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateX(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <h3 style={{ 
                      fontSize: '1.1rem', 
                      fontWeight: '600', 
                      color: 'var(--primary-green)',
                      marginBottom: '0.5rem'
                    }}>
                      {club.name}
                    </h3>
                    <span style={{ 
                      color: '#888', 
                      fontSize: '1.25rem' 
                    }}>→</span>
                  </div>
                  
                  <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>
                    {club.states.length > 0 && (
                      <div>📍 {club.states.join(', ')}</div>
                    )}
                    <div>⚽ {club.teamCount} team{club.teamCount !== 1 ? 's' : ''}</div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    {club.leagues.map(league => (
                      <span 
                        key={league}
                        style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          background: league === 'ECNL' ? '#e3f2fd' : 
                                     league === 'GA' ? '#f3e5f5' :
                                     league === 'ECNL-RL' ? '#ffebee' :
                                     league === 'ASPIRE' ? '#e8f5e9' : '#f5f5f5',
                          color: league === 'ECNL' ? '#1976d2' : 
                                league === 'GA' ? '#7b1fa2' :
                                league === 'ECNL-RL' ? '#c62828' :
                                league === 'ASPIRE' ? '#2e7d32' : '#666'
                        }}
                      >
                        {league}
                      </span>
                    ))}
                  </div>
                  
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    padding: '0.5rem',
                    background: 'white',
                    borderRadius: '6px',
                    fontSize: '0.85rem'
                  }}>
                    <span>
                      <span style={{ fontWeight: '600' }}>{club.totalWins}-{club.totalLosses}-{club.totalDraws}</span>
                      <span style={{ color: '#888', marginLeft: '0.25rem' }}>record</span>
                    </span>
                    <span style={{ 
                      fontWeight: '600',
                      color: club.goalDiff > 0 ? '#2e7d32' : club.goalDiff < 0 ? '#c62828' : '#666'
                    }}>
                      {club.goalDiff > 0 ? '+' : ''}{club.goalDiff} GD
                    </span>
                  </div>
                  
                  <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.5rem' }}>
                    Age Groups: {club.ageGroups.join(', ')}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Clubs;
