// PlayerProfile.jsx - Individual player page
// V39+: Now loads players from rankings JSON (playersData)
// V40: Added player claiming system

import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import { storage, BADGE_TYPES, rosterHelpers } from '../data/sampleData';
import { useUser } from '../context/UserContext';
import ClaimPlayerButton from './ClaimPlayerButton';
import ChallengeClaimButton from './ChallengeClaimButton';
import ProfileEditorModal from './ProfileEditorModal';

function PlayerProfile() {
  const { playerId } = useParams();
  const navigate = useNavigate();
  const { playersData, teamsData, isLoading } = useRankingsData();
  const { canPerform, isPaid, isClaimedByMe, getMyClaimForPlayer, getPlayerClaimStatus, user } = useUser();

  const [localPlayers, setLocalPlayers] = useState([]);
  const [badges, setBadges] = useState({});
  const [claimStatus, setClaimStatus] = useState({ claimed: false, loading: true });
  const [showEditModal, setShowEditModal] = useState(false);
  const [teamHistory, setTeamHistory] = useState([]);
  
  useEffect(() => {
    // Load local players (user-created)
    const savedPlayers = storage.getPlayers();
    setLocalPlayers(savedPlayers);

    // Load badges
    const savedBadges = storage.getBadges();
    setBadges(savedBadges);

    // Load team history
    const id = parseInt(playerId);
    if (!isNaN(id)) {
      const history = rosterHelpers.getPlayerTeamHistory(id);
      setTeamHistory(history);
    }
  }, [playerId]);

  // Check claim status for this player
  useEffect(() => {
    async function checkClaimStatus() {
      const id = parseInt(playerId);
      if (isNaN(id)) {
        setClaimStatus({ claimed: false, loading: false });
        return;
      }

      try {
        const status = await getPlayerClaimStatus(id);
        setClaimStatus({ ...status, loading: false });
      } catch (error) {
        console.error('Error checking claim status:', error);
        setClaimStatus({ claimed: false, loading: false });
      }
    }

    checkClaimStatus();
  }, [playerId, getPlayerClaimStatus]);

  // Get my claim for this player if I own it
  const myClaim = useMemo(() => {
    const id = parseInt(playerId);
    return getMyClaimForPlayer(id);
  }, [playerId, getMyClaimForPlayer]);

  // Determine if current user owns this player
  const isOwnedByMe = myClaim !== undefined;
  
  // Find the player - check both database players and local players
  const player = useMemo(() => {
    const id = parseInt(playerId);
    
    // First, check database players (from rankings JSON)
    if (playersData && playersData.length > 0) {
      const dbPlayer = playersData.find(p => p.id === id);
      if (dbPlayer) {
        return {
          ...dbPlayer,
          source: 'database'
        };
      }
    }
    
    // Then check local players (user-created via localStorage)
    const localPlayer = localPlayers.find(p => p.id === id);
    if (localPlayer) {
      return {
        ...localPlayer,
        source: 'local'
      };
    }
    
    return null;
  }, [playerId, playersData, localPlayers]);
  
  // Find the team this player belongs to
  const team = useMemo(() => {
    if (!player) return null;

    // Try to find by teamId first (most reliable)
    if (player.teamId) {
      const teamById = teamsData.find(t => t.id === player.teamId);
      if (teamById) return teamById;
    }

    // Try to find by team name
    if (player.teamName) {
      const playerTeamLower = player.teamName.toLowerCase();

      // Find all teams that match the name
      const matchingTeams = teamsData.filter(t =>
        t.name === player.teamName ||
        t.name.toLowerCase().includes(playerTeamLower)
      );

      if (matchingTeams.length === 0) return null;
      if (matchingTeams.length === 1) return matchingTeams[0];

      // If multiple matches, prefer one with matching age group
      if (player.ageGroup) {
        const ageMatch = matchingTeams.find(t => t.ageGroup === player.ageGroup);
        if (ageMatch) return ageMatch;
      }

      // If no age group match, prefer one with matching league
      if (player.league) {
        const leagueMatch = matchingTeams.find(t => t.league === player.league);
        if (leagueMatch) return leagueMatch;
      }

      // Fall back to first match
      return matchingTeams[0];
    }

    return null;
  }, [player, teamsData]);
  
  // Get badges for this player
  const playerBadges = useMemo(() => {
    if (!player) return [];
    const playerBadgeData = badges[playerId] || {};
    return Object.entries(playerBadgeData)
      .filter(([_, count]) => count > 0)
      .map(([badgeId, count]) => {
        const badgeType = BADGE_TYPES.find(b => b.id === badgeId);
        return {
          ...badgeType,
          count
        };
      })
      .filter(b => b.id);  // Filter out any undefined badge types
  }, [player, badges, playerId]);
  
  // Handle badge award/removal - toggle: tap once to award, tap again to unaward
  const handleBadgeToggle = (badgeId) => {
    if (!canPerform('canAwardBadges')) return;

    const currentCount = (badges[playerId]?.[badgeId]) || 0;
    const newCount = currentCount > 0 ? 0 : 1;  // Simple toggle: 0 or 1
    
    const newBadges = {
      ...badges,
      [playerId]: {
        ...(badges[playerId] || {}),
        [badgeId]: newCount
      }
    };
    
    setBadges(newBadges);
    storage.setBadges(newBadges);
  };
  
  if (isLoading) {
    return (
      <div className="player-profile">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading player data...</p>
        </div>
      </div>
    );
  }
  
  if (!player) {
    return (
      <div className="player-profile">
        <div className="not-found">
          <h2>Player Not Found</h2>
          <div className="not-found-card">
            <div className="not-found-icon">✕</div>
            <p>Player not found</p>
            <p className="not-found-detail">Player ID: {playerId}</p>
            <p className="not-found-detail">
              Database players: {playersData?.length || 0}
            </p>
            <button 
              className="btn btn-primary"
              onClick={() => navigate('/players')}
            >
              Back to Players
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  // Get photo URL from claim status or my claim
  const photoUrl = myClaim?.photo_url || claimStatus?.photo_url || null;
  const avatarConfig = myClaim?.avatar_config || claimStatus?.avatar_config || null;

  // Get display name mode from claim
  const displayNameMode = myClaim?.display_name_mode || claimStatus?.display_name_mode || 'full';

  // Format display name based on privacy preference
  const getDisplayName = () => {
    // Get the full name
    const fullName = player.name || `${player.firstName} ${player.lastName}`;

    // If display mode is 'initial', show first name + last initial
    if (displayNameMode === 'initial') {
      const parts = fullName.trim().split(/\s+/);
      if (parts.length >= 2) {
        const firstName = parts[0];
        const lastInitial = parts[parts.length - 1].charAt(0).toUpperCase();
        return `${firstName} ${lastInitial}.`;
      }
    }

    // Default: return full name
    return fullName;
  };

  const displayName = getDisplayName();

  return (
    <div className="player-profile">
      <div className="profile-header">
        <button
          className="back-button"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>
        <h1>{displayName}</h1>
        {player.source === 'database' && (
          <span className="source-badge database">Database Player</span>
        )}
        {player.source === 'local' && (
          <span className="source-badge local">My Player</span>
        )}
      </div>

      {/* Player Photo Section */}
      <div className="player-photo-section">
        <div className="player-photo-container">
          {photoUrl ? (
            <img
              src={photoUrl}
              alt={displayName}
              className="player-photo"
            />
          ) : (
            <div className="player-photo-placeholder">
              <span className="placeholder-icon">
                {player.jerseyNumber ? `#${player.jerseyNumber}` : '⚽'}
              </span>
            </div>
          )}
        </div>
        <div className="player-name-display">
          <span className="player-display-name">
            {displayName}
          </span>
          {player.position && (
            <span className="player-position-badge">{player.position}</span>
          )}
        </div>
      </div>

      <div className="profile-content">
        {/* Player Info Card */}
        <div className="profile-card info-card">
          <h3>Player Information</h3>
          <div className="info-grid">
            {player.jerseyNumber && (
              <div className="info-item">
                <span className="info-label">Jersey</span>
                <span className="info-value">#{player.jerseyNumber}</span>
              </div>
            )}
            {player.position && (
              <div className="info-item">
                <span className="info-label">Position</span>
                <span className="info-value">{player.position}</span>
              </div>
            )}
            {player.ageGroup && (
              <div className="info-item">
                <span className="info-label">Age Group</span>
                <span className="info-value">{player.ageGroup}</span>
              </div>
            )}
            {player.gender && (
              <div className="info-item">
                <span className="info-label">Gender</span>
                <span className="info-value">{player.gender}</span>
              </div>
            )}
            {player.graduationYear && (
              <div className="info-item">
                <span className="info-label">Grad Year</span>
                <span className="info-value">{player.graduationYear}</span>
              </div>
            )}
            {player.height && (
              <div className="info-item">
                <span className="info-label">Height</span>
                <span className="info-value">{player.height}</span>
              </div>
            )}
            {player.hometown && (
              <div className="info-item">
                <span className="info-label">Hometown</span>
                <span className="info-value">{player.hometown}</span>
              </div>
            )}
            {player.highSchool && (
              <div className="info-item">
                <span className="info-label">High School</span>
                <span className="info-value">{player.highSchool}</span>
              </div>
            )}
            {player.collegeCommitment && (
              <div className="info-item commitment">
                <span className="info-label">Committed</span>
                <span className="info-value">{player.collegeCommitment}</span>
              </div>
            )}
          </div>
        </div>
        
        {/* Team Card */}
        <div className="profile-card team-card">
          <h3>Team</h3>
          {team ? (
            <Link to={`/team/${team.id}`} className="team-link">
              <div className="team-info">
                <span className="team-name">{team.name} {team.ageGroup}</span>
                <span className="team-league">{team.league}</span>
                {team.state && <span className="team-state">{team.state}</span>}
              </div>
              <div className="team-stats">
                <span className="team-rank">Rank #{team.rank}</span>
                <span className="team-record">
                  {team.wins}-{team.losses}-{team.draws}
                </span>
              </div>
            </Link>
          ) : player.teamName ? (
            <div className="team-info no-link">
              <span className="team-name">{player.teamName}</span>
              {player.league && <span className="team-league">{player.league}</span>}
            </div>
          ) : (
            <p className="no-team">No team assigned</p>
          )}

          {/* Team History Section */}
          {teamHistory.length > 0 && (
            <div className="team-history" style={{ marginTop: '1rem', borderTop: '1px solid #eee', paddingTop: '1rem' }}>
              <h4 style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>Team History</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {teamHistory
                  .sort((a, b) => new Date(b.joinedAt) - new Date(a.joinedAt))
                  .map((entry, idx) => {
                    const joinDate = new Date(entry.joinedAt);
                    const leftDate = entry.leftAt ? new Date(entry.leftAt) : null;
                    const formatDate = (d) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

                    // Determine the action badge
                    let actionBadge = null;
                    if (entry.action === 'transferred_in') {
                      actionBadge = <span style={{ fontSize: '0.7rem', background: '#e3f2fd', color: '#1976d2', padding: '2px 6px', borderRadius: '4px', marginLeft: '0.5rem' }}>Transferred In</span>;
                    } else if (entry.leftAction === 'transferred_out') {
                      actionBadge = <span style={{ fontSize: '0.7rem', background: '#fff3e0', color: '#e65100', padding: '2px 6px', borderRadius: '4px', marginLeft: '0.5rem' }}>Transferred Out</span>;
                    } else if (entry.leftAction === 'removed') {
                      actionBadge = <span style={{ fontSize: '0.7rem', background: '#ffebee', color: '#c62828', padding: '2px 6px', borderRadius: '4px', marginLeft: '0.5rem' }}>Left</span>;
                    }

                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '0.5rem',
                          background: idx === 0 && !leftDate ? '#f8f9fa' : 'white',
                          borderRadius: '6px',
                          border: '1px solid #eee'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: '500', fontSize: '0.85rem' }}>{entry.teamName}</span>
                          {actionBadge}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#888' }}>
                          {formatDate(joinDate)}
                          {leftDate ? ` - ${formatDate(leftDate)}` : ' - Present'}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>

        {/* Claim/Edit Card */}
        <div className="profile-card claim-card">
          <h3>Profile Ownership</h3>

          {claimStatus.loading ? (
            <div className="claim-loading">
              <div className="loading-spinner small"></div>
              <span>Checking claim status...</span>
            </div>
          ) : isOwnedByMe ? (
            // Player is claimed by current user
            <div className="claim-owned">
              <div className="owned-badge">
                <span className="owned-icon">✓</span>
                <span>You own this profile</span>
              </div>
              <button
                className="btn btn-edit"
                onClick={() => setShowEditModal(true)}
              >
                Edit Profile
              </button>
              {myClaim?.has_pending_challenge && (
                <div className="challenge-notice">
                  <span className="warning-icon">⚠️</span>
                  This profile has a pending challenge
                </div>
              )}
            </div>
          ) : claimStatus.claimed ? (
            // Player is claimed by someone else
            <div className="claim-other">
              <div className="claimed-badge">
                <span className="claimed-icon">👤</span>
                <span>Profile claimed by another user</span>
              </div>
              {isPaid && (
                <ChallengeClaimButton
                  claimId={claimStatus.claim_id}
                  playerName={displayName}
                  onChallenged={() => {}}
                />
              )}
            </div>
          ) : (
            // Player is not claimed
            <div className="claim-available">
              <p className="claim-desc">
                This player profile is unclaimed. Claim it to customize the photo,
                avatar, and display settings.
              </p>
              <ClaimPlayerButton
                playerId={parseInt(playerId)}
                teamId={team?.id}
                playerName={displayName}
                onClaimed={() => {
                  // Refresh claim status
                  getPlayerClaimStatus(parseInt(playerId)).then(setClaimStatus);
                }}
              />
            </div>
          )}
        </div>

        {/* Badges Card */}
        <div className="profile-card badges-card">
          <h3>Badges {playerBadges.length > 0 && `(${playerBadges.length})`}</h3>
          
          {playerBadges.length > 0 ? (
            <div className="earned-badges">
              {playerBadges.map(badge => (
                <div key={badge.id} className="badge-item earned">
                  <span className="badge-emoji">{badge.emoji}</span>
                  <span className="badge-name">{badge.name}</span>
                  {badge.count > 1 && (
                    <span className="badge-count">×{badge.count}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="no-badges">No badges earned yet</p>
          )}
          
          {canPerform('canAwardBadges') && (
            <div className="award-badges">
              <h4>Award Badges</h4>
              <div className="badge-grid">
                {BADGE_TYPES.map(badge => {
                  const currentCount = badges[playerId]?.[badge.id] || 0;
                  return (
                    <button
                      key={badge.id}
                      className={`badge-button ${currentCount > 0 ? 'awarded' : ''}`}
                      onClick={() => handleBadgeToggle(badge.id)}
                      title={`${badge.name}: ${badge.description} (${currentCount}/3)`}
                    >
                      <span className="badge-emoji">{badge.emoji}</span>
                      {currentCount > 0 && (
                        <span className="badge-count">{currentCount}</span>
                      )}
                      <span className="badge-name">{badge.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Profile Editor Modal */}
      {showEditModal && myClaim && (
        <ProfileEditorModal
          claim={myClaim}
          onClose={() => setShowEditModal(false)}
          onSaved={() => {
            setShowEditModal(false);
            // Refresh claim status
            getPlayerClaimStatus(parseInt(playerId)).then(setClaimStatus);
          }}
        />
      )}

      <style jsx>{`
        .player-profile {
          padding: 1rem;
          max-width: 1200px;
          margin: 0 auto;
        }
        
        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4rem;
        }
        
        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #e0e0e0;
          border-top-color: #2e7d32;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .not-found {
          text-align: center;
          padding: 2rem;
        }
        
        .not-found h2 {
          color: #2e7d32;
          margin-bottom: 1rem;
        }
        
        .not-found-card {
          background: white;
          border-radius: 12px;
          padding: 3rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          max-width: 400px;
          margin: 0 auto;
        }
        
        .not-found-icon {
          font-size: 4rem;
          color: #f48fb1;
          margin-bottom: 1rem;
        }
        
        .not-found-detail {
          color: #666;
          font-size: 0.9rem;
          margin: 0.5rem 0;
        }
        
        .profile-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .back-button {
          background: none;
          border: 1px solid #ddd;
          padding: 0.5rem 1rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.9rem;
        }
        
        .back-button:hover {
          background: #f5f5f5;
        }
        
        .profile-header h1 {
          flex: 1;
          margin: 0;
          color: #333;
        }
        
        .source-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 500;
        }
        
        .source-badge.database {
          background: #e3f2fd;
          color: #1976d2;
        }

        .player-photo-section {
          display: flex;
          flex-direction: column;
          align-items: center;
          margin-bottom: 2rem;
          padding: 1.5rem;
          background: linear-gradient(135deg, #e8f5e9 0%, #fff 100%);
          border-radius: 16px;
        }

        .player-photo-container {
          width: 150px;
          height: 150px;
          border-radius: 50%;
          overflow: hidden;
          border: 4px solid #2e7d32;
          box-shadow: 0 4px 12px rgba(46, 125, 50, 0.3);
          margin-bottom: 1rem;
        }

        .player-photo {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .player-photo-placeholder {
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #43a047 0%, #2e7d32 100%);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .placeholder-icon {
          font-size: 2.5rem;
          color: white;
          font-weight: bold;
        }

        .player-name-display {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
        }

        .player-display-name {
          font-size: 1.5rem;
          font-weight: 700;
          color: #333;
        }

        .player-position-badge {
          padding: 0.25rem 0.75rem;
          background: #2e7d32;
          color: white;
          border-radius: 20px;
          font-size: 0.85rem;
          font-weight: 500;
        }

        .source-badge.local {
          background: #fff3e0;
          color: #f57c00;
        }
        
        .profile-content {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
        }
        
        .profile-card {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .profile-card h3 {
          margin: 0 0 1rem 0;
          color: #2e7d32;
          font-size: 1.1rem;
          border-bottom: 2px solid #e8f5e9;
          padding-bottom: 0.5rem;
        }
        
        .info-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 1rem;
        }
        
        .info-item {
          display: flex;
          flex-direction: column;
        }
        
        .info-item.commitment {
          grid-column: span 2;
          background: #e8f5e9;
          padding: 0.75rem;
          border-radius: 8px;
        }
        
        .info-label {
          font-size: 0.75rem;
          color: #666;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .info-value {
          font-size: 1rem;
          color: #333;
          font-weight: 500;
        }
        
        .team-link {
          display: block;
          text-decoration: none;
          color: inherit;
          padding: 1rem;
          background: #f5f5f5;
          border-radius: 8px;
          transition: background 0.2s;
        }
        
        .team-link:hover {
          background: #e8f5e9;
        }
        
        .team-info {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          align-items: center;
          margin-bottom: 0.5rem;
        }
        
        .team-info.no-link {
          padding: 1rem;
          background: #f5f5f5;
          border-radius: 8px;
        }
        
        .team-name {
          font-weight: 600;
          color: #333;
        }
        
        .team-league {
          background: #2e7d32;
          color: white;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
        }
        
        .team-state {
          background: #1976d2;
          color: white;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
        }
        
        .team-stats {
          display: flex;
          gap: 1rem;
          font-size: 0.9rem;
          color: #666;
        }
        
        .team-rank {
          font-weight: 600;
          color: #2e7d32;
        }
        
        .no-team {
          color: #999;
          font-style: italic;
        }
        
        .earned-badges {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }
        
        .badge-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 0.75rem;
          background: #fff3e0;
          border-radius: 20px;
        }
        
        .badge-emoji {
          font-size: 1.2rem;
        }
        
        .badge-name {
          font-size: 0.85rem;
          color: #333;
        }
        
        .badge-count {
          background: #ff9800;
          color: white;
          font-size: 0.7rem;
          padding: 0.1rem 0.4rem;
          border-radius: 10px;
          font-weight: 600;
        }
        
        .no-badges {
          color: #999;
          font-style: italic;
          margin-bottom: 1.5rem;
        }
        
        .award-badges h4 {
          margin: 0 0 0.75rem 0;
          font-size: 0.9rem;
          color: #666;
        }
        
        .badge-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
          gap: 0.5rem;
        }

        .badge-button {
          position: relative;
          width: 70px;
          height: 70px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: white;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 0.25rem;
          transition: all 0.2s;
        }

        .badge-button:hover {
          border-color: #2e7d32;
          background: #e8f5e9;
        }

        .badge-button.awarded {
          border-color: #ff9800;
          background: #fff3e0;
        }

        .badge-button .badge-emoji {
          font-size: 1.5rem;
        }

        .badge-button .badge-name {
          font-size: 0.6rem;
          color: #666;
          margin-top: 2px;
          text-align: center;
          line-height: 1.1;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .badge-button .badge-count {
          position: absolute;
          top: -5px;
          right: -5px;
          min-width: 18px;
          height: 18px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 1rem;
          font-weight: 500;
          transition: background 0.2s;
        }
        
        .btn-primary {
          background: #2e7d32;
          color: white;
        }
        
        .btn-primary:hover {
          background: #1b5e20;
        }

        .btn-edit {
          background: #2e7d32;
          color: white;
          margin-top: 0.75rem;
        }

        .btn-edit:hover {
          background: #1b5e20;
        }

        .claim-card {
          background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
        }

        .claim-loading {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          color: #666;
          padding: 1rem 0;
        }

        .loading-spinner.small {
          width: 20px;
          height: 20px;
          border-width: 2px;
        }

        .claim-owned {
          text-align: center;
        }

        .owned-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: #e8f5e9;
          color: #2e7d32;
          border-radius: 20px;
          font-weight: 500;
        }

        .owned-icon {
          font-size: 1.1rem;
        }

        .challenge-notice {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin-top: 1rem;
          padding: 0.75rem;
          background: #fff3e0;
          color: #e65100;
          border-radius: 8px;
          font-size: 0.9rem;
        }

        .claim-other {
          text-align: center;
        }

        .claimed-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: #f5f5f5;
          color: #666;
          border-radius: 20px;
          margin-bottom: 1rem;
        }

        .claimed-icon {
          font-size: 1.1rem;
        }

        .claim-available {
          text-align: center;
        }

        .claim-desc {
          color: #666;
          font-size: 0.9rem;
          margin-bottom: 1rem;
          line-height: 1.5;
        }

        @media (max-width: 600px) {
          .profile-header {
            flex-wrap: wrap;
          }
          
          .profile-header h1 {
            order: 1;
            width: 100%;
          }
          
          .info-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}

export default PlayerProfile;
