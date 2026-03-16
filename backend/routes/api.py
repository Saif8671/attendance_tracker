import time
import secrets
import threading
import time
import qrcode
from io import BytesIO
from datetime import datetime
from collections import OrderedDict
from functools import lru_cache
from flask import Blueprint, jsonify, request, session, current_app, send_file

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
    user = db.execute("SELECT * FROM profiles WHERE username=%s AND password=%s", (username, password)).fetchone()
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["full_name"]
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
    roll_no = (data.get("rollno") or "").strip()

    if role not in {"student", "faculty"}:
        return jsonify({"error": "Please choose Student or Faculty"}), 400
    if not name or not username or not password:
        return jsonify({"error": "Name, username, and password are required"}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM profiles WHERE username=%s", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already taken"}), 400

    # 1. Insert Profile
    db.execute(
        "INSERT INTO profiles (username, password, role, full_name, phone, email) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (username, hash_pw(password), role, name, phone, email),
    )
    user_id = db.fetchone()["id"]

    # 2. Add Role-Specific Profile
    if role == "student":
        cls = db.execute("SELECT id FROM classes WHERE section=%s LIMIT 1", (class_name,)).fetchone()
        if not cls:
             return jsonify({"error": "Class not found"}), 400
        db.execute(
            "INSERT INTO student_profiles (id, roll_no, class_id) VALUES (%s, %s, %s)",
            (user_id, roll_no, cls["id"])
        )
    else:
        db.execute("INSERT INTO faculty_profiles (id) VALUES (%s)", (user_id,))
    
    db.commit()
    session["user_id"] = user_id
    session["role"] = role
    session["name"] = name
    return jsonify({"ok": True, "role": role})


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
    stats = db.execute(
        """
        SELECT 
            (SELECT COUNT(*) FROM profiles WHERE role='student') as students,
            (SELECT COUNT(*) FROM profiles WHERE role='faculty') as faculty,
            (SELECT COUNT(*) FROM classes) as classes,
            (SELECT COUNT(*) FROM sessions) as sessions
        """
    ).fetchone()

    students_raw = db.execute(
        """
        SELECT 
            p.*, 
            p.full_name as name,
            sp.roll_no as rollno, 
            c.section as class_name, 
            sp.class_id, 
            COALESCE(att.present_count, 0) as present_count
        FROM profiles p
        JOIN student_profiles sp ON p.id = sp.id
        JOIN classes c ON sp.class_id = c.id
        LEFT JOIN (
            SELECT student_id, COUNT(*) as present_count
            FROM attendance_records
            WHERE status='present'
            GROUP BY student_id
        ) att ON p.id = att.student_id
        WHERE p.role='student'
        ORDER BY c.section, sp.roll_no
        """
    ).fetchall()
    
    students = []
    for s in students_raw:
        d = dict(s)
        d["name"] = s["full_name"]
        d["total_sessions"] = session_counts.get(str(s["class_id"]), 0)
        students.append(d)


    faculty_list = db.execute("SELECT * FROM profiles WHERE role='faculty' ORDER BY full_name").fetchall()
    classes = db.execute(
        """
        SELECT c.*, d.code as dept_code, p.full_name as faculty_name
        FROM classes c
        JOIN departments d ON c.department_id = d.id
        JOIN faculty_profiles fp ON fp.department_id = d.id -- This is a guess, might need a better join
        JOIN profiles p ON fp.id = p.id
        ORDER BY c.section, c.semester
        """
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
    role = (data.get("role") or "student").lower()
    if role == "student":
        return admin_add_student()
    return admin_add_faculty()

@api_bp.route("/api/admin/add_subject", methods=["POST"])
def admin_add_subject():
    return admin_add_class()

@api_bp.route("/api/admin/add_student", methods=["POST"])
def admin_add_student():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        # 1. Profile
        username = data.get("username", "").strip().lower()
        full_name = data.get("name", "").strip()
        db.execute(
            "INSERT INTO profiles (username,password,role,full_name,phone,email) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (
                username,
                hash_pw(data.get("password", "student123")),
                "student",
                full_name,
                data.get("phone", ""),
                data.get("email", ""),
            ),
        )
        profile_id = db.fetchone()["id"]

        # 2. Student Profile
        cls = db.execute("SELECT id FROM classes WHERE section=%s LIMIT 1", (data.get("class_name", ""),)).fetchone()
        if not cls:
             return jsonify({"error": f"Class '{data.get('class_name')}' not found"}), 400
             
        db.execute(
            "INSERT INTO student_profiles (id, roll_no, class_id) VALUES (%s,%s,%s)",
            (profile_id, data.get("rollno", ""), cls["id"]),
        )
        db.commit()
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)[:60]}"}), 400
    return jsonify({"ok": True})


