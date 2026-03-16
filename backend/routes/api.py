import time
import secrets
import threading
from datetime import datetime
from collections import OrderedDict
from flask import Blueprint, jsonify, request, session, current_app

from db.database import get_db
from utils.security import hash_pw
from utils.helpers import get_dashboard_data
from utils.notify import notify_absentees, check_and_notify

api_bp = Blueprint("api", __name__)

@api_bp.route("/health")
def health():
    return jsonify({"ok": True})

def _require_role(role):
    if session.get("role") != role:
        return jsonify({"error": "unauthorized"}), 401
    return None

# ---- Auth API ----

@api_bp.route("/api/auth/session")
def auth_session():
    if "user_id" not in session:
        return jsonify({"authenticated": False})
    return jsonify({
        "authenticated": True,
        "user_id": session.get("user_id"),
        "role": session.get("role"),
        "name": session.get("name"),
    })

@api_bp.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = hash_pw(data.get("password") or "")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password)).fetchone()
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]
    next_scan = session.pop("next_scan", None)
    return jsonify({"ok": True, "role": user["role"], "next_scan": next_scan})

@api_bp.route("/api/auth/signup", methods=["POST"])
def auth_signup():
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip().lower()
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    class_name = (data.get("class_name") or "").strip()
    rollno = (data.get("rollno") or "").strip()

    if role not in {"student", "faculty"}:
        return jsonify({"error": "Please choose Student or Faculty"}), 400
    if not name or not username or not password:
        return jsonify({"error": "Name, username, and password are required"}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400
    if role == "student" and not class_name:
        return jsonify({"error": "Class name is required for students"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username=%s", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already taken"}), 400

    db.execute(
        "INSERT INTO users (username,password,role,name,phone,email,class_name,rollno) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (username, hash_pw(password), role, name, phone, email, class_name if role == "student" else "", rollno),
    )
    db.commit()

    user = db.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
    if not user:
        return jsonify({"error": "Signup failed. Please try again."}), 400
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]
    return jsonify({"ok": True, "role": user["role"]})

@api_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})

# ---- Admin API ----

@api_bp.route("/api/admin/dashboard")
def admin_dashboard():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) as c FROM users WHERE role='student'").fetchone()["c"],
        "faculty": db.execute("SELECT COUNT(*) as c FROM users WHERE role='faculty'").fetchone()["c"],
        "classes": db.execute("SELECT COUNT(*) as c FROM classes").fetchone()["c"],
        "sessions": db.execute("SELECT COUNT(*) as c FROM qr_tokens").fetchone()["c"],
    }

    session_counts = {}
    for r in db.execute(
        """
        SELECT c.class_name, COUNT(*) as cnt
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id
        WHERE q.is_active=0 GROUP BY c.class_name
        """
    ).fetchall():
        session_counts[r["class_name"]] = r["cnt"]

    students_raw = db.execute(
        """
        SELECT u.*,
        (SELECT COUNT(*) FROM attendance a WHERE a.student_id=u.id AND a.status='present') as present_count
        FROM users u WHERE u.role='student' ORDER BY u.class_name, u.rollno
        """
    ).fetchall()
    students = []
    for s in students_raw:
        d = dict(s)
        d["total_sessions"] = session_counts.get(s["class_name"], 0)
        students.append(d)

    faculty_list = db.execute("SELECT * FROM users WHERE role='faculty' ORDER BY name").fetchall()
    classes = db.execute(
        "SELECT c.*, u.name as faculty_name FROM classes c JOIN users u ON c.faculty_id=u.id ORDER BY c.class_name, c.subject"
    ).fetchall()

    return jsonify({
        "stats": stats,
        "students": students,
        "faculty_list": [dict(f) for f in faculty_list],
        "classes": [dict(c) for c in classes],
    })

@api_bp.route("/api/admin/add_user", methods=["POST"])
def admin_add_user():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    try:
        get_db().execute(
            "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                data.get("username", "").strip(),
                hash_pw(data.get("password", "")),
                data.get("role"),
                data.get("name", "").strip(),
                data.get("phone", ""),
                data.get("email", ""),
                data.get("gender", ""),
                data.get("dob", ""),
                data.get("class_name", ""),
                data.get("rollno", ""),
            ),
        )
        get_db().commit()
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)[:60]}"}), 400
    return jsonify({"ok": True})

