<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0f0a,50:064e3b,100:059669&height=220&section=header&text=AttendX&fontSize=72&fontColor=ffffff&fontAlignY=40&desc=Smart%20QR-Based%20Attendance%20Platform&descSize=20&descAlignY=62&animation=fadeIn" width="100%"/>

<br/>

<a href="#"><img src="https://img.shields.io/badge/▶%20Live%20Demo-Visit%20App-059669?style=for-the-badge&logoColor=white"/></a>&nbsp;
<a href="#"><img src="https://img.shields.io/badge/📄%20Docs-Read%20Docs-064e3b?style=for-the-badge"/></a>&nbsp;
<a href="#-quick-start"><img src="https://img.shields.io/badge/⚡%20Quick%20Start-5%20Minutes-10b981?style=for-the-badge"/></a>

<br/><br/>

<img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Flask-2.x-000000?style=flat-square&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/SQLite%20%2F%20PostgreSQL-supported-4169E1?style=flat-square&logo=postgresql&logoColor=white"/>
<img src="https://img.shields.io/badge/Twilio%20SMS-optional-F22F46?style=flat-square&logo=twilio&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-059669?style=flat-square"/>

<br/><br/>

```
╔══════════════════════════════════════════════════════════════╗
║  Three dashboards. QR sessions. Auto SMS alerts.            ║
║  From paper registers to real-time digital tracking.        ║
╚══════════════════════════════════════════════════════════════╝
```

</div> 

## 🎯 Why AttendX

Traditional attendance systems are slow, error-prone, and frustrating for everyone involved. AttendX replaces paper sheets and manual roll calls with a **QR-based, role-aware platform** that works for the entire institution — admins, faculty, and students — each with their own tailored experience.

| Problem | AttendX Solution |
|---|---|
| 📋 Manual paper roll calls | ⚡ One QR scan marks attendance instantly |
| ❌ No visibility for students | 📊 Real-time subject-wise % on student dashboard |
| 🐌 Faculty spends class time on attendance | ⏱️ Generate QR in one click, expires automatically |
| 📭 Students unaware of attendance shortage | 📲 Auto SMS alert when below threshold |
| 🗄️ Data locked in spreadsheets | ☁️ Cloud-ready with PostgreSQL / Supabase support |

---

## ✨ Feature Overview

<table>
<tr>
<td width="33%" valign="top">

### 🛠️ Admin
- Full user management (add / delete)
- Subject & class management
- Bulk user import via CSV
- Manual attendance override
- Attendance reports (JSON)
- Password reset for any user

</td>
<td width="33%" valign="top">

### 👨‍🏫 Faculty
- Generate time-limited QR per class
- Live countdown timer on QR display
- View per-student attendance stats
- Close sessions manually
- Auto-notify absentees on session close

</td>
<td width="33%" valign="top">

### 🎓 Student
- Subject-wise attendance percentage
- Full scan history with timestamps
- Visual progress indicators
- Mobile QR scanner built-in
- SMS alert on threshold breach

</td>
</tr>
</table>

---

## 📱 How QR Attendance Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        FACULTY SIDE                             │
│                                                                 │
│   Login ──► Select Class ──► Generate QR ──► QR + Countdown    │
│                                                    │            │
│                              Session expires ◄─────┘           │
│                              (configurable, default 2 min)     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │  QR code displayed on screen
┌─────────────────────────────────▼───────────────────────────────┐
│                        STUDENT SIDE                             │
│                                                                 │
│   Open phone camera ──► Scan QR ──► Redirect to /scan/<token>  │
│                                              │                  │
│                         Attendance marked ◄──┘                  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                       ALERT ENGINE                              │
│                                                                 │
│   Attendance < SMS_THRESHOLD (default 75%)?                     │
│                                                                 │
│   YES ──► Twilio SMS fired to student's phone                   │
│   NO  ──► No action required ✅                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

