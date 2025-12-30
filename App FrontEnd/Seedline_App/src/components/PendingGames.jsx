// PendingGames.jsx
// Component for displaying user-submitted games with voting functionality

import { useState, useEffect } from 'react';
import { userGameHelpers, VERIFICATION_STATUS } from '../data/sampleData';
import { useUser } from '../context/UserContext';
import { validateGameUrl, getValidationDisplay } from '../data/urlValidatorService';
import { TeamsIcon, TournamentIcon, PlayersIcon } from './PaperIcons';

export default function PendingGames({ team, onRefresh }) {
  const { canPerform } = useUser();
  const canVote = canPerform('canVoteOnGames');
  
  const [pendingGames, setPendingGames] = useState([]);
  const [userVotes, setUserVotes] = useState({});
  const [validatingGame, setValidatingGame] = useState(null);

  // Load pending games for this team
  useEffect(() => {
    loadGames();
  }, [team.name, team.ageGroup]);

  const loadGames = () => {
    const games = userGameHelpers.getGamesForTeam(team.name, team.ageGroup);
    setPendingGames(games);
    
    // Load user's votes for each game
    const votes = {};
    games.forEach(game => {
      votes[game.id] = userGameHelpers.getUserVote(game.id);
    });
    setUserVotes(votes);
  };

  // Handle voting
  const handleVote = (gameId, isValid) => {
    userGameHelpers.voteOnGame(gameId, isValid);
    loadGames();
    if (onRefresh) onRefresh();
  };

  // Handle AI validation
  const handleAIValidate = async (game) => {
    if (!game.scoreUrl) {
      alert('No URL provided for this game');
      return;
    }
    
    setValidatingGame(game.id);
    try {
      const result = await validateGameUrl(game.scoreUrl, {
        homeTeam: game.homeTeam,
        awayTeam: game.awayTeam,
        homeScore: game.homeScore,
        awayScore: game.awayScore,
        date: game.date
      });
      
      // Show result to user
      if (result.serverOffline) {
        alert('⚠️ Validation server is not running.\n\nTo start the server:\n1. Open a terminal\n2. cd server\n3. npm install\n4. npm start');
      } else if (result.verified) {
        alert(`✅ Verified! (${result.confidence}% confidence)\n\n${result.message}`);
      } else if (result.confidence > 0) {
        alert(`⚠️ Partial match (${result.confidence}% confidence)\n\n${result.message}`);
      } else {
        alert(`❌ Could not verify\n\n${result.message || 'No matching data found on the page'}`);
      }
      
      userGameHelpers.saveValidationResult(game.id, result);
      loadGames();
      if (onRefresh) onRefresh();
    } catch (error) {
      console.error('AI validation error:', error);
      alert('Error during validation: ' + error.message);
    } finally {
      setValidatingGame(null);
    }
  };

  // Get verification badge
  const getVerificationBadge = (game) => {
    // Check if we have AI validation info
    if (game.urlValidationConfidence !== undefined && game.urlValidationConfidence > 0) {
      if (game.verificationStatus === VERIFICATION_STATUS.URL_VERIFIED) {
        return { 
          icon: '🤖', 
          text: `AI Verified (${game.urlValidationConfidence}%)`, 
          color: '#1976d2', 
          bg: '#e3f2fd' 
        };
      } else if (game.urlValidationConfidence >= 40) {
        return { 
          icon: '⚠️', 
          text: `Partial (${game.urlValidationConfidence}%)`, 
          color: '#f57c00', 
          bg: '#fff3e0' 
        };
      }
    }
    
    switch (game.verificationStatus) {
      case VERIFICATION_STATUS.URL_VERIFIED:
        return { icon: '🔗', text: 'URL Verified', color: '#1976d2', bg: '#e3f2fd' };
      case VERIFICATION_STATUS.COMMUNITY_VERIFIED:
        return { icon: '👥', text: 'Community Verified', color: '#388e3c', bg: '#e8f5e9' };
      case VERIFICATION_STATUS.SCRAPED:
        return { icon: '✅', text: 'Official', color: '#2e7d32', bg: '#e8f5e9' };
      case VERIFICATION_STATUS.REJECTED:
        return { icon: '❌', text: 'Rejected', color: '#c62828', bg: '#ffebee' };
      default:
        return { icon: '⏳', text: 'Pending', color: '#f57c00', bg: '#fff3e0' };
    }
  };

  // Format date
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Get game result for this team
  const getGameResult = (game) => {
    const isHome = game.homeTeam.toLowerCase() === team.name.toLowerCase();
    const teamScore = isHome ? game.homeScore : game.awayScore;
    const oppScore = isHome ? game.awayScore : game.homeScore;
    
    if (teamScore > oppScore) return { result: 'W', color: '#2e7d32' };
    if (teamScore < oppScore) return { result: 'L', color: '#c62828' };
    return { result: 'D', color: '#757575' };
  };

  if (pendingGames.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: '2rem' }}>
      <h3 style={{ 
        fontSize: '1rem', 
        fontWeight: '600', 
        color: '#f57c00', 
        marginBottom: '1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        ⏳ User-Submitted Games ({pendingGames.length})
      </h3>
      
      <p style={{ 
        fontSize: '0.85rem', 
        color: '#666', 
        marginBottom: '1rem',
        lineHeight: '1.5'
      }}>
        These games were submitted by users and are pending verification. 
        Help verify them by marking as Valid or Incorrect.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {pendingGames.map(game => {
          const isHome = game.homeTeam.toLowerCase() === team.name.toLowerCase();
          const opponent = isHome ? game.awayTeam : game.homeTeam;
          const teamScore = isHome ? game.homeScore : game.awayScore;
          const oppScore = isHome ? game.awayScore : game.homeScore;
          const result = getGameResult(game);
          const badge = getVerificationBadge(game);
          const userVote = userVotes[game.id];

          return (
            <div 
              key={game.id}
              style={{
                padding: '1rem',
                background: '#fff',
                borderRadius: '10px',
                border: '2px dashed #f57c00',
                position: 'relative'
              }}
            >
              {/* Verification badge */}
              <div style={{
                position: 'absolute',
                top: '-10px',
                right: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.25rem 0.5rem',
                background: badge.bg,
                color: badge.color,
                borderRadius: '12px',
                fontSize: '0.75rem',
                fontWeight: '600'
              }}>
                {badge.icon} {badge.text}
              </div>

              {/* Game info */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '0.75rem'
              }}>
                {/* Result indicator */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: result.color,
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  fontSize: '0.85rem'
                }}>
                  {result.result}
                </div>

                <div style={{ flex: 1 }}>
                  {/* Opponent and score */}
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    marginBottom: '0.25rem'
                  }}>
                    <span style={{ fontWeight: '600' }}>
                      {isHome ? 'vs' : '@'} {opponent}
                    </span>
                    <span style={{ 
                      fontWeight: '700', 
                      fontSize: '1.1rem',
                      color: result.color
                    }}>
                      {teamScore} - {oppScore}
                    </span>
                  </div>

                  {/* Date and event type */}
                  <div style={{ 
                    fontSize: '0.8rem', 
                    color: '#666',
                    display: 'flex',
                    gap: '0.75rem',
                    flexWrap: 'wrap'
                  }}>
                    <span>📅 {formatDate(game.date)}</span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><TeamsIcon size={14} color="green" /> {game.eventTypeName}</span>
                    {game.location && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><TournamentIcon size={14} color="green" /> {game.location}</span>}
                  </div>
                </div>
              </div>

              {/* URL if provided */}
              {game.scoreUrl && (
                <div style={{
                  fontSize: '0.8rem',
                  marginBottom: '0.75rem',
                  padding: '0.5rem',
                  background: '#f5f5f5',
                  borderRadius: '6px'
                }}>
                  <a 
                    href={game.scoreUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#1976d2', textDecoration: 'none' }}
                  >
                    🔗 View Score Source
                  </a>
                  {game.urlVerified && (
                    <span style={{ 
                      marginLeft: '0.5rem', 
                      color: '#388e3c',
                      fontWeight: '500'
                    }}>
                      ✓ Verified
                    </span>
                  )}
                  {/* AI Verify button */}
                  {game.verificationStatus === VERIFICATION_STATUS.PENDING && !game.urlVerified && (
                    <button
                      onClick={() => handleAIValidate(game)}
                      disabled={validatingGame === game.id}
                      style={{
                        marginLeft: '0.5rem',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        border: '1px solid #1976d2',
                        background: validatingGame === game.id ? '#e3f2fd' : '#fff',
                        color: '#1976d2',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        cursor: validatingGame === game.id ? 'wait' : 'pointer'
                      }}
                    >
                      {validatingGame === game.id ? '🤖 Checking...' : '🤖 AI Verify'}
                    </button>
                  )}
                </div>
              )}

              {/* Vote counts and buttons */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '0.75rem',
                borderTop: '1px solid #eee'
              }}>
                {/* Vote counts */}
                <div style={{ 
                  display: 'flex', 
                  gap: '1rem',
                  fontSize: '0.85rem'
                }}>
                  <span style={{ color: '#388e3c' }}>
                    ✓ {game.confirmations} confirmed
                  </span>
                  <span style={{ color: '#c62828' }}>
                    ✗ {game.denials} denied
                  </span>
                </div>

                {/* Vote buttons - Pro users only */}
                {game.verificationStatus === VERIFICATION_STATUS.PENDING && canVote && (
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={() => handleVote(game.id, true)}
                      disabled={userVote === 'confirmed'}
                      style={{
                        padding: '0.4rem 0.75rem',
                        borderRadius: '6px',
                        border: userVote === 'confirmed' ? '2px solid #388e3c' : '1px solid #388e3c',
                        background: userVote === 'confirmed' ? '#e8f5e9' : '#fff',
                        color: '#388e3c',
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        cursor: userVote === 'confirmed' ? 'default' : 'pointer'
                      }}
                    >
                      {userVote === 'confirmed' ? '✓ Valid' : 'Valid'}
                    </button>
                    <button
                      onClick={() => handleVote(game.id, false)}
                      disabled={userVote === 'denied'}
                      style={{
                        padding: '0.4rem 0.75rem',
                        borderRadius: '6px',
                        border: userVote === 'denied' ? '2px solid #c62828' : '1px solid #c62828',
                        background: userVote === 'denied' ? '#ffebee' : '#fff',
                        color: '#c62828',
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        cursor: userVote === 'denied' ? 'default' : 'pointer'
                      }}
                    >
                      {userVote === 'denied' ? '✗ Incorrect' : 'Incorrect'}
                    </button>
                  </div>
                )}
                {game.verificationStatus === VERIFICATION_STATUS.PENDING && !canVote && (
                  <span style={{ fontSize: '0.75rem', color: '#999' }}>
                    🔒 Pro to vote
                  </span>
                )}
              </div>

              {/* Verification progress */}
              {game.verificationStatus === VERIFICATION_STATUS.PENDING && (
                <div style={{
                  marginTop: '0.75rem',
                  fontSize: '0.75rem',
                  color: '#888'
                }}>
                  {game.confirmations < 5 ? (
                    <span>
                      Needs {5 - game.confirmations} more confirmation{5 - game.confirmations !== 1 ? 's' : ''} 
                      {game.denials === 0 ? ' (with no denials) ' : ' '}
                      to be verified
                    </span>
                  ) : game.denials > 0 ? (
                    <span>Has denials - under review</span>
                  ) : null}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
