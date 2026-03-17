import csv
import io
import time
from typing import Any, Dict, List

import qrcode
from flask import Blueprint, jsonify, request, send_file, session, current_app
from io import BytesIO

from store import InMemoryStore


api_bp = Blueprint("api", __name__)

_STORE = InMemoryStore()
_STORE.seed_demo()


@api_bp.route("/health")
def health():
    return jsonify({"ok": True})


def _require_role(role: str):
    if session.get("role") != role:
        return jsonify({"error": "unauthorized"}), 401
    return None


def _json():
    return request.get_json(silent=True) or {}


def _as_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime())


def _class_payload(c):
    faculty = _STORE.get_user(c.faculty_id)
    return {
        "id": c.id,
        "subject": c.subject,
        "class_name": c.class_name,
        "faculty_id": c.faculty_id,
        "faculty_name": (faculty.full_name if faculty else "Unknown"),
    }


# -----------------
# Auth
# -----------------


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
    data = _json()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = _STORE.authenticate(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user.id
    session["role"] = user.role
    session["name"] = user.full_name
    next_scan = session.pop("next_scan", None)
    return jsonify({"ok": True, "role": user.role, "next_scan": next_scan})


@api_bp.route("/api/auth/signup", methods=["POST"])
def auth_signup():
    data = _json()
    role = (data.get("role") or "").strip().lower()
    full_name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    class_name = (data.get("class_name") or "").strip()
    rollno = (data.get("rollno") or "").strip()

    if role not in {"student", "faculty"}:
        return jsonify({"error": "Please choose Student or Faculty"}), 400
    if not full_name or not username or not password:
        return jsonify({"error": "Name, username, and password are required"}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    try:
        user = _STORE.create_user(
            username,
            password,
            role,
            full_name=full_name,
            email=email,
            phone=phone,
            class_name=(class_name if role == "student" else ""),
            rollno=(rollno if role == "student" else ""),
        )
    except ValueError as e:
        if str(e) == "username_taken":
            return jsonify({"error": "Username already taken"}), 400
        return jsonify({"error": "Unable to create account"}), 400

    session["user_id"] = user.id
    session["role"] = user.role
    session["name"] = user.full_name
    return jsonify({"ok": True, "role": user.role})


@api_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


# -----------------
# Admin
# -----------------


@api_bp.route("/api/admin/dashboard")
def admin_dashboard():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    users_students = _STORE.list_users("student")
    users_faculty = _STORE.list_users("faculty")
    classes = _STORE.list_classes()

    # sessions = closed tokens
    total_sessions = 0
    for c in classes:
        total_sessions += _STORE.total_completed_sessions_for_class(c.id)

    students_out: List[Dict[str, Any]] = []
    for s in users_students:
        # overall stats for their class_name
        class_offerings = [c for c in classes if c.class_name == (s.class_name or "").strip().upper()]
        total = sum(_STORE.total_completed_sessions_for_class(c.id) for c in class_offerings)
        present = sum(_STORE.student_present_count_for_class(student_id=s.id, class_id=c.id) for c in class_offerings)
        students_out.append(
            {
                "id": s.id,
                "name": s.full_name,
                "username": s.username,
                "rollno": s.rollno,
                "class_name": s.class_name,
                "present_count": present,
                "total_sessions": total,
            }
        )

    faculty_out = [{"id": f.id, "name": f.full_name, "username": f.username} for f in users_faculty]
    classes_out = [_class_payload(c) for c in classes]

    stats = {
        "students": len(users_students),
        "faculty": len(users_faculty),
        "classes": len(classes_out),
        "sessions": total_sessions,
    }

    return jsonify({"stats": stats, "students": students_out, "faculty_list": faculty_out, "classes": classes_out})


@api_bp.route("/api/admin/add_user", methods=["POST"])
def admin_add_user():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    data = _json()
    role = (data.get("role") or "").strip().lower()
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    class_name = (data.get("class_name") or "").strip()
    rollno = (data.get("rollno") or "").strip()

    if role not in {"student", "faculty", "admin"}:
        return jsonify({"error": "Invalid role"}), 400
    if not name or not username or not password:
        return jsonify({"error": "Name, username, and password are required"}), 400

    try:
        _STORE.create_user(
            username,
            password,
            role,
            full_name=name,
            email=email,
            phone=phone,
            class_name=(class_name if role == "student" else ""),
            rollno=(rollno if role == "student" else ""),
        )
    except ValueError as e:
        if str(e) == "username_taken":
            return jsonify({"error": "Username already taken"}), 400
        return jsonify({"error": "Unable to add user"}), 400

    return jsonify({"ok": True})


@api_bp.route("/api/admin/reset_password/<user_id>", methods=["POST"])
def admin_reset_password(user_id):
    role_check = _require_role("admin")
    if role_check:
        return role_check

    data = _json()
    new_password = data.get("new_password") or ""
    if not new_password:
        return jsonify({"error": "New password required"}), 400
    try:
        _STORE.reset_password(user_id, new_password)
    except ValueError:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"ok": True})


