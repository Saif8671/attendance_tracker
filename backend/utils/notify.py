import os
from datetime import datetime
from flask import current_app, has_app_context

from db.database import get_db, get_db_standalone


def _twilio_config():
    if has_app_context():
        return (
            current_app.config.get("TWILIO_ACCOUNT_SID", ""),
            current_app.config.get("TWILIO_AUTH_TOKEN", ""),
            current_app.config.get("TWILIO_PHONE", ""),
        )
    return (
        os.getenv("TWILIO_ACCOUNT_SID", ""),
        os.getenv("TWILIO_AUTH_TOKEN", ""),
        os.getenv("TWILIO_PHONE", ""),
    )


def send_sms(to, msg):
    sid, token, phone = _twilio_config()
    if not sid:
        print(f"[SMS SIMULATION] To {to}: {msg}")
        return True
    try:
        from twilio.rest import Client

        Client(sid, token).messages.create(body=msg, from_=phone, to=to)
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False


# ============================================================
# Legacy schema helpers (users/classes/qr_tokens/attendance)
# ============================================================


def check_and_notify(student_id, class_id):
    db = get_db()
    from utils.helpers import _sms_threshold

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
        threshold = _sms_threshold()
        if pct < threshold:
            student = db.execute("SELECT * FROM users WHERE id=%s", (student_id,)).fetchone()
            cls = db.execute("SELECT * FROM classes WHERE id=%s", (class_id,)).fetchone()
            if student and student.get("phone"):
                send_sms(
                    student["phone"],
                    f"Attendance Alert: Dear {student['name']}, your attendance in {cls['subject']} is {pct:.1f}% ({present}/{total}). Min required: {threshold}%.",
                )


def notify_absentees(token_id, class_id, class_name, subject):
    db = get_db_standalone()
    from utils.helpers import _sms_threshold

    try:
        all_students = db.execute(
            """
            SELECT u.id, u.name, u.phone
            FROM users u
            JOIN enrollments e ON e.student_id=u.id
            WHERE e.class_id=%s AND u.role='student'
            """,
            (class_id,),
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
        threshold = _sms_threshold()

        for s in absent_students:
            if not s.get("phone"):
                continue
            send_sms(
                s["phone"],
                f"Attendance Alert: Dear {s['name']}, you were marked ABSENT for {subject} class ({class_name}).",
            )
            if total > 0:
                present = db.execute(
                    "SELECT COUNT(*) as c FROM attendance WHERE student_id=%s AND class_id=%s AND status='present'",
                    (s["id"], class_id),
                ).fetchone()["c"]
                pct = (present / total) * 100
                if pct < threshold:
                    send_sms(
                        s["phone"],
                        f"Low Attendance Warning: Dear {s['name']}, your attendance in {subject} is {pct:.1f}% ({present}/{total}).",
                    )
    finally:
        db.close()


# ============================================================
# Supabase schema helpers (profiles/.../attendance_records)
# ============================================================


def check_and_notify_supabase(student_id, assignment_id):
    db = get_db()
    from utils.helpers import _sms_threshold

    total = db.execute(
        "SELECT COUNT(*) as c FROM sessions WHERE assignment_id=%s AND status='completed'",
        (assignment_id,),
    ).fetchone()["c"]
    present = db.execute(
        """
        SELECT COUNT(*) as c
        FROM attendance_records ar
        JOIN sessions s ON s.id=ar.session_id
        WHERE ar.student_id=%s AND s.assignment_id=%s
          AND s.status='completed'
          AND ar.status in ('present','late')
        """,
        (student_id, assignment_id),
    ).fetchone()["c"]

    if total > 0:
        pct = (present / total) * 100
        threshold = _sms_threshold()
        if pct < threshold:
            student = db.execute("SELECT full_name, phone FROM profiles WHERE id=%s", (student_id,)).fetchone()
            subj = db.execute(
                """
                SELECT sub.name as subject
                FROM faculty_assignments fa
                JOIN subjects sub ON sub.id=fa.subject_id
                WHERE fa.id=%s
                """,
                (assignment_id,),
            ).fetchone()
            if student and student.get("phone") and subj:
                send_sms(
                    student["phone"],
                    f"Attendance Alert: Dear {student['full_name']}, your attendance in {subj['subject']} is {pct:.1f}% ({present}/{total}). Min required: {threshold}%.",
                )


def notify_absentees_supabase(session_id):
    db = get_db_standalone()
    from utils.helpers import _sms_threshold

    try:
        sess = db.execute(
            """
            SELECT
              s.id as session_id,
              s.assignment_id,
              sub.name as subject,
              c.id as class_id,
              d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name
            FROM sessions s
            JOIN faculty_assignments fa ON fa.id=s.assignment_id
            JOIN subjects sub ON sub.id=fa.subject_id
            JOIN classes c ON c.id=fa.class_id
            JOIN departments d ON d.id=c.department_id
            WHERE s.id=%s
            """,
            (session_id,),
        ).fetchone()
        if not sess:
            return

        all_students = db.execute(
            """
            SELECT p.id, p.full_name, p.phone
            FROM student_profiles sp
            JOIN profiles p ON p.id=sp.id
            WHERE sp.class_id=%s
            """,
            (sess["class_id"],),
        ).fetchall()

        present_ids = set(
            r["student_id"]
            for r in db.execute(
                "SELECT student_id FROM attendance_records WHERE session_id=%s AND status in ('present','late')",
                (session_id,),
            ).fetchall()
        )

        threshold = _sms_threshold()
        for s in all_students:
            if s["id"] in present_ids:
                continue

            try:
                db.execute(
                    """
                    INSERT INTO attendance_records (session_id, student_id, status, method)
                    VALUES (%s,%s,'absent','manual')
                    ON CONFLICT (session_id, student_id) DO NOTHING
                    """,
                    (session_id, s["id"]),
                )
            except Exception:
                pass

            if s.get("phone"):
                send_sms(
                    s["phone"],
                    f"Attendance Alert: Dear {s['full_name']}, you were marked ABSENT for {sess['subject']} session ({sess['class_name']}).",
                )
                # Low attendance warning (per subject/assignment)
                total = db.execute(
                    "SELECT COUNT(*) as c FROM sessions WHERE assignment_id=%s AND status='completed'",
                    (sess["assignment_id"],),
                ).fetchone()["c"]
                if total > 0:
                    present = db.execute(
                        """
                        SELECT COUNT(*) as c
                        FROM attendance_records ar
                        JOIN sessions s2 ON s2.id=ar.session_id
                        WHERE ar.student_id=%s AND s2.assignment_id=%s
                          AND s2.status='completed'
                          AND ar.status in ('present','late')
                        """,
                        (s["id"], sess["assignment_id"]),
                    ).fetchone()["c"]
                    pct = (present / total) * 100
                    if pct < threshold:
                        send_sms(
                            s["phone"],
                            f"Low Attendance Warning: Dear {s['full_name']}, your attendance in {sess['subject']} is {pct:.1f}% ({present}/{total}).",
                        )

        db.commit()
    finally:
        db.close()

