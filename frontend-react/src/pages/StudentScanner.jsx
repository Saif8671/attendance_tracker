import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Html5QrcodeScanner } from 'html5-qrcode';
import { apiFetch } from '../api.js';

export default function StudentScanner() {
  const [token, setToken] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const scanner = new Html5QrcodeScanner('reader', {
      fps: 10,
      qrbox: { width: 250, height: 250 },
    }, false);

    const onScanSuccess = async (decodedText) => {
      // Small delay to prevent double scans
      scanner.pause();
      setStatus('Validating QR code…');
      
      let finalToken = decodedText;
      if (decodedText.includes('/scan/')) {
        finalToken = decodedText.split('/scan/').pop();
      }

      try {
        const data = await apiFetch(`/api/scan/${encodeURIComponent(finalToken)}`);
        scanner.clear();
        navigate('/scan-result', { state: data });
      } catch (err) {
        setStatus('');
        alert(err.data?.error || 'Unable to mark attendance');
        scanner.resume();
      }
    };

    const onScanFailure = (error) => {
      // Failures are expected while scanning
    };

    scanner.render(onScanSuccess, onScanFailure);

    return () => {
      scanner.clear().catch(() => {});
    };
  }, [navigate]);

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

        <div id="reader" style={{ width: '100%', maxWidth: 360, margin: '0 auto', overflow: 'hidden', borderRadius: 12 }}>
          <div className="notice" style={{ textAlign: 'center' }}>Initializing camera…</div>
        </div>

        <div style={{ marginTop: 16 }}>
          <div className="divider"><span>OR</span></div>
          <p className="muted" style={{ fontSize: '.8rem', marginBottom: 8, textAlign: 'center' }}>Already have a token? Paste it below:</p>
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
          <a className="btn full soft" href="/student">← Back to Dashboard</a>
        </div>
      </div>
    </div>
  );
}

