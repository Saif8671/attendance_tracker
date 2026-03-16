from flask import session
from db.database import get_db

def get_dashboard_data(role):
    db = get_db()
    if role == "student":
        student = db.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()
        class_name = student["class_name"]
        classes = db.execute("SELECT * FROM classes WHERE class_name=%s", (class_name,)).fetchall()
        
        subject_stats = []
        for c in classes:
            total = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0", (c["id"],)).fetchone()["c"]
            present = db.execute("SELECT COUNT(*) as c FROM attendance WHERE student_id=%s AND class_id=%s AND status='present'", (session["user_id"], c["id"])).fetchone()["c"]
            pct = (present / total * 100) if total > 0 else 0
            subject_stats.append({
                "subject": c["subject"],
                "present": present,
                "total": total,
                "pct": round(pct, 1)
            })
            
        history = db.execute(
            "SELECT a.*, c.subject FROM attendance a JOIN classes c ON a.class_id=c.id WHERE a.student_id=%s ORDER BY a.marked_at DESC LIMIT 20",
            (session["user_id"],)
        ).fetchall()
        
        return {
            "student": dict(student),
            "stats": subject_stats,
            "history": [dict(h) for h in history]
        }
    return {}

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

def _sms_threshold():
    from flask import current_app, has_app_context
    import os
    if has_app_context():
        return current_app.config.get("SMS_THRESHOLD", 75)
    return int(os.getenv("SMS_THRESHOLD", "75"))
