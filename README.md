<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0f0a,50:064e3b,100:059669&height=220&section=header&text=AttendX&fontSize=72&fontColor=ffffff&fontAlignY=40&desc=Professional%20QR%20Attendance%20Platform&descSize=20&descAlignY=62&animation=fadeIn" width="100%"/>

<br/>

<a href="#"><img src="https://img.shields.io/badge/▶%20Live%20Demo-Visit%20App-059669?style=for-the-badge&logoColor=white"/></a>&nbsp;
<a href="#"><img src="https://img.shields.io/badge/📄%20Docs-Read%20Docs-064e3b?style=for-the-badge"/></a>&nbsp;
<a href="#-quick-start"><img src="https://img.shields.io/badge/⚡%20Quick%20Start-5%20Minutes-10b981?style=for-the-badge"/></a>

<br/><br/>

<img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=flat-square&logo=postgresql&logoColor=white"/>
<img src="https://img.shields.io/badge/Twilio-SMS-F22F46?style=flat-square&logo=twilio&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-059669?style=flat-square"/>

<br/><br/>

```text
╔══════════════════════════════════════════════════════════════╗
║  Professional QR-Based Attendance Platform                   ║
║  Designed for Speed, Security, and Seamless User Management. ║
╚══════════════════════════════════════════════════════════════╝
```

</div> 

## 🎯 The AttendX Edge

AttendX is a high-performance attendance tracking system that eliminates the friction of manual roll calls. By leveraging dynamic QR codes and a role-based architecture, it provides a tailored experience for educational and corporate environments.

| Challenge | AttendX Solution |
|---|---|
| 📋 Manual Paper Logs | ⚡ Instant QR scanning for attendance |
| ❌ Zero Visibility | 📊 Real-time dashboards with analytics |
| 🐌 Time Wastage | ⏱️ 2-minute auto-expiring QR sessions |
| 📭 Late Awareness | 📲 Automated SMS alerts for low attendance |
| 🗄️ Static Data | ☁️ Cloud-ready PostgreSQL integration |

---

## ✨ Features by Role

### 🛠️ Administrator
- **User Management**: Rapidly add or remove users.
- **Bulk Import**: Process entire classes via CSV.
- **Global Visibility**: Real-time stats across all subjects.
- **Manual Overrides**: Correct errors with manual attendance entries.

### 👨‍🏫 Faculty
- **Session Control**: Generate temporary QR codes for specific classes.
- **Live Monitoring**: Track attendance as it happens.
- **Auto-Notify**: Automatically mark absentees and notify them on session close.

### 🎓 Student
- **Integrated Scanner**: Built-in mobile-responsive QR scanner.
- **Personal Dashboard**: Subject-wise attendance percentages.
- **Activity Feed**: Full history of attendance scans.

---

## 🏗️ Technical Architecture

The project follows a **flatter, professional modular structure** to ensure low cognitive load and ease of deployment.

```text
attendance_tracker/
├── backend/                    
│   ├── app.py                  # API Server Entry Point
│   ├── config.py               # Centralized Configuration
│   ├── db/                     # Data Layer (PostgreSQL)
│   ├── routes/                 # Consolidated API Blueprint (api.py)
│   ├── utils/                  # Shared Business Logic & Helpers
│   ├── .env                    # Environment Secrets
│   └── requirements.txt        # Core Dependencies
└── frontend-react/             # Modern React Frontend
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **API** | Flask 3.x (Python 3.9+) |
| **Database** | Supabase / PostgreSQL |
| **Messaging** | Twilio SMS API |
| **Visuals** | QR Code Generation Engine (Pillow) |
| **Frontend** | React / Tailwind / Vite |
| **Server** | Gunicorn (Multi-worker) |

---

## ⚡ Quick Start

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python app.py
```
API runs at **[http://localhost:5000](http://localhost:5000)**.

### 2. Frontend Setup
```bash
cd frontend-react
npm install
npm run dev
```
Visit **[http://localhost:5173](http://localhost:5173)**.

If your backend is not running on `http://127.0.0.1:5000`, set `VITE_BACKEND_URL` in `frontend-react/.env` (see `frontend-react/.env.example`).

If your database already has tables named `profiles`, `classes`, etc. from another project, set `DB_SCHEMA` in `backend/.env` (default is `attendx`) to isolate AttendX tables.

---

## 🔐 Credentials (Local Demo)
| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin123` |
| Faculty | `faculty1` | `faculty123` |
| Student | `student1` | `student123` |

---

## 📄 License
Released under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ by [Saif ur Rahman](https://github.com/Saif8671)**

[![GitHub](https://img.shields.io/badge/GitHub-Saif8671-100000?style=flat-square&logo=github)](https://github.com/Saif8671)&nbsp;
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/saif-ur-rahman-0211002b9)

</div>
