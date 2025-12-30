import { useState } from 'react';
import { useUser } from '../context/UserContext';

/**
 * Button to challenge someone else's claim on a player
 * Shows modal to enter reason for challenge
 */
export default function ChallengeClaimButton({ claimId, playerName, onChallenged }) {
  const { user, isPaid, challengeClaim } = useUser();

  const [showModal, setShowModal] = useState(false);
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    if (!reason.trim()) {
      setError('Please explain why you are the rightful parent/guardian');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await challengeClaim(claimId, reason.trim());

      if (result.success) {
        setSuccess(true);
        if (onChallenged) {
          onChallenged(result.challenge_id);
        }
        // Close modal after 2 seconds
        setTimeout(() => {
          setShowModal(false);
          setSuccess(false);
          setReason('');
        }, 2000);
      } else {
        setError(result.error || 'Failed to submit challenge');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Don't show for non-Pro users
  if (!isPaid) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        style={styles.challengeButton}
      >
        <span style={styles.icon}>🙋</span>
        <span>This is my child</span>
      </button>

      {showModal && (
        <div style={styles.modalOverlay} onClick={() => !loading && setShowModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>Challenge This Claim</h3>
              <button
                onClick={() => setShowModal(false)}
                style={styles.closeButton}
                disabled={loading}
              >
                ✕
              </button>
            </div>

            {success ? (
              <div style={styles.successMessage}>
                <span style={styles.successIcon}>✓</span>
                <p>Challenge submitted successfully!</p>
                <p style={styles.successNote}>
                  An administrator will review your request.
                </p>
              </div>
            ) : (
              <>
                <div style={styles.modalBody}>
                  <p style={styles.explanation}>
                    Someone else has claimed <strong>{playerName}</strong>. If this is your child,
                    you can challenge their claim. An administrator will review and decide.
                  </p>

                  <label style={styles.label}>
                    Why are you the rightful parent/guardian?
                  </label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g., I am the parent of this player. My name is..."
                    style={styles.textarea}
                    rows={4}
                    disabled={loading}
                  />

                  <div style={styles.note}>
                    <strong>Note:</strong> Both you and the current claimant can continue
                    to edit the profile while the challenge is under review.
                  </div>

                  {error && <div style={styles.error}>{error}</div>}
                </div>

                <div style={styles.modalFooter}>
                  <button
                    onClick={() => setShowModal(false)}
                    style={styles.cancelButton}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmit}
                    style={styles.submitButton}
                    disabled={loading || !reason.trim()}
                  >
                    {loading ? 'Submitting...' : 'Submit Challenge'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

const styles = {
  challengeButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '10px 20px',
    backgroundColor: '#fff3e0',
    color: '#e65100',
    border: '2px solid #e65100',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  icon: {
    fontSize: '16px',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '480px',
    maxHeight: '90vh',
    overflow: 'auto',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #eee',
  },
  modalTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    color: '#666',
    padding: '4px',
  },
  modalBody: {
    padding: '20px',
  },
  explanation: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '16px',
    lineHeight: '1.5',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '8px',
  },
  textarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    resize: 'vertical',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
  },
  note: {
    fontSize: '12px',
    color: '#666',
    backgroundColor: '#f5f5f5',
    padding: '12px',
    borderRadius: '8px',
    marginTop: '16px',
    lineHeight: '1.5',
  },
  error: {
    fontSize: '14px',
    color: '#c62828',
    backgroundColor: '#ffebee',
    padding: '12px',
    borderRadius: '8px',
    marginTop: '16px',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '16px 20px',
    borderTop: '1px solid #eee',
  },
  cancelButton: {
    padding: '10px 20px',
    backgroundColor: '#f5f5f5',
    color: '#666',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  submitButton: {
    padding: '10px 20px',
    backgroundColor: '#e65100',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  successMessage: {
    padding: '40px 20px',
    textAlign: 'center',
  },
  successIcon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '60px',
    height: '60px',
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
    borderRadius: '50%',
    fontSize: '32px',
    marginBottom: '16px',
  },
  successNote: {
    fontSize: '14px',
    color: '#666',
    marginTop: '8px',
  },
};
