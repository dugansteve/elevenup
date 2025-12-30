import { useState, useEffect } from 'react';
import { useUser } from '../context/UserContext';
import { useRankingsData } from '../data/useRankingsData';
import PhotoUpload from './PhotoUpload';
import AvatarBuilder from './AvatarBuilder';
import TeamSelector from './TeamSelector';
import { ClubsIcon } from './PaperIcons';

/**
 * Modal for editing a claimed player's profile
 * Includes photo upload, avatar builder, display settings, and team switching
 */
export default function ProfileEditorModal({ claim, onClose, onSaved }) {
  const { user, updatePlayerProfile, switchPlayerTeam } = useUser();
  const { teamsData } = useRankingsData();

  const [activeTab, setActiveTab] = useState('photo');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Get initial team name from claim or lookup from teams data
  const getInitialTeamName = () => {
    // First try claim data
    const claimTeamName = claim.original_player?.team_name || claim.created_player?.team_name;
    if (claimTeamName) return claimTeamName;

    // Fallback: lookup from teams data using team_id
    if (claim.team_id && teamsData?.length > 0) {
      const team = teamsData.find(t => t.id === claim.team_id);
      if (team) return team.name;
    }

    return '';
  };

  // Local state for edits
  const [photoUrl, setPhotoUrl] = useState(claim.photo_url || null);
  const [avatarConfig, setAvatarConfig] = useState(claim.avatar_config || null);
  const [displayNameMode, setDisplayNameMode] = useState(claim.display_name_mode || 'full');
  const [selectedTeam, setSelectedTeam] = useState({
    id: claim.team_id,
    name: getInitialTeamName()
  });

  // Update team name when teamsData loads
  useEffect(() => {
    if (!selectedTeam.name && claim.team_id && teamsData?.length > 0) {
      const team = teamsData.find(t => t.id === claim.team_id);
      if (team) {
        setSelectedTeam(prev => ({ ...prev, name: team.name }));
      }
    }
  }, [teamsData, claim.team_id, selectedTeam.name]);

  // Track what's changed
  const [hasChanges, setHasChanges] = useState(false);

  const handlePhotoUploaded = (url) => {
    setPhotoUrl(url);
    setHasChanges(true);
  };

  const handlePhotoRemoved = () => {
    setPhotoUrl(null);
    setHasChanges(true);
  };

  const handleAvatarChange = (config) => {
    setAvatarConfig(config);
    setHasChanges(true);
  };

  const handleDisplayModeChange = (mode) => {
    setDisplayNameMode(mode);
    setHasChanges(true);
  };

  const handleTeamChange = (team) => {
    setSelectedTeam(team);
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      // Update profile settings
      const profileResult = await updatePlayerProfile(claim.claim_id, {
        photo_url: photoUrl,
        avatar_config: avatarConfig,
        display_name_mode: displayNameMode
      });

      if (!profileResult.success) {
        throw new Error(profileResult.error || 'Failed to update profile');
      }

      // Switch team if changed
      if (selectedTeam.id !== claim.team_id) {
        const teamResult = await switchPlayerTeam(claim.claim_id, selectedTeam.id);
        if (!teamResult.success) {
          throw new Error(teamResult.error || 'Failed to switch team');
        }
      }

      if (onSaved) {
        onSaved();
      }
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // Get player name for display
  const playerName = claim.original_player?.name ||
    (claim.created_player ? `${claim.created_player.first_name} ${claim.created_player.last_name}` : 'Player');

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h2 style={styles.title}>Edit Profile: {playerName}</h2>
          <button onClick={onClose} style={styles.closeButton} disabled={saving}>
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div style={styles.tabs}>
          {[
            { id: 'photo', label: 'Photo', icon: '📷' },
            { id: 'avatar', label: 'Avatar', icon: '😊' },
            { id: 'display', label: 'Display', icon: '👁️' },
            { id: 'team', label: 'Team', icon: <ClubsIcon size={16} color="green" /> },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                ...styles.tab,
                ...(activeTab === tab.id && styles.tabActive)
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={styles.content}>
          {activeTab === 'photo' && (
            <div style={styles.tabContent}>
              <h3 style={styles.sectionTitle}>Upload Photo</h3>
              <p style={styles.sectionDesc}>
                Upload a photo of the player. This will be shown on their profile.
              </p>
              <PhotoUpload
                userId={user.id}
                claimId={claim.claim_id}
                currentPhotoUrl={photoUrl}
                onPhotoUploaded={handlePhotoUploaded}
                onPhotoRemoved={handlePhotoRemoved}
              />
            </div>
          )}

          {activeTab === 'avatar' && (
            <div style={styles.tabContent}>
              <h3 style={styles.sectionTitle}>Build Avatar</h3>
              <p style={styles.sectionDesc}>
                Create a custom avatar if you prefer not to use a photo.
              </p>
              <AvatarBuilder
                initialConfig={avatarConfig}
                onConfigChange={handleAvatarChange}
              />
            </div>
          )}

          {activeTab === 'display' && (
            <div style={styles.tabContent}>
              <h3 style={styles.sectionTitle}>Display Settings</h3>
              <p style={styles.sectionDesc}>
                Control how the player's name is shown on their profile.
              </p>

              <div style={styles.displayOptions}>
                <label style={styles.radioLabel}>
                  <input
                    type="radio"
                    name="displayMode"
                    value="full"
                    checked={displayNameMode === 'full'}
                    onChange={() => handleDisplayModeChange('full')}
                    style={styles.radio}
                  />
                  <div style={styles.radioContent}>
                    <strong>Full Name</strong>
                    <span style={styles.example}>e.g., Sarah Johnson</span>
                  </div>
                </label>

                <label style={styles.radioLabel}>
                  <input
                    type="radio"
                    name="displayMode"
                    value="initial"
                    checked={displayNameMode === 'initial'}
                    onChange={() => handleDisplayModeChange('initial')}
                    style={styles.radio}
                  />
                  <div style={styles.radioContent}>
                    <strong>First Name + Last Initial</strong>
                    <span style={styles.example}>e.g., Sarah J.</span>
                  </div>
                </label>
              </div>

              <div style={styles.privacyNote}>
                <strong>Privacy Note:</strong> Choosing "Last Initial" helps protect
                your child's privacy while still allowing teammates and coaches to
                identify them.
              </div>
            </div>
          )}

          {activeTab === 'team' && (
            <div style={styles.tabContent}>
              <h3 style={styles.sectionTitle}>Team Assignment</h3>
              <p style={styles.sectionDesc}>
                Assign or switch the player to a different team.
              </p>

              <div style={styles.teamSection}>
                <label style={styles.label}>Current Team</label>
                <TeamSelector
                  currentTeamId={selectedTeam.id}
                  currentTeamName={selectedTeam.name}
                  onSelect={handleTeamChange}
                />
              </div>

              {selectedTeam.id !== claim.team_id && (
                <div style={styles.teamChangeWarning}>
                  Team will be changed when you save.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          {error && <div style={styles.error}>{error}</div>}

          <div style={styles.footerButtons}>
            <button
              onClick={onClose}
              style={styles.cancelButton}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              style={{
                ...styles.saveButton,
                ...((!hasChanges || saving) && styles.saveButtonDisabled)
              }}
              disabled={!hasChanges || saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
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
    borderRadius: '16px',
    width: '100%',
    maxWidth: '500px',
    maxHeight: '90vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.2)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #eee',
  },
  title: {
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
    padding: '4px 8px',
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid #eee',
    padding: '0 16px',
  },
  tab: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    padding: '12px 8px',
    border: 'none',
    backgroundColor: 'transparent',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#666',
    borderBottom: '2px solid transparent',
    transition: 'all 0.2s ease',
  },
  tabActive: {
    color: '#2d5016',
    borderBottomColor: '#2d5016',
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '20px',
  },
  tabContent: {
    minHeight: '200px',
  },
  sectionTitle: {
    margin: '0 0 8px 0',
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
  },
  sectionDesc: {
    margin: '0 0 16px 0',
    fontSize: '14px',
    color: '#666',
  },
  displayOptions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  radioLabel: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  radio: {
    marginTop: '4px',
  },
  radioContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  example: {
    fontSize: '13px',
    color: '#666',
  },
  privacyNote: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: '#e3f2fd',
    borderRadius: '8px',
    fontSize: '13px',
    color: '#1976d2',
    lineHeight: '1.5',
  },
  teamSection: {
    marginBottom: '16px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#333',
  },
  teamChangeWarning: {
    padding: '12px',
    backgroundColor: '#fff3e0',
    borderRadius: '8px',
    fontSize: '13px',
    color: '#e65100',
  },
  footer: {
    padding: '16px 20px',
    borderTop: '1px solid #eee',
  },
  error: {
    marginBottom: '12px',
    padding: '10px',
    backgroundColor: '#ffebee',
    color: '#c62828',
    borderRadius: '8px',
    fontSize: '14px',
  },
  footerButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
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
  saveButton: {
    padding: '10px 20px',
    backgroundColor: '#2d5016',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  saveButtonDisabled: {
    backgroundColor: '#999',
    cursor: 'not-allowed',
  },
};
