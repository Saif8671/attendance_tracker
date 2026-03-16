import secrets
import threading
import time
import qrcode
from io import BytesIO
from datetime import datetime, date, timedelta
from collections import OrderedDict
from functools import lru_cache
from flask import Blueprint, jsonify, request, session, current_app, send_file

from db.database import get_db
from utils.helpers import get_dashboard_data
from utils.notify import notify_absentees_supabase, check_and_notify_supabase
from utils.supabase_auth import SupabaseAuthError, sign_in_with_password, sign_up

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health():
    return jsonify({"ok": True})


def _require_role(role):
    if session.get("role") != role:
        return jsonify({"error": "unauthorized"}), 401
    return None


def _class_lookup_by_label(label: str):
    """
    Accepts: "CSE", "CSE-A", "CSE A", "cse-a"
    Uses DEFAULT_SEMESTER if semester is not specified in the label.
    """
    label = (label or "").strip().upper().replace("_", "-").replace(" ", "-")
    if not label:
        return None
    parts = [p for p in label.split("-") if p]
    dept_code = parts[0]
    section = parts[1] if len(parts) >= 2 else "A"
    semester = int(current_app.config.get("DEFAULT_SEMESTER", 4))

    db = get_db()
    return db.execute(
        """
        SELECT c.*, d.code as department_code, d.name as department_name
        FROM classes c
        JOIN departments d ON d.id=c.department_id
        WHERE d.code=%s AND c.section=%s AND c.semester=%s
        ORDER BY c.academic_year_start DESC
        LIMIT 1
        """,
        (dept_code, section, semester),
    ).fetchone()


def _class_label(cls_row: dict):
    return f"{cls_row['department_code']}-{cls_row['section']} (S{cls_row['semester']})"


def _get_assignment(assignment_id: str):
    db = get_db()
    return db.execute(
        """
        SELECT fa.*, sub.name as subject_name,
               c.section, c.semester, c.id as cls_id,
               d.code as department_code,
               p.full_name as faculty_name
        FROM faculty_assignments fa
        JOIN subjects sub ON sub.id=fa.subject_id
        JOIN classes c ON c.id=fa.class_id
        JOIN departments d ON d.id=c.department_id
        JOIN profiles p ON p.id=fa.faculty_id
        WHERE fa.id=%s
        """,
        (assignment_id,),
    ).fetchone()


def _ensure_admin():
    role_check = _require_role("admin")
    if role_check:
        return role_check
    return None


# ---- Auth API (Supabase-backed) ----


@api_bp.route("/api/auth/session")
def auth_session():
    if "user_id" not in session:
        return jsonify({"authenticated": False})
    return jsonify(
        {
            "authenticated": True,
            "user_id": session.get("user_id"),
            "role": session.get("role"),
            "name": session.get("name"),
        }
    )


@api_bp.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    db = get_db()
    prof = db.execute(
        "SELECT id, role, full_name, email FROM profiles WHERE username=%s",
        (username,),
    ).fetchone()
    if not prof or not prof.get("email"):
        return jsonify({"error": "Invalid username or password"}), 401

    try:
        sign_in_with_password(prof["email"], password)
    except SupabaseAuthError:
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = str(prof["id"])
    session["role"] = prof["role"]
    session["name"] = prof["full_name"]
    next_scan = session.pop("next_scan", None)
    return jsonify({"ok": True, "role": prof["role"], "next_scan": next_scan})


