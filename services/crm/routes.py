import os
from datetime import datetime
from collections import OrderedDict
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, send_file, current_app, has_app_context
import time, secrets, threading
import qrcode
from io import BytesIO

from services.shared.db import get_db, get_db_standalone
from services.shared.security import hash_pw
from services.shared.notify import send_sms

crm_bp = Blueprint("crm", __name__)

# ---- Helpers ----

def get_class_from_htno(htno):
    try:
        year = htno[3:5]
        branch = htno[6:8]
        branch_map = {"02": "CSE", "03": "ECE", "04": "EEE", "05": "MECH", "06": "CIVIL", "66": "AIML"}
        b = branch_map.get(branch, f"BR{branch}")
        yr = "Y1" if year == "P1" else "Y3"
        return f"{b}-{yr}"
    except Exception:
        return "GENERAL"


def get_dashboard_data(role):
    db = get_db()
    if role == "student":
        student = db.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()
        attendance = db.execute(
            """
            SELECT c.subject, c.class_name, c.id as class_id,
                   COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
                   (SELECT COUNT(*) FROM qr_tokens q2 WHERE q2.class_id=c.id AND q2.is_active=0) as total_sessions
            FROM classes c LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=?
            WHERE c.class_name=? GROUP BY c.id
            """,
            (session["user_id"], student["class_name"]),
        ).fetchall()
        recent = db.execute(
            """
            SELECT a.marked_at, a.status, c.subject, q.session_label FROM attendance a
            JOIN qr_tokens q ON a.token_id=q.id JOIN classes c ON a.class_id=c.id
            WHERE a.student_id=? ORDER BY a.marked_at DESC LIMIT 10
            """,
            (session["user_id"],),
        ).fetchall()
        return {"student": dict(student), "attendance": attendance, "recent": recent}

    return {}\n\n\ndef _sms_threshold():\n    if has_app_context():\n        return _sms_threshold()\n    return int(os.getenv("SMS_THRESHOLD", "75"))\n\n\n# ---- Admin ----

@crm_bp.route("/admin")
def dashboard_admin():
    if session.get("role") != "admin":
        return redirect("/")
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

    msg = request.args.get("msg", "")
    tab = request.args.get("tab", "overview")
    errors = session.pop("csv_errors", [])

    return render_template(
        "admin.html",
        stats=stats,
        students=students,
        classes=[dict(c) for c in classes],
        faculty_list=[dict(f) for f in faculty_list],
        msg=msg,
        active_tab=tab,
        csv_errors=errors,
    )


@crm_bp.route("/admin/add_user", methods=["POST"])
def add_user():
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                request.form["username"].strip(),
                hash_pw(request.form["password"]),
                request.form["role"],
                request.form["name"].strip(),
                request.form.get("phone", ""),
                request.form.get("email", ""),
                request.form.get("gender", ""),
                request.form.get("dob", ""),
                request.form.get("class_name", ""),
                request.form.get("rollno", ""),
            ),
        )
        db.commit()
    except Exception as e:
        return redirect(url_for("crm.dashboard_admin") + f"?msg=Error:+{str(e)[:60]}&tab=students")

    role = request.form["role"]
    tab = "students" if role == "student" else "teachers"
    return redirect(url_for("crm.dashboard_admin") + f"?msg=User+added+successfully&tab={tab}")


@crm_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    u = db.execute("SELECT role FROM users WHERE id=%s", (user_id,)).fetchone()
    tab = "teachers" if u and u["role"] == "faculty" else "students"
    db.execute("DELETE FROM attendance WHERE student_id=%s", (user_id,))
    db.execute("DELETE FROM qr_tokens WHERE faculty_id=%s", (user_id,))
    db.execute("DELETE FROM classes WHERE faculty_id=%s", (user_id,))
    db.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    return redirect(url_for("crm.dashboard_admin") + f"?msg=User+deleted&tab={tab}")


@crm_bp.route("/admin/add_subject", methods=["POST"])
def add_subject():
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    try:
        db.execute(
            "INSERT INTO classes (subject,faculty_id,class_name) VALUES (%s,%s,%s)",
            (request.form["subject"], int(request.form["faculty_id"]), request.form["class_name"]),
        )
        db.commit()
    except Exception:
        pass
    return redirect(url_for("crm.dashboard_admin") + "?msg=Subject+added&tab=subjects")


@crm_bp.route("/admin/delete_subject/<int:class_id>", methods=["POST"])
def delete_subject(class_id):
    if session.get("role") != "admin":
        return redirect("/")
    db = get_db()
    db.execute("DELETE FROM attendance WHERE class_id=%s", (class_id,))
    db.execute("DELETE FROM qr_tokens WHERE class_id=%s", (class_id,))
    db.execute("DELETE FROM classes WHERE id=%s", (class_id,))
    db.commit()
    return redirect(url_for("crm.dashboard_admin") + "?msg=Subject+deleted&tab=subjects")


