"""
AttendX — Attendance Tracker v3
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, g
import sqlite3, os, csv, io, time, hashlib, secrets, threading
from datetime import datetime
from functools import lru_cache
from collections import OrderedDict
import qrcode
from io import BytesIO

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

QR_VALID_SECONDS = 120
DB_PATH = "attendance.db"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE       = os.getenv("TWILIO_PHONE", "")
SMS_THRESHOLD = 75

# ─── DB ───────────────────────────────────────────────────────────────────────
def get_db():
    """Return a per-request DB connection (reused via Flask g)."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")   # faster concurrent reads
        g.db.execute("PRAGMA synchronous=NORMAL") # safe + faster writes
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_db_standalone():
    """Get a new standalone connection (for use outside request context, e.g. threads)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_class_from_htno(htno):
    try:
        year   = htno[3:5]
        branch = htno[6:8]
        branch_map = {'02':'CSE','03':'ECE','04':'EEE','05':'MECH','06':'CIVIL','66':'AIML'}
        b  = branch_map.get(branch, f'BR{branch}')
        yr = 'Y1' if year == 'P1' else 'Y3'
        return f'{b}-{yr}'
    except:
        return 'GENERAL'

def init_db():
    db = get_db_standalone()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT, email TEXT, gender TEXT, dob TEXT,
        class_name TEXT, rollno TEXT
    );
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        faculty_id INTEGER NOT NULL,
        class_name TEXT NOT NULL,
        FOREIGN KEY(faculty_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS qr_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        class_id INTEGER NOT NULL,
        faculty_id INTEGER NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        session_label TEXT,
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        token_id INTEGER NOT NULL,
        marked_at TEXT NOT NULL,
        status TEXT DEFAULT 'present',
        UNIQUE(student_id, token_id),
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(class_id) REFERENCES classes(id)
    );
    """)

    # ── Indexes (biggest single performance win) ──────────────────────────────
    db.executescript("""
        CREATE INDEX IF NOT EXISTS idx_users_role       ON users(role);
        CREATE INDEX IF NOT EXISTS idx_users_class      ON users(class_name);
        CREATE INDEX IF NOT EXISTS idx_users_username   ON users(username);
        CREATE INDEX IF NOT EXISTS idx_att_student      ON attendance(student_id, class_id);
        CREATE INDEX IF NOT EXISTS idx_att_token        ON attendance(token_id);
        CREATE INDEX IF NOT EXISTS idx_att_status       ON attendance(student_id, class_id, status);
        CREATE INDEX IF NOT EXISTS idx_qr_class_active  ON qr_tokens(class_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_qr_faculty       ON qr_tokens(faculty_id);
        CREATE INDEX IF NOT EXISTS idx_qr_token         ON qr_tokens(token);
        CREATE INDEX IF NOT EXISTS idx_classes_faculty   ON classes(faculty_id);
        CREATE INDEX IF NOT EXISTS idx_classes_classname ON classes(class_name);
    """)

    # Migrate old DBs
    for col, typedef in [("email","TEXT"),("gender","TEXT"),("dob","TEXT")]:
        try: db.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
        except: pass

    # Only seed the admin account — all faculty, students, and subjects
    # are created dynamically through the admin dashboard.
    pw = lambda p: hashlib.sha256(p.encode()).hexdigest()
    try:
        db.execute("INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("admin", pw("admin123"), "admin", "Administrator", None, None, None, None, None, None))
    except: pass

    db.commit()
    db.close()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def send_sms(to, msg):
    if not TWILIO_ACCOUNT_SID:
        print(f"[SMS] To {to}: {msg}"); return True
    try:
        from twilio.rest import Client
        Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(body=msg, from_=TWILIO_PHONE, to=to)
        return True
    except Exception as e:
        print(f"SMS error: {e}"); return False

def check_and_notify(student_id, class_id):
    db = get_db()
    total   = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=? AND is_active=0", (class_id,)).fetchone()["c"]
    present = db.execute("SELECT COUNT(*) as c FROM attendance WHERE student_id=? AND class_id=? AND status='present'", (student_id, class_id)).fetchone()["c"]
    if total > 0:
        pct = (present / total) * 100
        if pct < SMS_THRESHOLD:
            student = db.execute("SELECT * FROM users WHERE id=?", (student_id,)).fetchone()
            cls     = db.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
            if student and student["phone"]:
                send_sms(student["phone"],
                    f"Attendance Alert: Dear {student['name']}, your attendance in {cls['subject']} is {pct:.1f}% ({present}/{total}). Min required: {SMS_THRESHOLD}%.")


# ─── AUTH ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(f"dashboard_{session['role']}"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip().lower()
    password = hash_pw(request.form["password"])
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()

    if user:
        session["user_id"] = user["id"]
        session["role"]    = user["role"]
        session["name"]    = user["name"]
        next_scan = session.pop("next_scan", None)
        if next_scan and user["role"] == "student":
            return redirect(url_for("scan_qr", token=next_scan))
        return redirect(url_for(f"dashboard_{user['role']}"))
    return render_template("login.html", error="Invalid username or password")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ─── PASSWORD RESET ───────────────────────────────────────────────────────────
@app.route("/admin/reset_password/<int:user_id>", methods=["POST"])
def reset_password(user_id):
    if session.get("role") != "admin": return redirect("/")
    new_pw = request.form.get("new_password","").strip()
    if not new_pw:
        return redirect(url_for("dashboard_admin") + "?msg=Password+cannot+be+empty")
    db = get_db()
    db.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_pw), user_id))
    db.commit()

    return redirect(url_for("dashboard_admin") + "?msg=Password+reset+successfully")

