import { useState, useEffect } from 'react';

/**
 * Team selector dropdown with search
 * Used for assigning players to teams or switching teams
 */
export default function TeamSelector({
  currentTeamId,
  currentTeamName,
  onSelect,
  disabled = false,
  placeholder = 'Select a team...'
}) {
  const [teams, setTeams] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load teams from rankings data
  useEffect(() => {
    async function loadTeams() {
      setLoading(true);
      try {
        const response = await fetch('/rankings_for_react.json');
        const data = await response.json();

        if (data.rankings) {
          // Extract unique teams
          const teamList = data.rankings.map((team, index) => ({
            id: team.id || index,
            name: team.name,
            club: team.club,
            ageGroup: team.ageGroup,
            league: team.league,
            state: team.state
          }));
          setTeams(teamList);
        }
      } catch (error) {
        console.error('Error loading teams:', error);
      } finally {
        setLoading(false);
      }
    }

    loadTeams();
  }, []);

  // Filter teams based on search
  const filteredTeams = teams.filter(team => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      team.name?.toLowerCase().includes(query) ||
      team.club?.toLowerCase().includes(query) ||
      team.ageGroup?.toLowerCase().includes(query)
    );
  }).slice(0, 50); // Limit to 50 results for performance

  const handleSelect = (team) => {
    onSelect(team);
    setIsOpen(false);
    setSearchQuery('');
  };

  return (
    <div style={styles.container}>
      <div
        style={{
          ...styles.selector,
          ...(disabled && styles.disabled)
        }}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        {currentTeamName ? (
          <span style={styles.selectedTeam}>{currentTeamName}</span>
        ) : (
          <span style={styles.placeholder}>{placeholder}</span>
        )}
        <span style={styles.arrow}>{isOpen ? '▲' : '▼'}</span>
      </div>

      {isOpen && !disabled && (
        <div style={styles.dropdown}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search teams..."
            style={styles.searchInput}
            autoFocus
          />

          <div style={styles.teamList}>
            {loading ? (
              <div style={styles.loading}>Loading teams...</div>
            ) : filteredTeams.length === 0 ? (
              <div style={styles.noResults}>No teams found</div>
            ) : (
              filteredTeams.map((team) => (
                <div
                  key={team.id}
                  style={{
                    ...styles.teamItem,
                    ...(team.id === currentTeamId && styles.teamItemSelected)
                  }}
                  onClick={() => handleSelect(team)}
                >
                  <div style={styles.teamName}>{team.name} {team.ageGroup}</div>
                  <div style={styles.teamMeta}>
                    <span style={styles.leagueBadge}>{team.league}</span>
                    {team.state && <span>{team.state}</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    position: 'relative',
    width: '100%',
  },
  selector: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  disabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  selectedTeam: {
    fontWeight: '500',
    color: '#333',
  },
  placeholder: {
    color: '#999',
  },
  arrow: {
    fontSize: '10px',
    color: '#666',
  },
  dropdown: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    backgroundColor: 'white',
    border: '1px solid #ddd',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    zIndex: 100,
    marginTop: '4px',
    maxHeight: '300px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  searchInput: {
    padding: '12px 16px',
    border: 'none',
    borderBottom: '1px solid #eee',
    fontSize: '14px',
    outline: 'none',
  },
  teamList: {
    overflowY: 'auto',
    maxHeight: '250px',
  },
  loading: {
    padding: '20px',
    textAlign: 'center',
    color: '#666',
  },
  noResults: {
    padding: '20px',
    textAlign: 'center',
    color: '#999',
  },
  teamItem: {
    padding: '12px 16px',
    cursor: 'pointer',
    borderBottom: '1px solid #f0f0f0',
    transition: 'background-color 0.2s ease',
  },
  teamItemSelected: {
    backgroundColor: '#e8f5e9',
  },
  teamName: {
    fontWeight: '500',
    color: '#333',
    marginBottom: '4px',
  },
  teamMeta: {
    display: 'flex',
    gap: '8px',
    fontSize: '12px',
    color: '#666',
  },
  leagueBadge: {
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
    padding: '2px 6px',
    borderRadius: '4px',
    fontWeight: '500',
  },
};
