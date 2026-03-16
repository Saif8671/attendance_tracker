import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api.js';

export default function Signup() {
  const [role, setRole] = useState('student');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(form.entries());

    try {
      const data = await apiFetch('/api/auth/signup', {
        method: 'POST',
        body: payload,
      });
      if (data && data.role) {
        navigate(`/${data.role}`);
        return;
      }
      navigate('/');
    } catch (err) {
      setError(err.data?.error || 'Signup failed');
    }
  };

  return (
    <div className="login-shell">
      <div className="login-brand">
        <h1>AttendX</h1>
        <p style={{ fontSize: '1.05rem' }}>Create your account and start tracking attendance</p>
        <div style={{ marginTop: 48, display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'center', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--subtle)' }}>
            <span style={{ fontSize: '1.3rem' }}>🧑‍🏫</span>
            <span>Faculty generate QR sessions in seconds</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--subtle)' }}>
            <span style={{ fontSize: '1.3rem' }}>🎓</span>
            <span>Students scan to mark attendance instantly</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--subtle)' }}>
            <span style={{ fontSize: '1.3rem' }}>📈</span>
            <span>Track progress and receive alerts</span>
          </div>
        </div>
      </div>

      <div className="login-card">
        <h2>Create account</h2>
        <p className="subtitle">Register as a student or faculty member</p>

        {error && <div className="notice error">{error}</div>}

        <form className="stack" onSubmit={onSubmit}>
          <div className="form-group">
            <label>Role</label>
            <select name="role" id="role" required value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="">Select a role</option>
              <option value="student">Student</option>
              <option value="faculty">Faculty</option>
            </select>
          </div>

          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Full Name</label>
            <input type="text" name="name" required placeholder="Enter your full name" autoComplete="name" />
          </div>

          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Username</label>
            <input type="text" name="username" required placeholder="Choose a username" autoComplete="username" />
          </div>

          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Password</label>
            <input type="password" name="password" required placeholder="Create a password" autoComplete="new-password" />
          </div>

          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Confirm Password</label>
            <input type="password" name="confirm_password" required placeholder="Re-enter your password" autoComplete="new-password" />
          </div>

          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Email (optional)</label>
            <input type="email" name="email" placeholder="you@example.com" autoComplete="email" />
          </div>

          <div className="form-group" style={{ marginTop: 0 }}>
            <label>Phone (optional)</label>
            <input type="text" name="phone" placeholder="+1234567890" autoComplete="tel" />
          </div>

          {role === 'student' && (
            <>
              <div className="form-group" style={{ marginTop: 0 }}>
                <label>Class Name</label>
                <input type="text" name="class_name" placeholder="e.g., CSE-A" />
              </div>

              <div className="form-group" style={{ marginTop: 0 }}>
                <label>Roll No (optional)</label>
                <input type="text" name="rollno" placeholder="e.g., 42" />
              </div>
            </>
          )}

          <button className="btn full lg" type="submit" style={{ marginTop: 6 }}>Create Account →</button>
        </form>

        <p className="muted" style={{ textAlign: 'center', marginTop: 24 }}>
          Already have an account? <a href="/">Sign in</a>
        </p>
      </div>
    </div>
  );
}