@app.route("/reset_my_password", methods=["POST"])
def reset_my_password():
    if "user_id" not in session: return redirect("/")
    old_pw  = request.form.get("old_password","")
    new_pw  = request.form.get("new_password","").strip()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=? AND password=?", (session["user_id"], hash_pw(old_pw))).fetchone()
    if not user:

        role = session["role"]
        return render_template(f"{role}.html", pw_error="Current password is incorrect",
                               **get_dashboard_data(role))
    db.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_pw), session["user_id"]))
    db.commit()
    return redirect(url_for(f"dashboard_{session['role']}") + "?msg=Password+changed+successfully")

def get_dashboard_data(role):
    """Helper to re-fetch data when re-rendering with an error"""
    db = get_db()
    if role == "student":
        student = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        attendance = db.execute("""
            SELECT c.subject, c.class_name, c.id as class_id,
                   COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
                   (SELECT COUNT(*) FROM qr_tokens q2 WHERE q2.class_id=c.id AND q2.is_active=0) as total_sessions
            FROM classes c LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=?
            WHERE c.class_name=? GROUP BY c.id
        """, (session["user_id"], student["class_name"])).fetchall()
        recent = db.execute("""
            SELECT a.marked_at, a.status, c.subject, q.session_label FROM attendance a
            JOIN qr_tokens q ON a.token_id=q.id JOIN classes c ON a.class_id=c.id
            WHERE a.student_id=? ORDER BY a.marked_at DESC LIMIT 10
        """, (session["user_id"],)).fetchall()
        return {"student": dict(student), "attendance": attendance, "recent": recent}

    return {}

# ─── ADMIN ────────────────────────────────────────────────────────────────────
@app.route("/admin")
def dashboard_admin():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) as c FROM users WHERE role='student'").fetchone()["c"],
        "faculty":  db.execute("SELECT COUNT(*) as c FROM users WHERE role='faculty'").fetchone()["c"],
        "classes":  db.execute("SELECT COUNT(*) as c FROM classes").fetchone()["c"],
        "sessions": db.execute("SELECT COUNT(*) as c FROM qr_tokens").fetchone()["c"],
    }
    # Pre-compute session counts per class_name (avoids correlated subquery per student)
    session_counts = {}
    for r in db.execute("""
        SELECT c.class_name, COUNT(*) as cnt
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id
        WHERE q.is_active=0 GROUP BY c.class_name
    """).fetchall():
        session_counts[r["class_name"]] = r["cnt"]

    students_raw = db.execute("""
        SELECT u.*,
        (SELECT COUNT(*) FROM attendance a WHERE a.student_id=u.id AND a.status='present') as present_count
        FROM users u WHERE u.role='student' ORDER BY u.class_name, u.rollno
    """).fetchall()
    students = []
    for s in students_raw:
        d = dict(s)
        d["total_sessions"] = session_counts.get(s["class_name"], 0)
        students.append(d)
    faculty_list = db.execute("SELECT * FROM users WHERE role='faculty' ORDER BY name").fetchall()
    classes = db.execute("SELECT c.*, u.name as faculty_name FROM classes c JOIN users u ON c.faculty_id=u.id ORDER BY c.class_name, c.subject").fetchall()

    msg   = request.args.get("msg", "")
    tab   = request.args.get("tab", "overview")
    errors = session.pop("csv_errors", [])
    return render_template("admin.html", stats=stats,
                           students=students,
                           classes=[dict(c) for c in classes],
                           faculty_list=[dict(f) for f in faculty_list],
                           msg=msg, active_tab=tab, csv_errors=errors)

