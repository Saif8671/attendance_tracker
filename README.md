# 📡 AttendX — Smart Attendance Tracker

A full-featured attendance tracking system with QR-based sessions, 3 role dashboards, and SMS alerts.

## ✨ Features

| Feature | Details |
|---|---|
| **3 Dashboards** | Admin, Faculty, Student — each with their own UI |
| **QR Token Attendance** | Time-limited QR codes (configurable, default 2 min) |
| **SMS Notifications** | Auto-alerts when attendance < 75% via Twilio |
| **Cloud-Ready** | Replace SQLite with PostgreSQL/Supabase easily |
| **Admin Panel** | Add users, view all reports, manage classes |
| **Faculty** | Generate QR per class, live countdown timer, view per-student stats |
| **Student** | See subject-wise %, scan history, visual progress bars |

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure SMS (Optional)
Copy `.env.example` to `.env` and fill in Twilio credentials:
```bash
cp .env.example .env
```
Get free Twilio credentials at https://twilio.com

### 3. Run the App
```bash
python app.py
```
Open: http://localhost:5000

## 🔐 Demo Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Faculty | `faculty1` | `faculty123` |
| Faculty | `faculty2` | `faculty123` |
| Student | `student1` | `student123` |
| Student | `student2` | `student123` |

## 📱 How QR Attendance Works

1. **Faculty** logs in → selects a class → clicks "Generate QR"
2. A QR code appears with a live countdown timer (default: 2 minutes)
3. **Students** open their phone camera → scan the QR → attendance marked instantly
4. QR expires after the countdown — faculty generates a new one for next session
5. If a student's attendance drops below 75%, an **SMS is automatically sent** to their phone

## 🏗 Architecture

```
app.py              ← Main Flask app (routes, DB, SMS logic)
templates/
  login.html        ← Unified login with role tabs
  admin.html        ← Admin dashboard
  faculty.html      ← Faculty dashboard
  qr_display.html   ← Live QR with countdown ring
  student.html      ← Student attendance view
  scan_result.html  ← Post-scan confirmation
  faculty_attendance.html ← Per-class detailed view
attendance.db       ← SQLite database (auto-created)
```

## ☁️ Using a Cloud Database (Supabase/PostgreSQL)

Replace the `get_db()` and `init_db()` functions in `app.py` with:

```python
import psycopg2
DATABASE_URL = os.getenv("DATABASE_URL")  # Set your cloud DB URL

def get_db():
    return psycopg2.connect(DATABASE_URL)
```

## 📦 Production Deployment

```bash
pip install gunicorn
gunicorn -w 4 app:app
```

Set environment variables for Twilio before deploying.
