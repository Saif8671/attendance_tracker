import os
from flask import session, current_app, has_app_context

from db.database import get_db


def _db_mode():
    if has_app_context():
        return (current_app.config.get("DB_MODE") or "legacy").strip().lower()
    return (os.getenv("DB_MODE") or "legacy").strip().lower()


def get_dashboard_data(role):
    if role != "student":
        return {}

    db = get_db()
    user_id = session.get("user_id")
    if not user_id:
        return {"student": None, "attendance": [], "recent": []}

    if _db_mode() == "supabase":
        student = db.execute(
            """
            SELECT
              p.id,
              p.full_name as name,
              p.username,
              p.phone,
              p.email,
              sp.roll_no as rollno,
              sp.class_id,
              d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name
            FROM profiles p
            JOIN student_profiles sp ON sp.id=p.id
            JOIN classes c ON c.id=sp.class_id
            JOIN departments d ON d.id=c.department_id
            WHERE p.id=%s
            """,
            (user_id,),
        ).fetchone()
        if not student:
            return {"student": None, "attendance": [], "recent": []}

        attendance = db.execute(
            """
            SELECT
              fa.id as class_id,
              sub.name as subject,
              d.code || '-' || c.section || ' (S' || c.semester || ')' as class_name,
              COUNT(DISTINCT s.id) FILTER (WHERE s.status='completed') as total_sessions,
              COUNT(DISTINCT ar.id) FILTER (WHERE ar.status in ('present','late')) as present_count
            FROM faculty_assignments fa
            JOIN subjects sub ON sub.id=fa.subject_id
            JOIN classes c ON c.id=fa.class_id
            JOIN departments d ON d.id=c.department_id
            LEFT JOIN sessions s ON s.assignment_id=fa.id AND s.status='completed'
            LEFT JOIN attendance_records ar ON ar.session_id=s.id AND ar.student_id=%s
            WHERE fa.class_id=%s
            GROUP BY fa.id, sub.name, class_name
            ORDER BY sub.name
            """,
            (user_id, student["class_id"]),
        ).fetchall()

        recent = db.execute(
            """
            SELECT
              ar.status,
              ar.method,
              ar.marked_at,
              sub.name as subject,
              COALESCE(s.topic, s.session_date::text) as session_label
            FROM attendance_records ar
            JOIN sessions s ON s.id=ar.session_id
            JOIN faculty_assignments fa ON fa.id=s.assignment_id
            JOIN subjects sub ON sub.id=fa.subject_id
            WHERE ar.student_id=%s
            ORDER BY ar.marked_at DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()

        return {
            "student": dict(student),
            "attendance": [dict(a) for a in attendance],
            "recent": [dict(r) for r in recent],
        }

    # ---- Legacy schema ----
    student = db.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
    if not student:
        return {"student": None, "attendance": [], "recent": []}

    subject_stats = db.execute(
        """
        SELECT c.subject, c.id as class_id,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
               (SELECT COUNT(*) FROM qr_tokens q WHERE q.class_id=c.id AND q.is_active=0) as total_sessions
        FROM classes c
        JOIN enrollments e ON e.class_id=c.id AND e.student_id=%s
        LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=%s
        GROUP BY c.id, c.subject
        ORDER BY c.subject
        """,
        (user_id, user_id),
    ).fetchall()

    attendance = []
    for s in subject_stats:
        attendance.append(
            {
                "subject": s["subject"],
                "class_id": s["class_id"],
                "class_name": student.get("class_name") or "",
                "present_count": int(s["present_count"] or 0),
                "total_sessions": int(s["total_sessions"] or 0),
            }
        )

    recent = db.execute(
        """
        SELECT a.status, a.marked_at, c.subject, q.session_label
        FROM attendance a
        JOIN classes c ON c.id=a.class_id
        LEFT JOIN qr_tokens q ON q.id=a.token_id
        WHERE a.student_id=%s
        ORDER BY a.marked_at DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()

    return {
        "student": dict(student),
        "attendance": attendance,
        "recent": [dict(r) for r in recent],
    }


def _sms_threshold():
    if has_app_context():
        return current_app.config.get("SMS_THRESHOLD", 75)
    return int(os.getenv("SMS_THRESHOLD", "75"))

