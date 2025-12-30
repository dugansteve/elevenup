import { useState } from 'react';
import { useUser } from '../context/UserContext';
import ProfileEditorModal from './ProfileEditorModal';

/**
 * List of claimed players for the Settings page
 * Shows all players claimed by the current user with edit/release actions
 */
export default function ClaimedPlayersList() {
  const {
    claimedPlayers,
    claimLimits,
    claimsLoading,
    releasePlayer,
    loadClaimedPlayers
  } = useUser();

  const [editingClaim, setEditingClaim] = useState(null);
  const [releasingId, setReleasingId] = useState(null);
  const [confirmRelease, setConfirmRelease] = useState(null);

  const handleRelease = async (claimId) => {
    setReleasingId(claimId);
    try {
      const result = await releasePlayer(claimId);
      if (!result.success) {
        alert(result.error || 'Failed to release player');
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setReleasingId(null);
      setConfirmRelease(null);
    }
  };

  // Get player name from claim
  const getPlayerName = (claim) => {
    if (claim.original_player) {
      return claim.original_player.name;
    }
    if (claim.created_player) {
      return `${claim.created_player.first_name} ${claim.created_player.last_name}`;
    }
    return 'Unknown Player';
  };

  // Get team info from claim
  const getTeamInfo = (claim) => {
    if (claim.original_player) {
      return {
        name: claim.original_player.team_name,
        ageGroup: claim.original_player.age_group
      };
    }
    if (claim.created_player) {
      return {
        name: 'User Created',
        ageGroup: claim.created_player.age_group
      };
    }
    return { name: 'Unknown Team', ageGroup: '' };
  };

  if (claimsLoading) {
    return (
      <div style={styles.loading}>
        <div style={styles.spinner} />
        <span>Loading claimed players...</span>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header with limits */}
      <div style={styles.header}>
        <h3 style={styles.title}>My Claimed Players</h3>
        <div style={styles.limits}>
          <span style={styles.limitBadge}>
            {claimLimits.total}/{claimLimits.maxTotal} players
          </span>
        </div>
      </div>

      {/* Player list */}
      {claimedPlayers.length === 0 ? (
        <div style={styles.empty}>
          <span style={styles.emptyIcon}>👤</span>
          <p style={styles.emptyText}>No claimed players yet</p>
          <p style={styles.emptyHint}>
            Go to a player's profile and click "Claim This Player" to get started.
          </p>
        </div>
      ) : (
        <div style={styles.list}>
          {claimedPlayers.map(claim => {
            const playerName = getPlayerName(claim);
            const teamInfo = getTeamInfo(claim);
            const isReleasing = releasingId === claim.claim_id;

            return (
              <div key={claim.claim_id} style={styles.playerCard}>
                {/* Player avatar/photo */}
                <div style={styles.avatar}>
                  {claim.photo_url ? (
                    <img src={claim.photo_url} alt={playerName} style={styles.avatarImg} />
                  ) : (
                    <span style={styles.avatarPlaceholder}>
                      {playerName.charAt(0).toUpperCase()}
                    </span>
                  )}
                  {claim.is_user_created && (
                    <span style={styles.userCreatedBadge} title="User Created">✨</span>
                  )}
                </div>

                {/* Player info */}
                <div style={styles.playerInfo}>
                  <div style={styles.playerName}>{playerName}</div>
                  <div style={styles.teamName}>{teamInfo.name}</div>
                  <div style={styles.meta}>
                    {teamInfo.ageGroup && <span>{teamInfo.ageGroup}</span>}
                    {claim.display_name_mode === 'initial' && (
                      <span style={styles.privacyBadge}>Privacy On</span>
                    )}
                    {claim.has_pending_challenge && (
                      <span style={styles.challengeBadge}>Challenge Pending</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div style={styles.actions}>
                  <button
                    onClick={() => setEditingClaim(claim)}
                    style={styles.editButton}
                  >
                    Edit
                  </button>

                  {confirmRelease === claim.claim_id ? (
                    <div style={styles.confirmRelease}>
                      <span style={styles.confirmText}>Release?</span>
                      <button
                        onClick={() => handleRelease(claim.claim_id)}
                        style={styles.confirmYes}
                        disabled={isReleasing}
                      >
                        {isReleasing ? '...' : 'Yes'}
                      </button>
                      <button
                        onClick={() => setConfirmRelease(null)}
                        style={styles.confirmNo}
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmRelease(claim.claim_id)}
                      style={styles.releaseButton}
                    >
                      Release
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Edit Modal */}
      {editingClaim && (
        <ProfileEditorModal
          claim={editingClaim}
          onClose={() => setEditingClaim(null)}
          onSaved={() => {
            setEditingClaim(null);
            loadClaimedPlayers();
          }}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
  },
  limits: {
    display: 'flex',
    gap: '8px',
  },
  limitBadge: {
    padding: '4px 10px',
    backgroundColor: '#e8f5e9',
    color: '#2d5016',
    borderRadius: '12px',
    fontSize: '13px',
    fontWeight: '500',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    padding: '40px',
    color: '#666',
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '3px solid #e8f5e9',
    borderTop: '3px solid #2d5016',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  empty: {
    textAlign: 'center',
    padding: '40px 20px',
  },
  emptyIcon: {
    fontSize: '48px',
  },
  emptyText: {
    margin: '12px 0 8px',
    fontSize: '16px',
    fontWeight: '500',
    color: '#666',
  },
  emptyHint: {
    margin: 0,
    fontSize: '14px',
    color: '#999',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  playerCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    backgroundColor: '#f9f9f9',
    borderRadius: '10px',
    border: '1px solid #eee',
  },
  avatar: {
    position: 'relative',
    width: '48px',
    height: '48px',
    flexShrink: 0,
  },
  avatarImg: {
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    objectFit: 'cover',
    border: '2px solid #2d5016',
  },
  avatarPlaceholder: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    backgroundColor: '#e8f5e9',
    color: '#2d5016',
    fontSize: '20px',
    fontWeight: '600',
  },
  userCreatedBadge: {
    position: 'absolute',
    bottom: '-2px',
    right: '-2px',
    fontSize: '14px',
  },
  playerInfo: {
    flex: 1,
    minWidth: 0,
  },
  playerName: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#333',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  teamName: {
    fontSize: '13px',
    color: '#666',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  meta: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
    marginTop: '4px',
    fontSize: '11px',
    color: '#999',
  },
  privacyBadge: {
    padding: '2px 6px',
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
    borderRadius: '4px',
  },
  challengeBadge: {
    padding: '2px 6px',
    backgroundColor: '#fff3e0',
    color: '#e65100',
    borderRadius: '4px',
  },
  actions: {
    display: 'flex',
    gap: '8px',
    flexShrink: 0,
  },
  editButton: {
    padding: '6px 12px',
    backgroundColor: '#2d5016',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  releaseButton: {
    padding: '6px 12px',
    backgroundColor: 'transparent',
    color: '#c62828',
    border: '1px solid #c62828',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  confirmRelease: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  confirmText: {
    fontSize: '12px',
    color: '#c62828',
    marginRight: '4px',
  },
  confirmYes: {
    padding: '4px 8px',
    backgroundColor: '#c62828',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  confirmNo: {
    padding: '4px 8px',
    backgroundColor: '#f5f5f5',
    color: '#666',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
  },
};
