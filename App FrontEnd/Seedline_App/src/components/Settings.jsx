import { useState } from 'react';
import { useUser } from '../context/UserContext';
import { getSuggestions, exportSuggestionsJSON } from './SuggestTournament';
import ClaimedPlayersList from './ClaimedPlayersList';
import { currentBrand } from '../config/brand';

function Settings() {
  const { user, isPaid } = useUser();
  const [notifications, setNotifications] = useState(true);
  const [emailUpdates, setEmailUpdates] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  return (
    <div className="settings-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-description">
          Manage your account preferences and notification settings.
        </p>
      </div>

      {/* Account Section */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Account</h2>
        </div>
        <div className="settings-section">
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Name</div>
              <div className="setting-value">{user?.name || 'Guest User'}</div>
            </div>
          </div>
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Role</div>
              <div className="setting-value">{user?.role || 'Guest'}</div>
            </div>
          </div>
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Account Type</div>
              <div className="setting-value">{user?.accountType || 'Free'}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Claimed Players Section - Only for Pro users */}
      {isPaid && (
        <div className="card claimed-players-card">
          <div className="card-header">
            <h2 className="card-title">My Claimed Players</h2>
          </div>
          <div className="claimed-players-section">
            <ClaimedPlayersList />
          </div>
        </div>
      )}

      {/* Upgrade prompt for Free users */}
      {!isPaid && user?.accountType !== 'guest' && (
        <div className="card upgrade-card">
          <div className="card-header">
            <h2 className="card-title">Claim Player Profiles</h2>
          </div>
          <div className="upgrade-section">
            <div className="upgrade-icon">🔒</div>
            <p className="upgrade-text">
              Upgrade to Pro to claim up to 8 player profiles. Customize photos,
              avatars, and control how player names are displayed.
            </p>
            <button className="upgrade-btn">Upgrade to Pro</button>
          </div>
        </div>
      )}

      {/* Preferences Section */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Preferences</h2>
        </div>
        <div className="settings-section">
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Push Notifications</div>
              <div className="setting-description">
                Receive notifications about game updates and rankings
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={notifications}
                onChange={(e) => setNotifications(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Email Updates</div>
              <div className="setting-description">
                Receive weekly digest of team rankings and news
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={emailUpdates}
                onChange={(e) => setEmailUpdates(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Dark Mode</div>
              <div className="setting-description">
                Use dark theme (coming soon)
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={darkMode}
                onChange={(e) => setDarkMode(e.target.checked)}
                disabled
              />
              <span className="toggle-slider disabled"></span>
            </label>
          </div>
        </div>
      </div>

      {/* Tournament Suggestions Section */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Tournament Suggestions</h2>
        </div>
        <div className="settings-section">
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Your Suggestions</div>
              <div className="setting-description">
                {getSuggestions().length} tournament{getSuggestions().length !== 1 ? 's' : ''} suggested
              </div>
            </div>
            <button
              className="export-btn"
              onClick={exportSuggestionsJSON}
              disabled={getSuggestions().length === 0}
            >
              Export & Send
            </button>
          </div>
          <div className="suggestion-instructions">
            <p>
              After exporting, email the file to{' '}
              <a href={`mailto:${currentBrand.supportEmail}?subject=Tournament%20Suggestions`} className="support-link">
                {currentBrand.supportEmail}
              </a>{' '}
              for review. Approved tournaments will be added to our database.
            </p>
          </div>
        </div>
      </div>

      {/* About Section */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">About</h2>
        </div>
        <div className="settings-section">
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Version</div>
              <div className="setting-value">1.0.0</div>
            </div>
          </div>
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-label">Support</div>
              <div className="setting-value">
                <a href={`mailto:${currentBrand.supportEmail}`} className="support-link">
                  {currentBrand.supportEmail}
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .settings-page {
          max-width: 800px;
          margin: 0 auto;
        }

        .settings-section {
          display: flex;
          flex-direction: column;
        }

        .setting-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem 0;
          border-bottom: 1px solid #f0f0f0;
        }

        .setting-item:last-child {
          border-bottom: none;
        }

        .setting-info {
          flex: 1;
        }

        .setting-label {
          font-weight: 600;
          color: var(--text-dark);
          margin-bottom: 0.25rem;
        }

        .setting-description {
          font-size: 0.85rem;
          color: #666;
        }

        .setting-value {
          color: #555;
          font-size: 0.95rem;
        }

        .support-link {
          color: var(--primary-green);
          text-decoration: none;
        }

        .support-link:hover {
          text-decoration: underline;
        }

        .export-btn {
          background: var(--accent-green);
          color: white;
          border: none;
          padding: 0.6rem 1rem;
          border-radius: 6px;
          font-weight: 600;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .export-btn:hover:not(:disabled) {
          background: var(--primary-green);
        }

        .export-btn:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        .suggestion-instructions {
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
          margin-top: 0.5rem;
        }

        .suggestion-instructions p {
          margin: 0;
          font-size: 0.9rem;
          color: #555;
          line-height: 1.5;
        }

        /* Toggle Switch */
        .toggle-switch {
          position: relative;
          display: inline-block;
          width: 50px;
          height: 28px;
        }

        .toggle-switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }

        .toggle-slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: #ccc;
          transition: 0.3s;
          border-radius: 28px;
        }

        .toggle-slider:before {
          position: absolute;
          content: "";
          height: 22px;
          width: 22px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: 0.3s;
          border-radius: 50%;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        input:checked + .toggle-slider {
          background-color: var(--primary-green);
        }

        input:checked + .toggle-slider:before {
          transform: translateX(22px);
        }

        .toggle-slider.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Claimed Players Section */
        .claimed-players-card {
          overflow: visible;
        }

        .claimed-players-section {
          padding: 0;
        }

        .claimed-players-section > div {
          box-shadow: none;
          padding: 0;
        }

        /* Upgrade Card */
        .upgrade-card {
          background: linear-gradient(135deg, #fff3e0 0%, #ffffff 100%);
          border: 2px solid #e65100;
        }

        .upgrade-section {
          text-align: center;
          padding: 2rem 1rem;
        }

        .upgrade-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .upgrade-text {
          color: #666;
          font-size: 0.95rem;
          line-height: 1.6;
          margin-bottom: 1.5rem;
          max-width: 400px;
          margin-left: auto;
          margin-right: auto;
        }

        .upgrade-btn {
          background: linear-gradient(135deg, #e65100 0%, #ff9800 100%);
          color: white;
          border: none;
          padding: 0.75rem 2rem;
          border-radius: 8px;
          font-weight: 600;
          font-size: 1rem;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(230, 81, 0, 0.3);
        }

        .upgrade-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(230, 81, 0, 0.4);
        }

        @media (max-width: 768px) {
          .setting-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.75rem;
          }

          .toggle-switch {
            align-self: flex-start;
          }
        }
      `}</style>
    </div>
  );
}

export default Settings;
