# AttendX - Smart QR-Based Attendance Tracking System

A full-featured attendance tracking system with QR-based sessions, three role dashboards, and optional SMS alerts.

## Features
- Admin, Faculty, Student dashboards
- Time-limited QR attendance (default 2 minutes)
- Optional SMS alerts via Twilio when attendance drops below a threshold
- Cloud-ready database (PostgreSQL/Supabase)
- Admin user/class management and reports
- Faculty QR generation and class attendance views
- Student attendance history and progress

## Architecture

Target layout
```
Frontend 
      |
API Gateway
      |
Backend Services
 |        |        |
Auth    Lead AI   CRM
      |
Database
```

Current project layout
```
attendx/
├── app.py                 # API Gateway entrypoint (Flask)
├── api_gateway/           # Gateway routes (e.g., /health)
├── services/
│   ├── auth/              # Auth routes (login, logout, password reset)
│   ├── crm/               # Admin/faculty/student workflows, QR, attendance
│   ├── lead_ai/           # Placeholder for AI/analytics
│   └── shared/            # DB, config, security, notifications
├── frontend/
│   ├── templates/         # Server-rendered HTML
│   └── static/            # CSS/JS/images
├── attendance.db          # SQLite (optional; Postgres supported)
└── requirements.txt
```

Notes
- The app runs as a single Flask process, but routes are split into service modules.


## Setup Guide

Prerequisites
- Python 3.9+
- Optional: Twilio account for SMS alerts

Install
```bash
pip install -r requirements.txt
```

Environment
```bash
cp .env.example .env
```

Required/optional variables
```env
DATABASE_URL=postgresql://user:password@host:5432/dbname   # optional (defaults to SQLite)
TWILIO_ACCOUNT_SID=your_account_sid                       # optional
TWILIO_AUTH_TOKEN=your_auth_token                         # optional
TWILIO_PHONE=+1234567890                                  # optional
QR_VALID_SECONDS=120                                      # optional
SMS_THRESHOLD=75                                          # optional
```

Run
```bash
python app.py
```

Open http://localhost:5000

## API Documentation

All routes are served by the API Gateway (Flask) and backed by service modules.

Auth
- `GET /` Login page
- `POST /login` Authenticate user
- `GET /logout` Clear session
- `POST /admin/reset_password/<user_id>` Admin resets user password
- `POST /reset_my_password` Logged-in user changes password

Admin (CRM)
- `GET /admin` Admin dashboard
- `POST /admin/add_user` Create user
- `POST /admin/delete_user/<user_id>` Delete user
- `POST /admin/add_subject` Create class/subject
- `POST /admin/delete_subject/<class_id>` Delete class/subject
- `POST /admin/import_csv` Bulk import users
- `POST /admin/preview_csv` Preview CSV rows
- `GET /admin/manual_attendance` Manual attendance page
- `POST /admin/manual_attendance` Mark manual attendance
- `GET /admin/attendance_report` Attendance report (JSON)
- `GET /admin/get_sessions/<class_id>` Sessions list (JSON)
- `GET /admin/get_students_for_class/<class_id>` Students list (JSON)

Faculty (CRM)
- `GET /faculty` Faculty dashboard
- `POST /faculty/generate_qr` Create QR session
- `GET /faculty/attendance/<class_id>` Class attendance view
- `POST /faculty/close_session` Close QR session and notify absentees

Student (CRM)
- `GET /student` Student dashboard
- `GET /student/scanner` Scanner page

QR and utilities (CRM)
- `GET /qr/<token>` QR display page
- `GET /qr_image/<token>` QR image PNG
- `GET /scan/<token>` Scan handler
- `GET /api/token_status/<token>` Token status JSON

Gateway
- `GET /health` Health check

## Demo Credentials

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Faculty | faculty1 | faculty123 |
| Faculty | faculty2 | faculty123 |
| Student | student1 | student123 |
| Student | student2 | student123 |

Change these credentials before any real deployment.

## Cloud Database

To use PostgreSQL/Supabase, set `DATABASE_URL` in `.env`.

## Production Deployment

```bash
pip install gunicorn
gunicorn -w 4 app:app
```

Ensure environment variables are set before deploying.

## Roadmap
- Email notifications alongside SMS
- Exportable attendance reports (CSV/PDF)
- Geofencing for attendance
- Mobile PWA for students
- REST API for LMS integrations
- Multi-language UI support

## Contributing
1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Commit: `git commit -m "feat: describe your change"`
4. Push and open a PR

## License
MIT
