import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api.js';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const fill = (u, p) => {
    setUsername(u);
    setPassword(p);
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: { username, password },
      });
      if (data && data.role) {
        navigate(`/${data.role}`);
        return;
      }
      navigate('/');
    } catch (err) {
      setError(err.data?.error || 'Login failed');
    }
  };

  return (
    <div className="login-shell">
      <div className="login-brand">
        <h1>AttendX</h1>
        <p style={{ fontSize: '1.05rem' }}>Smart QR-based attendance management for modern institutions</p>
        <div style={{ marginTop: 48, display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'center', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--subtle)' }}>
            <span style={{ fontSize: '1.3rem' }}>📲</span>
            <span>Students scan QR to mark attendance instantly</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--subtle)' }}>
            <span style={{ fontSize: '1.3rem' }}>📊</span>
            <span>Real-time dashboards for faculty &amp; admin</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--subtle)' }}>
            <span style={{ fontSize: '1.3rem' }}>📩</span>
            <span>Automatic SMS alerts for absent students</span>
          </div>
        </div>
      </div>

      <div className="login-card">
        <h2>Welcome back</h2>
        <p className="subtitle">Sign in to your AttendX account</p>

        {error && <div className="notice error">{error}</div>}

        <form className="stack" onSubmit={onSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              name="username"
              id="username"
              required
              placeholder="Enter your username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Password</label>
            <input
              type="password"
              name="password"
              id="password"
              required
              placeholder="Enter your password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn full lg" type="submit" style={{ marginTop: 6 }}>Sign In →</button>
        </form>

        <p className="muted" style={{ textAlign: 'center', marginTop: 24, marginBottom: 10 }}>Quick demo access</p>
        <div className="role-pills">
          <button className="role-pill" onClick={() => fill('admin', 'admin123')} type="button">🔒 Admin</button>
          <button className="role-pill" onClick={() => fill('faculty1', 'faculty123')} type="button">👨‍🏫 Faculty</button>
          <button className="role-pill" onClick={() => fill('student1', 'student123')} type="button">🎓 Student</button>
        </div>

        <p className="muted" style={{ textAlign: 'center', marginTop: 18 }}>
          New here? <a href="/signup">Create an account</a>
        </p>
      </div>
    </div>
  );
}
