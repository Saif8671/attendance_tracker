import React from 'react';

export default function ManualAttendance() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div className="panel" style={{ maxWidth: 480, width: '100%' }}>
        <div className="panel-head">
          <h3>✏️ Manual Attendance Entry</h3>
        </div>
        <div className="panel-body">
          <p className="muted" style={{ marginBottom: 16 }}>This page redirects to the Admin dashboard Manual tab.</p>
          <a className="btn full" href="/admin">← Back to Dashboard</a>
        </div>
      </div>
    </div>
  );
}
