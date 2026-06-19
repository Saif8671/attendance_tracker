<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0f0a,50:064e3b,100:059669&height=220&section=header&text=AttendX&fontSize=72&fontColor=ffffff&fontAlignY=40&desc=Professional%20QR%20Attendance%20Platform&descSize=20&descAlignY=62&animation=fadeIn" width="100%"/>

<br/>

<a href="#"><img src="https://img.shields.io/badge/▶%20Live%20Demo-Visit%20App-059669?style=for-the-badge&logoColor=white"/></a>&nbsp;
<a href="#"><img src="https://img.shields.io/badge/📄%20Docs-Read%20Docs-064e3b?style=for-the-badge"/></a>&nbsp;
<a href="#-quick-start"><img src="https://img.shields.io/badge/⚡%20Quick%20Start-5%20Minutes-10b981?style=for-the-badge"/></a>
<img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/Twilio-SMS-F22F46?style=flat-square&logo=twilio&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-059669?style=flat-square"/>

<br/><br/>
</div align="center">

# 📖 Overview

**AttendX** is a modern QR-code-based attendance management platform designed for educational institutions, training centers, and organizations that need a fast, reliable, and contactless attendance solution.

Traditional attendance systems often suffer from manual errors, time-consuming roll calls, and lack of visibility. AttendX eliminates these challenges through dynamic QR sessions, real-time attendance tracking, automated notifications, and role-based dashboards.

By combining speed, automation, and analytics, AttendX transforms attendance management into a seamless digital experience.

---

# 🎯 Mission

> Simplify attendance tracking through intelligent automation, real-time insights, and frictionless QR-based verification.

---

# ⚡ The AttendX Edge

| Challenge                    | AttendX Solution                   |
| ---------------------------- | ---------------------------------- |
| 📋 Manual Paper Logs         | ⚡ Instant QR-based attendance      |
| 🐌 Time-Consuming Roll Calls | 🚀 Attendance in seconds           |
| ❌ Limited Visibility         | 📊 Real-time analytics dashboard   |
| 📭 Delayed Notifications     | 📲 Automated SMS alerts            |
| 🔒 Static Sessions           | ⏱️ Auto-expiring QR sessions       |
| 📈 No Insights               | 📉 Attendance performance tracking |

---

# ✨ Key Features

| Feature                  | Description                              |
| ------------------------ | ---------------------------------------- |
| 📲 Dynamic QR Attendance | Temporary attendance QR codes            |
| 👨‍🏫 Faculty Dashboard  | Generate and monitor attendance sessions |
| 🎓 Student Portal        | Attendance history and statistics        |
| 🛠️ Admin Panel          | User management and attendance oversight |
| 📊 Analytics Dashboard   | Attendance trends and insights           |
| 📁 Bulk User Import      | CSV-based onboarding                     |
| 📲 SMS Notifications     | Automated absence and warning alerts     |
| ⏱️ Session Expiry        | QR codes automatically expire            |
| 🔄 Real-Time Updates     | Live attendance tracking                 |
| 📝 Manual Corrections    | Attendance override capabilities         |

---

# ⚙️ Technology Stack

<div align="center">

| Layer      | Technology           |
| ---------- | -------------------- |
| Frontend   | React + Vite         |
| Styling    | Tailwind CSS         |
| Backend    | Flask 3.x            |
| Language   | Python 3.9+          |
| QR Engine  | Pillow + QRCode      |
| Messaging  | Twilio SMS API       |
| Deployment | Gunicorn             |
| Storage    | In-Memory Data Store |

</div>

---

# 🏗️ Architecture

```text
Administrators / Faculty / Students
                │
                ▼
          React Frontend
                │
                ▼
           Flask API Layer
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼

 QR Engine   Attendance   SMS Service
 Generator    Manager      (Twilio)

      │
      ▼

 Attendance Analytics Engine
```

---

# 👥 User Roles & Capabilities

## 🛠️ Administrator

* User Management
* Attendance Monitoring
* CSV Bulk Imports
* Attendance Corrections
* Global Statistics Dashboard

### Key Benefits

✔ Complete system oversight

✔ Class-wide attendance analytics

✔ Administrative controls

