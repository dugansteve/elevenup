import { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUser } from '../context/UserContext';

import {
  TeamsIcon,
  ClubsIcon,
  PlayersIcon,
  BadgesIcon,
  SimulationIcon,
  TournamentIcon,
  SettingsIcon,
  LogoutIcon
} from './PaperIcons';

// Check if dark theme is active
const isDarkTheme = () => document.body.classList.contains('elevenup-theme');
// Get icon color based on theme
const getIconColor = () => isDarkTheme() ? 'elevenup' : 'green';

function HamburgerMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const buttonRef = useRef(null);
  const location = useLocation();
  const { user, logout } = useUser();

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isOpen]);

  // Close menu when route changes
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const menuItems = [
    { path: '/rankings', label: 'Teams', icon: TeamsIcon },
    { path: '/clubs', label: 'Clubs', icon: ClubsIcon },
    { path: '/players', label: 'Players', icon: PlayersIcon },
    { path: '/badges', label: 'Badges', icon: BadgesIcon },
    { path: '/simulation', label: 'Conference Simulation', icon: SimulationIcon },
    { path: '/tournaments', label: 'Tournament Finder', icon: TournamentIcon },
    { path: '/settings', label: 'Settings', icon: SettingsIcon },
  ];

  const isActive = (path) => {
    if (path === '/rankings') {
      return location.pathname === '/rankings' || location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <>
      {/* Hamburger Button */}
      <button
        ref={buttonRef}
        className="hamburger-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Menu"
        aria-expanded={isOpen}
      >
        <div className={`hamburger-icon ${isOpen ? 'open' : ''}`}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </button>

      {/* Overlay */}
      {isOpen && <div className="menu-overlay" onClick={() => setIsOpen(false)} />}

      {/* Slide-out Menu */}
      <nav ref={menuRef} className={`slide-menu ${isOpen ? 'open' : ''}`}>
        <div className="menu-header">
          <div className="menu-user-info">
            <div className="menu-user-name">{user?.name || 'Guest'}</div>
            <div className="menu-user-role">{user?.role || ''}</div>
          </div>
        </div>

        <div className="menu-items">
          {menuItems.map((item) => {
            const IconComponent = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`menu-item ${isActive(item.path) ? 'active' : ''}`}
                onClick={() => setIsOpen(false)}
              >
                <span className="menu-item-icon">
                  <IconComponent size={24} color={getIconColor()} />
                </span>
                <span className="menu-item-label">{item.label}</span>
                {isActive(item.path) && <span className="menu-item-indicator" />}
              </Link>
            );
          })}
        </div>

        <div className="menu-footer">
          <button onClick={logout} className="menu-logout-btn">
            <span className="menu-item-icon">
              <LogoutIcon size={24} color={getIconColor()} />
            </span>
            <span>Logout</span>
          </button>
        </div>
      </nav>

      <style>{`
        .hamburger-button {
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          padding: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          transition: all 0.2s ease;
        }

        .hamburger-button:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        .hamburger-icon {
          width: 20px;
          height: 14px;
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .hamburger-icon span {
          display: block;
          height: 2px;
          width: 100%;
          background: white;
          border-radius: 1px;
          transition: all 0.3s ease;
        }

        .hamburger-icon.open span:nth-child(1) {
          transform: rotate(45deg) translate(4px, 4px);
        }

        .hamburger-icon.open span:nth-child(2) {
          opacity: 0;
        }

        .hamburger-icon.open span:nth-child(3) {
          transform: rotate(-45deg) translate(4px, -4px);
        }

        .menu-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          z-index: 1998;
          animation: fadeIn 0.1s ease;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .slide-menu {
          position: fixed;
          top: 0;
          right: -280px;
          width: 280px;
          height: 100vh;
          background: white;
          box-shadow: none;
          z-index: 1999;
          transition: right 0.15s ease-out;
          display: flex;
          flex-direction: column;
        }

        .slide-menu.open {
          right: 0;
          box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
        }

        .menu-header {
          background: linear-gradient(135deg, var(--primary-green) 0%, var(--secondary-green) 100%);
          color: white;
          padding: 1.5rem;
          padding-top: 2rem;
        }

        .menu-user-info {
          margin-top: 0.5rem;
        }

        .menu-user-name {
          font-size: 1.1rem;
          font-weight: 600;
        }

        .menu-user-role {
          font-size: 0.85rem;
          opacity: 0.85;
          margin-top: 0.25rem;
        }

        .menu-items {
          flex: 1;
          padding: 1rem 0;
          overflow-y: auto;
        }

        .menu-item {
          display: flex;
          align-items: center;
          padding: 1rem 1.5rem;
          text-decoration: none;
          color: var(--text-dark);
          transition: all 0.2s ease;
          position: relative;
        }

        .menu-item:hover {
          background: #f5f5f5;
        }

        .menu-item.active {
          background: rgba(45, 80, 22, 0.1);
          color: var(--primary-green);
        }

        .menu-item-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 1rem;
          width: 28px;
          height: 28px;
        }

        .menu-item-icon svg {
          display: block;
        }

        .menu-item-label {
          font-size: 1rem;
          font-weight: 500;
        }

        .menu-item-indicator {
          position: absolute;
          left: 0;
          top: 50%;
          transform: translateY(-50%);
          width: 4px;
          height: 60%;
          background: var(--primary-green);
          border-radius: 0 2px 2px 0;
        }

        .menu-footer {
          border-top: 1px solid #e0e0e0;
          padding: 1rem;
        }

        .menu-logout-btn {
          display: flex;
          align-items: center;
          width: 100%;
          padding: 0.875rem 1rem;
          background: #f5f5f5;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 1rem;
          color: #666;
          transition: all 0.2s ease;
        }

        .menu-logout-btn:hover {
          background: #e8e8e8;
          color: #333;
        }

        .menu-logout-btn .menu-item-icon {
          margin-right: 0.75rem;
        }

        /* Dark theme overrides for ElevenUp */
        .elevenup-theme .slide-menu {
          background: #242424;
          box-shadow: -4px 0 20px rgba(0, 0, 0, 0.5);
        }

        .elevenup-theme .menu-header {
          background: linear-gradient(135deg, #00E676 0%, #00BCD4 100%);
        }

        .elevenup-theme .menu-item {
          color: #ffffff;
        }

        .elevenup-theme .menu-item:hover {
          background: #333333;
        }

        .elevenup-theme .menu-item.active {
          background: rgba(0, 230, 118, 0.15);
          color: #00E676;
        }

        .elevenup-theme .menu-item-indicator {
          background: #00E676;
        }

        /* Icons use elevenup color scheme in dark theme - handled by component props */

        .elevenup-theme .menu-footer {
          border-top-color: #404040;
        }

        .elevenup-theme .menu-logout-btn {
          background: #333333;
          color: #b0b0b0;
        }

        .elevenup-theme .menu-logout-btn:hover {
          background: #404040;
          color: #ffffff;
        }

        .elevenup-theme .menu-overlay {
          background: rgba(0, 0, 0, 0.7);
        }
      `}</style>
    </>
  );
}

export default HamburgerMenu;