@api_bp.route("/api/auth/signup", methods=["POST"])
def auth_signup():
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip().lower()
    full_name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    class_name = (data.get("class_name") or "").strip()
    rollno = (data.get("rollno") or "").strip()

    if role not in {"student", "faculty"}:
        return jsonify({"error": "Please choose Student or Faculty"}), 400
    if not full_name or not username or not password:
        return jsonify({"error": "Name, username, and password are required"}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    if not email:
        email = f"{username}@attendx.local"

    try:
        res = sign_up(
            email=email,
            password=password,
            user_metadata={"role": role, "full_name": full_name, "username": username},
        )
    except SupabaseAuthError as e:
        return jsonify({"error": str(e)}), 400

    user = (res or {}).get("user") or {}
    user_id = user.get("id")
    if not user_id:
        return jsonify({"error": "Signup failed. Please try again."}), 400

    db = get_db()
    db.execute(
        """
        INSERT INTO profiles (id, role, full_name, username, phone, email)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET
          role=EXCLUDED.role,
          full_name=EXCLUDED.full_name,
          username=EXCLUDED.username,
          phone=EXCLUDED.phone,
          email=EXCLUDED.email
        """,
        (user_id, role, full_name, username, phone or None, email),
    )
    db.commit()

    if role == "student":
        if class_name:
            cls = _class_lookup_by_label(class_name)
            if not cls:
                return jsonify({"error": f"Class '{class_name}' not found. Ask admin to create it."}), 400
            roll_no = rollno or username.upper()
            db.execute(
                """
                INSERT INTO student_profiles (id, roll_no, class_id)
                VALUES (%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET roll_no=EXCLUDED.roll_no, class_id=EXCLUDED.class_id
                """,
                (user_id, roll_no, cls["id"]),
            )
            db.commit()
    else:
        dept_id = None
        if class_name:
            cls = _class_lookup_by_label(class_name)
            dept_id = cls["department_id"] if cls else None
        db.execute(
            "INSERT INTO faculty_profiles (id, department_id) VALUES (%s,%s) ON CONFLICT (id) DO NOTHING",
            (user_id, dept_id),
        )
        db.commit()

    session["user_id"] = str(user_id)
    session["role"] = role
    session["name"] = full_name
    return jsonify({"ok": True, "role": role})


@api_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


# ---- Admin API ----


@api_bp.route("/api/admin/dashboard")
def admin_dashboard():
    role_check = _ensure_admin()
    if role_check:
        return role_check

    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) as c FROM profiles WHERE role='student'").fetchone()["c"],
        "faculty": db.execute("SELECT COUNT(*) as c FROM profiles WHERE role='faculty'").fetchone()["c"],
        "classes": db.execute("SELECT COUNT(*) as c FROM faculty_assignments").fetchone()["c"],
        "sessions": db.execute("SELECT COUNT(*) as c FROM qr_tokens").fetchone()["c"],
    }

    students = db.execute(
        """
        SELECT
          p.id,
          p.username,
          p.full_name as name,
          p.phone,
          p.email,
          sp.roll_no as rollno,
          d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name,
          (
            SELECT COUNT(*)
            FROM attendance_records ar
            WHERE ar.student_id = sp.id AND ar.status in ('present','late')
          ) as present_count,
          (
            SELECT COUNT(*)
            FROM sessions s
            JOIN faculty_assignments fa ON fa.id=s.assignment_id
            WHERE fa.class_id = sp.class_id AND s.status='completed'
          ) as total_sessions
        FROM profiles p
        JOIN student_profiles sp ON sp.id=p.id
        JOIN classes c ON c.id=sp.class_id
        JOIN departments d ON d.id=c.department_id
        WHERE p.role='student'
        ORDER BY d.code, c.section, sp.roll_no, p.full_name
        """
    ).fetchall()

    faculty_list = db.execute(
        "SELECT id, username, full_name as name, phone, email FROM profiles WHERE role='faculty' ORDER BY full_name"
    ).fetchall()

    classes = db.execute(
        """
        SELECT
          fa.id,
          sub.name as subject,
          p.id as faculty_id,
          p.full_name as faculty_name,
          d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name
        FROM faculty_assignments fa
        JOIN subjects sub ON sub.id=fa.subject_id
        JOIN classes c ON c.id=fa.class_id
        JOIN departments d ON d.id=c.department_id
        JOIN profiles p ON p.id=fa.faculty_id
        ORDER BY class_name, subject, faculty_name
        """
    ).fetchall()

    return jsonify(
        {
            "stats": stats,
            "students": [dict(s) for s in students],
            "faculty_list": [dict(f) for f in faculty_list],
            "classes": [dict(c) for c in classes],
        }
    )