@api_bp.route("/api/admin/user/<user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    role_check = _require_role("admin")
    if role_check:
        return role_check
    _STORE.delete_user(user_id)
    return jsonify({"ok": True})


@api_bp.route("/api/admin/add_subject", methods=["POST"])
def admin_add_subject():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    data = _json()
    subject = (data.get("subject") or "").strip()
    class_name = (data.get("class_name") or "").strip()
    faculty_id = (data.get("faculty_id") or "").strip()
    if not subject or not class_name or not faculty_id:
        return jsonify({"error": "Subject, class name, and faculty are required"}), 400
    if not _STORE.get_user(faculty_id) or _STORE.get_user(faculty_id).role != "faculty":
        return jsonify({"error": "Faculty not found"}), 400

    cls = _STORE.create_class(subject=subject, class_name=class_name, faculty_id=faculty_id)
    return jsonify({"ok": True, "id": cls.id})


@api_bp.route("/api/admin/subject/<class_id>", methods=["DELETE"])
def admin_delete_subject(class_id):
    role_check = _require_role("admin")
    if role_check:
        return role_check
    _STORE.delete_class(class_id)
    return jsonify({"ok": True})


@api_bp.route("/api/admin/manual_attendance", methods=["POST"])
def admin_manual_attendance():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    data = _json()
    student_id = (data.get("student_id") or "").strip()
    class_id = (data.get("class_id") or "").strip()
    status = (data.get("status") or "present").strip().lower()

    if not student_id or not class_id:
        return jsonify({"error": "Student and subject are required"}), 400
    if status not in {"present", "absent"}:
        return jsonify({"error": "Invalid status"}), 400

    # manual entry is implemented as a closed session created for that class.
    token = _STORE.create_token(class_id=class_id, session_label="Manual Entry", valid_seconds=5)
    _STORE.close_token(token.token)
    if status == "present":
        _STORE.mark_attendance(token_str=token.token, student_id=student_id)

    return jsonify({"ok": True})


@api_bp.route("/api/admin/preview_csv", methods=["POST"])
def admin_preview_csv():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    f = request.files.get("csv_file")
    if not f:
        return jsonify({"error": "csv_file required"}), 400
    raw = f.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    headers = reader.fieldnames or []
    preview = []
    for i, row in enumerate(reader):
        if i >= 20:
            break
        preview.append(row)
    return jsonify({"headers": headers, "preview": preview})


@api_bp.route("/api/admin/import_csv", methods=["POST"])
def admin_import_csv():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    f = request.files.get("csv_file")
    if not f:
        return jsonify({"error": "csv_file required"}), 400
    raw = f.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))

    created = 0
    for row in reader:
        username = (row.get("username") or row.get("Username") or "").strip().lower()
        role = (row.get("role") or row.get("Role") or "").strip().lower() or "student"
        name = (row.get("name") or row.get("full_name") or row.get("Full Name") or username).strip()
        password = (row.get("password") or row.get("Password") or "changeme123").strip()
        class_name = (row.get("class_name") or row.get("Class") or "").strip()
        rollno = (row.get("rollno") or row.get("roll_no") or row.get("Roll") or "").strip()
        email = (row.get("email") or "").strip()
        phone = (row.get("phone") or "").strip()
        if not username:
            continue
        try:
            _STORE.create_user(
                username,
                password,
                role,
                full_name=name,
                email=email,
                phone=phone,
                class_name=(class_name if role == "student" else ""),
                rollno=(rollno if role == "student" else ""),
            )
            created += 1
        except Exception:
            continue
    return jsonify({"ok": True, "created": created})


