import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login.jsx';
import Signup from './pages/Signup.jsx';
import Admin from './pages/Admin.jsx';
import Faculty from './pages/Faculty.jsx';
import FacultyAttendance from './pages/FacultyAttendance.jsx';
import ManualAttendance from './pages/ManualAttendance.jsx';
import QrDisplay from './pages/QrDisplay.jsx';
import ScanResult from './pages/ScanResult.jsx';
import Student from './pages/Student.jsx';
import StudentScanner from './pages/StudentScanner.jsx';

function NotFound() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div className="panel" style={{ maxWidth: 520, width: '100%' }}>
        <div className="panel-head">
          <h3>Page Not Found</h3>
        </div>
        <div className="panel-body">
          <p className="muted" style={{ marginBottom: 16 }}>The page you requested does not exist.</p>
          <a className="btn" href="/">Go to Login</a>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/faculty" element={<Faculty />} />
      <Route path="/faculty/class/:classId" element={<FacultyAttendance />} />
      <Route path="/manual" element={<ManualAttendance />} />
      <Route path="/qr/:token" element={<QrDisplay />} />
      <Route path="/scan-result" element={<ScanResult />} />
      <Route path="/student" element={<Student />} />
      <Route path="/student/scan" element={<StudentScanner />} />
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