---

## 👨‍🏫 Faculty

* QR Session Generation
* Attendance Monitoring
* Session Management
* Automatic Absence Processing
* SMS Notification Triggers

### Key Benefits

✔ Faster attendance collection

✔ Reduced manual effort

✔ Real-time visibility

---

## 🎓 Student

* QR Attendance Scanner
* Attendance Dashboard
* Attendance History
* Subject-wise Statistics
* Attendance Performance Tracking

### Key Benefits

✔ Quick attendance marking

✔ Attendance transparency

✔ Mobile-friendly experience

---

# 📊 Platform Modules

| Module                  | Description                      |
| ----------------------- | -------------------------------- |
| Attendance Engine       | QR-based attendance processing   |
| QR Session Manager      | Session creation and validation  |
| User Management         | Student, faculty, admin accounts |
| Analytics Dashboard     | Attendance statistics            |
| SMS Notification System | Automated messaging              |
| Bulk Import System      | CSV onboarding                   |
| Reporting Engine        | Attendance reports               |

---

# 🚀 Quick Start

## Prerequisites

* Python 3.9+
* Node.js 18+
* npm
* Twilio Account

---

## 1️⃣ Clone Repository

```bash
git clone <repository-url>

cd attendance_tracker
```

---

## 2️⃣ Backend Setup

```bash
cd backend

pip install -r requirements.txt

cp .env.example .env

python app.py
```

Runs on:

```text
http://localhost:5000
```

---

## 3️⃣ Frontend Setup

```bash
cd frontend-react

npm install

npm run dev
```

Runs on:

```text
http://localhost:5173
```

---

## 4️⃣ Environment Variables

### Backend

```env
TWILIO_ACCOUNT_SID=

TWILIO_AUTH_TOKEN=

TWILIO_PHONE_NUMBER=

SECRET_KEY=
```

### Frontend

```env
VITE_BACKEND_URL=http://127.0.0.1:5000
```

---

# 📁 Project Structure

```bash
attendance_tracker/

├── backend/
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   ├── utils/
│   ├── requirements.txt
│   └── .env
│
└── frontend-react/
    ├── src/
    ├── components/
    ├── pages/
    ├── services/
    └── assets/
```

---

# 🔐 Demo Credentials

| Role          | Username | Password |
| ------------- | -------- | -------- |
| Administrator | admin    | admin    |
| Faculty       | faculty1 | faculty1 |
| Student       | student1 | student1 |

---

# 📸 Screenshots

<img src="assets/dashboard.png" width="100%" />

<img src="assets/attendance-session.png" width="100%" />

<img src="assets/qr-scanner.png" width="100%" />

<img src="assets/analytics.png" width="100%" />

> Add screenshots or GIF demonstrations of QR generation, scanning, dashboards, and analytics.

---

# 📈 Future Roadmap

* [ ] Facial Recognition Attendance
* [ ] GPS-Based Attendance Validation
* [ ] Mobile Applications
* [ ] Biometric Integration
* [ ] Advanced Analytics & Reporting
* [ ] Attendance Forecasting
* [ ] Institution Multi-Tenant Support
* [ ] AI Attendance Insights
* [ ] Parent Notification Portal
* [ ] Cloud Database Integration

---

# 👥 Team

<div align="center">

| Member             | Role                                    |
| ------------------ | --------------------------------------- |
| **Saif Ur Rahman** | Full Stack Developer & System Architect |

</div>

---

# 📚 Documentation

Comprehensive documentation is available inside the `docs/` directory.

* System Architecture
* API Documentation
* Attendance Workflow
* QR Session Design
* Deployment Guide
* Security Practices
* Development Guidelines

---

<div align="center">

### 📲 Reinventing Attendance Management with QR Technology

Track Faster • Monitor Smarter • Automate Everything

Built with ❤️ by Saif Ur Rahman

</div>

## 📄 License
Released under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ by [Saif ur Rahman](https://github.com/Saif8671)**

[![GitHub](https://img.shields.io/badge/GitHub-Saif8671-100000?style=flat-square&logo=github)](https://github.com/Saif8671)&nbsp;
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/saif-ur-rahman-0211002b9)

</div>