@api_bp.route("/api/admin/user/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    role_check = _require_role("admin")
    if role_check:
        return role_check
    db = get_db()
    db.execute("DELETE FROM attendance WHERE student_id=%s", (user_id,))
    db.execute("DELETE FROM qr_tokens WHERE faculty_id=%s", (user_id,))
    db.execute("DELETE FROM classes WHERE faculty_id=%s", (user_id,))
    db.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    return jsonify({"ok": True})

@api_bp.route("/api/admin/reset_password/<int:user_id>", methods=["POST"])
def admin_reset_password(user_id):
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    new_pw = (data.get("new_password") or "").strip()
    if not new_pw:
        return jsonify({"error": "Password cannot be empty"}), 400
    db = get_db()
    db.execute("UPDATE users SET password=%s WHERE id=%s", (hash_pw(new_pw), user_id))
    db.commit()
    return jsonify({"ok": True})

@api_bp.route("/api/admin/add_subject", methods=["POST"])
def admin_add_subject():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    try:
        get_db().execute(
            "INSERT INTO classes (subject,faculty_id,class_name) VALUES (%s,%s,%s)",
            (data.get("subject"), int(data.get("faculty_id")), data.get("class_name")),
        )
        get_db().commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})

@api_bp.route("/api/admin/subject/<int:class_id>", methods=["DELETE"])
def admin_delete_subject(class_id):
    role_check = _require_role("admin")
    if role_check:
        return role_check
    db = get_db()
    db.execute("DELETE FROM attendance WHERE class_id=%s", (class_id,))
    db.execute("DELETE FROM qr_tokens WHERE class_id=%s", (class_id,))
    db.execute("DELETE FROM classes WHERE id=%s", (class_id,))
    db.commit()
    return jsonify({"ok": True})

@api_bp.route("/api/admin/preview_csv", methods=["POST"])
def admin_preview_csv():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    file = request.files.get("csv_file")
    if not file:
        return jsonify({"headers": [], "preview": []})
    data = file.read().decode("utf-8", errors="ignore")
    import csv, io
    reader = csv.DictReader(io.StringIO(data))
    headers = reader.fieldnames or []
    rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        rows.append({k.strip(): v.strip() for k, v in row.items() if k})
    return jsonify({"headers": headers, "preview": rows})