@api_bp.route("/api/admin/add_user", methods=["POST"])
def admin_add_user():
    role_check = _ensure_admin()
    if role_check:
        return role_check
    return jsonify({"error": "Use Supabase Auth to create users; then update roles in profiles."}), 501


@api_bp.route("/api/admin/user/<user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    role_check = _ensure_admin()
    if role_check:
        return role_check
    return jsonify({"error": "Delete users via Supabase Auth dashboard."}), 501


@api_bp.route("/api/admin/reset_password/<user_id>", methods=["POST"])
def admin_reset_password(user_id):
    role_check = _ensure_admin()
    if role_check:
        return role_check
    return jsonify({"error": "Reset passwords via Supabase Auth dashboard."}), 501


def _generate_subject_code(dept_code: str, semester: int):
    base = f"{dept_code}{semester}"
    for _ in range(10):
        code = base + secrets.token_hex(2).upper()
        exists = get_db().execute("SELECT 1 as ok FROM subjects WHERE code=%s", (code,)).fetchone()
        if not exists:
            return code
    return base + secrets.token_hex(4).upper()


@api_bp.route("/api/admin/add_subject", methods=["POST"])
def admin_add_subject():
    role_check = _ensure_admin()
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    subject_name = (data.get("subject") or "").strip()
    faculty_id = (data.get("faculty_id") or "").strip()
    class_name = (data.get("class_name") or "").strip()
    if not subject_name or not faculty_id or not class_name:
        return jsonify({"error": "subject, faculty_id, class_name are required"}), 400

    cls = _class_lookup_by_label(class_name)
    if not cls:
        return jsonify({"error": f"Class '{class_name}' not found."}), 400

    db = get_db()
    subj = db.execute(
        "SELECT id FROM subjects WHERE name=%s AND department_id=%s AND semester=%s",
        (subject_name, cls["department_id"], cls["semester"]),
    ).fetchone()
    if not subj:
        code = _generate_subject_code(cls["department_code"], int(cls["semester"]))
        subj = db.execute(
            "INSERT INTO subjects (department_id, name, code, semester) VALUES (%s,%s,%s,%s) RETURNING id",
            (cls["department_id"], subject_name, code, int(cls["semester"])),
        ).fetchone()
        db.commit()

    db.execute(
        """
        INSERT INTO faculty_assignments (faculty_id, class_id, subject_id)
        VALUES (%s,%s,%s)
        ON CONFLICT (faculty_id, class_id, subject_id) DO NOTHING
        """,
        (faculty_id, cls["id"], subj["id"]),
    )
    db.commit()
    return jsonify({"ok": True})


@api_bp.route("/api/admin/subject/<assignment_id>", methods=["DELETE"])
def admin_delete_subject(assignment_id):
    role_check = _ensure_admin()
    if role_check:
        return role_check
    db = get_db()
    db.execute("DELETE FROM faculty_assignments WHERE id=%s", (assignment_id,))
    db.commit()
    return jsonify({"ok": True})


@api_bp.route("/api/admin/preview_csv", methods=["POST"])
def admin_preview_csv():
    role_check = _ensure_admin()
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
    role_check = _ensure_admin()
    if role_check:
        return role_check
    return jsonify({"error": "Bulk import must be implemented via Supabase Auth admin APIs."}), 501


@api_bp.route("/api/admin/manual_attendance", methods=["POST"])
def admin_manual_attendance():
    role_check = _ensure_admin()
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    student_id = (data.get("student_id") or "").strip()
    assignment_id = (data.get("class_id") or "").strip()
    status = (data.get("status") or "present").strip().lower()
    session_date = (data.get("session_date") or date.today().isoformat()).strip()
    if not student_id or not assignment_id:
        return jsonify({"error": "student_id and class_id are required"}), 400

    db = get_db()
    session_row = db.execute(
        """
        INSERT INTO sessions (assignment_id, session_date, start_time, end_time, topic, status)
        VALUES (%s,%s,%s,%s,%s,'completed')
        RETURNING id
        """,
        (assignment_id, session_date, "00:00", "00:01", "Manual Entry"),
    ).fetchone()
    db.execute(
        """
        INSERT INTO attendance_records (session_id, student_id, status, method)
        VALUES (%s,%s,%s,'manual')
        ON CONFLICT (session_id, student_id) DO UPDATE SET status=EXCLUDED.status, method='manual', marked_at=now()
        """,
        (session_row["id"], student_id, status),
    )
    db.commit()
    return jsonify({"ok": True})


@api_bp.route("/api/admin/attendance_report")
def admin_attendance_report():
    role_check = _ensure_admin()
    if role_check:
        return role_check

    db = get_db()
    rows = db.execute(
        """
        SELECT
          sp.id as student_id,
          p.full_name as name,
          sp.roll_no as rollno,
          d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name,
          fa.id as assignment_id,
          sub.name as subject,
          COUNT(DISTINCT s.id) FILTER (WHERE s.status='completed') as total,
          COUNT(DISTINCT ar.id) FILTER (WHERE ar.status in ('present','late')) as present
        FROM student_profiles sp
        JOIN profiles p ON p.id=sp.id
        JOIN classes c ON c.id=sp.class_id
        JOIN departments d ON d.id=c.department_id
        JOIN faculty_assignments fa ON fa.class_id=sp.class_id
        JOIN subjects sub ON sub.id=fa.subject_id
        LEFT JOIN sessions s ON s.assignment_id=fa.id AND s.status='completed'
        LEFT JOIN attendance_records ar ON ar.session_id=s.id AND ar.student_id=sp.id
        GROUP BY sp.id, p.full_name, sp.roll_no, class_name, fa.id, sub.name
        ORDER BY class_name, sp.roll_no, p.full_name, sub.name
        """
    ).fetchall()

    grouped = OrderedDict()
    for r in rows:
        sid = r["student_id"]
        if sid not in grouped:
            grouped[sid] = {
                "id": sid,
                "name": r["name"],
                "rollno": r["rollno"] or "-",
                "class_name": r["class_name"],
                "subjects": [],
            }
        total = int(r["total"] or 0)
        present = int(r["present"] or 0)
        pct = round((present * 100.0 / max(total, 1)), 1)
        grouped[sid]["subjects"].append(
            {"subject": r["subject"], "class_id": r["assignment_id"], "present": present, "total": total, "pct": pct}
        )

    return jsonify(list(grouped.values()))


# ---- Faculty API ----


@api_bp.route("/api/faculty/dashboard")
def faculty_dashboard():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    db = get_db()
    classes = db.execute(
        """
        SELECT fa.id, sub.name as subject,
               d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name
        FROM faculty_assignments fa
        JOIN subjects sub ON sub.id=fa.subject_id
        JOIN classes c ON c.id=fa.class_id
        JOIN departments d ON d.id=c.department_id
        WHERE fa.faculty_id=%s
        ORDER BY class_name, subject
        """,
        (session["user_id"],),
    ).fetchall()

    recent_tokens = db.execute(
        """
        SELECT qt.*, sub.name as subject,
               d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name,
               (SELECT COUNT(*) FROM attendance_records ar WHERE ar.session_id=qt.session_id AND ar.status in ('present','late')) as marked_count
        FROM qr_tokens qt
        JOIN sessions s ON s.id=qt.session_id
        JOIN faculty_assignments fa ON fa.id=s.assignment_id
        JOIN subjects sub ON sub.id=fa.subject_id
        JOIN classes c ON c.id=fa.class_id
        JOIN departments d ON d.id=c.department_id
        WHERE fa.faculty_id=%s
        ORDER BY qt.created_at DESC
        LIMIT 10
        """,
        (session["user_id"],),
    ).fetchall()

    return jsonify(
        {
            "classes": [dict(c) for c in classes],
            "recent_tokens": [dict(t) for t in recent_tokens],
            "name": session.get("name"),
            "qr_valid": current_app.config.get("QR_VALID_SECONDS", 120),
            "now": time.time(),
        }
    )


@api_bp.route("/api/faculty/generate_qr", methods=["POST"])
def faculty_generate_qr():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    assignment_id = str(data.get("class_id") or "").strip()
    label = (data.get("label") or datetime.now().strftime("%d %b %Y %H:%M")).strip()
    if not assignment_id:
        return jsonify({"error": "class_id is required"}), 400

    a = _get_assignment(assignment_id)
    if not a or str(a["faculty_id"]) != str(session["user_id"]):
        return jsonify({"error": "Class not found"}), 404

    db = get_db()
    prev = db.execute(
        """
        SELECT qt.id as token_id, qt.token, qt.session_id
        FROM qr_tokens qt
        JOIN sessions s ON s.id=qt.session_id
        WHERE s.assignment_id=%s AND qt.is_active=true
        ORDER BY qt.created_at DESC
        LIMIT 1
        """,
        (assignment_id,),
    ).fetchone()
    if prev:
        db.execute("UPDATE qr_tokens SET is_active=false WHERE session_id=%s", (prev["session_id"],))
        db.execute("UPDATE sessions SET status='completed' WHERE id=%s", (prev["session_id"],))
        db.commit()
        notify_absentees_supabase(prev["session_id"])

    start = datetime.now()
    end = start + timedelta(hours=1)
    srow = db.execute(
        """
        INSERT INTO sessions (assignment_id, session_date, start_time, end_time, topic, status)
        VALUES (%s,%s,%s,%s,%s,'ongoing')
        RETURNING id
        """,
        (assignment_id, date.today().isoformat(), start.time().isoformat(timespec="minutes"), end.time().isoformat(timespec="minutes"), label),
    ).fetchone()

    expires_at = datetime.utcnow() + timedelta(seconds=int(current_app.config.get("QR_VALID_SECONDS", 120)))
    token_row = db.execute(
        """
        INSERT INTO qr_tokens (session_id, expires_at, is_active)
        VALUES (%s,%s,true)
        RETURNING token
        """,
        (srow["id"], expires_at),
    ).fetchone()
    db.commit()
    return jsonify({"ok": True, "token": token_row["token"]})


@api_bp.route("/api/faculty/class/<assignment_id>")
def faculty_class(assignment_id):
    role_check = _require_role("faculty")
    if role_check:
        return role_check

    a = _get_assignment(assignment_id)
    if not a or str(a["faculty_id"]) != str(session["user_id"]):
        return jsonify({"error": "Class not found"}), 404

    db = get_db()
    sessions_list = db.execute(
        """
        SELECT qt.*, s.session_date, s.topic, s.status
        FROM qr_tokens qt
        JOIN sessions s ON s.id=qt.session_id
        WHERE s.assignment_id=%s
        ORDER BY qt.created_at DESC
        """,
        (assignment_id,),
    ).fetchall()

    students = db.execute(
        """
        SELECT
          p.id,
          p.full_name as name,
          sp.roll_no as rollno,
          COUNT(ar.id) FILTER (WHERE ar.status in ('present','late')) as present_count
        FROM student_profiles sp
        JOIN profiles p ON p.id=sp.id
        LEFT JOIN sessions s ON s.assignment_id=%s AND s.status='completed'
        LEFT JOIN attendance_records ar ON ar.session_id=s.id AND ar.student_id=sp.id
        WHERE sp.class_id=%s
        GROUP BY p.id, p.full_name, sp.roll_no
        ORDER BY sp.roll_no, p.full_name
        """,
        (assignment_id, a["class_id"]),
    ).fetchall()

    total_sessions = db.execute(
        "SELECT COUNT(*) as c FROM sessions WHERE assignment_id=%s AND status='completed'",
        (assignment_id,),
    ).fetchone()["c"]

    cls_payload = {
        "id": a["id"],
        "subject": a["subject_name"],
        "class_name": f"{a['department_code']}-{a['section']} (S{a['semester']})",
    }

    return jsonify(
        {
            "cls": cls_payload,
            "sessions": [dict(s) for s in sessions_list],
            "students": [dict(s) for s in students],
            "total": total_sessions,
        }
    )


@api_bp.route("/api/faculty/close_session", methods=["POST"])
def faculty_close_session():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    data = request.get_json(silent=True) or {}
    token_str = (data.get("token") or "").strip()
    if not token_str:
        return jsonify({"ok": False, "error": "no token"}), 400

    db = get_db()
    t = db.execute(
        """
        SELECT qt.id as token_id, qt.token, qt.is_active, qt.session_id,
               s.assignment_id,
               fa.faculty_id
        FROM qr_tokens qt
        JOIN sessions s ON s.id=qt.session_id
        JOIN faculty_assignments fa ON fa.id=s.assignment_id
        WHERE qt.token=%s
        """,
        (token_str,),
    ).fetchone()
    if not t:
        return jsonify({"ok": False, "error": "token not found"}), 404
    if str(t["faculty_id"]) != str(session["user_id"]):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    already_closed = not bool(t["is_active"])
    if not already_closed:
        db.execute("UPDATE qr_tokens SET is_active=false WHERE token=%s", (token_str,))
        db.execute("UPDATE sessions SET status='completed' WHERE id=%s", (t["session_id"],))
        db.commit()
        threading.Thread(target=notify_absentees_supabase, args=(t["session_id"],), daemon=True).start()
    return jsonify({"ok": True, "already_closed": already_closed})


# ---- QR / Student API ----


@api_bp.route("/api/qr/<token>")
def qr_info(token):
    db = get_db()
    t = db.execute(
        """
        SELECT qt.*, s.session_date, s.topic,
               sub.name as subject,
               d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name
        FROM qr_tokens qt
        JOIN sessions s ON s.id=qt.session_id
        JOIN faculty_assignments fa ON fa.id=s.assignment_id
        JOIN subjects sub ON sub.id=fa.subject_id
        JOIN classes c ON c.id=fa.class_id
        JOIN departments d ON d.id=c.department_id
        WHERE qt.token=%s
        """,
        (token,),
    ).fetchone()
    if not t:
        return jsonify({"error": "Invalid token"}), 404
    payload = dict(t)
    payload["session_label"] = payload.get("topic") or str(payload.get("session_date") or "")
    return jsonify(payload)


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
        """
        SELECT qt.*, s.id as session_id, s.assignment_id, s.status as session_status,
               fa.class_id, sub.name as subject,
               d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name
        FROM qr_tokens qt
        JOIN sessions s ON s.id=qt.session_id
        JOIN faculty_assignments fa ON fa.id=s.assignment_id
        JOIN subjects sub ON sub.id=fa.subject_id
        JOIN classes c ON c.id=fa.class_id
        JOIN departments d ON d.id=c.department_id
        WHERE qt.token=%s AND qt.is_active=true AND qt.expires_at > now()
        """,
        (token,),
    ).fetchone()
    if not t:
        return jsonify({"success": False, "msg": "Invalid or expired QR code."}), 400

    sp = db.execute("SELECT class_id FROM student_profiles WHERE id=%s", (session["user_id"],)).fetchone()
    if not sp or str(sp["class_id"]) != str(t["class_id"]):
        return jsonify({"success": False, "msg": "You are not enrolled in this class."}), 403

    try:
        db.execute(
            """
            INSERT INTO attendance_records (session_id, student_id, qr_token_id, status, method)
            VALUES (%s,%s,%s,'present','qr')
            """,
            (t["session_id"], session["user_id"], t["id"]),
        )
        db.commit()
        check_and_notify_supabase(session["user_id"], t["assignment_id"])
        return jsonify(
            {
                "success": True,
                "msg": f"Attendance marked for {t['subject']}!",
                "subject": t["subject"],
                "label": t.get("topic") or "",
            }
        )
    except Exception:
        return jsonify({"success": False, "msg": "Attendance already marked for this session."}), 400


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
