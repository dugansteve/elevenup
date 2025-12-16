import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import './App.css';

// Import components
import AuthGate from './components/AuthGate';
import Rankings from './components/Rankings';
import Clubs from './components/Clubs';
import ClubProfile from './components/ClubProfile';
import TeamProfile from './components/TeamProfile';
import Players from './components/Players';
import Badges from './components/Badges';
import PlayerProfile from './components/PlayerProfile';

// Import context
import { UserProvider, useUser, ACCOUNT_TYPES } from './context/UserContext';

// Navigation component that uses useLocation for proper URL-based highlighting
function Navigation() {
  const location = useLocation();
  const currentPath = location.pathname;
  const { user, logout, isPaid, isFree, isGuest } = useUser();

  // Get account badge style
  const getAccountBadge = () => {
    if (isPaid) {
      return {
        text: '⭐ Pro',
        background: 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)',
        color: 'white'
      };
    }
    if (isFree) {
      return {
        text: '🌱 Free',
        background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
        color: 'var(--primary-green)'
      };
    }
    return {
      text: '👤 Guest',
      background: '#f5f5f5',
      color: '#666'
    };
  };

  const badge = getAccountBadge();

  return (
    <header className="app-header">
      <div className="header-top">
        <div className="logo-section">
          <img 
            src="/seedline-logo.png" 
            alt="Seedline" 
            className="logo"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
        
        <div className="user-section">
          <div className="user-info">
            <div className="user-name">{user.name}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                padding: '0.2rem 0.5rem',
                borderRadius: '12px',
                fontSize: '0.7rem',
                fontWeight: '600',
                background: badge.background,
                color: badge.color
              }}>
                {badge.text}
              </span>
              {!isGuest && (
                <span className="user-role">{user.role}</span>
              )}
            </div>
          </div>
          <button onClick={logout} className="logout-btn">
            Logout
          </button>
        </div>
      </div>
      
      <nav className="main-nav">
        <Link 
          to="/rankings" 
          className={`nav-item ${currentPath === '/rankings' || currentPath === '/' ? 'active' : ''}`}
        >
          <span className="nav-icon">🏆 </span>Rankings
        </Link>
        <Link 
          to="/clubs" 
          className={`nav-item ${currentPath === '/clubs' || currentPath.startsWith('/club/') ? 'active' : ''}`}
        >
          <span className="nav-icon">⚽ </span>Clubs
        </Link>
        <Link 
          to="/players" 
          className={`nav-item ${currentPath === '/players' || currentPath.startsWith('/player/') ? 'active' : ''}`}
        >
          <span className="nav-icon">👥 </span>Players
        </Link>
        <Link 
          to="/badges" 
          className={`nav-item ${currentPath === '/badges' ? 'active' : ''}`}
        >
          <span className="nav-icon">🎖️ </span>Badges
        </Link>
      </nav>
    </header>
  );
}

// Main App content (needs to be inside UserProvider)
function AppContent() {
  const { user, login } = useUser();

  if (!user) {
    return <AuthGate onLogin={login} />;
  }

  return (
    <Router>
      <div className="app">
        {/* Modern Navigation Header */}
        <Navigation />

        {/* Main Content */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/rankings" replace />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/clubs" element={<Clubs />} />
            <Route path="/club/:clubName" element={<ClubProfile />} />
            <Route path="/team/:teamId" element={<TeamProfile />} />
            <Route path="/players" element={<Players />} />
            <Route path="/badges" element={<Badges />} />
            <Route path="/player/:playerId" element={<PlayerProfile />} />
            {/* Redirect old routes to new ones */}
            <Route path="/my-players" element={<Navigate to="/players" replace />} />
            <Route path="/my-badges" element={<Navigate to="/badges" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function App() {
  return (
    <UserProvider>
      <AppContent />
    </UserProvider>
  );
}

export default App;