AttendX is structured as a **modular monolith** — a single Flask process with routes cleanly split into service modules, designed to decompose into microservices as requirements grow.

```
┌─────────────────────────────────────────────────────────────────┐
│                         TARGET LAYOUT                           │
│                                                                 │
│          Frontend                                               │
│              │                                                  │
│         API Gateway                                             │
│              │                                                  │
│    ┌─────────┼──────────┐                                       │
│   Auth    Lead AI      CRM                                      │
│              │                                                  │
│           Database                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       CURRENT LAYOUT                            │
│                                                                 │
│  attendx/                                                       │
│  ├── app.py                   ← Flask entry + API Gateway       │
│  ├── api_gateway/             ← Gateway routes (/health etc.)   │
│  ├── services/                                                  │
│  │   ├── auth/                ← Login, logout, password reset   │
│  │   ├── crm/                 ← QR, attendance, dashboards      │
│  │   ├── lead_ai/             ← AI/analytics (in progress)      │
│  │   └── shared/              ← DB, config, security, SMS       │
│  ├── frontend/                                                  │
│  │   ├── templates/           ← Server-rendered HTML            │
│  │   └── static/              ← CSS / JS / images               │
│  ├── attendance.db            ← SQLite (default)                │
│  └── requirements.txt                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Web Framework** | Flask 2.x | API gateway + server-rendered UI |
| **Database** | SQLite / supabase | Local dev / production |
| **ORM / DB Layer** | SQLAlchemy / psycopg2 | Database abstraction |
| **SMS Alerts** | Twilio | Automated attendance notifications |
| **QR Generation** | qrcode + Pillow | Session token QR images |
| **Frontend** | HTML + CSS + JS | Server-rendered templates |
| **Production Server** | Gunicorn | WSGI multi-worker deployment |
| **Environment** | python-dotenv | Config and secrets management |

---

## ⚡ Quick Start

> Get AttendX running in under 5 minutes.

### Prerequisites

- Python **3.9+**
- pip
-  Twilio account for SMS alerts
-  PostgreSQL for production database

---

### Step 1 — Clone

```bash
git clone https://github.com/Saif8671/attendx.git
cd attendx
```

---

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3 — Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values. See the [Configuration Reference](#-configuration-reference) for all options.

---

### Step 4 — Run

```bash
python app.py
```

Open **[http://localhost:5000](http://localhost:5000)** — database initializes automatically on first run.

---

## 🔌 API Reference

<details>
<summary><strong>🔐 Auth Routes</strong></summary>

<br/>

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/` | Public | Login page |
| `POST` | `/login` | Public | Authenticate and start session |
| `GET` | `/logout` | Session | Clear session |
| `POST` | `/admin/reset_password/<user_id>` | Admin | Reset any user's password |
| `POST` | `/reset_my_password` | Session | Change own password |

</details>

<details>
<summary><strong>🛠️ Admin Routes</strong></summary>

<br/>

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin` | Admin dashboard |
| `POST` | `/admin/add_user` | Create a new user |
| `POST` | `/admin/delete_user/<user_id>` | Delete a user |
| `POST` | `/admin/add_subject` | Create a class/subject |
| `POST` | `/admin/delete_subject/<class_id>` | Delete a class/subject |
| `POST` | `/admin/import_csv` | Bulk import users from CSV |
| `POST` | `/admin/preview_csv` | Preview CSV before import |
| `GET/POST` | `/admin/manual_attendance` | Manual attendance entry |
| `GET` | `/admin/attendance_report` | Full attendance report (JSON) |
| `GET` | `/admin/get_sessions/<class_id>` | Session list for a class (JSON) |
| `GET` | `/admin/get_students_for_class/<class_id>` | Students in a class (JSON) |

</details>

<details>
<summary><strong>👨‍🏫 Faculty Routes</strong></summary>

<br/>

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/faculty` | Faculty dashboard |
| `POST` | `/faculty/generate_qr` | Create a new QR session |
| `GET` | `/faculty/attendance/<class_id>` | Per-student attendance for class |
| `POST` | `/faculty/close_session` | Close session + notify absentees |

