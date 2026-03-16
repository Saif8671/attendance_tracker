import React from 'react';

export default function StudentScanner() {
  return (
    <div className="scanner-shell">
      <div className="scanner-card">
        <h2 style={{ marginBottom: 6 }}>📷 Scan Attendance QR</h2>
        <p className="muted" style={{ marginBottom: 16 }}>Point your camera at the QR code shown by your faculty</p>

        <div id="reader" style={{ width: '100%', maxWidth: 360, margin: '0 auto' }}>
          <div className="notice" style={{ textAlign: 'center' }}>Camera preview placeholder</div>
        </div>

        <div id="scanStatus" className="notice" style={{ marginTop: 16, display: 'none' }}></div>

        <div style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="btn soft" type="button">■ Stop Scanner</button>
          <a className="btn full" href="/student">← Back to Dashboard</a>
        </div>
      </div>
    </div>
  );
}