@api_bp.route("/api/admin/attendance_report")
def admin_attendance_report():
    role_check = _require_role("admin")
    if role_check:
        return role_check

    students = _STORE.list_users("student")
    classes = _STORE.list_classes()

    out = []
    for s in students:
        subjects = []
        class_offerings = [c for c in classes if c.class_name == (s.class_name or "").strip().upper()]
        for c in class_offerings:
            total = _STORE.total_completed_sessions_for_class(c.id)
            present = _STORE.student_present_count_for_class(student_id=s.id, class_id=c.id)
            pct = int(round((present / total) * 100)) if total else 0
            subjects.append({"subject": c.subject, "pct": pct})
        out.append({"id": s.id, "name": s.full_name, "rollno": s.rollno, "class_name": s.class_name, "subjects": subjects})
    return jsonify(out)


# -----------------
# Faculty
# -----------------


@api_bp.route("/api/faculty/dashboard")
def faculty_dashboard():
    role_check = _require_role("faculty")
    if role_check:
        return role_check

    faculty_id = session.get("user_id")
    classes = _STORE.list_faculty_classes(faculty_id)
    tokens = _STORE.list_tokens_for_faculty(faculty_id)

    recent_tokens = []
    for t in tokens:
        cls = next((c for c in classes if c.id == t.class_id), None) or next((c for c in _STORE.list_classes() if c.id == t.class_id), None)
        if not cls:
            continue
        recent_tokens.append(
            {
                "id": t.id,
                "token": t.token,
                "subject": cls.subject,
                "class_name": cls.class_name,
                "session_label": t.session_label,
                "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.created_at)),
                "is_active": 1 if t.is_active else 0,
                "marked_count": _STORE.token_marked_count(t.id),
            }
        )

    return jsonify(
        {
            "classes": [_class_payload(c) for c in classes],
            "recent_tokens": recent_tokens,
            "name": session.get("name"),
        }
    )


@api_bp.route("/api/faculty/generate_qr", methods=["POST"])
def faculty_generate_qr():
    role_check = _require_role("faculty")
    if role_check:
        return role_check

    data = _json()
    class_id = (data.get("class_id") or "").strip()
    label = (data.get("label") or data.get("topic") or "Lecture").strip()
    if not class_id:
        return jsonify({"error": "class_id required"}), 400

    cls = next((c for c in _STORE.list_faculty_classes(session.get("user_id")) if c.id == class_id), None)
    if not cls:
        return jsonify({"error": "Class not found"}), 404

    valid_seconds = _as_int(current_app.config.get("QR_VALID_SECONDS", 120), 120)
    token = _STORE.create_token(class_id=class_id, session_label=label, valid_seconds=valid_seconds)
    return jsonify({"ok": True, "token": token.token})


@api_bp.route("/api/faculty/close_session", methods=["POST"])
def faculty_close_session():
    role_check = _require_role("faculty")
    if role_check:
        return role_check
    data = _json()
    token_str = (data.get("token") or "").strip()
    if not token_str:
        return jsonify({"ok": False, "error": "no token"}), 400
    t = _STORE.get_token(token_str)
    if not t:
        return jsonify({"ok": False, "error": "token not found"}), 404

    already_closed = not bool(t.is_active)
    _STORE.close_token(token_str)
    return jsonify({"ok": True, "already_closed": already_closed})


