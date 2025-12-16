import { useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import { storage } from '../data/sampleData';
import LinkManager from './LinkManager';
import SubmitGameForm from './SubmitGameForm';
import PendingGames from './PendingGames';
import { useUser } from '../context/UserContext';
import { 
  predictGame, 
  rankGamesByPerformance, 
  getPredictionColor, 
  getPerformanceColor,
  findOpponentInData
} from '../data/scorePredictions';

function TeamProfile() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const { teamsData, gamesData, isLoading } = useRankingsData();
  const { canPerform, addToMyTeams, removeFromMyTeams, isInMyTeams, getMyTeams } = useUser();
  const canSubmitScores = canPerform('canSubmitScores');
  const canSaveMyTeams = canPerform('canSaveMyTeams');
  
  const [activeTab, setActiveTab] = useState('games');
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [pendingGamesKey, setPendingGamesKey] = useState(0);
  const [myTeamsRefreshKey, setMyTeamsRefreshKey] = useState(0);
  const [showPredictions, setShowPredictions] = useState(false);
  const [showUpcoming, setShowUpcoming] = useState(true);

  // Callback to refresh pending games after submission
  const handleGameSubmitted = useCallback(() => {
    setShowSubmitForm(false);
    setPendingGamesKey(prev => prev + 1);
  }, []);

  // Find the team
  const team = useMemo(() => {
    return teamsData.find(t => t.id === parseInt(teamId));
  }, [teamsData, teamId]);

  // Helper to normalize team names for comparison
  // Strips league suffixes and normalizes for matching
  const normalizeTeamName = (name) => {
    if (!name) return '';
    return name.toLowerCase()
      .replace(/\s+(ga|ecnl|ecnl-rl|ecnl rl|aspire)$/i, '')  // Remove league suffix at end
      .trim();
  };

  // Get games for this team (past and future)
  const teamGames = useMemo(() => {
    if (!team || !gamesData) return { past: [], upcoming: [] };
    
    const normalizedTeamName = normalizeTeamName(team.name);
    const teamLeague = (team.league || '').toUpperCase();
    const today = new Date().toISOString().split('T')[0];
    
    // Find all games where this team played (home or away)
    // Must match BOTH team name AND league to avoid cross-league confusion
    const allGames = gamesData.filter(game => {
      const normalizedHome = normalizeTeamName(game.homeTeam);
      const normalizedAway = normalizeTeamName(game.awayTeam);
      const gameLeague = (game.league || '').toUpperCase();
      
      // Normalize league names for comparison
      const normalizeLeague = (lg) => {
        if (!lg) return '';
        lg = lg.toUpperCase();
        if (lg === 'ECNL-RL' || lg === 'ECNL RL') return 'ECNL-RL';
        if (lg === 'GIRLS ACADEMY') return 'GA';
        return lg;
      };
      
      const normalizedGameLeague = normalizeLeague(gameLeague);
      const normalizedTeamLeague = normalizeLeague(teamLeague);
      
      // Exact match after normalization
      const homeMatch = normalizedHome === normalizedTeamName;
      const awayMatch = normalizedAway === normalizedTeamName;
      
      // Must match league too (same team name can exist in different leagues)
      const leagueMatch = normalizedGameLeague === normalizedTeamLeague;
      
      // Also check age group if available
      const ageMatch = !game.ageGroup || game.ageGroup === team.ageGroup;
      
      return (homeMatch || awayMatch) && leagueMatch && ageMatch;
    });
    
    // Sort by date
    const sortedGames = allGames.sort((a, b) => 
      new Date(b.date) - new Date(a.date)
    );
    
    // Split into past and upcoming
    // Upcoming = future date OR scheduled status (even if date comparison fails)
    // Past = past date AND has scores (completed games)
    const past = sortedGames.filter(g => {
      const isPastDate = g.date <= today;
      const hasScores = g.homeScore !== null && g.awayScore !== null;
      return isPastDate && hasScores;
    });
    
    const upcoming = sortedGames.filter(g => {
      const isFutureDate = g.date > today;
      const isScheduled = g.status === 'scheduled' || (g.homeScore === null || g.awayScore === null);
      return isFutureDate || isScheduled;
    }).reverse(); // Oldest upcoming first
    
    return { past, upcoming };
  }, [team, gamesData]);

  // Games with predictions and performance rankings
  const rankedGames = useMemo(() => {
    if (!team || !teamGames.past.length) return [];
    return rankGamesByPerformance(teamGames.past, team, teamsData);
  }, [team, teamGames.past, teamsData]);

  // Get prediction for upcoming games
  const upcomingWithPredictions = useMemo(() => {
    if (!team || !teamGames.upcoming.length) return [];
    
    const normalizedTeamName = normalizeTeamName(team.name);
    
    return teamGames.upcoming.map(game => {
      const isHome = normalizeTeamName(game.homeTeam) === normalizedTeamName;
      const opponentName = isHome ? game.awayTeam : game.homeTeam;
      
      // Find opponent using improved matching
      const opponent = findOpponentInData(opponentName, team.ageGroup, teamsData);
      
      // Get prediction
      const prediction = isHome 
        ? predictGame(team, opponent, teamsData)
        : predictGame(opponent, team, teamsData);
      
      return {
        ...game,
        opponent: opponentName,
        opponentData: opponent,  // Include full opponent data for rank display
        isHome,
        prediction,
        teamWinProb: isHome ? prediction.homeWinProbability : prediction.awayWinProbability,
        teamLossProb: isHome ? prediction.awayWinProbability : prediction.homeWinProbability,
        drawProb: prediction.drawProbability,
        predictedTeamScore: isHome ? prediction.predictedHomeScore : prediction.predictedAwayScore,
        predictedOppScore: isHome ? prediction.predictedAwayScore : prediction.predictedHomeScore
      };
    });
  }, [team, teamGames.upcoming, teamsData]);

  // Get players on this team's roster
  const roster = useMemo(() => {
    const allPlayers = storage.getPlayers();
    return allPlayers.filter(p => p.teamId === parseInt(teamId));
  }, [teamId]);

  // Get all badges for roster players
  const badges = storage.getBadges();

  // Find rank within the team's age group and league
  const rankInCategory = useMemo(() => {
    if (!team) return null;
    const sameCategory = teamsData
      .filter(t => t.ageGroup === team.ageGroup && t.league === team.league)
      .sort((a, b) => b.powerScore - a.powerScore);
    return sameCategory.findIndex(t => t.id === team.id) + 1;
  }, [team, teamsData]);

  const totalInCategory = useMemo(() => {
    if (!team) return 0;
    return teamsData.filter(t => t.ageGroup === team.ageGroup && t.league === team.league).length;
  }, [team, teamsData]);

  // Helper to determine if team won/lost/tied a game
  const getGameResult = (game) => {
    const normalizedTeamName = normalizeTeamName(team.name);
    const isHome = normalizeTeamName(game.homeTeam) === normalizedTeamName;
    const teamScore = isHome ? game.homeScore : game.awayScore;
    const oppScore = isHome ? game.awayScore : game.homeScore;
    
    if (teamScore > oppScore) return 'win';
    if (teamScore < oppScore) return 'loss';
    return 'draw';
  };

  // Format date nicely
  const formatDate = (dateStr) => {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">Loading team data...</div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-text">Team not found</div>
          <button 
            onClick={() => navigate('/rankings')} 
            className="btn btn-primary"
            style={{ marginTop: '1rem' }}
          >
            Back to Rankings
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 className="page-title" style={{ marginBottom: '0.25rem' }}>{team.name}</h1>
            <p className="page-description" style={{ marginBottom: 0 }}>
              {team.ageGroup} • {team.league}
              {team.state && ` • ${team.state}`}
            </p>
          </div>
          {canSaveMyTeams && (
            <div>
              {isInMyTeams(team) ? (
                <button
                  onClick={() => {
                    removeFromMyTeams(team);
                    setMyTeamsRefreshKey(prev => prev + 1);
                  }}
                  style={{
                    padding: '0.6rem 1rem',
                    borderRadius: '8px',
                    border: '2px solid var(--accent-green)',
                    background: '#f0f7ed',
                    color: 'var(--primary-green)',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  ⭐ In My Teams
                </button>
              ) : getMyTeams().length < 5 ? (
                <button
                  onClick={() => {
                    addToMyTeams(team);
                    setMyTeamsRefreshKey(prev => prev + 1);
                  }}
                  style={{
                    padding: '0.6rem 1rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--primary-green)',
                    color: 'white',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  ☆ Add to My Teams
                </button>
              ) : (
                <span style={{
                  padding: '0.6rem 1rem',
                  borderRadius: '8px',
                  background: '#f5f5f5',
                  color: '#888',
                  fontSize: '0.85rem'
                }}>
                  My Teams Full (5/5)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Team Stats Overview */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Club</div>
            <Link 
              to={`/club/${encodeURIComponent(team.club)}`}
              style={{ 
                fontSize: '1.25rem', 
                fontWeight: '600', 
                color: 'var(--primary-green)',
                textDecoration: 'none'
              }}
            >
              {team.club} →
            </Link>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              {team.league} {team.ageGroup} Rank
            </div>
            <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--primary-green)' }}>
              #{rankInCategory} <span style={{ fontSize: '1rem', color: '#888' }}>of {totalInCategory}</span>
            </div>
          </div>
        </div>

        <div className="stats-grid" style={{ marginTop: '1.5rem' }}>
          <div className="stat-card">
            <div className="stat-value">{team.powerScore?.toFixed(1)}</div>
            <div className="stat-label">Power Score</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{team.wins}-{team.losses}-{team.draws}</div>
            <div className="stat-label">Record</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: team.goalDiff > 0 ? '#a5d6a7' : team.goalDiff < 0 ? '#ef9a9a' : 'white' }}>
              {team.goalDiff > 0 ? '+' : ''}{team.goalDiff}
            </div>
            <div className="stat-label">Goal Diff</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{(team.winPct * 100).toFixed(0)}%</div>
            <div className="stat-label">Win %</div>
          </div>
        </div>

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
          gap: '1rem',
          marginTop: '1.5rem',
          padding: '1rem',
          background: '#f8f9fa',
          borderRadius: '8px'
        }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Goals For</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#2e7d32' }}>{team.goalsFor}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Goals Against</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#c62828' }}>{team.goalsAgainst}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Games Played</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '600' }}>{team.gamesPlayed}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Strength of Schedule</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '600' }}>{(team.sos * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Big Wins</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#2e7d32' }}>{team.bigWins}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>Blowout Losses</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#c62828' }}>{team.blowoutLosses}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card">
        <div className="team-profile-tabs">
          <button
            className={`team-profile-tab ${activeTab === 'games' ? 'active' : ''}`}
            onClick={() => setActiveTab('games')}
          >
            <span className="tab-icon">📅 </span>Games ({teamGames.past.length + teamGames.upcoming.length})
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'roster' ? 'active' : ''}`}
            onClick={() => setActiveTab('roster')}
          >
            <span className="tab-icon">👥 </span>Roster ({roster.length})
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'links' ? 'active' : ''}`}
            onClick={() => setActiveTab('links')}
          >
            <span className="tab-icon">🔗 </span>Links
          </button>
          <button
            className={`team-profile-tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <span className="tab-icon">📊 </span>Overview
          </button>
        </div>

        {activeTab === 'overview' && (
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--primary-green)', marginBottom: '1rem' }}>
              Season Summary
            </h3>
            <p style={{ color: '#666', lineHeight: '1.6' }}>
              {team.name} has played {team.gamesPlayed} games this season with a record of {team.wins}-{team.losses}-{team.draws}.
              They have scored {team.goalsFor} goals while allowing {team.goalsAgainst}, for a goal differential of {team.goalDiff > 0 ? '+' : ''}{team.goalDiff}.
              {team.bigWins > 0 && ` They have ${team.bigWins} big wins this season.`}
              {team.blowoutLosses > 0 && ` They have suffered ${team.blowoutLosses} blowout losses.`}
            </p>
            
            <div style={{ marginTop: '1.5rem' }}>
              <Link 
                to={`/club/${encodeURIComponent(team.club)}`}
                className="btn btn-primary"
              >
                View All {team.club} Teams →
              </Link>
            </div>
          </div>
        )}

        {activeTab === 'links' && (
          <LinkManager 
            entityType="team"
            entityId={team.id}
            entityName={team.name}
            isOwner={false}
          />
        )}

        {activeTab === 'games' && (
          <div>
            {/* Report Missing Game Button - Pro users only */}
            {canSubmitScores && (
              <div style={{ 
                display: 'flex', 
                justifyContent: 'flex-end',
                marginBottom: '1rem'
              }}>
                <button
                  onClick={() => setShowSubmitForm(!showSubmitForm)}
                  style={{
                    padding: '0.6rem 1rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: showSubmitForm ? '#f5f5f5' : 'var(--primary-green)',
                    color: showSubmitForm ? '#666' : '#fff',
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  {showSubmitForm ? '✕ Cancel' : '➕ Report Missing Game'}
                </button>
              </div>
            )}

            {!canSubmitScores && (
              <div style={{
                padding: '0.75rem 1rem',
                background: '#f8f9fa',
                borderRadius: '8px',
                marginBottom: '1rem',
                border: '1px solid #e0e0e0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.5rem'
              }}>
                <span style={{ color: '#666', fontSize: '0.9rem' }}>
                  🔒 Pro account required to submit missing games
                </span>
              </div>
            )}

            {/* Submit Game Form - Pro users only */}
            {canSubmitScores && showSubmitForm && (
              <div style={{
                marginBottom: '1.5rem',
                background: '#fafafa',
                borderRadius: '12px',
                border: '1px solid #e0e0e0'
              }}>
                <SubmitGameForm 
                  team={team}
                  onSubmit={handleGameSubmitted}
                  onCancel={() => setShowSubmitForm(false)}
                />
              </div>
            )}

            {teamGames.past.length === 0 && teamGames.upcoming.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📅</div>
                <div className="empty-state-text">No official games found</div>
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  Game data for this team is not yet available.
                  Use the "Report Missing Game" button above to submit games.
                </p>
              </div>
            ) : (
              <div>
                {/* Toggle Options */}
                <div style={{ 
                  display: 'flex', 
                  gap: '0.5rem', 
                  marginBottom: '1.5rem',
                  flexWrap: 'wrap'
                }}>
                  <button
                    onClick={() => setShowUpcoming(!showUpcoming)}
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      border: '1px solid #ddd',
                      background: showUpcoming ? 'var(--primary-green)' : '#f8f9fa',
                      color: showUpcoming ? 'white' : '#666',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: '500',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    🗓️ {showUpcoming ? 'Hide' : 'Show'} Upcoming
                  </button>
                  <button
                    onClick={() => setShowPredictions(!showPredictions)}
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      border: '1px solid #ddd',
                      background: showPredictions ? '#7b1fa2' : '#f8f9fa',
                      color: showPredictions ? 'white' : '#666',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: '500',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    🔮 {showPredictions ? 'Hide' : 'Show'} Predictions
                  </button>
                </div>

                {/* Upcoming Games */}
                {showUpcoming && upcomingWithPredictions.length > 0 && (
                  <div style={{ marginBottom: '2rem' }}>
                    <h3 style={{ 
                      fontSize: '1rem', 
                      fontWeight: '600', 
                      color: 'var(--primary-green)', 
                      marginBottom: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      🗓️ Upcoming Games ({upcomingWithPredictions.length})
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {upcomingWithPredictions.map(game => (
                        <div 
                          key={game.id}
                          style={{
                            padding: '0.75rem 1rem',
                            background: '#f0f7ff',
                            borderRadius: '8px',
                            borderLeft: '4px solid #2196f3'
                          }}
                        >
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '1rem',
                            flexWrap: 'wrap'
                          }}>
                            <div style={{ 
                              minWidth: '100px',
                              fontSize: '0.85rem',
                              color: '#666'
                            }}>
                              {formatDate(game.date)}
                            </div>
                            <div style={{ 
                              fontWeight: '500',
                              color: '#333',
                              flex: 1,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem'
                            }}>
                              {game.isHome ? 'vs' : '@'} {game.opponent}
                              {showPredictions && game.opponentData && (
                                <span style={{
                                  fontSize: '0.7rem',
                                  color: game.opponentData.isUnranked ? '#999' : '#7b1fa2',
                                  fontWeight: '600',
                                  padding: '0.15rem 0.4rem',
                                  background: game.opponentData.isUnranked ? '#f5f5f5' : 'rgba(123, 31, 162, 0.1)',
                                  borderRadius: '4px'
                                }}>
                                  {game.opponentData.isUnranked 
                                    ? 'Unranked' 
                                    : `#${game.opponentData.rank || '?'}`}
                                </span>
                              )}
                            </div>
                            <div style={{
                              fontSize: '0.75rem',
                              color: '#888',
                              background: '#e3f2fd',
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px'
                            }}>
                              {game.league}
                            </div>
                          </div>
                          
                          {/* Prediction Display */}
                          {showPredictions && (
                            <div style={{
                              marginTop: '0.75rem',
                              padding: '0.75rem',
                              background: 'rgba(123, 31, 162, 0.05)',
                              borderRadius: '6px',
                              border: '1px solid rgba(123, 31, 162, 0.2)'
                            }}>
                              <div style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '1rem',
                                flexWrap: 'wrap',
                                marginBottom: '0.5rem'
                              }}>
                                <span style={{ 
                                  fontSize: '0.75rem', 
                                  color: '#7b1fa2',
                                  fontWeight: '600',
                                  textTransform: 'uppercase'
                                }}>
                                  🔮 Prediction
                                </span>
                                <span style={{ 
                                  fontSize: '1rem',
                                  fontWeight: '700',
                                  color: '#333'
                                }}>
                                  {game.predictedTeamScore} - {game.predictedOppScore}
                                </span>
                              </div>
                              <div style={{ 
                                display: 'flex', 
                                gap: '1rem',
                                flexWrap: 'wrap',
                                fontSize: '0.8rem'
                              }}>
                                <span style={{ 
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '4px',
                                  background: getPredictionColor(game.teamWinProb, 'win'),
                                  color: 'white',
                                  fontWeight: '600'
                                }}>
                                  Win {game.teamWinProb}%
                                </span>
                                <span style={{ 
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '4px',
                                  background: '#666',
                                  color: 'white',
                                  fontWeight: '600'
                                }}>
                                  Draw {game.drawProb}%
                                </span>
                                <span style={{ 
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '4px',
                                  background: getPredictionColor(game.teamLossProb, 'loss'),
                                  color: 'white',
                                  fontWeight: '600'
                                }}>
                                  Loss {game.teamLossProb}%
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Past Games */}
                {teamGames.past.length > 0 && (
                  <div>
                    <h3 style={{ 
                      fontSize: '1rem', 
                      fontWeight: '600', 
                      color: 'var(--primary-green)', 
                      marginBottom: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      📋 Past Results ({teamGames.past.length})
                      {showPredictions && (
                        <span style={{ 
                          fontSize: '0.75rem', 
                          color: '#7b1fa2',
                          fontWeight: '500',
                          marginLeft: '0.5rem'
                        }}>
                          • Ranked by Performance
                        </span>
                      )}
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {(showPredictions ? rankedGames : teamGames.past).map(game => {
                        const isHome = showPredictions ? game.isHome : normalizeTeamName(game.homeTeam) === normalizeTeamName(team.name);
                        const opponent = showPredictions ? game.opponent : (isHome ? game.awayTeam : game.homeTeam);
                        const teamScore = isHome ? game.homeScore : game.awayScore;
                        const oppScore = isHome ? game.awayScore : game.homeScore;
                        const result = getGameResult(game);
                        
                        const resultColors = {
                          win: { bg: '#e8f5e9', border: '#4caf50', text: '#2e7d32' },
                          loss: { bg: '#ffebee', border: '#f44336', text: '#c62828' },
                          draw: { bg: '#fff3e0', border: '#ff9800', text: '#e65100' }
                        };
                        const colors = resultColors[result];
                        
                        return (
                          <div 
                            key={game.id}
                            style={{
                              padding: '0.75rem 1rem',
                              background: colors.bg,
                              borderRadius: '8px',
                              borderLeft: `4px solid ${colors.border}`
                            }}
                          >
                            <div style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '1rem',
                              flexWrap: 'wrap'
                            }}>
                              {/* Performance Rank Badge */}
                              {showPredictions && game.performanceRank && (
                                <div style={{
                                  minWidth: '45px',
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '6px',
                                  background: getPerformanceColor(game.performanceScore),
                                  color: 'white',
                                  fontSize: '0.75rem',
                                  fontWeight: '700',
                                  textAlign: 'center'
                                }}>
                                  #{game.performanceRank}
                                </div>
                              )}
                              
                              <div style={{ 
                                minWidth: '100px',
                                fontSize: '0.85rem',
                                color: '#666'
                              }}>
                                {formatDate(game.date)}
                              </div>
                              <div style={{
                                fontWeight: '700',
                                color: colors.text,
                                minWidth: '30px'
                              }}>
                                {result === 'win' ? 'W' : result === 'loss' ? 'L' : 'D'}
                              </div>
                              <div style={{ 
                                fontWeight: '600',
                                color: '#333',
                                minWidth: '50px'
                              }}>
                                {teamScore} - {oppScore}
                              </div>
                              <div style={{ 
                                fontWeight: '500',
                                color: '#333',
                                flex: 1,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem'
                              }}>
                                {isHome ? 'vs' : '@'} {opponent}
                                {showPredictions && game.opponentData && (
                                  <span style={{
                                    fontSize: '0.7rem',
                                    color: game.opponentData.isUnranked ? '#999' : '#7b1fa2',
                                    fontWeight: '600',
                                    padding: '0.15rem 0.4rem',
                                    background: game.opponentData.isUnranked ? '#f5f5f5' : 'rgba(123, 31, 162, 0.1)',
                                    borderRadius: '4px'
                                  }}>
                                    {game.opponentData.isUnranked 
                                      ? 'Unranked' 
                                      : `#${game.opponentData.rank || '?'}`}
                                  </span>
                                )}
                              </div>
                              <div style={{
                                fontSize: '0.75rem',
                                color: '#888',
                                background: 'rgba(255,255,255,0.7)',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px'
                              }}>
                                {game.league}
                              </div>
                            </div>
                            
                            {/* Prediction vs Actual Display */}
                            {showPredictions && game.analysis && (
                              <div style={{
                                marginTop: '0.75rem',
                                padding: '0.75rem',
                                background: 'rgba(123, 31, 162, 0.05)',
                                borderRadius: '6px',
                                border: '1px solid rgba(123, 31, 162, 0.15)'
                              }}>
                                <div style={{ 
                                  display: 'flex', 
                                  alignItems: 'center', 
                                  gap: '1rem',
                                  flexWrap: 'wrap',
                                  justifyContent: 'space-between'
                                }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                    <span style={{ 
                                      fontSize: '0.75rem', 
                                      color: '#666'
                                    }}>
                                      Predicted: <strong>{game.analysis.predictedScore}</strong>
                                    </span>
                                    <span style={{ color: '#ccc' }}>→</span>
                                    <span style={{ 
                                      fontSize: '0.75rem', 
                                      color: '#333'
                                    }}>
                                      Actual: <strong>{game.analysis.actualScore}</strong>
                                    </span>
                                  </div>
                                  <div style={{
                                    padding: '0.25rem 0.75rem',
                                    borderRadius: '12px',
                                    background: game.analysis.outperformed ? '#e8f5e9' : '#fff3e0',
                                    color: game.analysis.outperformed ? '#2e7d32' : '#e65100',
                                    fontSize: '0.75rem',
                                    fontWeight: '600'
                                  }}>
                                    {game.analysis.performanceLabel}
                                  </div>
                                </div>
                                <div style={{
                                  marginTop: '0.5rem',
                                  fontSize: '0.7rem',
                                  color: '#888'
                                }}>
                                  Performance Score: {game.performanceScore?.toFixed(0)}/100 
                                  {game.analysis.performanceDiff > 0 
                                    ? ` (+${game.analysis.performanceDiff} GD vs expected)` 
                                    : game.analysis.performanceDiff < 0 
                                      ? ` (${game.analysis.performanceDiff} GD vs expected)`
                                      : ' (Met expectations)'}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* User-Submitted Pending Games */}
            <PendingGames 
              key={pendingGamesKey}
              team={team} 
              onRefresh={() => setPendingGamesKey(prev => prev + 1)}
            />
          </div>
        )}

        {activeTab === 'roster' && (
          <div>
            {roster.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">👥</div>
                <div className="empty-state-text">No players on roster yet</div>
                <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  Add players to this team from the Players page.
                </p>
                <button 
                  onClick={() => navigate('/players')} 
                  className="btn btn-primary"
                  style={{ marginTop: '1rem' }}
                >
                  Go to Players
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                {roster.map(player => {
                  const playerBadges = badges[player.id] || {};
                  const totalBadges = Object.values(playerBadges).reduce((sum, count) => sum + count, 0);
                  
                  return (
                    <div
                      key={player.id}
                      onClick={() => navigate(`/player/${player.id}`)}
                      style={{
                        padding: '1rem',
                        background: '#f8f9fa',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        border: '2px solid transparent'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = 'var(--accent-green)';
                        e.currentTarget.style.transform = 'translateY(-2px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'transparent';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <h4 style={{ 
                            fontSize: '1.1rem', 
                            fontWeight: '600', 
                            color: 'var(--primary-green)',
                            marginBottom: '0.25rem'
                          }}>
                            {player.name}
                          </h4>
                          <div style={{ fontSize: '0.85rem', color: '#666' }}>
                            {player.position}
                          </div>
                        </div>
                        {totalBadges > 0 && (
                          <div style={{
                            background: 'var(--accent-green)',
                            color: 'white',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: '600'
                          }}>
                            {totalBadges} 🎖️
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default TeamProfile;
