import { useState } from 'react';
import { useUser, CLAIM_LIMITS } from '../context/UserContext';

/**
 * Button to claim an existing player profile
 * Shows on unclaimed players for Pro users
 */
export default function ClaimPlayerButton({ playerId, teamId, playerName, onClaimed }) {
  const {
    user,
    isPaid,
    canClaimMore,
    claimPlayer,
    claimLimits
  } = useUser();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check if user can claim
  const claimCheck = canClaimMore(teamId);

  const handleClaim = async () => {
    if (!claimCheck.allowed) {
      setError(claimCheck.reason);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await claimPlayer(playerId, teamId);

      if (result.success) {
        if (onClaimed) {
          onClaimed(result.claim_id);
        }
      } else {
        setError(result.error || 'Failed to claim player');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Don't show for non-Pro users
  if (!isPaid) {
    return (
      <div style={styles.upgradePrompt}>
        <span style={styles.lockIcon}>🔒</span>
        <span>Upgrade to Pro to claim this player</span>
      </div>
    );
  }

  // Show limit info
  const limitInfo = `${claimLimits.total}/${claimLimits.maxTotal} players claimed`;

  return (
    <div style={styles.container}>
      <button
        onClick={handleClaim}
        disabled={loading || !claimCheck.allowed}
        style={{
          ...styles.claimButton,
          ...(loading && styles.loading),
          ...(!claimCheck.allowed && styles.disabled)
        }}
      >
        {loading ? (
          <span>Claiming...</span>
        ) : (
          <>
            <span style={styles.icon}>✋</span>
            <span>Claim This Player</span>
          </>
        )}
      </button>

      <div style={styles.limitInfo}>{limitInfo}</div>

      {error && <div style={styles.error}>{error}</div>}

      {!claimCheck.allowed && !error && (
        <div style={styles.warning}>{claimCheck.reason}</div>
      )}
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    padding: '12px',
  },
  claimButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px 24px',
    backgroundColor: '#2d5016',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    width: '100%',
    maxWidth: '280px',
  },
  loading: {
    backgroundColor: '#4d8527',
    cursor: 'wait',
  },
  disabled: {
    backgroundColor: '#999',
    cursor: 'not-allowed',
    opacity: 0.7,
  },
  icon: {
    fontSize: '18px',
  },
  limitInfo: {
    fontSize: '12px',
    color: '#666',
  },
  error: {
    fontSize: '14px',
    color: '#c62828',
    backgroundColor: '#ffebee',
    padding: '8px 12px',
    borderRadius: '4px',
    marginTop: '4px',
  },
  warning: {
    fontSize: '14px',
    color: '#e65100',
    backgroundColor: '#fff3e0',
    padding: '8px 12px',
    borderRadius: '4px',
    marginTop: '4px',
  },
  upgradePrompt: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
    color: '#666',
    fontSize: '14px',
  },
  lockIcon: {
    fontSize: '16px',
  },
};
