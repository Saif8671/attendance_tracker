import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from '../api.js';

export default function QrDisplay() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [left, setLeft] = useState(0);
  const [closed, setClosed] = useState(false);

  useEffect(() => {
    apiFetch(`/api/qr/${token}`)
      .then((payload) => {
        setData(payload);
        const expires = payload.expires_at || 0;
        const now = Date.now() / 1000;
        setLeft(Math.max(0, Math.floor(expires - now)));
      })
      .catch(() => setData(null));
  }, [token]);

  useEffect(() => {
    if (!data) return undefined;
    const timer = setInterval(() => {
      const now = Date.now() / 1000;
      const remaining = Math.max(0, Math.floor((data.expires_at || 0) - now));
      setLeft(remaining);
      if (remaining <= 0 && !closed) {
        setClosed(true);
        apiFetch('/api/faculty/close_session', { method: 'POST', body: { token } }).catch(() => {});
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [data, token, closed]);

  const validSec = useMemo(() => {
    if (!data) return 120;
    return Math.max(1, Math.floor((data.expires_at || 0) - (data.created_at || 0)));
  }, [data]);

  const mins = String(Math.floor(left / 60)).padStart(2, '0');
  const secs = String(left % 60).padStart(2, '0');
  const circ = 2 * Math.PI * 44;
  const pct = validSec ? left / validSec : 0;
  const dash = circ * (1 - pct);
  const stroke = pct < 0.33 ? '#ef4444' : pct < 0.66 ? '#f59e0b' : '#7c3aed';

  if (!data) {
    return (
      <div className="qr-shell">
        <div className="qr-card">
          <div className="notice">Loading QR session…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="qr-shell">
      <div className="qr-card">
        <h2 style={{ marginBottom: 4 }}>📡 Live QR Session</h2>
        <p className="muted">Share this QR with students in <strong style={{ color: 'var(--text)' }}>{data.class_name}</strong></p>

        <div className="qr-info">
          <span className="qr-tag">{data.subject}</span>
          <span className="qr-tag">{data.class_name}</span>
          {data.session_label && <span className="qr-tag">{data.session_label}</span>}
        </div>

        <img src={`/qr_image/${data.token}`} alt="QR Code for attendance" style={{ width: 220, height: 220 }} />

        <div className="countdown-ring" id="countdownRing">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle className="cr-track" cx="50" cy="50" r="44" />
            <circle className="cr-fill" cx="50" cy="50" r="44" strokeDasharray={circ.toFixed(2)} strokeDashoffset={dash} style={{ stroke }} />
          </svg>
          <div className="cr-label">{left > 0 ? `${mins}:${secs}` : 'Done'}</div>
        </div>

        <p className="live-count">👥 Students scanned: <span id="scannedCount">—</span></p>
        <p className="muted" style={{ fontSize: '.82rem', marginTop: 8 }}>Session closes automatically when timer ends</p>

        <div style={{ marginTop: 20 }}>
          <a className="btn soft" href="/faculty">← Faculty Dashboard</a>
        </div>
      </div>
    </div>
  );
}
