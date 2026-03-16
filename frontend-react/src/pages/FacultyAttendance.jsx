import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from '../api.js';

export default function FacultyAttendance() {
  const { classId } = useParams();
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [cls, setCls] = useState(null);
  const [students, setStudents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch(`/api/faculty/class/${classId}`)
      .then((data) => {
        setCls(data.cls || null);
        setStudents(data.students || []);
        setSessions(data.sessions || []);
        setTotal(data.total || 0);
      })
      .catch((err) => setError(err.data?.error || 'Failed to load class data'));
  }, [classId]);

  const avg = useMemo(() => {
    if (!students.length || !total) return 0;
    const sum = students.reduce((acc, s) => acc + s.present_count, 0);
    return Math.round((sum / students.length / total) * 100);
  }, [students, total]);

  const filteredStudents = useMemo(() => students.filter((s) => (
    `${s.name} ${s.rollno}`.toLowerCase().includes(search.toLowerCase())
  )), [students, search]);

  if (!cls) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div className="notice">{error || 'Loading class...'}</div>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`} id="appSidebar">
        <div className="brand">
          <h1>AttendX</h1>
          <p>Faculty Portal</p>
        </div>
        <a className="nav-link" href="/faculty">📊 Dashboard</a>
        <a className="logout-link" href="/" onClick={async (e) => { e.preventDefault(); await apiFetch('/api/auth/logout', { method: 'POST' }); window.location.href = '/'; }}>🚪 Logout</a>
      </aside>

      <main className="main">
        <div className="page-header">
          <div>
            <button id="mobileMenuBtn" className="mobile-toggle" type="button" onClick={() => setMenuOpen((v) => !v)}>☰ Menu</button>
            <h2 className="page-title">{cls.subject}</h2>
            <p className="page-subtitle">{cls.class_name} · {total} completed sessions</p>
          </div>
          <a className="btn soft" href="/faculty">← Faculty Dashboard</a>
        </div>

        {error && <div className="notice error">{error}</div>}

        <div className="metric-grid" style={{ marginBottom: 20 }}>
          <div className="metric cyan">
            <div className="label">Total Students</div>
            <div className="value">{students.length}</div>
            <div className="icon">🎓</div>
          </div>
          <div className="metric violet">
            <div className="label">Sessions Run</div>
            <div className="value">{total}</div>
            <div className="icon">📡</div>
          </div>
          <div className="metric emerald">
            <div className="label">Avg Attendance</div>
            <div className="value">{avg}%</div>
            <div className="icon">📊</div>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <h3>Student Attendance</h3>
            <input
              type="text"
              placeholder="Search students…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ maxWidth: 200 }}
            />
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Roll No</th>
                  <th>Present</th>
                  <th>Total</th>
                  <th>Attendance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((s) => {
                  const pct = total ? Math.round((s.present_count / total) * 100) : 0;
                  return (
                    <tr key={s.id}>
                      <td><strong>{s.name}</strong></td>
                      <td>{s.rollno || '—'}</td>
                      <td>{s.present_count}</td>
                      <td>{total}</td>
                      <td style={{ minWidth: 120 }}>
                        <div className={`progress ${pct < 50 ? 'danger' : pct < 75 ? 'warn' : ''}`}>
                          <span style={{ width: `${pct}%` }}></span>
                        </div>
                        <small className="muted">{pct}%</small>
                      </td>
                      <td>
                        <span className={`badge ${pct >= 75 ? 'good' : pct >= 50 ? 'warn' : 'danger'}`}>
                          {pct >= 75 ? 'Good' : pct >= 50 ? 'At Risk' : 'Critical'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>Session Log</h3></div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Session Label</th>
                  <th>Started</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, index) => (
                  <tr key={s.id}>
                    <td className="muted">{index + 1}</td>
                    <td>{s.session_label || '—'}</td>
                    <td>{s.created_at}</td>
                    <td>
                      <span className={`badge ${s.is_active ? 'active' : 'danger'}`}>
                        {s.is_active ? '🟢 Live' : '🔴 Closed'}
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
  );
}
