from flask import session
from db.database import get_db

def get_dashboard_data(role):
    db = get_db()
    if role == "student":
        student = db.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()
        if not student:
            return {}
        attendance = db.execute(
            """
            SELECT c.subject, c.class_name, c.id as class_id,
                   COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
                   (SELECT COUNT(*) FROM qr_tokens q2 WHERE q2.class_id=c.id AND q2.is_active=0) as total_sessions
            FROM classes c LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=%s
            WHERE c.class_name=%s GROUP BY c.id, c.subject, c.class_name
            """,
            (session["user_id"], student["class_name"]),
        ).fetchall()
        recent = db.execute(
            """
            SELECT a.marked_at, a.status, c.subject, q.session_label FROM attendance a
            JOIN qr_tokens q ON a.token_id=q.id JOIN classes c ON a.class_id=c.id
            WHERE a.student_id=%s ORDER BY a.marked_at DESC LIMIT 10
            """,
            (session["user_id"],),
        ).fetchall()
        return {"student": dict(student), "attendance": attendance, "recent": recent}
    return {}