@app.route("/admin/add_user", methods=["POST"])
def add_user():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    try:
        db.execute("INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (request.form["username"].strip(), hash_pw(request.form["password"]),
             request.form["role"], request.form["name"].strip(),
             request.form.get("phone",""), request.form.get("email",""),
             request.form.get("gender",""), request.form.get("dob",""),
             request.form.get("class_name",""), request.form.get("rollno","")))
        db.commit()
    except Exception as e:

        return redirect(url_for("dashboard_admin") + f"?msg=Error:+{str(e)[:60]}&tab=students")

    role = request.form["role"]
    tab  = "students" if role == "student" else "teachers"
    return redirect(url_for("dashboard_admin") + f"?msg=User+added+successfully&tab={tab}")

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    u = db.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
    tab = "teachers" if u and u["role"] == "faculty" else "students"
    db.execute("DELETE FROM attendance WHERE student_id=?", (user_id,))
    db.execute("DELETE FROM qr_tokens WHERE faculty_id=?", (user_id,))
    db.execute("DELETE FROM classes WHERE faculty_id=?", (user_id,))
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    return redirect(url_for("dashboard_admin") + f"?msg=User+deleted&tab={tab}")

# ─── SUBJECTS ─────────────────────────────────────────────────────────────────
@app.route("/admin/add_subject", methods=["POST"])
def add_subject():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    try:
        db.execute("INSERT INTO classes (subject,faculty_id,class_name) VALUES (?,?,?)",
            (request.form["subject"], int(request.form["faculty_id"]), request.form["class_name"]))
        db.commit()
    except: pass

    return redirect(url_for("dashboard_admin") + "?msg=Subject+added&tab=subjects")

@app.route("/admin/delete_subject/<int:class_id>", methods=["POST"])
def delete_subject(class_id):
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    db.execute("DELETE FROM attendance WHERE class_id=?", (class_id,))
    db.execute("DELETE FROM qr_tokens WHERE class_id=?", (class_id,))
    db.execute("DELETE FROM classes WHERE id=?", (class_id,))
    db.commit(); db.close()
    return redirect(url_for("dashboard_admin") + "?msg=Subject+deleted&tab=subjects")