@api_bp.route("/api/admin/import_csv", methods=["POST"])
def admin_import_csv():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    file = request.files.get("csv_file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    data = file.read().decode("utf-8", errors="ignore")
    import csv, io
    rows = list(csv.DictReader(io.StringIO(data)))
    errors = []
    db = get_db()
    for i, row in enumerate(rows, start=1):
        try:
            username = (row.get("username") or row.get("Username") or row.get("User", "")).strip().lower()
            password = row.get("password") or row.get("Password") or "student123"
            role = row.get("role") or row.get("Role") or "student"
            name = row.get("name") or row.get("Name") or ""
            phone = row.get("phone") or row.get("Phone") or ""
            email = row.get("email") or row.get("Email") or ""
            gender = row.get("gender") or row.get("Gender") or ""
            dob = row.get("dob") or row.get("DOB") or ""
            class_name = row.get("class_name") or row.get("Class") or ""
            rollno = row.get("rollno") or row.get("RollNo") or ""
            if not username or not name:
                raise ValueError("Missing username or name")
            db.execute(
                "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (username, hash_pw(password), role, name, phone, email, gender, dob, class_name, rollno),
            )
            db.commit()
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return jsonify({"ok": True, "errors": errors})

@api_bp.route("/api/admin/manual_attendance", methods=["POST"])
def admin_manual_attendance():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    student_id = int(data.get("student_id"))
    class_id = int(data.get("class_id"))
    status = data.get("status", "present")
    session_date = data.get("session_date", datetime.now().strftime("%Y-%m-%d"))
    db = get_db()
    token = f"MANUAL_{student_id}_{class_id}_{session_date}_{secrets.token_hex(4)}"
    now = time.time()
    db.execute(
        "INSERT INTO qr_tokens (token,class_id,faculty_id,created_at,expires_at,session_label,is_active) VALUES (%s,%s,%s,%s,%s,%s,0)",
        (token, class_id, 1, now, now, f"Manual Entry {session_date}", 0),
    )
    token_id = db.execute("SELECT id FROM qr_tokens WHERE token=%s", (token,)).fetchone()["id"]
    try:
        db.execute(
            "INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (%s,%s,%s,%s,%s)",
            (student_id, class_id, token_id, datetime.now().isoformat(), status),
        )
        db.commit()
    except Exception:
        db.execute(
            "UPDATE attendance SET status=%s, marked_at=%s WHERE student_id=%s AND token_id=%s",
            (status, datetime.now().isoformat(), student_id, token_id),
        )
        db.commit()
    return jsonify({"ok": True})

@api_bp.route("/api/admin/attendance_report")
def admin_attendance_report():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    db = get_db()
    rows = db.execute(
        """
        SELECT u.id, u.name, u.rollno, u.class_name, c.subject, c.id as class_id,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present,
               (SELECT COUNT(*) FROM qr_tokens q WHERE q.class_id=c.id AND q.is_active=0) as total,
               ROUND(COUNT(CASE WHEN a.status='present' THEN 1 END)*100.0/
                     MAX((SELECT COUNT(*) FROM qr_tokens q WHERE q.class_id=c.id AND q.is_active=0),1),1) as pct
        FROM users u
        JOIN classes c ON c.class_name=u.class_name
        LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=u.id
        WHERE u.role='student'
        GROUP BY u.id, u.name, u.rollno, u.class_name, c.subject, c.id
        ORDER BY u.class_name, u.rollno, u.name
        """
    ).fetchall()
    grouped = OrderedDict()
    for r in rows:
        key = r["id"]
        if key not in grouped:
            grouped[key] = {
                "id": r["id"],
                "name": r["name"],
                "rollno": r["rollno"] or "-",
                "class_name": r["class_name"],
                "subjects": [],
            }
        grouped[key]["subjects"].append(
            {"subject": r["subject"], "class_id": r["class_id"], "present": r["present"], "total": r["total"], "pct": r["pct"]}
        )
    return jsonify(list(grouped.values()))

# ---- Faculty API ----

@api_bp.route("/api/faculty/dashboard")
def faculty_dashboard():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    db = get_db()
    classes = db.execute("SELECT * FROM classes WHERE faculty_id=%s", (session["user_id"],)).fetchall()
    recent_tokens = db.execute(
        """
        SELECT q.*, c.subject, c.class_name,
               (SELECT COUNT(*) FROM attendance a WHERE a.token_id=q.id) as marked_count
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id
        WHERE q.faculty_id=%s ORDER BY q.created_at DESC LIMIT 10
        """,
        (session["user_id"],),
    ).fetchall()
    return jsonify({
        "classes": [dict(c) for c in classes],
        "recent_tokens": [dict(t) for t in recent_tokens],
        "name": session.get("name"),
        "qr_valid": current_app.config.get("QR_VALID_SECONDS", 120),
        "now": time.time(),
    })

@api_bp.route("/api/faculty/generate_qr", methods=["POST"])
def faculty_generate_qr():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    class_id = int(data.get("class_id"))
    label = data.get("label") or datetime.now().strftime("%d %b %Y %H:%M")
    db = get_db()
    prev = db.execute(
        "SELECT q.id, q.token, c.subject, c.class_name FROM qr_tokens q "
        "JOIN classes c ON q.class_id=c.id "
        "WHERE q.class_id=%s AND q.faculty_id=%s AND q.is_active=1",
        (class_id, session["user_id"]),
    ).fetchone()
    db.execute("UPDATE qr_tokens SET is_active=0 WHERE class_id=%s AND faculty_id=%s", (class_id, session["user_id"]))
    db.commit()
    if prev:
        notify_absentees(prev["id"], class_id, prev["class_name"], prev["subject"])
    token = secrets.token_urlsafe(32)
    now = time.time()
    db.execute(
        "INSERT INTO qr_tokens (token,class_id,faculty_id,created_at,expires_at,session_label,is_active) VALUES (%s,%s,%s,%s,%s,%s,1)",
        (token, class_id, session["user_id"], now, now + current_app.config.get("QR_VALID_SECONDS", 120), label),
    )
    db.commit()
    return jsonify({"ok": True, "token": token})

@api_bp.route("/api/faculty/class/<int:class_id>")
def faculty_class(class_id):
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    db = get_db()
    cls = db.execute("SELECT * FROM classes WHERE id=%s AND faculty_id=%s", (class_id, session["user_id"])).fetchone()
    if not cls:
        return jsonify({"error": "Class not found"}), 404
    sessions_list = db.execute("SELECT * FROM qr_tokens WHERE class_id=%s ORDER BY created_at DESC", (class_id,)).fetchall()
    students = db.execute(
        """
        SELECT u.*, COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count
        FROM users u LEFT JOIN attendance a ON a.student_id=u.id AND a.class_id=%s
        WHERE u.class_name=%s AND u.role='student' GROUP BY u.id ORDER BY u.rollno
        """,
        (class_id, cls["class_name"]),
    ).fetchall()
    total_sessions = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0", (class_id,)).fetchone()["c"]
    return jsonify({
        "cls": dict(cls),
        "sessions": [dict(s) for s in sessions_list],
        "students": [dict(s) for s in students],
        "total": total_sessions,
    })

@api_bp.route("/api/faculty/close_session", methods=["POST"])
def faculty_close_session():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    token_str = data.get("token")
    if not token_str:
        return jsonify({"ok": False, "error": "no token"}), 400
    db = get_db()
    t = db.execute("SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=%s", (token_str,)).fetchone()
    if not t:
        return jsonify({"ok": False, "error": "token not found"}), 404
    already_closed = (t["is_active"] == 0)
    if not already_closed:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=%s", (token_str,))
        db.commit()
    threading.Thread(target=notify_absentees, args=(t["id"], t["class_id"], t["class_name"], t["subject"]), daemon=True).start()
    return jsonify({"ok": True, "already_closed": already_closed})

# ---- QR / Student API ----

@api_bp.route("/api/qr/<token>")
def qr_info(token):
    db = get_db()
    t = db.execute(
        "SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=%s",
        (token,),
    ).fetchone()
    if not t:
        return jsonify({"error": "Invalid token"}), 404
    return jsonify(dict(t))

@api_bp.route("/api/student/dashboard")
def student_dashboard():
    role_check = _require_role("student")
    if role_check:
        return role_check
    return jsonify(get_dashboard_data("student"))

@api_bp.route("/api/scan/<token>")
def api_scan(token):
    if "user_id" not in session:
        session["next_scan"] = token
        return jsonify({"error": "Authentication required"}), 401
    if session.get("role") != "student":
        return jsonify({"error": "Only students can mark attendance."}), 403
    db = get_db()
    t = db.execute(
        "SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=%s AND q.is_active=1",
        (token,),
    ).fetchone()
    if not t:
        return jsonify({"success": False, "msg": "Invalid or expired QR code."}), 400
    if time.time() > t["expires_at"]:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=%s", (token,))
        db.commit()
        return jsonify({"success": False, "msg": "QR Code expired. Ask faculty to generate a new one."}), 400
    student = db.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()
    if student["class_name"] != t["class_name"]:
        return jsonify({"success": False, "msg": "You are not enrolled in this class."}), 403
    try:
        db.execute(
            "INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (%s,%s,%s,%s,%s)",
            (session["user_id"], t["class_id"], t["id"], datetime.now().isoformat(), "present"),
        )
        db.commit()
        return jsonify({"success": True, "msg": f"Attendance marked for {t['subject']}!", "subject": t["subject"], "label": t["session_label"]})
    except Exception:
        return jsonify({"success": False, "msg": "Attendance already marked for this session."}), 400
