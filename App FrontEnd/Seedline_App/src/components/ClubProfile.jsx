import { useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import LinkManager from './LinkManager';

function ClubProfile() {
  const { clubName } = useParams();
  const navigate = useNavigate();
  const { teamsData, ageGroups, isLoading } = useRankingsData();
  const [selectedAgeGroup, setSelectedAgeGroup] = useState('ALL');
  const [activeTab, setActiveTab] = useState('teams');

  const decodedClubName = decodeURIComponent(clubName);

  // Get all teams for this club
  const clubTeams = useMemo(() => {
    return teamsData
      .filter(t => t.club === decodedClubName)
      .sort((a, b) => {
        // Sort by age group first, then by power score
        if (a.ageGroup !== b.ageGroup) {
          return ageGroups.indexOf(a.ageGroup) - ageGroups.indexOf(b.ageGroup);
        }
        return b.powerScore - a.powerScore;
      });
  }, [teamsData, decodedClubName, ageGroups]);

  // Filter by age group
  const filteredTeams = useMemo(() => {
    if (selectedAgeGroup === 'ALL') return clubTeams;
    return clubTeams.filter(t => t.ageGroup === selectedAgeGroup);
  }, [clubTeams, selectedAgeGroup]);

  // Get unique age groups for this club
  const clubAgeGroups = useMemo(() => {
    const ages = [...new Set(clubTeams.map(t => t.ageGroup))];
    return ageGroups.filter(ag => ages.includes(ag));
  }, [clubTeams, ageGroups]);

  // Calculate club totals
  const clubStats = useMemo(() => {
    const stats = clubTeams.reduce((acc, team) => ({
      totalWins: acc.totalWins + team.wins,
      totalLosses: acc.totalLosses + team.losses,
      totalDraws: acc.totalDraws + team.draws,
      totalGoalsFor: acc.totalGoalsFor + team.goalsFor,
      totalGoalsAgainst: acc.totalGoalsAgainst + team.goalsAgainst,
      totalGames: acc.totalGames + team.gamesPlayed
    }), { totalWins: 0, totalLosses: 0, totalDraws: 0, totalGoalsFor: 0, totalGoalsAgainst: 0, totalGames: 0 });
    
    stats.goalDiff = stats.totalGoalsFor - stats.totalGoalsAgainst;
    stats.winPct = stats.totalGames > 0 ? stats.totalWins / stats.totalGames : 0;
    return stats;
  }, [clubTeams]);

  // Get rank for a team within its age group and league
  const getTeamRank = (team) => {
    const sameCategory = teamsData
      .filter(t => t.ageGroup === team.ageGroup && t.league === team.league)
      .sort((a, b) => b.powerScore - a.powerScore);
    return sameCategory.findIndex(t => t.id === team.id) + 1;
  };

  const getTotalInCategory = (team) => {
    return teamsData.filter(t => t.ageGroup === team.ageGroup && t.league === team.league).length;
  };

  // Get unique states and leagues for this club
  const clubStates = [...new Set(clubTeams.map(t => t.state).filter(Boolean))];
  const clubLeagues = [...new Set(clubTeams.map(t => t.league))];

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">Loading club data...</div>
      </div>
    );
  }

  if (clubTeams.length === 0) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-text">Club not found</div>
          <button 
            onClick={() => navigate('/clubs')} 
            className="btn btn-primary"
            style={{ marginTop: '1rem' }}
          >
            Back to Clubs
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <button 
          onClick={() => navigate(-1)} 
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--primary-green)',
            cursor: 'pointer',
            fontSize: '0.9rem',
            marginBottom: '0.5rem',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          ← Back
        </button>
        <h1 className="page-title">{decodedClubName}</h1>
        <p className="page-description">
          {clubTeams.length} team{clubTeams.length !== 1 ? 's' : ''} across {clubAgeGroups.length} age group{clubAgeGroups.length !== 1 ? 's' : ''}
          {clubStates.length > 0 && ` • ${clubStates.join(', ')}`}
        </p>
      </div>

      {/* Club Overview Stats */}
      <div className="card">
        <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--primary-green)', marginBottom: '1rem' }}>
          Club Overview
        </h3>
        
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          {clubLeagues.map(league => (
            <span 
              key={league}
              style={{
                padding: '0.25rem 0.75rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
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

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{clubTeams.length}</div>
            <div className="stat-label">Teams</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{clubStats.totalWins}-{clubStats.totalLosses}-{clubStats.totalDraws}</div>
            <div className="stat-label">Combined Record</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: clubStats.goalDiff > 0 ? '#a5d6a7' : clubStats.goalDiff < 0 ? '#ef9a9a' : 'white' }}>
              {clubStats.goalDiff > 0 ? '+' : ''}{clubStats.goalDiff}
            </div>
            <div className="stat-label">Goal Diff</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{(clubStats.winPct * 100).toFixed(0)}%</div>
            <div className="stat-label">Win %</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'teams' ? 'active' : ''}`}
            onClick={() => setActiveTab('teams')}
          >
            ⚽ Teams ({clubTeams.length})
          </button>
          <button
            className={`tab ${activeTab === 'links' ? 'active' : ''}`}
            onClick={() => setActiveTab('links')}
          >
            🔗 Links
          </button>
        </div>

        {activeTab === 'teams' && (
          <>
            {/* Age Group Filter */}
            <div className="filter-group" style={{ maxWidth: '300px', marginBottom: '1.5rem' }}>
              <label className="filter-label">Filter by Age Group</label>
              <select 
                className="filter-select"
                value={selectedAgeGroup}
                onChange={(e) => setSelectedAgeGroup(e.target.value)}
              >
                <option value="ALL">All Age Groups ({clubTeams.length})</option>
                {clubAgeGroups.map(age => {
                  const count = clubTeams.filter(t => t.ageGroup === age).length;
                  return (
                    <option key={age} value={age}>{age} ({count})</option>
                  );
                })}
              </select>
            </div>

            {/* Teams List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {filteredTeams.map(team => {
                const rank = getTeamRank(team);
                const total = getTotalInCategory(team);
                
                return (
                  <Link
                    key={team.id}
                    to={`/team/${team.id}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '1rem 1.5rem',
                      background: '#f8f9fa',
                      borderRadius: '10px',
                      border: '2px solid transparent',
                      textDecoration: 'none',
                      color: 'inherit',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--accent-green)';
                      e.currentTarget.style.transform = 'translateX(4px)';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'transparent';
                      e.currentTarget.style.transform = 'translateX(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    {/* Rank */}
                    <div style={{ 
                      minWidth: '60px',
                      textAlign: 'center',
                      marginRight: '1rem'
                    }}>
                      <div style={{ 
                        fontSize: '1.25rem', 
                        fontWeight: '700',
                        color: 'var(--primary-green)'
                      }}>
                        #{rank}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#888' }}>
                        of {total}
                      </div>
                    </div>

                    {/* Team Info */}
                    <div style={{ flex: 1 }}>
                      <div style={{ 
                        fontSize: '1.1rem', 
                        fontWeight: '600', 
                        color: 'var(--primary-green)',
                        marginBottom: '0.25rem'
                      }}>
                        {team.name}
                      </div>
                      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                        <span style={{
                          padding: '0.125rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          background: '#e8f5e9',
                          color: 'var(--primary-green)'
                        }}>
                          {team.ageGroup}
                        </span>
                        <span style={{
                          padding: '0.125rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          background: team.league === 'ECNL' ? '#e3f2fd' : 
                                     team.league === 'GA' ? '#f3e5f5' :
                                     team.league === 'ECNL-RL' ? '#ffebee' :
                                     team.league === 'ASPIRE' ? '#e8f5e9' : '#f5f5f5',
                          color: team.league === 'ECNL' ? '#1976d2' : 
                                team.league === 'GA' ? '#7b1fa2' :
                                team.league === 'ECNL-RL' ? '#c62828' :
                                team.league === 'ASPIRE' ? '#2e7d32' : '#666'
                        }}>
                          {team.league}
                        </span>
                        <span style={{ fontSize: '0.85rem', color: '#666' }}>
                          {team.wins}-{team.losses}-{team.draws}
                        </span>
                      </div>
                    </div>

                    {/* Power Score */}
                    <div style={{ textAlign: 'right', marginLeft: '1rem' }}>
                      <div style={{ 
                        fontSize: '1.25rem', 
                        fontWeight: '700',
                        color: 'var(--accent-green)'
                      }}>
                        {team.powerScore?.toFixed(1)}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>
                        Power Score
                      </div>
                    </div>

                    {/* Goal Diff */}
                    <div style={{ 
                      minWidth: '60px',
                      textAlign: 'right',
                      marginLeft: '1rem'
                    }}>
                      <div style={{ 
                        fontSize: '1.1rem', 
                        fontWeight: '600',
                        color: team.goalDiff > 0 ? '#2e7d32' : team.goalDiff < 0 ? '#c62828' : '#666'
                      }}>
                        {team.goalDiff > 0 ? '+' : ''}{team.goalDiff}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>
                        GD
                      </div>
                    </div>

                    {/* Arrow */}
                    <div style={{ marginLeft: '1rem', color: '#888' }}>
                      →
                    </div>
                  </Link>
                );
              })}
            </div>
          </>
        )}

        {activeTab === 'links' && (
          <LinkManager 
            entityType="club"
            entityId={decodedClubName}
            entityName={decodedClubName}
            isOwner={false}
          />
        )}
      </div>
    </div>
  );
}

export default ClubProfile;