</details>

<details>
<summary><strong>🎓 Student & QR Routes</strong></summary>

<br/>

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/student` | Student dashboard |
| `GET` | `/student/scanner` | QR scanner page |
| `GET` | `/qr/<token>` | QR code display page |
| `GET` | `/qr_image/<token>` | QR code image (PNG) |
| `GET` | `/scan/<token>` | Scan handler — marks attendance |
| `GET` | `/api/token_status/<token>` | Token validity status (JSON) |

</details>

<details>
<summary><strong>🔧 Gateway Routes</strong></summary>

<br/>

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check |

**Sample response:**
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2026-03-11T10:45:00Z"
}
```

</details>

---

## 🔐 Demo Credentials

> For local testing only. **Change all credentials before any real deployment.**

| Role | Username | Password |
|---|---|---|
| 🛠️ Admin | `admin` | `admin123` |
| 👨‍🏫 Faculty | `faculty1` | `faculty123` |
| 👨‍🏫 Faculty | `faculty2` | `faculty123` |
| 🎓 Student | `student1` | `student123` |
| 🎓 Student | `student2` | `student123` |

---

## 🖼️ Screenshots

![attendx_final_verification_fixed_1773168033448](https://github.com/user-attachments/assets/2a79efb8-17ff-4462-987e-72394d0b994f)
<img width="1365" height="670" alt="Screenshot 2026-03-11 152712" src="https://github.com/user-attachments/assets/cfcabb1a-83d0-4f4d-82dc-5e307f060a7e" />
<img width="864" height="680" alt="Screenshot 2026-03-11 154012" src="https://github.com/user-attachments/assets/df7b71e5-9215-4c4b-9f20-f4a6649b8508" />
<img width="1326" height="645" alt="Screenshot 2026-03-11 154516" src="https://github.com/user-attachments/assets/bac0d422-492c-4f52-9a72-9900e902519e" />
<img width="744" height="531" alt="Screenshot 2026-03-11 154045" src="https://github.com/user-attachments/assets/9aadcc36-13fa-4431-a795-60542f839310" />



---


## 🗺️ Roadmap

| Status | Feature |
|---|---|
| 🔄 In Progress | Lead AI analytics module |
| 📋 Planned | Email notifications alongside SMS |
| 📋 Planned | Exportable reports (CSV / PDF) |
| 📋 Planned | Geofencing — attend only within campus radius |
| 📋 Planned | Mobile PWA for students |
| 📋 Planned | REST API for LMS integrations (Moodle, Canvas) |
| 📋 Planned | Multi-language UI support |
| 💡 Idea | Bulk QR scanning for large auditoriums |
| 💡 Idea | Analytics dashboard with attendance trend graphs |


---

Please follow [Conventional Commits](https://www.conventionalcommits.org) for commit messages. Open an issue first for large changes.

---

## 📄 License

MIT © [Saif ur Rahman](https://github.com/Saif8671)  
Free to use, modify, and distribute with attribution.

---

<div align="center">

<br/>

**Built by [Saif ur Rahman](https://github.com/Saif8671)**

<br/>

[![GitHub](https://img.shields.io/badge/GitHub-Saif8671-100000?style=flat-square&logo=github)](https://github.com/Saif8671)&nbsp;
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/saif-ur-rahman-0211002b9)&nbsp;
[![Portfolio](https://img.shields.io/badge/Portfolio-Visit-00C7B7?style=flat-square&logo=netlify)](https://saif-portfolio8671.netlify.app)&nbsp;
[![Email](https://img.shields.io/badge/Email-Contact-D14836?style=flat-square&logo=gmail)](mailto:saifurrahman887@gmail.com)

<br/>

*No more paper registers. No more excuses.* 

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:059669,50:064e3b,100:0a0f0a&height=120&section=footer" width="100%"/>

</div>

## License
MIT