@api_bp.route("/api/admin/add_faculty", methods=["POST"])
def admin_add_faculty():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        db.execute(
            "INSERT INTO profiles (username,password,role,full_name,phone,email) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (
                data.get("username", "").strip().lower(),
                hash_pw(data.get("password", "faculty123")),
                "faculty",
                data.get("name", ""),
                data.get("phone", ""),
                data.get("email", ""),
            ),
        )
        profile_id = db.fetchone()["id"]
        
        db.execute(
            "INSERT INTO faculty_profiles (id, employee_id) VALUES (%s, %s)",
            (profile_id, data.get("employee_id", ""))
        )
        db.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@api_bp.route("/api/admin/add_class", methods=["POST"])
def admin_add_class():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        # Note: In new schema, classes require department_id and dates
        dept = db.execute("SELECT id FROM departments LIMIT 1").fetchone() # Fallback for now
        if not dept:
             return jsonify({"error": "No departments found. Create one first."}), 400
             
        db.execute(
            "INSERT INTO classes (department_id, section, semester, academic_year_start, academic_year_end) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (dept["id"], data.get("class_name"), 4, "2025-01-01", "2025-12-31"),
        )
        db.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@api_bp.route("/api/admin/upload_users", methods=["POST"])
def admin_upload_users():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    rows = request.get_json(silent=True) or []
    db = get_db()
    errors = []
    
    # Pre-fetch classes for lookup
    classes_map = {c["section"]: c["id"] for c in db.execute("SELECT id, section FROM classes").fetchall()}
    
    for i, row in enumerate(rows):
        try:
            username = (row.get("username") or row.get("Username") or row.get("User", "")).strip().lower()
            password = row.get("password") or row.get("Password") or "student123"
            role = (row.get("role") or row.get("Role") or "student").strip().lower()
            name = row.get("name") or row.get("Name") or ""
            phone = row.get("phone") or row.get("Phone") or ""
            email = row.get("email") or row.get("Email") or ""
            class_name = row.get("class_name") or row.get("Class") or ""
            rollno = row.get("rollno") or row.get("Roll No") or ""

            db.execute(
                "INSERT INTO profiles (username, password, role, full_name, phone, email) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (username, hash_pw(password), role, name, phone, email),
            )
            profile_id = db.fetchone()["id"]
            
            if role == "student" and class_name:
                cls_id = classes_map.get(class_name)
                if cls_id:
                    db.execute(
                        "INSERT INTO student_profiles (id, roll_no, class_id) VALUES (%s, %s, %s)",
                        (profile_id, rollno, cls_id)
                    )
            elif role == "faculty":
                 db.execute("INSERT INTO faculty_profiles (id) VALUES (%s)", (profile_id,))
                 
            db.commit()
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return jsonify({"ok": True, "errors": errors})


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

@api_bp.route("/api/admin/manual_attendance", methods=["POST"])
def admin_manual_attendance():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    class_id = data.get("class_id")
    status = data.get("status", "present")
    
    db = get_db()
    try:
        # 1. Create a placeholder session if one doesn't exist for today
        db.execute(
            """
            INSERT INTO sessions (assignment_id, session_date, topic, status)
            SELECT id, CURRENT_DATE, 'Manual Entry', 'completed'
            FROM faculty_assignments
            WHERE class_id = %s LIMIT 1
            RETURNING id
            """,
            (class_id,)
        )
        session_id = db.fetchone()["id"]
        
        # 2. Mark attendance
        db.execute(
            """
            INSERT INTO attendance_records (session_id, student_id, status, method)
            VALUES (%s, %s, %s, 'manual')
            """,
            (session_id, student_id, status)
        )
        db.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@api_bp.route("/api/admin/attendance_report")
