import React, { useEffect, useState } from 'react';

const VALID_SEC = 120;
const CIRC = 2 * Math.PI * 44;

export default function QrDisplay() {
  const [left, setLeft] = useState(VALID_SEC);
  const [scanned, setScanned] = useState(18);

  useEffect(() => {
    const timer = setInterval(() => {
      setLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    const poll = setInterval(() => {
      setScanned((prev) => prev + (Math.random() > 0.7 ? 1 : 0));
    }, 5000);
    return () => {
      clearInterval(timer);
      clearInterval(poll);
    };
  }, []);

  const mins = String(Math.floor(left / 60)).padStart(2, '0');
  const secs = String(left % 60).padStart(2, '0');
  const pct = left / VALID_SEC;
  const dash = CIRC * (1 - pct);
  const stroke = pct < 0.33 ? '#ef4444' : pct < 0.66 ? '#f59e0b' : '#7c3aed';

  return (
    <div className="qr-shell">
      <div className="qr-card">
        <h2 style={{ marginBottom: 4 }}>📡 Live QR Session</h2>
        <p className="muted">Share this QR with students in <strong style={{ color: 'var(--text)' }}>CSE-Y3</strong></p>

        <div className="qr-info">
          <span className="qr-tag">Data Structures</span>
          <span className="qr-tag">CSE-Y3</span>
          <span className="qr-tag">Week 6</span>
        </div>

        <div style={{ width: 240, height: 240, borderRadius: 16, background: 'rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 18px' }}>
          <div className="muted">QR Image Placeholder</div>
        </div>

        <div className="countdown-ring" id="countdownRing">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle className="cr-track" cx="50" cy="50" r="44" />
            <circle className="cr-fill" cx="50" cy="50" r="44" strokeDasharray={CIRC.toFixed(2)} strokeDashoffset={dash} style={{ stroke }} />
          </svg>
          <div className="cr-label">{left > 0 ? `${mins}:${secs}` : 'Done'}</div>
        </div>

        <p className="live-count">👥 Students scanned: <span id="scannedCount">{left > 0 ? scanned : '—'}</span></p>
        <p className="muted" style={{ fontSize: '.82rem', marginTop: 8 }}>Session closes automatically when timer ends</p>

        <div style={{ marginTop: 20 }}>
          <a className="btn soft" href="/faculty">← Faculty Dashboard</a>
        </div>
      </div>
    </div>
  );
}
