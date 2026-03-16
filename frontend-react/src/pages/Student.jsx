import React, { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api.js';

export default function Student() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [student, setStudent] = useState(null);
  const [attendance, setAttendance] = useState([]);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/student/dashboard')
      .then((data) => {
        setStudent(data.student || null);
        setAttendance(data.attendance || []);
        setRecent(data.recent || []);
      })
      .catch((err) => setError(err.data?.error || 'Failed to load student dashboard'));
  }, []);

  const totalPresent = attendance.reduce((acc, a) => acc + (a.present_count || 0), 0);
  const totalSessions = attendance.reduce((acc, a) => acc + (a.total_sessions || 0), 0);
  const overallPct = totalSessions ? Math.round((totalPresent / totalSessions) * 100) : 0;

  const filteredHistory = useMemo(() => recent.filter((r) => (
    `${r.marked_at} ${r.subject} ${r.session_label}`.toLowerCase().includes(search.toLowerCase())
  )), [recent, search]);

  const bigCirc = 2 * Math.PI * 48;

  if (!student) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div className="notice">{error || 'Loading student dashboard…'}</div>
      </div>
    );
  }

  return (
    <>
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
      </svg>
      <div className="shell">
        <aside className={`sidebar ${menuOpen ? 'open' : ''}`} id="appSidebar">
          <div className="brand">
            <h1>AttendX</h1>
            <p>Student Portal</p>
          </div>
          <a className="nav-link active" href="/student">📊 Dashboard</a>
          <a className="nav-link" href="/student/scan">📷 Scan QR</a>
          <a className="logout-link" href="/" onClick={async (e) => { e.preventDefault(); await apiFetch('/api/auth/logout', { method: 'POST' }); window.location.href = '/'; }}>🚪 Logout</a>
        </aside>

        <main className="main">
          <div className="page-header">
            <div>
              <button id="mobileMenuBtn" className="mobile-toggle" type="button" onClick={() => setMenuOpen((v) => !v)}>☰ Menu</button>
              <h2 className="page-title">My Attendance</h2>
              <p className="page-subtitle">
                {student.name}
                {student.rollno ? ` · ${student.rollno}` : ''}
                {student.class_name ? ` · ${student.class_name}` : ''}
              </p>
            </div>
            <a className="btn" href="/student/scan">📷 Scan Attendance</a>
          </div>

          {error && <div className="notice error">{error}</div>}

          <div className="hero" style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', marginBottom: 20 }}>
            <div className="circle-wrap" style={{ margin: 0 }}>
              <div className="circle" style={{ width: 110, height: 110 }}>
                <svg width="110" height="110" viewBox="0 0 110 110">
                  <circle className="track" cx="55" cy="55" r="48" strokeWidth="9" />
                  <circle
                    className="fill"
                    cx="55"
                    cy="55"
                    r="48"
                    strokeWidth="9"
                    stroke="url(#grad)"
                    strokeDasharray={bigCirc.toFixed(2)}
                    strokeDashoffset={((1 - overallPct / 100) * bigCirc).toFixed(2)}
                  />
                </svg>
                <div className="circle-label">{overallPct}<small>%</small></div>
              </div>
            </div>
            <div>
              <h3 style={{ fontSize: '1.3rem', marginBottom: 4 }}>Overall Attendance</h3>
              <p className="muted">{totalPresent} present out of {totalSessions} total sessions</p>
              <span className={`badge ${overallPct >= 75 ? 'good' : overallPct >= 50 ? 'warn' : 'danger'}`} style={{ marginTop: 8 }}>
                {overallPct >= 75 ? '✓ Good Standing' : overallPct >= 50 ? '⚠ Below Average' : '⚠ Critical — Contact Faculty'}
              </span>
            </div>
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-head"><h3>Subject-wise Attendance</h3></div>
            <div className="panel-body">
              {attendance.length ? (
                <div className="grid-3">
                  {attendance.map((a) => {
                    const pct = a.total_sessions ? Math.round((a.present_count / a.total_sessions) * 100) : 0;
                    const circ = 2 * Math.PI * 38;
                    return (
                      <div className="card" key={a.class_id || a.subject}>
                        <h3 style={{ marginBottom: 4, fontSize: '1rem' }}>{a.subject}</h3>
                        <p className="muted" style={{ fontSize: '.8rem', marginBottom: 14 }}>{a.class_name}</p>
                        <div className="circle-wrap">
                          <div className="circle">
                            <svg width="90" height="90" viewBox="0 0 90 90">
                              <circle className="track" cx="45" cy="45" r="38" strokeWidth="8" />
                              <circle
                                className="fill"
                                cx="45"
                                cy="45"
                                r="38"
                                strokeWidth="8"
                                stroke="url(#grad)"
                                strokeDasharray={circ.toFixed(2)}
                                strokeDashoffset={((1 - pct / 100) * circ).toFixed(2)}
                              />
                            </svg>
                            <div className="circle-label" style={{ fontSize: '1rem' }}>{pct}<small>%</small></div>
                          </div>
                        </div>
                        <p className="muted" style={{ textAlign: 'center', fontSize: '.8rem', marginTop: 8 }}>{a.present_count}/{a.total_sessions} classes</p>
                        <div style={{ textAlign: 'center', marginTop: 8 }}>
                          <span className={`badge ${pct >= 75 ? 'good' : pct >= 50 ? 'warn' : 'danger'}`}>
                            {pct >= 75 ? 'Good' : pct >= 50 ? 'Warning' : 'Critical'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="muted" style={{ textAlign: 'center', padding: 20 }}>No subjects assigned yet. Contact your admin.</p>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h3>Recent Attendance</h3>
              <input
                type="text"
                placeholder="Search…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ maxWidth: 200 }}
              />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date &amp; Time</th>
                    <th>Subject</th>
                    <th>Session</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((r, idx) => (
                    <tr key={idx}>
                      <td>{(r.marked_at || '').replace('T', ' ').slice(0, 16)}</td>
                      <td>{r.subject}</td>
                      <td>{r.session_label || '—'}</td>
                      <td>
                        <span className={`badge ${r.status === 'present' ? 'present' : 'absent'}`}>
                          {r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : 'Unknown'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