def admin_attendance_report():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    db = get_db()
    
    # Calculate session counts per assignment
    session_counts = {
        str(r["assignment_id"]): r["cnt"]
        for r in db.execute(
            "SELECT assignment_id, COUNT(*) as cnt FROM sessions WHERE status='completed' GROUP BY assignment_id"
        ).fetchall()
    }

    rows = db.execute(
        """
        SELECT 
            p.id, 
            p.full_name as name, 
            sp.roll_no as rollno, 
            c.section as class_name, 
            sub.name as subject, 
            fa.id as assignment_id,
            COUNT(CASE WHEN ar.status='present' THEN 1 END) as present
        FROM profiles p
        JOIN student_profiles sp ON p.id = sp.id
        JOIN classes c ON sp.class_id = c.id
        JOIN faculty_assignments fa ON fa.class_id = c.id
        JOIN subjects sub ON fa.subject_id = sub.id
        LEFT JOIN sessions s ON s.assignment_id = fa.id AND s.status='completed'
        LEFT JOIN attendance_records ar ON ar.session_id = s.id AND ar.student_id = p.id
        WHERE p.role='student'
        GROUP BY p.id, p.full_name, sp.roll_no, c.section, sub.name, fa.id
        ORDER BY c.section, sp.roll_no, sub.name
        """
    ).fetchall()

    grouped = OrderedDict()
    for r in rows:
        key = str(r["id"])
        if key not in grouped:
            grouped[key] = {
                "id": key,
                "name": r["name"],
                "rollno": r["rollno"] or "-",
                "class_name": r["class_name"],
                "subjects": [],
            }
        
        total = session_counts.get(str(r["assignment_id"]), 0)
        present = r["present"]
        pct = round((present * 100.0 / max(total, 1)), 1)
        
        grouped[key]["subjects"].append(
            {"subject": r["subject"], "present": present, "total": total, "pct": pct}
        )
    return jsonify(list(grouped.values()))

# ---- Faculty API ----

@api_bp.route("/api/faculty/dashboard")
def faculty_dashboard():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    db = get_db()
    # Get assignments for this faculty
    assignments = db.execute(
        """
        SELECT fa.id as assignment_id, c.section as class_name, c.semester, sub.name as subject, sub.code as subject_code, fa.class_id
        FROM faculty_assignments fa
        JOIN classes c ON fa.class_id = c.id
        JOIN subjects sub ON fa.subject_id = sub.id
        WHERE fa.faculty_id = %s
        """,
        (session["user_id"],)
    ).fetchall()

    recent_sessions = db.execute(
        """
        SELECT s.*, s.topic as session_label, sub.name as subject, c.section as class_name,
               (SELECT COUNT(*) FROM attendance_records ar WHERE ar.session_id=s.id) as marked_count
        FROM sessions s
        JOIN faculty_assignments fa ON s.assignment_id = fa.id
        JOIN subjects sub ON fa.subject_id = sub.id
        JOIN classes c ON fa.class_id = c.id
        WHERE fa.faculty_id=%s ORDER BY s.created_at DESC LIMIT 10
        """,
        (session["user_id"],),
    ).fetchall()
    
    # Map for frontend compatibility
    classes = []
    for a in assignments:
        d = dict(a)
        d["id"] = a["class_id"] # Faculty.jsx expects class_id as id for generating QR
        classes.append(d)

    return jsonify({
        "classes": classes,
        "assignments": [dict(a) for a in assignments],
        "recent_tokens": [dict(s) for s in recent_sessions],
        "recent_sessions": [dict(s) for s in recent_sessions],
        "name": session.get("name"),
    })

