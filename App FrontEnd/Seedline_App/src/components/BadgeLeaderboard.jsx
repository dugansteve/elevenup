import { useState, useMemo } from 'react';
import { storage, BADGE_TYPES, AGE_GROUPS, LEAGUES, STATES } from '../data/sampleData';
import BottomSheetSelect from './BottomSheetSelect';
import { SimulationIcon, TeamsIcon } from './PaperIcons';

function BadgeLeaderboard() {
  const [selectedBadge, setSelectedBadge] = useState(BADGE_TYPES[0].id);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    ageGroup: 'ALL',
    league: 'ALL',
    state: 'ALL'
  });

  const players = storage.getPlayers();
  const badges = storage.getBadges();

  // Calculate leaderboard for selected badge
  const leaderboard = useMemo(() => {
    let playersList = players.map(player => {
      const playerBadges = badges[player.id] || {};
      const badgeCount = playerBadges[selectedBadge] || 0;
      return {
        ...player,
        badgeCount
      };
    });

    // Apply filters
    if (filters.ageGroup !== 'ALL') {
      playersList = playersList.filter(p => p.ageGroup === filters.ageGroup);
    }
    if (filters.league !== 'ALL') {
      playersList = playersList.filter(p => p.league === filters.league);
    }
    if (filters.state !== 'ALL') {
      playersList = playersList.filter(p => p.state === filters.state);
    }

    // Sort by badge count and get top 10
    return playersList
      .filter(p => p.badgeCount > 0)
      .sort((a, b) => b.badgeCount - a.badgeCount)
      .slice(0, 10);
  }, [players, badges, selectedBadge, filters]);

  const selectedBadgeInfo = BADGE_TYPES.find(b => b.id === selectedBadge);

  const getMedalIcon = (rank) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return null;
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: 'var(--primary-green)' }}>
            Select Badge Type
          </h3>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <SimulationIcon size={14} color="green" /> Filters {showFilters ? '▲' : '▼'}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '0.75rem' }}>
          {BADGE_TYPES.map(badge => (
            <button
              key={badge.id}
              onClick={() => setSelectedBadge(badge.id)}
              style={{
                padding: '0.75rem',
                background: selectedBadge === badge.id ? 'var(--accent-green)' : 'white',
                color: selectedBadge === badge.id ? 'white' : 'var(--text-dark)',
                border: selectedBadge === badge.id ? 'none' : '2px solid #e0e0e0',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                transition: 'all 0.2s ease',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.25rem'
              }}
            >
              <span style={{ fontSize: '1.5rem' }}>{badge.emoji}</span>
              <span>{badge.name}</span>
            </button>
          ))}
        </div>
      </div>

      {showFilters && (
        <div style={{ 
          padding: '1.5rem', 
          background: '#f8f9fa', 
          borderRadius: '12px', 
          marginBottom: '1.5rem',
          border: '2px solid #e0e0e0'
        }}>
          <h4 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '1rem' }}>Filter Leaderboard</h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div className="filter-group">
              <label className="filter-label">Age Group</label>
              <BottomSheetSelect
                label="Age Group"
                value={filters.ageGroup}
                onChange={(val) => setFilters({...filters, ageGroup: val})}
                options={[
                  { value: 'ALL', label: 'All Age Groups' },
                  ...AGE_GROUPS.map(age => ({ value: age, label: age }))
                ]}
              />
            </div>

            <div className="filter-group">
              <label className="filter-label">League</label>
              <BottomSheetSelect
                label="League"
                value={filters.league}
                onChange={(val) => setFilters({...filters, league: val})}
                options={[
                  { value: 'ALL', label: 'All Leagues' },
                  ...LEAGUES.map(league => ({ value: league, label: league }))
                ]}
              />
            </div>

            <div className="filter-group">
              <label className="filter-label">State</label>
              <BottomSheetSelect
                label="State"
                value={filters.state}
                onChange={(val) => setFilters({...filters, state: val})}
                options={[
                  { value: 'ALL', label: 'All States' },
                  ...STATES.map(state => ({ value: state, label: state }))
                ]}
              />
            </div>
          </div>

          <button
            onClick={() => setFilters({ ageGroup: 'ALL', league: 'ALL', state: 'ALL' })}
            className="btn btn-secondary"
            style={{ marginTop: '1rem' }}
          >
            Clear Filters
          </button>
        </div>
      )}

      <div style={{
        padding: '1.5rem',
        background: 'linear-gradient(135deg, var(--primary-green) 0%, var(--accent-green) 100%)',
        borderRadius: '12px',
        color: 'white',
        marginBottom: '1.5rem'
      }}>
        <div style={{ fontSize: '2.5rem', textAlign: 'center', marginBottom: '0.5rem' }}>
          {selectedBadgeInfo?.emoji}
        </div>
        <h2 style={{ fontSize: '1.75rem', fontWeight: '700', textAlign: 'center', marginBottom: '0.25rem' }}>
          {selectedBadgeInfo?.name} Badge
        </h2>
        <p style={{ textAlign: 'center', opacity: 0.9 }}>
          {selectedBadgeInfo?.description}
        </p>
      </div>

      {leaderboard.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><TeamsIcon size={48} color="gray" /></div>
          <div className="empty-state-text">
            No players have earned this badge yet
            {(filters.ageGroup !== 'ALL' || filters.league !== 'ALL' || filters.state !== 'ALL') && 
              ' with the selected filters'}
          </div>
        </div>
      ) : (
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: 'var(--primary-green)' }}>
            Top 10 Players
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {leaderboard.map((player, index) => {
              const rank = index + 1;
              const medal = getMedalIcon(rank);
              
              return (
                <div
                  key={player.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '1rem 1.5rem',
                    background: rank <= 3 ? '#fffef0' : 'white',
                    borderRadius: '10px',
                    border: rank <= 3 ? '2px solid #ffd700' : '2px solid #e0e0e0',
                    transition: 'all 0.2s ease'
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
                  <div style={{ 
                    fontSize: '1.5rem', 
                    fontWeight: '700',
                    minWidth: '50px',
                    color: 'var(--primary-green)'
                  }}>
                    {medal || `#${rank}`}
                  </div>
                  
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                      {player.name}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#666' }}>
                      {player.position} • {player.teamName} ({player.league})
                    </div>
                  </div>
                  
                  <div style={{
                    background: 'var(--accent-green)',
                    color: 'white',
                    padding: '0.5rem 1rem',
                    borderRadius: '8px',
                    fontWeight: '700',
                    fontSize: '1.1rem'
                  }}>
                    {player.badgeCount} {selectedBadgeInfo?.emoji}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default BadgeLeaderboard;
