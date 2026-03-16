import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api.js';

export default function StudentScanner() {
  const [token, setToken] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate();

  const submitToken = async () => {
    if (!token) return;
    setStatus('Submitting attendance…');
    try {
      const data = await apiFetch(`/api/scan/${encodeURIComponent(token)}`);
      navigate('/scan-result', { state: data });
    } catch (err) {
      navigate('/scan-result', { state: { success: false, msg: err.data?.error || 'Unable to mark attendance' } });
    }
  };

  return (
    <div className="scanner-shell">
      <div className="scanner-card">
        <h2 style={{ marginBottom: 6 }}>📷 Scan Attendance QR</h2>
        <p className="muted" style={{ marginBottom: 16 }}>Point your camera at the QR code shown by your faculty</p>

        <div id="reader" style={{ width: '100%', maxWidth: 360, margin: '0 auto' }}>
          <div className="notice" style={{ textAlign: 'center' }}>Camera preview placeholder</div>
        </div>

        <div style={{ marginTop: 16 }}>
          <input
            type="text"
            placeholder="Paste QR token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button className="btn full" type="button" style={{ marginTop: 8 }} onClick={submitToken}>Submit Token</button>
        </div>

        {status && <div id="scanStatus" className="notice" style={{ marginTop: 16 }}>{status}</div>}

        <div style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
          <a className="btn full" href="/student">← Back to Dashboard</a>
        </div>
      </div>
    </div>
  );
}