@crm_bp.route("/admin/import_csv", methods=["POST"])
def import_csv():
    if session.get("role") != "admin":
        return redirect("/")
    file = request.files.get("csv_file")
    if not file:
        return redirect(url_for("crm.dashboard_admin") + "?msg=No+file+uploaded&tab=students")

    data = file.read().decode("utf-8", errors="ignore")
    rows = list(
        __import__("csv").DictReader(
            __import__("io").StringIO(data)
        )
    )

    errors = []
    db = get_db()
    for i, row in enumerate(rows, start=1):
        try:
            username = row.get("username") or row.get("Username") or row.get("User")
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
                (username.strip().lower(), hash_pw(password), role, name, phone, email, gender, dob, class_name, rollno),
            )
            db.commit()
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    session["csv_errors"] = errors
    return redirect(url_for("crm.dashboard_admin") + "?msg=CSV+import+complete&tab=students")


@crm_bp.route("/admin/preview_csv", methods=["POST"])
def preview_csv():
    if session.get("role") != "admin":
        return jsonify({"headers": [], "preview": []})
    file = request.files.get("csv_file")
    if not file:
        return jsonify({"headers": [], "preview": []})

    data = file.read().decode("utf-8", errors="ignore")
    reader = __import__("csv").DictReader(__import__("io").StringIO(data))
    headers = reader.fieldnames or []
    rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        rows.append({k.strip(): v.strip() for k, v in row.items() if k})

    return jsonify({"headers": headers, "preview": rows})


@crm_bp.route("/admin/manual_attendance", methods=["GET"])
def manual_attendance_page():
    if session.get("role") != "admin":
        return redirect("/")
    msg = request.args.get("msg", "")
    return redirect(url_for("crm.dashboard_admin") + (f"?tab=manual&msg={msg}" if msg else "?tab=manual"))


@crm_bp.route("/admin/manual_attendance", methods=["POST"])
def manual_attendance_submit():
    if session.get("role") != "admin":
        return redirect("/")
    student_id = int(request.form["student_id"])
    class_id = int(request.form["class_id"])
    status = request.form.get("status", "present")
    session_date = request.form.get("session_date", datetime.now().strftime("%Y-%m-%d"))
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
        msg = "Attendance+marked+successfully"
    except Exception:
        db.execute(
            "UPDATE attendance SET status=%s, marked_at=%s WHERE student_id=%s AND token_id=%s",
            (status, datetime.now().isoformat(), student_id, token_id),
        )
        db.commit()
        msg = "Attendance+updated"

    return redirect(url_for("crm.dashboard_admin") + f"?tab=manual&msg={msg}")


@crm_bp.route("/admin/attendance_report")
def attendance_report():
    if session.get("role") != "admin":
        return redirect("/")
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
        GROUP BY u.id, c.id
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
            {
                "subject": r["subject"],
                "class_id": r["class_id"],
                "present": r["present"],
                "total": r["total"],
                "pct": r["pct"],
            }
        )
    return jsonify(list(grouped.values()))