# ─── IMPORT CSV ───────────────────────────────────────────────────────────────
@app.route("/admin/import_csv", methods=["POST"])
def import_csv():
    if session.get("role") != "admin": return redirect("/")
    file = request.files.get("csv_file")
    role = request.form.get("role", "student")
    if not file or not file.filename.endswith(".csv"):
        return redirect(url_for("dashboard_admin") + "?msg=Invalid+file&tab=import")

    raw = file.read()
    content = None
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try: content = raw.decode(enc); break
        except: pass
    if not content:
        return redirect(url_for("dashboard_admin") + "?msg=Could+not+read+file&tab=import")

    reader  = csv.DictReader(io.StringIO(content))
    success, skipped, errors = 0, 0, []
    default_pw_hash = hash_pw("student123")  # pre-compute once instead of per-row
    db = get_db()

    for i, raw_row in enumerate(reader, start=2):
        row = {k.strip(): (v.strip() if v else "") for k, v in raw_row.items() if k}
        if not any(row.values()): continue

        htno   = row.get("HTNO") or row.get("htno") or row.get("Hall Ticket No") or row.get("Roll No") or row.get("rollno") or ""
        name   = (row.get("Name") or row.get("name") or row.get("Student Name") or "").title()
        phone  = row.get("Phone No") or row.get("phone") or row.get("Mobile") or row.get("Mobile No") or ""
        email  = row.get("Email ID") or row.get("email") or row.get("Email") or ""
        gender = row.get("Gender") or row.get("gender") or ""
        dob    = row.get("Date of Birth") or row.get("dob") or row.get("DOB") or ""
        pwd    = row.get("password") or row.get("Password") or "student123"
        uname  = row.get("username") or row.get("Username") or ""
        class_name_csv = row.get("class_name") or row.get("Class") or row.get("Section") or ""

        if not name:
            errors.append(f"Row {i}: skipped — Name is empty"); skipped += 1; continue

        if not uname:
            uname = htno.lower().strip() if htno else name.replace(" ","").lower()[:15]

        if phone and not phone.startswith("+"):
            digits = "".join(c for c in phone if c.isdigit())
            phone = ("+91" + digits[-10:]) if digits else phone

        class_name = get_class_from_htno(htno) if htno else (class_name_csv or "GENERAL")

        pw_hash = default_pw_hash if pwd == "student123" else hash_pw(pwd)
        try:
            db.execute("INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (uname, pw_hash, role, name, phone, email, gender, dob, class_name, htno or uname))
            success += 1
        except sqlite3.IntegrityError:
            alt = uname + "_" + str(i)
            try:
                db.execute("INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (alt, pw_hash, role, name, phone, email, gender, dob, class_name, htno or uname))
                success += 1
            except:
                errors.append(f"Row {i} ({name}): duplicate — skipped"); skipped += 1
        except Exception as e:
            errors.append(f"Row {i} ({name}): {str(e)}"); skipped += 1

    db.commit()
    session["csv_errors"] = errors[:20]
    msg = f"Imported:+{success}+added" + (f",+{skipped}+skipped" if skipped else "")
    return redirect(url_for("dashboard_admin") + f"?msg={msg}&tab=import")

@app.route("/admin/preview_csv", methods=["POST"])
def preview_csv():
    if session.get("role") != "admin": return jsonify({"error": "unauthorized"})
    file = request.files.get("csv_file")
    if not file: return jsonify({"error": "no file"})
    raw = file.read()
    content = None
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try: content = raw.decode(enc); break
        except: pass
    if not content: return jsonify({"error": "encoding error"})
    reader  = csv.DictReader(io.StringIO(content))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows    = []
    for i, row in enumerate(reader):
        if i >= 5: break
        rows.append({k.strip(): v.strip() for k, v in row.items() if k})
    return jsonify({"headers": headers, "preview": rows})

# ─── MANUAL ATTENDANCE ────────────────────────────────────────────────────────
@app.route("/admin/manual_attendance", methods=["GET"])
def manual_attendance_page():
    if session.get("role") != "admin": return redirect("/")
    msg = request.args.get("msg","")
    return redirect(url_for("dashboard_admin") + f"?tab=manual&msg={msg}" if msg else url_for("dashboard_admin") + "?tab=manual")

@app.route("/admin/manual_attendance", methods=["POST"])
def manual_attendance_submit():
    if session.get("role") != "admin": return redirect("/")
    student_id = int(request.form["student_id"])
    class_id   = int(request.form["class_id"])
    status     = request.form.get("status","present")
    session_date = request.form.get("session_date", datetime.now().strftime("%Y-%m-%d"))
    db = get_db()

    # Create a virtual token for manual entry if no real session exists
    token = f"MANUAL_{student_id}_{class_id}_{session_date}_{secrets.token_hex(4)}"
    now   = time.time()
    db.execute("INSERT INTO qr_tokens (token,class_id,faculty_id,created_at,expires_at,session_label,is_active) VALUES (?,?,?,?,?,?,0)",
               (token, class_id, 1, now, now, f"Manual Entry {session_date}", 0))
    token_id = db.execute("SELECT id FROM qr_tokens WHERE token=?", (token,)).fetchone()["id"]

    try:
        db.execute("INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (?,?,?,?,?)",
                   (student_id, class_id, token_id, datetime.now().isoformat(), status))
        db.commit()
        msg = "Attendance+marked+successfully"
    except sqlite3.IntegrityError:
        db.execute("UPDATE attendance SET status=?, marked_at=? WHERE student_id=? AND token_id=?",
                   (status, datetime.now().isoformat(), student_id, token_id))
        db.commit()
        msg = "Attendance+updated"
    except Exception as e:
        msg = f"Error:+{str(e)[:60]}"

    return redirect(url_for("dashboard_admin") + f"?tab=manual&msg={msg}")

# ─── REPORTS API ──────────────────────────────────────────────────────────────
@app.route("/admin/attendance_report")
def attendance_report():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    # Single query instead of N+1 (one query per student)
    rows = db.execute("""
        SELECT u.id, u.name, u.rollno, u.class_name, c.subject, c.id as class_id,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present,
               (SELECT COUNT(*) FROM qr_tokens q WHERE q.class_id=c.id AND q.is_active=0) as total,
               ROUND(COUNT(CASE WHEN a.status='present' THEN 1 END)*100.0/
                     MAX((SELECT COUNT(*) FROM qr_tokens q WHERE q.class_id=c.id AND q.is_active=0),1),1) as pct
        FROM users u
        JOIN classes c ON c.class_name=u.class_name
        LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=u.id
        WHERE u.role='student'
        GROUP BY u.id, c.id
        ORDER BY u.class_name, u.rollno, u.name
    """).fetchall()
    # Group by student in Python (fast, avoids N separate queries)
    grouped = OrderedDict()
    for r in rows:
        key = r["id"]
        if key not in grouped:
            grouped[key] = {"id": r["id"], "name": r["name"], "rollno": r["rollno"] or "—",
                            "class_name": r["class_name"], "subjects": []}
        grouped[key]["subjects"].append({"subject": r["subject"], "class_id": r["class_id"],
                                          "present": r["present"], "total": r["total"], "pct": r["pct"]})
    return jsonify(list(grouped.values()))

@app.route("/admin/get_sessions/<int:class_id>")
def get_sessions_for_class(class_id):
    if session.get("role") != "admin": return jsonify([])
    db = get_db()
    rows = db.execute("SELECT id, session_label, created_at FROM qr_tokens WHERE class_id=? ORDER BY created_at DESC", (class_id,)).fetchall()

    return jsonify([dict(r) for r in rows])

@app.route("/admin/get_students_for_class/<int:class_id>")
def get_students_for_class(class_id):
    if session.get("role") != "admin": return jsonify([])
    db = get_db()
    cls = db.execute("SELECT class_name FROM classes WHERE id=?", (class_id,)).fetchone()
    if not cls: return jsonify([])
    rows = db.execute("SELECT id, name, rollno FROM users WHERE class_name=? AND role='student' ORDER BY rollno", (cls["class_name"],)).fetchall()

    return jsonify([dict(r) for r in rows])

# ─── FACULTY ──────────────────────────────────────────────────────────────────
@app.route("/faculty")
def dashboard_faculty():
    if session.get("role") != "faculty": return redirect("/")
    db = get_db()
    classes = db.execute("SELECT * FROM classes WHERE faculty_id=?", (session["user_id"],)).fetchall()
    recent_tokens = db.execute("""
        SELECT q.*, c.subject, c.class_name,
               (SELECT COUNT(*) FROM attendance a WHERE a.token_id=q.id) as marked_count
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id
        WHERE q.faculty_id=? ORDER BY q.created_at DESC LIMIT 10
    """, (session["user_id"],)).fetchall()
    msg = request.args.get("msg","")

    return render_template("faculty.html", classes=classes, recent_tokens=recent_tokens,
                           now=time.time(), qr_valid=QR_VALID_SECONDS, msg=msg)

@app.route("/faculty/generate_qr", methods=["POST"])
def generate_qr():
    if session.get("role") != "faculty": return redirect("/")
    class_id = int(request.form["class_id"])
    label    = request.form.get("label", datetime.now().strftime("%d %b %Y %H:%M"))
    db = get_db()

    # Find any still-active token for this class to close it and notify absentees
    prev = db.execute(
        "SELECT q.id, q.token, c.subject, c.class_name FROM qr_tokens q "
        "JOIN classes c ON q.class_id=c.id "
        "WHERE q.class_id=? AND q.faculty_id=? AND q.is_active=1",
        (class_id, session["user_id"])
    ).fetchone()

    db.execute("UPDATE qr_tokens SET is_active=0 WHERE class_id=? AND faculty_id=?",
               (class_id, session["user_id"]))
    db.commit()

    if prev:
        # Fire absentee notifications for the session just closed
        notify_absentees(prev["id"], class_id, prev["class_name"], prev["subject"])

    token = secrets.token_urlsafe(32)
    now   = time.time()
    db.execute("INSERT INTO qr_tokens (token,class_id,faculty_id,created_at,expires_at,session_label,is_active) VALUES (?,?,?,?,?,?,1)",
               (token, class_id, session["user_id"], now, now + QR_VALID_SECONDS, label))
    db.commit()
    return redirect(url_for("show_qr", token=token))

@app.route("/qr/<token>")
def show_qr(token):
    db = get_db()
    t = db.execute("SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=?", (token,)).fetchone()

    if not t: return "Invalid token", 404
    return render_template("qr_display.html", token=dict(t), now=time.time(), qr_valid=QR_VALID_SECONDS)

@lru_cache(maxsize=128)
def _generate_qr_bytes(scan_url):
    """Cache QR image bytes — same token always produces same image."""
    img = qrcode.make(scan_url)
    buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf.getvalue()

@app.route("/qr_image/<token>")
def qr_image(token):
    scan_url = request.host_url + f"scan/{token}"
    data = _generate_qr_bytes(scan_url)
    return send_file(BytesIO(data), mimetype="image/png",
                     max_age=300)  # browser cache for 5 min

@app.route("/faculty/attendance/<int:class_id>")
def faculty_attendance(class_id):
    if session.get("role") != "faculty": return redirect("/")
    db = get_db()
    cls = db.execute("SELECT * FROM classes WHERE id=? AND faculty_id=?", (class_id, session["user_id"])).fetchone()
    if not cls: return redirect(url_for("dashboard_faculty"))
    sessions_list = db.execute("SELECT * FROM qr_tokens WHERE class_id=? ORDER BY created_at DESC", (class_id,)).fetchall()
    students = db.execute("""
        SELECT u.*, COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count
        FROM users u LEFT JOIN attendance a ON a.student_id=u.id AND a.class_id=?
        WHERE u.class_name=? AND u.role='student' GROUP BY u.id ORDER BY u.rollno
    """, (class_id, cls["class_name"])).fetchall()
    total_sessions = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=? AND is_active=0", (class_id,)).fetchone()["c"]

    return render_template("faculty_attendance.html", cls=dict(cls), sessions=sessions_list,
                           students=students, total=total_sessions)

# ─── STUDENT ──────────────────────────────────────────────────────────────────
@app.route("/student")
def dashboard_student():
    if session.get("role") != "student": return redirect("/")
    db = get_db()
    student = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    # Dynamic: subjects come from admin-configured classes for this student's class
    attendance = db.execute("""
        SELECT c.subject, c.class_name, c.id as class_id,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
               (SELECT COUNT(*) FROM qr_tokens q2 WHERE q2.class_id=c.id AND q2.is_active=0) as total_sessions
        FROM classes c
        LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=?
        WHERE c.class_name=?
        GROUP BY c.id
    """, (session["user_id"], student["class_name"])).fetchall()
    recent = db.execute("""
        SELECT a.marked_at, a.status, c.subject, q.session_label FROM attendance a
        JOIN qr_tokens q ON a.token_id=q.id JOIN classes c ON a.class_id=c.id
        WHERE a.student_id=? ORDER BY a.marked_at DESC LIMIT 10
    """, (session["user_id"],)).fetchall()
    msg = request.args.get("msg","")

    return render_template("student.html", student=dict(student), attendance=attendance, recent=recent, msg=msg)

@app.route("/student/scanner")
def student_scanner():
    if session.get("role") != "student": return redirect("/")
    return render_template("student_scanner.html")

# ─── QR SCAN ──────────────────────────────────────────────────────────────────
@app.route("/scan/<token>")
def scan_qr(token):
    if "user_id" not in session:
        session["next_scan"] = token
        return redirect(url_for("index"))
    if session.get("role") != "student":
        return render_template("scan_result.html", success=False, msg="Only students can mark attendance.")
    db = get_db()
    t = db.execute("SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=? AND q.is_active=1", (token,)).fetchone()
    if not t:

        return render_template("scan_result.html", success=False, msg="Invalid or expired QR code.")
    if time.time() > t["expires_at"]:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=?", (token,))
        db.commit()
        return render_template("scan_result.html", success=False, msg="QR Code expired. Ask faculty to generate a new one.")
    student = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if student["class_name"] != t["class_name"]:

        return render_template("scan_result.html", success=False, msg="You are not enrolled in this class.")
    try:
        db.execute("INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (?,?,?,?,?)",
                   (session["user_id"], t["class_id"], t["id"], datetime.now().isoformat(), "present"))
        db.commit()
        check_and_notify(session["user_id"], t["class_id"])

        return render_template("scan_result.html", success=True,
                               msg=f"Attendance marked for {t['subject']}!",
                               subject=t["subject"], label=t["session_label"])
    except sqlite3.IntegrityError:

        return render_template("scan_result.html", success=False, msg="Attendance already marked for this session.")

@app.route("/api/token_status/<token>")
def token_status(token):
    db = get_db()
    t  = db.execute("SELECT * FROM qr_tokens WHERE token=?", (token,)).fetchone()

    if not t: return jsonify({"valid": False})
    remaining = max(0, t["expires_at"] - time.time())
    return jsonify({"valid": t["is_active"] == 1 and remaining > 0, "remaining": int(remaining)})

if __name__ == "__main__":
    init_db()
    print("\nAttendX running at http://localhost:5000")
    app.run(debug=True, port=5000)

# ─── SESSION CLOSE & ABSENTEE SMS ─────────────────────────────────────────────
def notify_absentees(token_id, class_id, class_name, subject):
    """
    Called when a QR session expires (runs in a background thread).
    Marks absent all students who did NOT scan, then sends SMS alerts.
    Uses a standalone DB connection since this runs outside the request context.
    """
    db = get_db_standalone()
    try:
        # All students in this class
        all_students = db.execute(
            "SELECT id, name, phone FROM users WHERE class_name=? AND role='student'",
            (class_name,)
        ).fetchall()

        # Students who already scanned (present)
        present_ids = set(
            r["student_id"] for r in
            db.execute("SELECT student_id FROM attendance WHERE token_id=?", (token_id,)).fetchall()
        )

        absent_count = 0
        absent_students = []
        for s in all_students:
            if s["id"] in present_ids:
                continue
            # Insert absent record (ignore if already exists)
            try:
                db.execute(
                    "INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (?,?,?,?,?)",
                    (s["id"], class_id, token_id, datetime.now().isoformat(), "absent")
                )
                absent_count += 1
            except sqlite3.IntegrityError:
                pass  # already recorded
            absent_students.append(s)

        db.commit()

        # Pre-compute total sessions ONCE (same for every student in this class)
        total = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=? AND is_active=0",
                           (class_id,)).fetchone()["c"]

        # Send SMS to absent students (batched after DB work)
        for s in absent_students:
            if not s["phone"]:
                continue
            send_sms(
                s["phone"],
                f"Attendance Alert: Dear {s['name']}, you were marked ABSENT for {subject} "
                f"class ({class_name}). If this is an error, contact your faculty."
            )
            # Check if overall attendance dropped below threshold
            if total > 0:
                present = db.execute(
                    "SELECT COUNT(*) as c FROM attendance WHERE student_id=? AND class_id=? AND status='present'",
                    (s["id"], class_id)).fetchone()["c"]
                pct = (present / total) * 100
                if pct < SMS_THRESHOLD:
                    send_sms(
                        s["phone"],
                        f"Low Attendance Warning: Dear {s['name']}, your attendance in {subject} "
                        f"is now {pct:.1f}% ({present}/{total} classes). Minimum required: {SMS_THRESHOLD}%."
                    )

        print(f"[AbsentSMS] token_id={token_id} | {subject} | {class_name} | {absent_count} absent marked")
        return absent_count
    finally:
        db.close()


@app.route("/faculty/close_session", methods=["POST"])
def close_session():
    """
    Called by the QR display page JS when countdown reaches zero.
    Closes the token and fires absentee SMS notifications.
    """
    if session.get("role") != "faculty":
        return jsonify({"ok": False, "error": "unauthorized"})

    token_str = request.json.get("token")
    if not token_str:
        return jsonify({"ok": False, "error": "no token"})

    db = get_db()
    t = db.execute(
        "SELECT q.*, c.subject, c.class_name FROM qr_tokens q "
        "JOIN classes c ON q.class_id=c.id WHERE q.token=?",
        (token_str,)
    ).fetchone()

    if not t:

        return jsonify({"ok": False, "error": "token not found"})

    already_closed = t["is_active"] == 0
    if not already_closed:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=?", (token_str,))
        db.commit()

    token_id   = t["id"]
    class_id   = t["class_id"]
    class_name = t["class_name"]
    subject    = t["subject"]


    # Run absentee notifications in background thread (don't block the response)
    threading.Thread(target=notify_absentees,
                     args=(token_id, class_id, class_name, subject), daemon=True).start()
    return jsonify({"ok": True, "already_closed": already_closed})