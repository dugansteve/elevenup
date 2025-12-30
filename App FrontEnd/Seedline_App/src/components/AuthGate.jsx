import { useState } from 'react';
import { ACCOUNT_TYPES } from '../context/UserContext';
import { firebaseSignIn, firebaseSignUp, firebaseResetPassword } from '../config/firebase';
import { currentBrand, isElevenUpBrand } from '../config/brand';

// Admin server API for local development (account type lookup)
// Set VITE_ADMIN_API in .env for local dev, leave empty for production
const ADMIN_API = import.meta.env.VITE_ADMIN_API || '';

function AuthGate({ onLogin }) {
  const [mode, setMode] = useState('welcome'); // welcome, login, signup, forgot-username, forgot-password
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('Parent');
  const [accountType, setAccountType] = useState(ACCOUNT_TYPES.FREE);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGuestLogin = () => {
    // Guest login - the UserContext and storage system handle clearing data
    onLogin({
      id: 'guest_' + Date.now(),
      name: 'Guest',
      username: 'guest',
      role: 'Visitor',
      accountType: ACCOUNT_TYPES.GUEST,
      createdAt: new Date().toISOString()
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // For Firebase Auth, we use email to login (username field accepts email)
    const loginEmail = email.trim() || username.trim();

    if (!loginEmail || !password.trim()) {
      setError('Please enter email and password');
      setLoading(false);
      return;
    }

    try {
      const user = await firebaseSignIn(loginEmail, password.trim());

      // Look up account type from admin server (for local development)
      let accountType = ACCOUNT_TYPES.FREE; // Default to free
      if (ADMIN_API) {
        try {
          // Add 3-second timeout to prevent slow logins if admin server is down
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 3000);

          const lookupResponse = await fetch(
            `${ADMIN_API}/user/lookup?email=${encodeURIComponent(user.email)}`,
            { signal: controller.signal }
          );
          clearTimeout(timeoutId);

          if (lookupResponse.ok) {
            const lookupData = await lookupResponse.json();
            if (lookupData.found) {
              // Map admin server account_type to app ACCOUNT_TYPES
              const typeMap = {
                'pro': ACCOUNT_TYPES.PAID,
                'paid': ACCOUNT_TYPES.PAID,
                'admin': ACCOUNT_TYPES.ADMIN,
                'coach': ACCOUNT_TYPES.COACH,
                'free': ACCOUNT_TYPES.FREE
              };
              accountType = typeMap[lookupData.account_type] || ACCOUNT_TYPES.FREE;
              console.log(`User ${user.email} account type: ${lookupData.account_type} -> ${accountType}`);
            }
          }
        } catch (lookupErr) {
          // Admin server not available or timed out, use default
          console.log('Account lookup not available, using free tier');
        }
      }

      // Login successful - use Firebase UID as stable userId to ensure consistent storage keys
      onLogin({
        id: user.uid,
        userId: user.uid,  // CRITICAL: Use Firebase UID as stable userId for localStorage keys
        name: user.displayName || loginEmail.split('@')[0],
        username: user.displayName || loginEmail.split('@')[0],
        email: user.email,
        role: role || 'Parent',
        accountType: accountType,
        createdAt: user.metadata.creationTime || new Date().toISOString()
      });
    } catch (err) {
      console.error('Login error:', err);
      // Firebase Auth error codes
      if (err.code === 'auth/user-not-found') {
        setError('No account found with this email');
      } else if (err.code === 'auth/wrong-password') {
        setError('Incorrect password');
      } else if (err.code === 'auth/invalid-email') {
        setError('Please enter a valid email address');
      } else if (err.code === 'auth/invalid-credential') {
        setError('Invalid email or password');
      } else {
        setError(err.message || 'Login failed. Please try again.');
      }
    }

    setLoading(false);
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!username.trim() || !email.trim() || !password.trim()) {
      setError('Please fill in all fields');
      setLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      setLoading(false);
      return;
    }

    try {
      const user = await firebaseSignUp(email.trim(), password.trim(), username.trim());

      // Auto-login after signup - use Firebase UID as stable userId
      onLogin({
        id: user.uid,
        userId: user.uid,  // CRITICAL: Use Firebase UID as stable userId for localStorage keys
        name: username.trim(),
        username: username.trim(),
        email: user.email,
        role: role || 'Parent',
        accountType: accountType,
        createdAt: new Date().toISOString()
      });
    } catch (err) {
      console.error('Signup error:', err);
      // Firebase Auth error codes
      if (err.code === 'auth/email-already-in-use') {
        setError('An account with this email already exists');
      } else if (err.code === 'auth/invalid-email') {
        setError('Please enter a valid email address');
      } else if (err.code === 'auth/weak-password') {
        setError('Password is too weak. Use at least 6 characters.');
      } else {
        setError(err.message || 'Could not create account. Please try again.');
      }
    }

    setLoading(false);
  };

  const handleForgotUsername = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    if (!email.trim()) {
      setError('Please enter your email address');
      setLoading(false);
      return;
    }

    if (!ADMIN_API) {
      // Admin server not configured, show generic success message
      setSuccess('If an account exists with this email, the username has been sent.');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${ADMIN_API}/auth/forgot-username`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() })
      });

      const data = await response.json();

      if (data.success) {
        setSuccess('If an account exists with this email, the username has been sent.');
      } else {
        // Still show success message to prevent email enumeration
        setSuccess('If an account exists with this email, the username has been sent.');
      }
    } catch (err) {
      setSuccess('If an account exists with this email, the username has been sent.');
    }

    setLoading(false);
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    if (!email.trim()) {
      setError('Please enter your email address');
      setLoading(false);
      return;
    }

    try {
      await firebaseResetPassword(email.trim());
      setSuccess('Password reset email sent! Check your inbox.');
    } catch (err) {
      console.error('Password reset error:', err);
      if (err.code === 'auth/user-not-found') {
        // Don't reveal if email exists for security
        setSuccess('If an account exists with this email, a password reset link has been sent.');
      } else if (err.code === 'auth/invalid-email') {
        setError('Please enter a valid email address');
      } else {
        setSuccess('If an account exists with this email, a password reset link has been sent.');
      }
    }

    setLoading(false);
  };

  // Welcome screen
  if (mode === 'welcome') {
    return (
      <div className="auth-container">
        <div className="auth-logo-outside">
          <img src={currentBrand.logo} alt={`${currentBrand.name} Logo`} onError={(e) => e.target.style.display = 'none'} />
        </div>
        <div className="auth-card auth-welcome-card">
          <h1 className="auth-title">Welcome to {currentBrand.name}</h1>
          <p className="auth-subtitle">Soccer Rankings & Player Badge Management</p>

          <div className="auth-buttons">
            {/* Guest Button */}
            <button onClick={handleGuestLogin} className="auth-option-btn auth-option-guest">
              <div className="auth-option-content">
                <div>
                  <div className="auth-option-title">Continue as Guest</div>
                  <div className="auth-option-desc">Browse rankings (no saved data)</div>
                </div>
                <span className="auth-option-arrow">→</span>
              </div>
            </button>

            {/* Sign In Button */}
            <button onClick={() => setMode('login')} className="auth-option-btn auth-option-signin">
              <div className="auth-option-content">
                <div>
                  <div className="auth-option-title" style={{ color: '#1976d2' }}>Sign In</div>
                  <div className="auth-option-desc">Access your saved players and badges</div>
                </div>
                <span className="auth-option-arrow" style={{ color: '#1976d2' }}>→</span>
              </div>
            </button>

            {/* Free Account Button */}
            <button onClick={() => { setAccountType(ACCOUNT_TYPES.FREE); setMode('signup'); }} className="auth-option-btn auth-option-free">
              <div className="auth-option-content">
                <div>
                  <div className="auth-option-title" style={{ color: 'var(--primary-green)' }}>Create Free Account</div>
                  <div className="auth-option-desc">Browse + save up to 5 teams</div>
                </div>
                <span className="auth-option-badge auth-badge-free">FREE</span>
              </div>
            </button>

            {/* Pro Account Button */}
            <button onClick={() => { setAccountType(ACCOUNT_TYPES.PAID); setMode('signup'); }} className="auth-option-btn auth-option-pro">
              <div className="auth-option-content">
                <div>
                  <div className="auth-option-title">Create Pro Account</div>
                  <div className="auth-option-desc">Full access: badges, players & more</div>
                </div>
                <span className="auth-option-badge auth-badge-pro">PRO</span>
              </div>
            </button>
          </div>

          {/* Feature Comparison */}
          <div className="auth-comparison">
            <h3 className="auth-comparison-title">Compare Account Types</h3>
            <table className="auth-comparison-table">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Feature</th>
                  <th>Guest</th>
                  <th>Free</th>
                  <th>Pro</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>Browse rankings</td><td className="check">✓</td><td className="check">✓</td><td className="check">✓</td></tr>
                <tr><td>Save My Teams</td><td className="dash">—</td><td className="check">✓</td><td className="check">✓</td></tr>
                <tr><td>Claim players</td><td className="dash">—</td><td className="dash">—</td><td className="check">✓</td></tr>
                <tr><td>Award badges</td><td className="dash">—</td><td className="dash">—</td><td className="check">✓</td></tr>
                <tr><td>Submit scores</td><td className="dash">—</td><td className="dash">—</td><td className="check">✓</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // Forgot Username
  if (mode === 'forgot-username') {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1 className="auth-title">Forgot Username</h1>
          <p className="auth-subtitle">Enter your email and we'll send your username</p>
          
          {error && <div style={{ padding: '0.75rem 1rem', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
          {success && <div style={{ padding: '0.75rem 1rem', background: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{success}</div>}
          
          <form onSubmit={handleForgotUsername}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input type="email" className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email" required />
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'Sending...' : 'Send Username'}
            </button>
          </form>

          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1.5rem' }}>
            <button onClick={() => { setMode('login'); setError(''); setSuccess(''); }} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer' }}>← Back to Sign In</button>
          </div>
        </div>
      </div>
    );
  }

  // Forgot Password
  if (mode === 'forgot-password') {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1 className="auth-title">Reset Password</h1>
          <p className="auth-subtitle">Enter your email and we'll send a reset link</p>
          
          {error && <div style={{ padding: '0.75rem 1rem', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
          {success && <div style={{ padding: '0.75rem 1rem', background: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{success}</div>}
          
          <form onSubmit={handleForgotPassword}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input type="email" className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email" required />
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </form>

          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1.5rem' }}>
            <button onClick={() => { setMode('login'); setError(''); setSuccess(''); }} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer' }}>← Back to Sign In</button>
          </div>
        </div>
      </div>
    );
  }

  // Login Form
  if (mode === 'login') {
    return (
      <div className="auth-container">
        <div className="auth-logo-outside">
          <img src={currentBrand.logo} alt={`${currentBrand.name} Logo`} onError={(e) => e.target.style.display = 'none'} />
        </div>
        <div className="auth-card">
          <h1 className="auth-title">Welcome Back</h1>
          <p className="auth-subtitle">Sign in to your account</p>
          
          {error && <div style={{ padding: '0.75rem 1rem', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
          {success && <div style={{ padding: '0.75rem 1rem', background: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{success}</div>}
          
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input type="email" className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email" required />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input type="password" className="form-input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" required />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
              {loading ? 'Signing In...' : 'Sign In'}
            </button>
          </form>

          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1rem', fontSize: '0.85rem' }}>
            <button onClick={() => { setMode('forgot-password'); setError(''); setSuccess(''); }} style={{ background: 'none', border: 'none', color: 'var(--primary-green)', cursor: 'pointer' }}>Forgot Password?</button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginTop: '1.5rem', fontSize: '0.85rem' }}>
            <button onClick={() => setMode('welcome')} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer' }}>← Back</button>
            <button onClick={() => setMode('signup')} style={{ background: 'none', border: 'none', color: 'var(--primary-green)', cursor: 'pointer', fontWeight: '600' }}>Create Account</button>
          </div>
        </div>
      </div>
    );
  }

  // Signup Form
  return (
    <div className="auth-container">
      <div className="auth-logo-outside">
        <img src={currentBrand.logo} alt={`${currentBrand.name} Logo`} onError={(e) => e.target.style.display = 'none'} />
      </div>
      <div className="auth-card">
        <h1 className="auth-title">{accountType === ACCOUNT_TYPES.PAID ? 'Create Pro Account' : 'Create Free Account'}</h1>
        <p className="auth-subtitle">{accountType === ACCOUNT_TYPES.PAID ? 'Full access to all features' : 'Browse and save your favorite teams'}</p>

        <div style={{ display: 'inline-block', padding: '0.5rem 1rem', borderRadius: '20px', fontWeight: '600', fontSize: '0.85rem', marginBottom: '1.5rem',
          background: accountType === ACCOUNT_TYPES.PAID ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)' : 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
          color: accountType === ACCOUNT_TYPES.PAID ? 'white' : 'var(--primary-green)' }}>
          {accountType === ACCOUNT_TYPES.PAID ? (isElevenUpBrand ? '★ Pro Account' : '⭐ Pro Account') : '🌱 Free Account'}
        </div>
        
        {error && <div style={{ padding: '0.75rem 1rem', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
        
        <form onSubmit={handleSignup}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input type="text" className="form-input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Choose a username" required />
          </div>
          
          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="email" className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email" required />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input type="password" className="form-input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a password (min 6 chars)" required />
          </div>

          <div className="form-group">
            <label className="form-label">Confirm Password</label>
            <input type="password" className="form-input" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm your password" required />
          </div>
          
          <div className="form-group">
            <label className="form-label">I am a...</label>
            <select className="form-select" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="Parent">Parent</option>
              <option value="Player">Player</option>
              <option value="Coach">Coach</option>
              <option value="Scout">Scout</option>
            </select>
          </div>
          
          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
            {loading ? 'Creating...' : 'Create Account'}
          </button>
        </form>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginTop: '1.5rem', fontSize: '0.85rem' }}>
          <button onClick={() => setMode('welcome')} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer' }}>← Back</button>
          <button onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: 'var(--primary-green)', cursor: 'pointer', fontWeight: '600' }}>Sign In Instead</button>
        </div>
      </div>
    </div>
  );
}

export default AuthGate;
