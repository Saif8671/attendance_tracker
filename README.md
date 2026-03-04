<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,100:059669&height=200&section=header&text=AttendX&fontSize=56&fontColor=ffffff&fontAlignY=38&desc=Smart%20QR-Based%20Attendance%20Tracking%20System&descSize=18&descAlignY=58" width="100%"/>

[![Live Demo](https://img.shields.io/badge/Live_Demo-Visit_App-059669?style=for-the-badge&logo=render&logoColor=white)](#)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Twilio](https://img.shields.io/badge/Twilio_SMS-F22F46?style=for-the-badge&logo=twilio&logoColor=white)](https://twilio.com)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

> Three role dashboards. Time-limited QR sessions. Automated SMS alerts.  
> Attendance tracking that actually works — for faculty, students, and admins.

![App Screenshot](https://via.placeholder.com/900x450/0d1117/059669?text=AttendX+Screenshot+Here)
*(Replace with actual screenshot)*

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎭 3 Role Dashboards | Admin, Faculty, Student — each with a dedicated UI |
| 📱 QR Token Attendance | Time-limited QR codes (configurable, default 2 min) |
| 📲 SMS Notifications | Auto-alerts via Twilio when attendance drops below 75% |
| ☁️ Cloud-Ready | Swap SQLite for PostgreSQL / Supabase with one function change |
| 🛠️ Admin Panel | Add users, manage classes, view all reports |
| 👨‍🏫 Faculty Dashboard | Generate QR per class, live countdown timer, per-student stats |
| 🎓 Student Dashboard | Subject-wise % breakdown, scan history, visual progress bars |

---

## 📱 How QR Attendance Works
```
Faculty generates QR  ──►  QR appears with live countdown (2 min default)
        │
        ▼
Student scans QR with phone camera
        │
        ▼
Attendance marked instantly in database
        │
        ▼
Attendance < 75%?  ──► YES ──►  SMS alert sent to student via Twilio
                   ──► NO  ──►  No action needed ✅
```

1. **Faculty** logs in → selects a class → clicks **"Generate QR"**
2. A QR code appears with a live countdown ring (default: 2 minutes)
3. **Students** scan the QR with their phone camera → attendance marked instantly
4. QR expires after countdown — faculty generates a new one each session
5. If a student's attendance drops below **75%**, an SMS fires automatically

---

## 🏗️ Architecture
```
attendx/
├── app.py                        # Flask app — routes, DB, SMS logic
├── attendance.db                 # SQLite database (auto-created on first run)
├── requirements.txt
├── .env.example                  # Twilio credentials template
├── .env                          # Your credentials (never commit this)
└── templates/
    ├── login.html                # Unified login with role tabs
    ├── admin.html                # Admin dashboard
    ├── faculty.html              # Faculty dashboard
    ├── qr_display.html           # Live QR with countdown ring
    ├── student.html              # Student attendance view
    ├── scan_result.html          # Post-scan confirmation page
    └── faculty_attendance.html   # Per-class detailed view
```

---

## 🚀 Quick Start

### Prerequisites
- Python **3.9+**
- A free [Twilio account](https://twilio.com) *(optional — only needed for SMS alerts)*

### 1. Clone & Install
```bash
git clone https://github.com/Saif8671/attendx.git
cd attendx
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your Twilio credentials:
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

> SMS alerts are **optional** — the app runs fully without Twilio credentials.

### 3. Run
```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.  
The SQLite database initializes automatically on first run.

---

## 🔐 Demo Credentials

| Role | Username | Password |
|---|---|---|
| 🛠️ Admin | `admin` | `admin123` |
| 👨‍🏫 Faculty | `faculty1` | `faculty123` |
| 👨‍🏫 Faculty | `faculty2` | `faculty123` |
| 🎓 Student | `student1` | `student123` |
| 🎓 Student | `student2` | `student123` |

> ⚠️ Change these credentials before any real deployment.

---

## ☁️ Switching to a Cloud Database

The default SQLite setup works out of the box. To upgrade to **PostgreSQL** or **Supabase**, replace the `get_db()` and `init_db()` functions in `app.py`:
```python
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")  # Add to your .env

def get_db():
    return psycopg2.connect(DATABASE_URL)
```

Add `DATABASE_URL` to your `.env`:
```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

## 🌍 Production Deployment
```bash
pip install gunicorn
gunicorn -w 4 app:app
```

Make sure all environment variables (Twilio + DATABASE_URL if using PostgreSQL) are set before deploying.

**Recommended platforms:** [Render](https://render.com) · [Railway](https://railway.app) · [Fly.io](https://fly.io)

---


## 🗺️ Roadmap

- [ ] Email notifications alongside SMS
- [ ] Exportable attendance reports (CSV / PDF)
- [ ] Geofencing — only mark attendance within campus radius
- [ ] Mobile PWA for students (no app install required)
- [ ] Bulk user import via CSV for admin
- [ ] REST API for LMS integrations (Moodle, Canvas)
- [ ] Multi-language UI support

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Commit: `git commit -m "feat: describe your change"`
4. Push and open a PR

---

## 📄 License

MIT © [Saif ur Rahman](https://github.com/Saif8671)

---

<div align="center">

No more paper registers. 📋➡️📱

[![GitHub](https://img.shields.io/badge/GitHub-Saif8671-100000?style=flat&logo=github)](https://github.com/Saif8671)
[![Portfolio](https://img.shields.io/badge/Portfolio-Visit-00C7B7?style=flat&logo=netlify)](https://saif-portfolio8671.netlify.app)

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:059669,100:0d1117&height=100&section=footer" width="100%"/>

</div>
