import React, { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api.js';

export default function Admin() {
  const [tab, setTab] = useState('overview');
  const [menuOpen, setMenuOpen] = useState(false);
  const [overviewSearch, setOverviewSearch] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [facultySearch, setFacultySearch] = useState('');
  const [classSearch, setClassSearch] = useState('');
  const [stats, setStats] = useState({ students: 0, faculty: 0, classes: 0, sessions: 0 });
  const [students, setStudents] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [classes, setClasses] = useState([]);
  const [reportData, setReportData] = useState([]);
  const [csvPreview, setCsvPreview] = useState(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch('/api/admin/dashboard');
      setStats(data.stats || {});
      setStudents(data.students || []);
      setFaculty(data.faculty_list || []);
      setClasses(data.classes || []);
    } catch (err) {
      setError(err.data?.error || 'Failed to load admin dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (tab === 'reports') {
      apiFetch('/api/admin/attendance_report')
        .then((data) => setReportData(data || []))
        .catch(() => setReportData([]));
    }
  }, [tab]);

  const atRisk = useMemo(() => students.filter((s) => (s.total_sessions ? (s.present_count / s.total_sessions) * 100 : 0) < 75), [students]);
  const filteredOverview = useMemo(() => students.filter((s) => (
    `${s.name} ${s.rollno} ${s.class_name}`.toLowerCase().includes(overviewSearch.toLowerCase())
  )), [students, overviewSearch]);
  const filteredStudents = useMemo(() => students.filter((s) => (
    `${s.name} ${s.rollno} ${s.class_name} ${s.username}`.toLowerCase().includes(studentSearch.toLowerCase())
  )), [students, studentSearch]);
  const filteredFaculty = useMemo(() => faculty.filter((f) => (
    `${f.name} ${f.username}`.toLowerCase().includes(facultySearch.toLowerCase())
  )), [faculty, facultySearch]);
  const filteredClasses = useMemo(() => classes.filter((c) => (
    `${c.subject} ${c.class_name} ${c.faculty_name}`.toLowerCase().includes(classSearch.toLowerCase())
  )), [classes, classSearch]);

  const handleAddUser = async (e, role) => {
    e.preventDefault();
    setNotice('');
    setError('');
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.role = role;
    try {
      await apiFetch('/api/admin/add_user', { method: 'POST', body: payload });
      setNotice('User added successfully');
      e.currentTarget.reset();
      await loadDashboard();
    } catch (err) {
      setError(err.data?.error || 'Failed to add user');
    }
  };

  const handleResetPassword = async (e, userId) => {
    e.preventDefault();
    setNotice('');
    setError('');
    const form = new FormData(e.currentTarget);
    const new_password = form.get('new_password');
    try {
      await apiFetch(`/api/admin/reset_password/${userId}`, { method: 'POST', body: { new_password } });
      setNotice('Password reset successfully');
      e.currentTarget.reset();
    } catch (err) {
      setError(err.data?.error || 'Failed to reset password');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm('Delete this user?')) return;
    setNotice('');
    setError('');
    try {
      await apiFetch(`/api/admin/user/${userId}`, { method: 'DELETE' });
      setNotice('User deleted');
      await loadDashboard();
    } catch (err) {
      setError(err.data?.error || 'Failed to delete user');
    }
  };

  const handleAddClass = async (e) => {
    e.preventDefault();
    setNotice('');
    setError('');
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      await apiFetch('/api/admin/add_subject', { method: 'POST', body: payload });
      setNotice('Class added');
      e.currentTarget.reset();
      await loadDashboard();
    } catch (err) {
      setError(err.data?.error || 'Failed to add class');
    }
  };

  const handleDeleteClass = async (classId) => {
    if (!confirm('Delete this class?')) return;
    setNotice('');
    setError('');
    try {
      await apiFetch(`/api/admin/subject/${classId}`, { method: 'DELETE' });
      setNotice('Class deleted');
      await loadDashboard();
    } catch (err) {
      setError(err.data?.error || 'Failed to delete class');
    }
  };

  const handleManualAttendance = async (e) => {
    e.preventDefault();
    setNotice('');
    setError('');
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      await apiFetch('/api/admin/manual_attendance', { method: 'POST', body: payload });
      setNotice('Attendance saved');
      e.currentTarget.reset();
    } catch (err) {
      setError(err.data?.error || 'Failed to save attendance');
    }
  };

  const handleImportCsv = async (e) => {
    e.preventDefault();
    setNotice('');
    setError('');
    const form = new FormData(e.currentTarget);
    try {
      const data = await apiFetch('/api/admin/import_csv', { method: 'POST', body: form });
      if (data.errors && data.errors.length) {
        setError(data.errors.join(' | '));
      } else {
        setNotice('CSV import complete');
      }
      await loadDashboard();
    } catch (err) {
      setError(err.data?.error || 'CSV import failed');
    }
  };

  const handlePreviewCsv = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('csv_file', file);
    try {
      const data = await apiFetch('/api/admin/preview_csv', { method: 'POST', body: form });
      setCsvPreview(data);
    } catch {
      setCsvPreview(null);
    }
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div className="notice">Loading admin dashboard…</div>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`} id="appSidebar">
        <div className="brand">
          <h1>AttendX</h1>
          <p>Admin Panel</p>
        </div>
        <a className={`nav-link ${tab === 'overview' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('overview'); }}>📊 Overview</a>
        <a className={`nav-link ${tab === 'students' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('students'); }}>🎓 Students</a>
        <a className={`nav-link ${tab === 'teachers' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('teachers'); }}>👨‍🏫 Faculty</a>
        <a className={`nav-link ${tab === 'subjects' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('subjects'); }}>📚 Classes</a>
        <a className={`nav-link ${tab === 'manual' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('manual'); }}>✏️ Manual Entry</a>
        <a className={`nav-link ${tab === 'import' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('import'); }}>📥 Import CSV</a>
        <a className={`nav-link ${tab === 'reports' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('reports'); }}>📈 Reports</a>
        <a className={`nav-link ${tab === 'ai' ? 'active' : ''}`} href="#" onClick={(e) => { e.preventDefault(); setTab('ai'); }}>🤖 AI Insights</a>
        <a className="logout-link" href="/" onClick={async (e) => { e.preventDefault(); await apiFetch('/api/auth/logout', { method: 'POST' }); window.location.href = '/'; }}>🚪 Logout</a>
      </aside>

      <main className="main" id="adminTabs">
        <div className="page-header">
          <div>
            <button id="mobileMenuBtn" className="mobile-toggle" type="button" onClick={() => setMenuOpen((v) => !v)}>☰ Menu</button>
            <h2 className="page-title">Admin Control Center</h2>
            <p className="page-subtitle">Manage users, classes, attendance records and system analytics.</p>
          </div>
        </div>

        {notice && <div className="notice">{notice}</div>}
        {error && <div className="notice error">{error}</div>}

        <div className="tabs" id="tabNav">
          <button className={`tab-btn ${tab === 'overview' ? 'active' : ''}`} data-tab="overview" onClick={() => setTab('overview')}>Overview</button>
          <button className={`tab-btn ${tab === 'students' ? 'active' : ''}`} data-tab="students" onClick={() => setTab('students')}>Students</button>
          <button className={`tab-btn ${tab === 'teachers' ? 'active' : ''}`} data-tab="teachers" onClick={() => setTab('teachers')}>Faculty</button>
          <button className={`tab-btn ${tab === 'subjects' ? 'active' : ''}`} data-tab="subjects" onClick={() => setTab('subjects')}>Classes</button>
          <button className={`tab-btn ${tab === 'manual' ? 'active' : ''}`} data-tab="manual" onClick={() => setTab('manual')}>Manual</button>
          <button className={`tab-btn ${tab === 'import' ? 'active' : ''}`} data-tab="import" onClick={() => setTab('import')}>Import CSV</button>
          <button className={`tab-btn ${tab === 'reports' ? 'active' : ''}`} data-tab="reports" onClick={() => setTab('reports')}>Reports</button>
          <button className={`tab-btn ${tab === 'ai' ? 'active' : ''}`} data-tab="ai" onClick={() => setTab('ai')}>AI Insights</button>
        </div>

        <section className={`tab-pane ${tab === 'overview' ? 'active' : ''}`} data-pane="overview">
          <div className="metric-grid">
            <div className="metric cyan">
              <div className="label">Total Students</div>
              <div className="value" data-count={stats.students}>{stats.students}</div>
              <div className="icon">🎓</div>
            </div>
            <div className="metric violet">
              <div className="label">Total Faculty</div>
              <div className="value" data-count={stats.faculty}>{stats.faculty}</div>
              <div className="icon">👨‍🏫</div>
            </div>
            <div className="metric emerald">
              <div className="label">Classes</div>
              <div className="value" data-count={stats.classes}>{stats.classes}</div>
              <div className="icon">📚</div>
            </div>
            <div className="metric amber">
              <div className="label">QR Sessions</div>
              <div className="value" data-count={stats.sessions}>{stats.sessions}</div>
              <div className="icon">📡</div>
            </div>
          </div>

          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="panel">
              <div className="panel-head">
                <h3>Attendance Health Overview</h3>
              </div>
              <div className="panel-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
                <div className="notice">Chart placeholder (hook Chart.js to /api/admin/dashboard if needed)</div>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <h3>At-Risk Students</h3>
              </div>
              <div className="panel-body" style={{ padding: 12 }}>
                {atRisk.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Class</th>
                          <th>Attendance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {atRisk.slice(0, 8).map((s) => {
                          const pct = s.total_sessions ? Math.round((s.present_count / s.total_sessions) * 100) : 0;
                          return (
                            <tr key={s.id}>
                              <td><strong>{s.name}</strong></td>
                              <td className="muted">{s.class_name || '—'}</td>
                              <td><span className={`badge ${pct >= 50 ? 'warn' : 'danger'}`}>{pct}%</span></td>
                            </tr>
                          );
                        })}
                        {atRisk.length > 8 && (
                          <tr>
                            <td colSpan={3} className="muted" style={{ textAlign: 'center', fontSize: '.8rem' }}>+{atRisk.length - 8} more — see Reports</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted" style={{ textAlign: 'center', padding: 20 }}>🎉 All students above 75% attendance!</p>
                )}
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h3>Class Health Snapshot</h3>
              <input
                type="text"
                placeholder="Search students…"
                value={overviewSearch}
                onChange={(e) => setOverviewSearch(e.target.value)}
                style={{ maxWidth: 200 }}
              />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Roll</th>
                    <th>Class</th>
                    <th>Attendance</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOverview.map((s) => {
                    const pct = s.total_sessions ? Math.round((s.present_count / s.total_sessions) * 100) : 0;
                    const status = pct >= 75 ? 'Good' : pct >= 50 ? 'Warning' : 'Critical';
                    return (
                      <tr key={s.id}>
                        <td><strong>{s.name}</strong></td>
                        <td className="muted">{s.rollno || '—'}</td>
                        <td>{s.class_name || '—'}</td>
                        <td style={{ minWidth: 130 }}>
                          <div className={`progress ${pct < 50 ? 'danger' : pct < 75 ? 'warn' : ''}`}>
                            <span style={{ width: `${pct}%` }}></span>
                          </div>
                          <small className="muted">{pct}%</small>
                        </td>
                        <td><span className={`badge ${pct >= 75 ? 'good' : pct >= 50 ? 'warn' : 'danger'}`}>{status}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'students' ? 'active' : ''}`} data-pane="students">
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="panel">
              <div className="panel-head">
                <h3>Add Student</h3>
              </div>
              <div className="panel-body">
                <form className="stack" onSubmit={(e) => handleAddUser(e, 'student')}>
                  <div className="form-group"><label>Full Name</label><input name="name" required placeholder="e.g. Ahmed Khan" /></div>
                  <div className="form-group"><label>Username</label><input name="username" required placeholder="e.g. ahmed_khan" /></div>
                  <div className="form-group"><label>Password</label><input name="password" required placeholder="Min 6 characters" /></div>
                  <div className="form-group"><label>Roll Number</label><input name="rollno" placeholder="e.g. 22B01CS001" /></div>
                  <div className="form-group"><label>Class Name</label><input name="class_name" placeholder="e.g. CSE-Y3" /></div>
                  <div className="form-group"><label>Phone</label><input name="phone" placeholder="+91 XXXXXXXXXX" /></div>
                  <button type="submit" className="btn">➕ Add Student</button>
                </form>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <h3>Reset Student Password</h3>
              </div>
              <div className="panel-body">
                <form className="stack" onSubmit={(e) => handleResetPassword(e, e.currentTarget.resetStudentId.value)}>
                  <div className="form-group">
                    <label>Select Student</label>
                    <select name="resetStudentId" required>
                      <option value="">— pick student —</option>
                      {students.map((s) => (
                        <option key={s.id} value={s.id}>{s.name} ({s.rollno || '—'})</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group"><label>New Password</label><input name="new_password" required minLength={6} placeholder="New password" /></div>
                  <button className="btn soft" type="submit">🔑 Reset Password</button>
                </form>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h3>All Students ({students.length})</h3>
              <input
                type="text"
                placeholder="Search…"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
                style={{ maxWidth: 200 }}
              />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Roll</th>
                    <th>Class</th>
                    <th>Phone</th>
                    <th>Username</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map((s) => (
                    <tr key={s.id}>
                      <td><strong>{s.name}</strong></td>
                      <td className="muted">{s.rollno || '—'}</td>
                      <td>{s.class_name || '—'}</td>
                      <td className="muted">{s.phone || '—'}</td>
                      <td className="muted">{s.username}</td>
                      <td><button className="btn sm danger" type="button" onClick={() => handleDeleteUser(s.id)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'teachers' ? 'active' : ''}`} data-pane="teachers">
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="panel">
              <div className="panel-head"><h3>Add Faculty</h3></div>
              <div className="panel-body">
                <form className="stack" onSubmit={(e) => handleAddUser(e, 'faculty')}>
                  <div className="form-group"><label>Full Name</label><input name="name" required placeholder="e.g. Dr. Ali" /></div>
                  <div className="form-group"><label>Username</label><input name="username" required placeholder="e.g. ali" /></div>
                  <div className="form-group"><label>Password</label><input name="password" required placeholder="Min 6 characters" /></div>
                  <div className="form-group"><label>Phone</label><input name="phone" placeholder="+91 XXXXXXXXXX" /></div>
                  <button type="submit" className="btn">➕ Add Faculty</button>
                </form>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head"><h3>Reset Faculty Password</h3></div>
              <div className="panel-body">
                <form className="stack" onSubmit={(e) => handleResetPassword(e, e.currentTarget.resetFacultyId.value)}>
                  <div className="form-group">
                    <label>Select Faculty</label>
                    <select name="resetFacultyId" required>
                      <option value="">— pick faculty —</option>
                      {faculty.map((f) => (
                        <option key={f.id} value={f.id}>{f.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group"><label>New Password</label><input name="new_password" required minLength={6} placeholder="New password" /></div>
                  <button className="btn soft" type="submit">🔑 Reset Password</button>
                </form>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h3>All Faculty ({faculty.length})</h3>
              <input
                type="text"
                placeholder="Search…"
                value={facultySearch}
                onChange={(e) => setFacultySearch(e.target.value)}
                style={{ maxWidth: 200 }}
              />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Username</th>
                    <th>Phone</th>
                    <th>Subjects</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFaculty.map((f) => (
                    <tr key={f.id}>
                      <td><strong>{f.name}</strong></td>
                      <td className="muted">{f.username}</td>
                      <td className="muted">{f.phone}</td>
                      <td>{f.subjects || '-'}</td>
                      <td><button className="btn sm danger" type="button" onClick={() => handleDeleteUser(f.id)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'subjects' ? 'active' : ''}`} data-pane="subjects">
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="panel">
              <div className="panel-head"><h3>Add Class</h3></div>
              <div className="panel-body">
                <form className="stack" onSubmit={handleAddClass}>
                  <div className="form-group"><label>Subject</label><input name="subject" required placeholder="e.g. Data Structures" /></div>
                  <div className="form-group"><label>Class Name</label><input name="class_name" required placeholder="e.g. CSE-Y3" /></div>
                  <div className="form-group"><label>Assign Faculty</label>
                    <select name="faculty_id" required>
                      <option value="">Select faculty</option>
                      {faculty.map((f) => (
                        <option key={f.id} value={f.id}>{f.name}</option>
                      ))}
                    </select>
                  </div>
                  <button type="submit" className="btn">➕ Add Class</button>
                </form>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head"><h3>Bulk Actions</h3></div>
              <div className="panel-body">
                <p className="muted">Use CSV import to create multiple classes quickly.</p>
                <button className="btn soft" type="button" onClick={() => setTab('import')}>Open Import</button>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h3>All Classes ({classes.length})</h3>
              <input
                type="text"
                placeholder="Search…"
                value={classSearch}
                onChange={(e) => setClassSearch(e.target.value)}
                style={{ maxWidth: 200 }}
              />
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Class</th>
                    <th>Faculty</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredClasses.map((c) => (
                    <tr key={c.id}>
                      <td><strong>{c.subject}</strong></td>
                      <td>{c.class_name}</td>
                      <td className="muted">{c.faculty_name}</td>
                      <td><button className="btn sm danger" type="button" onClick={() => handleDeleteClass(c.id)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'manual' ? 'active' : ''}`} data-pane="manual">
          <div className="panel">
            <div className="panel-head"><h3>Manual Attendance Entry</h3></div>
            <div className="panel-body">
              <form className="stack" onSubmit={handleManualAttendance}>
                <div className="form-group">
                  <label>Student</label>
                  <select name="student_id" required>
                    <option value="">Select student</option>
                    {students.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Subject</label>
                  <select name="class_id" required>
                    <option value="">Select class</option>
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>{c.subject} · {c.class_name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group"><label>Date</label><input type="date" name="session_date" /></div>
                <div className="form-group"><label>Status</label><select name="status"><option value="present">Present</option><option value="absent">Absent</option></select></div>
                <button className="btn" type="submit">✅ Save Entry</button>
              </form>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'import' ? 'active' : ''}`} data-pane="import">
          <div className="panel">
            <div className="panel-head"><h3>CSV Import</h3></div>
            <div className="panel-body">
              <form className="stack" onSubmit={handleImportCsv}>
                <div className="form-group"><label>Upload CSV</label><input type="file" name="csv_file" accept=".csv" onChange={handlePreviewCsv} /></div>
                <button className="btn" type="submit">📥 Upload</button>
              </form>
              <div id="csvPreview" style={{ marginTop: 16 }}>
                {csvPreview ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          {csvPreview.headers.map((h) => <th key={h}>{h}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {csvPreview.preview.map((row, idx) => (
                          <tr key={idx}>
                            {csvPreview.headers.map((h) => <td key={h}>{row[h] || ''}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="notice">Preview will appear here.</div>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'reports' ? 'active' : ''}`} data-pane="reports">
          <div className="panel">
            <div className="panel-head"><h3>Attendance Reports</h3></div>
            <div className="panel-body">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Roll</th>
                      <th>Class</th>
                      <th>Overall</th>
                      <th>Subjects</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.map((s) => {
                      const total = s.subjects.reduce((acc, sub) => acc + sub.pct, 0);
                      const pct = s.subjects.length ? Math.round(total / s.subjects.length) : 0;
                      const cls = pct >= 75 ? 'good' : pct >= 50 ? 'warn' : 'danger';
                      return (
                        <tr key={s.id}>
                          <td><strong>{s.name}</strong></td>
                          <td className="muted">{s.rollno}</td>
                          <td>{s.class_name}</td>
                          <td><span className={`badge ${cls}`}>{pct}%</span></td>
                          <td style={{ whiteSpace: 'normal', display: 'flex', flexWrap: 'wrap', gap: 4, padding: '6px 0' }}>
                            {s.subjects.map((sub) => (
                              <span key={sub.subject} className={`badge ${sub.pct >= 75 ? 'good' : sub.pct >= 50 ? 'warn' : 'danger'}`}>
                                {sub.subject}: {sub.pct}%
                              </span>
                            ))}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <section className={`tab-pane ${tab === 'ai' ? 'active' : ''}`} data-pane="ai">
          <div className="panel">
            <div className="panel-head"><h3>🤖 AttendX AI Insights</h3></div>
            <div className="panel-body">
              <div className="metric cyan" style={{ marginBottom: 16 }}>
                <div className="label">AI Engine Status</div>
                <div className="value">READY</div>
                <div className="icon">🤖</div>
              </div>
              <p style={{ fontSize: '1.05rem' }}><strong>Insight Engine v2</strong></p>
              <p className="muted">At-risk students increased by 6% in the last 7 days. Consider targeted interventions.</p>
              <div className="notice" style={{ marginTop: 12, opacity: 0.8 }}>💡 Tip: AI insights improve as more students scan QR codes daily.</div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
