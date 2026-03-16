import os, time
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

def check_and_notify(student_id, class_id):
    db = get_db()
    from utils.helpers import _sms_threshold
    total = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0", (class_id,)).fetchone()["c"]
    present = db.execute("SELECT COUNT(*) as c FROM attendance WHERE student_id=%s AND class_id=%s AND status='present'", (student_id, class_id)).fetchone()["c"]
    if total > 0:
        pct = (present / total) * 100
        threshold = _sms_threshold()
        if pct < threshold:
            student = db.execute("SELECT * FROM users WHERE id=%s", (student_id,)).fetchone()
            cls = db.execute("SELECT * FROM classes WHERE id=%s", (class_id,)).fetchone()
            if student and student.get("phone"):
                send_sms(student["phone"], f"Attendance Alert: Dear {student['name']}, your attendance in {cls['subject']} is {pct:.1f}% ({present}/{total}). Min required: {threshold}%.")

def notify_absentees(token_id, class_id, class_name, subject):
    db = get_db_standalone()
    from utils.helpers import _sms_threshold
    try:
        all_students = db.execute("SELECT id, name, phone FROM users WHERE class_name=%s AND role='student'", (class_name,)).fetchall()
        present_ids = set(r["student_id"] for r in db.execute("SELECT student_id FROM attendance WHERE token_id=%s", (token_id,)).fetchall())
        absent_students = []
        for s in all_students:
            if s["id"] in present_ids: continue
            try:
                db.execute("INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (%s,%s,%s,%s,%s)", (s["id"], class_id, token_id, datetime.now().isoformat(), "absent"))
            except Exception: pass
            absent_students.append(s)
        db.commit()
        
        total = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=%s AND is_active=0", (class_id,)).fetchone()["c"]
        threshold = _sms_threshold()
        for s in absent_students:
            if not s.get("phone"): continue
            send_sms(s["phone"], f"Attendance Alert: Dear {s['name']}, you were marked ABSENT for {subject} class ({class_name}).")
            if total > 0:
                present = db.execute("SELECT COUNT(*) as c FROM attendance WHERE student_id=%s AND class_id=%s AND status='present'", (s["id"], class_id)).fetchone()["c"]
                pct = (present / total) * 100
                if pct < threshold:
                    send_sms(s["phone"], f"Low Attendance Warning: Dear {s['name']}, your attendance in {subject} is {pct:.1f}% ({present}/{total}).")
    finally:
        db.close()
