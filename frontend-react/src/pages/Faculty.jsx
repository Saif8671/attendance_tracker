import React, { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api.js';

export default function Faculty() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [classes, setClasses] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/faculty/dashboard')
      .then((data) => {
        setClasses(data.classes || []);
        setSessions(data.recent_tokens || []);
        setName(data.name || '');
      })
      .catch((err) => setError(err.data?.error || 'Failed to load faculty dashboard'));
  }, []);

  const filteredSessions = useMemo(() => sessions.filter((s) => (
    `${s.subject} ${s.class_name} ${s.session_label}`.toLowerCase().includes(search.toLowerCase())
  )), [sessions, search]);

  return (
    <div className="shell">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`} id="appSidebar">
        <div className="brand">
          <h1>AttendX</h1>
          <p>Faculty Portal</p>
        </div>
        <a className="nav-link active" href="/faculty">📊 Dashboard</a>
        <a className="nav-link" href="#sessions">📋 Recent Sessions</a>
        <a className="logout-link" href="/" onClick={async (e) => { e.preventDefault(); await apiFetch('/api/auth/logout', { method: 'POST' }); window.location.href = '/'; }}>🚪 Logout</a>
      </aside>

      <main className="main">
        <div className="page-header">
          <div>
            <button id="mobileMenuBtn" className="mobile-toggle" type="button" onClick={() => setMenuOpen((v) => !v)}>☰ Menu</button>
            <h2 className="page-title">Faculty Dashboard</h2>
            <p className="page-subtitle">Welcome back, <strong style={{ color: 'var(--text)' }}>{name || 'Faculty'}</strong> — Generate live QR sessions to record attendance.</p>
          </div>
        </div>

        {error && <div className="notice error">{error}</div>}

        <div className="metric-grid" style={{ marginBottom: 20 }}>
          <div className="metric cyan">
            <div className="label">Classes</div>
            <div className="value">{classes.length}</div>
            <div className="icon">📚</div>
          </div>
          <div className="metric violet">
            <div className="label">Total Sessions</div>
            <div className="value">{sessions.length}</div>
            <div className="icon">📡</div>
          </div>
          <div className="metric emerald">
            <div className="label">Active Now</div>
            <div className="value">{sessions.filter((s) => s.is_active === 1).length}</div>
            <div className="icon">🟢</div>
          </div>
        </div>

        <div className="panel" id="classGrid" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <h3>Your Classes</h3>
          </div>
          <div className="panel-body">
            {classes.length ? (
              <div className="card-grid">
                {classes.map((cls) => (
                  <div className="card" key={cls.id}>
                    <h3 style={{ marginBottom: 4, fontSize: '1.05rem' }}>{cls.subject}</h3>
                    <p className="muted" style={{ fontSize: '.82rem', marginBottom: 16 }}>{cls.class_name}</p>
                    <form style={{ marginBottom: 10 }} onSubmit={async (e) => {
                      e.preventDefault();
                      const form = new FormData(e.currentTarget);
                      const label = form.get('label');
                      try {
                        const data = await apiFetch('/api/faculty/generate_qr', { method: 'POST', body: { class_id: cls.id, label } });
                        if (data && data.token) {
                          window.location.href = `/qr/${data.token}`;
                        }
                      } catch {
                        alert('Failed to start session');
                      }
                    }}>
                      <input type="text" name="label" placeholder="Session label (optional)" style={{ marginBottom: 8 }} />
                      <button className="btn full" type="submit">📡 Start QR Session</button>
                    </form>
                    <a className="btn soft full" href={`/faculty/class/${cls.id}`}>📋 View Attendance</a>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted" style={{ textAlign: 'center', padding: 30 }}>No classes assigned yet. Contact admin.</p>
            )}
          </div>
        </div>

        <div className="panel" id="sessions">
          <div className="panel-head">
            <h3>Recent QR Sessions</h3>
            <input
              type="text"
              placeholder="Search sessions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ maxWidth: 200 }}
            />
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Class</th>
                  <th>Session Label</th>
                  <th>Scanned</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredSessions.map((t) => (
                  <tr key={t.id}>
                    <td><strong>{t.subject}</strong></td>
                    <td>{t.class_name}</td>
                    <td>{t.session_label || '—'}</td>
                    <td>{t.marked_count}</td>
                    <td>
                      <span className={`badge ${t.is_active === 1 ? 'active' : 'danger'}`}>
                        {t.is_active === 1 ? '🟢 Live' : '🔴 Closed'}
                      </span>
                    </td>
                    <td>
                      {t.is_active === 1 ? <a className="btn sm" href={`/qr/${t.token}`}>Open QR</a> : <span className="muted">Closed</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
