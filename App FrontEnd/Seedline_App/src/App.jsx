import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import './App.css';

// Import centralized brand configuration (determined by VITE_BRAND env var at build time)
import { currentBrand, isElevenUpBrand } from './config/brand';

// Conditionally import ElevenUp branding CSS (loads after App.css to override)
if (isElevenUpBrand) {
  import('./App.elevenup.css');
  // Add class to body for CSS targeting
  document.body.classList.add('elevenup-theme');
}

// Set page title based on brand
document.title = currentBrand.htmlTitle;

// Import components - AuthGate and HamburgerMenu load immediately (needed for login/nav)
import AuthGate from './components/AuthGate';
import HamburgerMenu from './components/HamburgerMenu';
import { TeamsIcon, ClubsIcon, PlayersIcon, BadgesIcon } from './components/PaperIcons';

// Lazy load all other components - they only load when user navigates to them
const Rankings = lazy(() => import('./components/Rankings'));
const Clubs = lazy(() => import('./components/Clubs'));
const ClubProfile = lazy(() => import('./components/ClubProfile'));
const TeamProfile = lazy(() => import('./components/TeamProfile'));
const Players = lazy(() => import('./components/Players'));
const Badges = lazy(() => import('./components/Badges'));
const PlayerProfile = lazy(() => import('./components/PlayerProfile'));
const TournamentFinder = lazy(() => import('./components/TournamentFinder'));
const ConferenceSimulation = lazy(() => import('./components/ConferenceSimulation'));
const Settings = lazy(() => import('./components/Settings'));
const IconPreview = lazy(() => import('./components/IconPreview'));

// Loading fallback component
const PageLoader = () => (
  <div className="card" style={{ margin: '1rem', padding: '2rem', textAlign: 'center' }}>
    <div className="loading">Loading...</div>
  </div>
);

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
            src={currentBrand.logo}
            alt={currentBrand.name}
            className="logo"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
          {currentBrand.tagline && (
            <span className="brand-tagline">{currentBrand.tagline}</span>
          )}
        </div>
        
        <div className="user-section">
          <div className="user-info hide-mobile">
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
          <HamburgerMenu />
        </div>
      </div>
      
      <nav className="main-nav">
        <Link
          to="/rankings"
          className={`nav-item ${currentPath === '/rankings' || currentPath === '/' ? 'active' : ''}`}
        >
          <span className="nav-icon"><TeamsIcon size={18} color="green" /></span>Teams
        </Link>
        <Link
          to="/clubs"
          className={`nav-item ${currentPath === '/clubs' || currentPath.startsWith('/club/') ? 'active' : ''}`}
        >
          <span className="nav-icon"><ClubsIcon size={18} color="green" /></span>Clubs
        </Link>
        <Link
          to="/players"
          className={`nav-item ${currentPath === '/players' || currentPath.startsWith('/player/') ? 'active' : ''}`}
        >
          <span className="nav-icon"><PlayersIcon size={18} color="green" /></span>Players
        </Link>
        <Link
          to="/badges"
          className={`nav-item ${currentPath === '/badges' ? 'active' : ''}`}
        >
          <span className="nav-icon"><BadgesIcon size={18} color="green" /></span>Badges
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

        {/* Main Content - wrapped in Suspense for lazy loading */}
        <main className="main-content">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Navigate to="/rankings" replace />} />
              <Route path="/rankings" element={<Rankings />} />
              <Route path="/clubs" element={<Clubs />} />
              <Route path="/club/:clubName" element={<ClubProfile />} />
              <Route path="/team/:teamId" element={<TeamProfile />} />
              <Route path="/players" element={<Players />} />
              <Route path="/badges" element={<Badges />} />
              <Route path="/player/:playerId" element={<PlayerProfile />} />
              <Route path="/tournaments" element={<TournamentFinder />} />
              <Route path="/simulation" element={<ConferenceSimulation />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/icon-preview" element={<IconPreview />} />
              {/* Redirect old routes to new ones */}
              <Route path="/my-players" element={<Navigate to="/players" replace />} />
              <Route path="/my-badges" element={<Navigate to="/badges" replace />} />
            </Routes>
          </Suspense>
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
