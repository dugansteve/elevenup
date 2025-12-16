// PlayerProfile.jsx - Individual player page
// V39+: Now loads players from rankings JSON (playersData)

import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import { storage, BADGE_TYPES } from '../data/sampleData';
import { useUser } from '../context/UserContext';

function PlayerProfile() {
  const { playerId } = useParams();
  const navigate = useNavigate();
  const { playersData, teamsData, isLoading } = useRankingsData();
  const { canPerform } = useUser();
  
  const [localPlayers, setLocalPlayers] = useState([]);
  const [badges, setBadges] = useState({});
  
  useEffect(() => {
    // Load local players (user-created)
    const savedPlayers = storage.getPlayers();
    setLocalPlayers(savedPlayers);
    
    // Load badges
    const savedBadges = storage.getBadges();
    setBadges(savedBadges);
  }, [playerId]);
  
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
    
    // Try to find by team name
    if (player.teamName) {
      return teamsData.find(t => 
        t.name === player.teamName || 
        t.name.toLowerCase().includes(player.teamName.toLowerCase())
      );
    }
    
    // Try to find by teamId
    if (player.teamId) {
      return teamsData.find(t => t.id === player.teamId);
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
  
  // Handle badge award/removal
  const handleBadgeToggle = (badgeId) => {
    if (!canPerform('canAwardBadges')) return;
    
    const currentCount = (badges[playerId]?.[badgeId]) || 0;
    const newCount = currentCount >= 3 ? 0 : currentCount + 1;
    
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
  
  return (
    <div className="player-profile">
      <div className="profile-header">
        <button 
          className="back-button"
          onClick={() => navigate(-1)}
        >
          ← Back
        </button>
        <h1>{player.name || `${player.firstName} ${player.lastName}`}</h1>
        {player.source === 'database' && (
          <span className="source-badge database">Database Player</span>
        )}
        {player.source === 'local' && (
          <span className="source-badge local">My Player</span>
        )}
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
                <span className="team-name">{team.name}</span>
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
                      title={`${badge.name} (${currentCount}/3)`}
                    >
                      <span className="badge-emoji">{badge.emoji}</span>
                      {currentCount > 0 && (
                        <span className="badge-count">{currentCount}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
      
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
          grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
          gap: 0.5rem;
        }
        
        .badge-button {
          position: relative;
          width: 50px;
          height: 50px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
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
