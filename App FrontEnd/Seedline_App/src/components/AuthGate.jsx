import { useState } from 'react';
import { ACCOUNT_TYPES } from '../context/UserContext';

// Admin server URL - port 5050 for admin server
const ADMIN_API = 'http://localhost:5050/api';

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

    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password');
      setLoading(false);
      return;
    }

    try {
      // Call admin server to authenticate
      const response = await fetch(`${ADMIN_API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password: password.trim() })
      });

      const data = await response.json();

      if (data.success && data.user) {
        // Login successful - storage is now user-specific so data loads automatically
        onLogin({
          id: data.user.id || data.user.username,
          name: data.user.username,
          username: data.user.username,
          email: data.user.email,
          role: data.user.role || 'Parent',
          accountType: data.user.account_type === 'pro' ? ACCOUNT_TYPES.PAID : 
                       data.user.account_type === 'free' ? ACCOUNT_TYPES.FREE : ACCOUNT_TYPES.FREE,
          createdAt: data.user.created_at || new Date().toISOString()
        });
      } else {
        setError(data.error || 'Invalid username or password');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Unable to connect to server. Please try again.');
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
      const response = await fetch(`${ADMIN_API}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          password: password.trim(),
          account_type: accountType === ACCOUNT_TYPES.PAID ? 'pro' : 'free',
          role: role
        })
      });

      const data = await response.json();

      if (data.success) {
        setSuccess('Account created! Please sign in.');
        setMode('login');
        setPassword('');
        setConfirmPassword('');
      } else {
        setError(data.error || 'Could not create account');
      }
    } catch (err) {
      console.error('Signup error:', err);
      setError('Unable to connect to server. Please try again.');
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
      const response = await fetch(`${ADMIN_API}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() })
      });

      const data = await response.json();

      if (data.success) {
        setSuccess('If an account exists with this email, a password reset link has been sent.');
      } else {
        setSuccess('If an account exists with this email, a password reset link has been sent.');
      }
    } catch (err) {
      setSuccess('If an account exists with this email, a password reset link has been sent.');
    }

    setLoading(false);
  };

  // Welcome screen
  if (mode === 'welcome') {
    return (
      <div className="auth-container">
        <div className="auth-card" style={{ maxWidth: '500px' }}>
          <div className="auth-logo">
            <img src="/seedline-logo.png" alt="Seedline Logo" onError={(e) => e.target.style.display = 'none'} />
          </div>
          
          <h1 className="auth-title">Welcome to Seedline</h1>
          <p className="auth-subtitle">Soccer Rankings & Player Badge Management</p>
          
          <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Guest Button */}
            <button onClick={handleGuestLogin} style={{
              padding: '1rem 1.5rem', background: '#f5f5f5', border: '2px solid #e0e0e0',
              borderRadius: '12px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s ease'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '1.1rem', color: '#333' }}>👤 Continue as Guest</div>
                  <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>Browse rankings (no saved data)</div>
                </div>
                <span style={{ fontSize: '1.5rem', color: '#999' }}>→</span>
              </div>
            </button>

            {/* Sign In Button */}
            <button onClick={() => setMode('login')} style={{
              padding: '1rem 1.5rem', background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
              border: '2px solid #1976d2', borderRadius: '12px', cursor: 'pointer', textAlign: 'left'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '1.1rem', color: '#1976d2' }}>🔐 Sign In</div>
                  <div style={{ fontSize: '0.85rem', color: '#555', marginTop: '0.25rem' }}>Access your saved players and badges</div>
                </div>
                <span style={{ fontSize: '1.5rem', color: '#1976d2' }}>→</span>
              </div>
            </button>

            {/* Free Account Button */}
            <button onClick={() => { setAccountType(ACCOUNT_TYPES.FREE); setMode('signup'); }} style={{
              padding: '1rem 1.5rem', background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
              border: '2px solid var(--accent-green)', borderRadius: '12px', cursor: 'pointer', textAlign: 'left'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '1.1rem', color: 'var(--primary-green)' }}>🌱 Create Free Account</div>
                  <div style={{ fontSize: '0.85rem', color: '#555', marginTop: '0.25rem' }}>Browse + save up to 5 teams</div>
                </div>
                <span style={{ background: '#fff', padding: '0.25rem 0.75rem', borderRadius: '20px', fontSize: '0.85rem', fontWeight: '600', color: 'var(--primary-green)' }}>FREE</span>
              </div>
            </button>

            {/* Pro Account Button */}
            <button onClick={() => { setAccountType(ACCOUNT_TYPES.PAID); setMode('signup'); }} style={{
              padding: '1rem 1.5rem', background: 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)',
              border: 'none', borderRadius: '12px', cursor: 'pointer', textAlign: 'left', color: 'white'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '1.1rem' }}>⭐ Create Pro Account</div>
                  <div style={{ fontSize: '0.85rem', opacity: 0.9, marginTop: '0.25rem' }}>Full access: badges, players & more</div>
                </div>
                <span style={{ background: 'rgba(255,255,255,0.2)', padding: '0.25rem 0.75rem', borderRadius: '20px', fontSize: '0.85rem', fontWeight: '600' }}>PRO</span>
              </div>
            </button>
          </div>

          {/* Feature Comparison */}
          <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#f8f9fa', borderRadius: '12px', fontSize: '0.85rem' }}>
            <h3 style={{ fontWeight: '600', marginBottom: '1rem', color: '#333', fontSize: '0.95rem' }}>Compare Account Types</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '2px solid #ddd' }}>Feature</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', borderBottom: '2px solid #ddd', width: '60px' }}>Guest</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', borderBottom: '2px solid #ddd', width: '60px' }}>Free</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', borderBottom: '2px solid #ddd', width: '60px' }}>Pro</th>
                </tr>
              </thead>
              <tbody>
                <tr><td style={{ padding: '0.5rem', color: '#555' }}>Browse rankings</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td></tr>
                <tr style={{ background: '#fff' }}><td style={{ padding: '0.5rem', color: '#555' }}>Save My Teams</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td></tr>
                <tr><td style={{ padding: '0.5rem', color: '#555' }}>Claim players</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td></tr>
                <tr style={{ background: '#fff' }}><td style={{ padding: '0.5rem', color: '#555' }}>Award badges</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td></tr>
                <tr><td style={{ padding: '0.5rem', color: '#555' }}>Submit scores</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#ccc' }}>—</td><td style={{ textAlign: 'center', color: '#4caf50' }}>✓</td></tr>
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
        <div className="auth-card">
          <div className="auth-logo">
            <img src="/seedline-logo.png" alt="Seedline Logo" onError={(e) => e.target.style.display = 'none'} />
          </div>
          
          <h1 className="auth-title">Welcome Back</h1>
          <p className="auth-subtitle">Sign in to your account</p>
          
          {error && <div style={{ padding: '0.75rem 1rem', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
          {success && <div style={{ padding: '0.75rem 1rem', background: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>{success}</div>}
          
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input type="text" className="form-input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" required />
            </div>
            
            <div className="form-group">
              <label className="form-label">Password</label>
              <input type="password" className="form-input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" required />
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
              {loading ? 'Signing In...' : 'Sign In'}
            </button>
          </form>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '1rem', fontSize: '0.85rem' }}>
            <button onClick={() => { setMode('forgot-username'); setError(''); setSuccess(''); }} style={{ background: 'none', border: 'none', color: 'var(--primary-green)', cursor: 'pointer' }}>Forgot Username?</button>
            <span style={{ color: '#ccc' }}>|</span>
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
      <div className="auth-card">
        <div className="auth-logo">
          <img src="/seedline-logo.png" alt="Seedline Logo" onError={(e) => e.target.style.display = 'none'} />
        </div>
        
        <h1 className="auth-title">{accountType === ACCOUNT_TYPES.PAID ? 'Create Pro Account' : 'Create Free Account'}</h1>
        <p className="auth-subtitle">{accountType === ACCOUNT_TYPES.PAID ? 'Full access to all features' : 'Browse and save your favorite teams'}</p>

        <div style={{ display: 'inline-block', padding: '0.5rem 1rem', borderRadius: '20px', fontWeight: '600', fontSize: '0.85rem', marginBottom: '1.5rem',
          background: accountType === ACCOUNT_TYPES.PAID ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)' : 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
          color: accountType === ACCOUNT_TYPES.PAID ? 'white' : 'var(--primary-green)' }}>
          {accountType === ACCOUNT_TYPES.PAID ? '⭐ Pro Account' : '🌱 Free Account'}
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
