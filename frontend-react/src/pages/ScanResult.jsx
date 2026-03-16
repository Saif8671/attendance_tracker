import React from 'react';
import { useLocation } from 'react-router-dom';

export default function ScanResult() {
  const location = useLocation();
  const state = location.state || {};
  const success = state.success === true;
  const subject = state.subject || '';
  const label = state.label || '';
  const msg = state.msg || 'Session expired or already marked.';

  return (
    <div className="result-shell">
      <div className="result-card">
        {success ? (
          <>
            <span className="result-icon">✅</span>
            <h2 style={{ color: '#6ee7b7', marginBottom: 10 }}>Attendance Marked!</h2>
            <p style={{ fontSize: '1.05rem', marginBottom: 6 }}><strong style={{ color: 'var(--text)' }}>{subject}</strong></p>
            {label && <p className="muted" style={{ marginBottom: 20 }}>Session: {label}</p>}
            <div className="notice" style={{ marginBottom: 20 }}>Your attendance has been successfully recorded.</div>
          </>
        ) : (
          <>
            <span className="result-icon">❌</span>
            <h2 style={{ color: '#fca5a5', marginBottom: 10 }}>Unable to Mark</h2>
            <div className="notice error" style={{ marginBottom: 20 }}>{msg}</div>
          </>
        )}
        <a className="btn full" href="/student">← Back to Dashboard</a>
      </div>
    </div>
  );
}