@crm_bp.route("/admin/get_sessions/<int:class_id>")
def get_sessions_for_class(class_id):
    if session.get("role") != "admin":
        return jsonify([])
    db = get_db()
    rows = db.execute(
        "SELECT id, session_label, created_at FROM qr_tokens WHERE class_id=%s ORDER BY created_at DESC",
        (class_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@crm_bp.route("/admin/get_students_for_class/<int:class_id>")
def get_students_for_class(class_id):
    if session.get("role") != "admin":
        return jsonify([])
    db = get_db()
    cls = db.execute("SELECT class_name FROM classes WHERE id=%s", (class_id,)).fetchone()
    if not cls:
        return jsonify([])
    rows = db.execute(
        "SELECT id, name, rollno FROM users WHERE class_name=%s AND role='student' ORDER BY rollno",
        (cls["class_name"],),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ---- Faculty ----

@crm_bp.route("/faculty")
def dashboard_faculty():
    if session.get("role") != "faculty":
        return redirect("/")
    db = get_db()
    classes = db.execute("SELECT * FROM classes WHERE faculty_id=%s", (session["user_id"],)).fetchall()
    recent_tokens = db.execute(
        """
        SELECT q.*, c.subject, c.class_name,
               (SELECT COUNT(*) FROM attendance a WHERE a.token_id=q.id) as marked_count
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id
        WHERE q.faculty_id=? ORDER BY q.created_at DESC LIMIT 10
        """,
        (session["user_id"],),
    ).fetchall()
    msg = request.args.get("msg", "")
    return render_template(
        "faculty.html",
        classes=classes,
        recent_tokens=recent_tokens,
        now=time.time(),
        qr_valid=current_app.config["QR_VALID_SECONDS"],
        msg=msg,
    )


@crm_bp.route("/faculty/generate_qr", methods=["POST"])
def generate_qr():
    if session.get("role") != "faculty":
        return redirect("/")
    class_id = int(request.form["class_id"])
    label = request.form.get("label", datetime.now().strftime("%d %b %Y %H:%M"))
    db = get_db()

    prev = db.execute(
        "SELECT q.id, q.token, c.subject, c.class_name FROM qr_tokens q "
        "JOIN classes c ON q.class_id=c.id "
        "WHERE q.class_id=? AND q.faculty_id=? AND q.is_active=1",
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
        (token, class_id, session["user_id"], now, now + current_app.config["QR_VALID_SECONDS"], label),
    )
    db.commit()
    return redirect(url_for("crm.show_qr", token=token))


@crm_bp.route("/qr/<token>")
def show_qr(token):
    db = get_db()
    t = db.execute(
        "SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=%s",
        (token,),
    ).fetchone()
    if not t:
        return "Invalid token", 404
    return render_template("qr_display.html", token=dict(t), now=time.time(), qr_valid=current_app.config["QR_VALID_SECONDS"])


from functools import lru_cache

@lru_cache(maxsize=128)
def _generate_qr_bytes(scan_url):
    img = qrcode.make(scan_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@crm_bp.route("/qr_image/<token>")
def qr_image(token):
    scan_url = request.host_url + f"scan/{token}"
    data = _generate_qr_bytes(scan_url)
    return send_file(BytesIO(data), mimetype="image/png", max_age=300)


@crm_bp.route("/faculty/attendance/<int:class_id>")
def faculty_attendance(class_id):
    if session.get("role") != "faculty":
        return redirect("/")
    db = get_db()
    cls = db.execute("SELECT * FROM classes WHERE id=%s AND faculty_id=%s", (class_id, session["user_id"])).fetchone()
    if not cls:
        return redirect(url_for("crm.dashboard_faculty"))
    sessions_list = db.execute("SELECT * FROM qr_tokens WHERE class_id=%s ORDER BY created_at DESC", (class_id,)).fetchall()
    students = db.execute(
        """
        SELECT u.*, COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count
        FROM users u LEFT JOIN attendance a ON a.student_id=u.id AND a.class_id=?
        WHERE u.class_name=? AND u.role='student' GROUP BY u.id ORDER BY u.rollno
        """,
        (class_id, cls["class_name"]),
    ).fetchall()
    total_sessions = db.execute(
        "SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0",
        (class_id,),
    ).fetchone()["c"]
    return render_template(
        "faculty_attendance.html",
        cls=dict(cls),
        sessions=sessions_list,
        students=students,
        total=total_sessions,
    )


# ---- Student ----

@crm_bp.route("/student")
def dashboard_student():
    if session.get("role") != "student":
        return redirect("/")
    db = get_db()
    student = db.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()
    attendance = db.execute(
        """
        SELECT c.subject, c.class_name, c.id as class_id,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
               (SELECT COUNT(*) FROM qr_tokens q2 WHERE q2.class_id=c.id AND q2.is_active=0) as total_sessions
        FROM classes c
        LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=?
        WHERE c.class_name=?
        GROUP BY c.id
        """,
        (session["user_id"], student["class_name"]),
    ).fetchall()
    recent = db.execute(
        """
        SELECT a.marked_at, a.status, c.subject, q.session_label FROM attendance a
        JOIN qr_tokens q ON a.token_id=q.id JOIN classes c ON a.class_id=c.id
        WHERE a.student_id=? ORDER BY a.marked_at DESC LIMIT 10
        """,
        (session["user_id"],),
    ).fetchall()
    msg = request.args.get("msg", "")
    return render_template("student.html", student=dict(student), attendance=attendance, recent=recent, msg=msg)


@crm_bp.route("/student/scanner")
def student_scanner():
    if session.get("role") != "student":
        return redirect("/")
    return render_template("student_scanner.html")


# ---- QR Scan ----

@crm_bp.route("/scan/<token>")
def scan_qr(token):
    if "user_id" not in session:
        session["next_scan"] = token
        return redirect(url_for("auth.index"))
    if session.get("role") != "student":
        return render_template("scan_result.html", success=False, msg="Only students can mark attendance.")
    db = get_db()
    t = db.execute(
        "SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=%s AND q.is_active=1",
        (token,),
    ).fetchone()
    if not t:
        return render_template("scan_result.html", success=False, msg="Invalid or expired QR code.")
    if time.time() > t["expires_at"]:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=%s", (token,))
        db.commit()
        return render_template("scan_result.html", success=False, msg="QR Code expired. Ask faculty to generate a new one.")
    student = db.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()
    if student["class_name"] != t["class_name"]:
        return render_template("scan_result.html", success=False, msg="You are not enrolled in this class.")
    try:
        db.execute(
            "INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (%s,%s,%s,%s,%s)",
            (session["user_id"], t["class_id"], t["id"], datetime.now().isoformat(), "present"),
        )
        db.commit()
        check_and_notify(session["user_id"], t["class_id"])
        return render_template(
            "scan_result.html",
            success=True,
            msg=f"Attendance marked for {t['subject']}!",
            subject=t["subject"],
            label=t["session_label"],
        )
    except Exception:
        return render_template("scan_result.html", success=False, msg="Attendance already marked for this session.")


@crm_bp.route("/api/token_status/<token>")
def token_status(token):
    db = get_db()
    t = db.execute("SELECT * FROM qr_tokens WHERE token=%s", (token,)).fetchone()
    if not t:
        return jsonify({"valid": False})
    remaining = max(0, t["expires_at"] - time.time())
    return jsonify({"valid": t["is_active"] == 1 and remaining > 0, "remaining": int(remaining)})


# ---- Notifications ----


def check_and_notify(student_id, class_id):
    db = get_db()
    total = db.execute(
        "SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0",
        (class_id,),
    ).fetchone()["c"]
    present = db.execute(
        "SELECT COUNT(*) as c FROM attendance WHERE student_id=%s AND class_id=%s AND status='present'",
        (student_id, class_id),
    ).fetchone()["c"]
    if total > 0:
        pct = (present / total) * 100
        if pct < _sms_threshold():
            student = db.execute("SELECT * FROM users WHERE id=%s", (student_id,)).fetchone()
            cls = db.execute("SELECT * FROM classes WHERE id=%s", (class_id,)).fetchone()
            if student and student.get("phone"):
                send_sms(
                    student["phone"],
                    f"Attendance Alert: Dear {student['name']}, your attendance in {cls['subject']} is {pct:.1f}% ({present}/{total}). Min required: {current_app.config['SMS_THRESHOLD']}%.",
                )


def notify_absentees(token_id, class_id, class_name, subject):
    db = get_db_standalone()
    try:
        all_students = db.execute(
            "SELECT id, name, phone FROM users WHERE class_name=%s AND role='student'",
            (class_name,),
        ).fetchall()

        present_ids = set(
            r["student_id"]
            for r in db.execute("SELECT student_id FROM attendance WHERE token_id=%s", (token_id,)).fetchall()
        )

        absent_students = []
        for s in all_students:
            if s["id"] in present_ids:
                continue
            try:
                db.execute(
                    "INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (%s,%s,%s,%s,%s)",
                    (s["id"], class_id, token_id, datetime.now().isoformat(), "absent"),
                )
            except Exception:
                pass
            absent_students.append(s)

        db.commit()

        total = db.execute(
            "SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0",
            (class_id,),
        ).fetchone()["c"]

        for s in absent_students:
            if not s.get("phone"):
                continue
            send_sms(
                s["phone"],
                f"Attendance Alert: Dear {s['name']}, you were marked ABSENT for {subject} class ({class_name}). If this is an error, contact your faculty.",
            )
            if total > 0:
                present = db.execute(
                    "SELECT COUNT(*) as c FROM attendance WHERE student_id=%s AND class_id=%s AND status='present'",
                    (s["id"], class_id),
                ).fetchone()["c"]
                pct = (present / total) * 100
                if pct < _sms_threshold():
                    send_sms(
                        s["phone"],
                        f"Low Attendance Warning: Dear {s['name']}, your attendance in {subject} is now {pct:.1f}% ({present}/{total} classes). Minimum required: {current_app.config['SMS_THRESHOLD']}%.",
                    )
    finally:
        db.close()


@crm_bp.route("/faculty/close_session", methods=["POST"])
def close_session():
    if session.get("role") != "faculty":
        return jsonify({"ok": False, "error": "unauthorized"})

    token_str = request.json.get("token")
    if not token_str:
        return jsonify({"ok": False, "error": "no token"})

    db = get_db()
    t = db.execute(
        "SELECT q.*, c.subject, c.class_name FROM qr_tokens q "
        "JOIN classes c ON q.class_id=c.id WHERE q.token=?",
        (token_str,),
    ).fetchone()

    if not t:
        return jsonify({"ok": False, "error": "token not found"})

    already_closed = t["is_active"] == 0
    if not already_closed:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=%s", (token_str,))
        db.commit()

    threading.Thread(
        target=notify_absentees,
        args=(t["id"], t["class_id"], t["class_name"], t["subject"]),
        daemon=True,
    ).start()
    return jsonify({"ok": True, "already_closed": already_closed})