@api_bp.route("/api/faculty/class/<class_id>")
def faculty_class(class_id):
    role_check = _require_role("faculty")
    if role_check:
        return role_check

    cls = next((c for c in _STORE.list_faculty_classes(session.get("user_id")) if c.id == str(class_id)), None)
    if not cls:
        return jsonify({"error": "Class not found"}), 404

    students = [u for u in _STORE.list_users("student") if (u.class_name or "").strip().upper() == cls.class_name]
    total = _STORE.total_completed_sessions_for_class(cls.id)
    student_rows = []
    for s in students:
        student_rows.append(
            {
                "id": s.id,
                "name": s.full_name,
                "rollno": s.rollno,
                "present_count": _STORE.student_present_count_for_class(student_id=s.id, class_id=cls.id),
            }
        )
    student_rows.sort(key=lambda r: (r.get("rollno") or "", r.get("name") or ""))

    sessions_out = []
    for t in _STORE.list_tokens_for_class(cls.id):
        sessions_out.append(
            {
                "id": t.id,
                "session_label": t.session_label,
                "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.created_at)),
                "is_active": bool(t.is_active),
            }
        )

    return jsonify({"cls": _class_payload(cls), "students": student_rows, "sessions": sessions_out, "total": total})


# -----------------
# Student
# -----------------


@api_bp.route("/api/student/dashboard")
def student_dashboard():
    role_check = _require_role("student")
    if role_check:
        return role_check

    user = _STORE.get_user(session.get("user_id"))
    if not user:
        return jsonify({"error": "Not found"}), 404

    classes = [c for c in _STORE.list_classes() if c.class_name == (user.class_name or "").strip().upper()]
    attendance = []
    recent = []

    for c in classes:
        total = _STORE.total_completed_sessions_for_class(c.id)
        present = _STORE.student_present_count_for_class(student_id=user.id, class_id=c.id)
        attendance.append(
            {
                "subject": c.subject,
                "class_id": c.id,
                "class_name": c.class_name,
                "present_count": present,
                "total_sessions": total,
            }
        )

    # recent activity: scan marks (best-effort)
    # We don't store per-subject history beyond token marks, so we synthesize from tokens.
    tokens = []
    for c in classes:
        tokens.extend(_STORE.list_tokens_for_class(c.id))
    tokens.sort(key=lambda t: t.created_at, reverse=True)
    for t in tokens[:30]:
        marked_at = _STORE.get_marked_at(token_id=t.id, student_id=user.id)
        if not marked_at:
            continue
        cls = next((c for c in classes if c.id == t.class_id), None)
        recent.append(
            {
                "status": "present",
                "method": "qr",
                "marked_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(marked_at)),
                "subject": (cls.subject if cls else ""),
                "session_label": t.session_label,
            }
        )

    return jsonify(
        {
            "student": {
                "id": user.id,
                "name": user.full_name,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "rollno": user.rollno,
                "class_name": user.class_name,
            },
            "attendance": attendance,
            "recent": recent,
        }
    )


# -----------------
# QR / scan
# -----------------


@api_bp.route("/api/qr/<token>")
def qr_info(token):
    t = _STORE.get_token(token)
    if not t:
        return jsonify({"error": "Invalid token"}), 404
    cls = next((c for c in _STORE.list_classes() if c.id == t.class_id), None)
    if not cls:
        return jsonify({"error": "Invalid token"}), 404

    return jsonify(
        {
            "id": t.id,
            "token": t.token,
            "class_id": cls.id,
            "subject": cls.subject,
            "class_name": cls.class_name,
            "session_label": t.session_label,
            "created_at": int(t.created_at),
            "expires_at": int(t.expires_at),
        }
    )


@api_bp.route("/api/scan/<token>")
def api_scan(token):
    if "user_id" not in session:
        session["next_scan"] = token
        return jsonify({"error": "Authentication required"}), 401
    if session.get("role") != "student":
        return jsonify({"error": "Only students can mark attendance."}), 403

    ok, msg = _STORE.mark_attendance(token_str=token, student_id=session.get("user_id"))
    t = _STORE.get_token(token)
    cls = None
    if t:
        cls = next((c for c in _STORE.list_classes() if c.id == t.class_id), None)

    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify(
        {
            "success": True,
            "msg": (f"Attendance marked for {cls.subject}!" if cls else "Attendance marked!"),
            "subject": (cls.subject if cls else ""),
            "label": (t.session_label if t else ""),
        }
    )


@api_bp.route("/qr_image/<token>")
def qr_image(token):
    scan_url = request.host_url.rstrip("/") + f"/scan/{token}"
    img = qrcode.make(scan_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", max_age=60)