@api_bp.route("/api/faculty/generate_qr", methods=["POST"])
def faculty_generate_qr():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    
    assignment_id = data.get("assignment_id")
    class_id = data.get("class_id")
    topic = data.get("topic") or data.get("label") or "Lecture"
    
    db = get_db()
    if not assignment_id and class_id:
        # Backward compatibility: find assignment for this class/faculty
        res = db.execute(
            "SELECT id FROM faculty_assignments WHERE faculty_id=%s AND class_id=%s LIMIT 1",
            (session["user_id"], class_id)
        ).fetchone()
        if res:
            assignment_id = res["id"]
            
    if not assignment_id:
        return jsonify({"error": "Assignment not found"}), 400

    # 1. Create a Session
    db.execute(
        """
        INSERT INTO sessions (assignment_id, session_date, start_time, end_time, topic, status)
        VALUES (%s, CURRENT_DATE, CURRENT_TIME, (CURRENT_TIME + INTERVAL '1 hour'), %s, 'ongoing')
        RETURNING id
        """,
        (assignment_id, topic)
    )
    session_id = db.fetchone()["id"]
    
    # 2. Generate Token
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO qr_tokens (session_id, token, expires_at) VALUES (%s, %s, NOW() + INTERVAL '2 minutes')",
        (session_id, token)
    )
    db.commit()
    return jsonify({"ok": True, "token": token})

@api_bp.route("/api/faculty/class/<uuid:class_id>") # Using UUID converter
def faculty_class(class_id):
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    db = get_db()
    # Find all sessions for this faculty in this class
    students = db.execute(
        """
        SELECT p.full_name as name, sp.roll_no, 
               COUNT(CASE WHEN ar.status='present' THEN 1 END) as present_count
        FROM profiles p
        JOIN student_profiles sp ON p.id = sp.id
        LEFT JOIN attendance_records ar ON ar.student_id = sp.id
        WHERE sp.class_id = %s
        GROUP BY p.id, sp.roll_no
        ORDER BY sp.roll_no
        """,
        (class_id,),
    ).fetchall()
    
    return jsonify({
        "students": [dict(s) for s in students],
    })

# ---- QR / Student API ----

@api_bp.route("/api/qr/<token>")
def qr_info(token):
    db = get_db()
    t = db.execute(
        """
        SELECT qt.*, s.topic, sub.name as subject, c.section
        FROM qr_tokens qt
        JOIN sessions s ON qt.session_id = s.id
        JOIN faculty_assignments fa ON s.assignment_id = fa.id
        JOIN subjects sub ON fa.subject_id = sub.id
        JOIN classes c ON fa.class_id = c.id
        WHERE qt.token=%s
        """,
        (token,),
    ).fetchone()
    if not t:
        return jsonify({"error": "Invalid token"}), 404
    return jsonify(dict(t))

@api_bp.route("/api/scan/<token>")
def api_scan(token):
    if "user_id" not in session:
        session["next_scan"] = token
        return jsonify({"error": "Authentication required"}), 401
    
    db = get_db()
    t = db.execute(
        """
        SELECT qt.id as token_id, qt.session_id, qt.expires_at, qt.is_active,
               sub.name as subject, fa.class_id
        FROM qr_tokens qt
        JOIN sessions s ON qt.session_id = s.id
        JOIN faculty_assignments fa ON s.assignment_id = fa.id
        JOIN subjects sub ON fa.subject_id = sub.id
        WHERE qt.token=%s
        """,
        (token,),
    ).fetchone()
    
    if not t or not t["is_active"] or datetime.now() > t["expires_at"]:
        return jsonify({"success": False, "msg": "QR Code expired or invalid."}), 400
        
    # Check enrollment
    enrolled = db.execute(
        "SELECT 1 FROM student_profiles WHERE id=%s AND class_id=%s",
        (session["user_id"], t["class_id"])
    ).fetchone()
    if not enrolled:
        return jsonify({"success": False, "msg": "You are not enrolled in this class."}), 403

    try:
        db.execute(
            """
            INSERT INTO attendance_records (session_id, student_id, qr_token_id, status, method)
            VALUES (%s, %s, %s, 'present', 'qr')
            """,
            (t["session_id"], session["user_id"], t["token_id"])
        )
        db.commit()
        return jsonify({"success": True, "msg": f"Attendance marked for {t['subject']}!"})
    except Exception:
        return jsonify({"success": False, "msg": "Already marked for this session."}), 400


@lru_cache(maxsize=128)
def _generate_qr_bytes(scan_url):
    img = qrcode.make(scan_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

@api_bp.route("/qr_image/<token>")
def qr_image(token):
    scan_url = request.host_url + f"scan/{token}"
    data = _generate_qr_bytes(scan_url)
    return send_file(BytesIO(data), mimetype="image/png", max_age=300)
