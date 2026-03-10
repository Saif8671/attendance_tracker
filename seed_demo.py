"""Seed demo faculty1 and student1 users into the database."""
import sqlite3, hashlib

def h(p): return hashlib.sha256(p.encode()).hexdigest()

db = sqlite3.connect("attendance.db")
db.row_factory = sqlite3.Row

try:
    db.execute(
        "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("faculty1", h("faculty123"), "faculty", "Demo Faculty", None, None, None, None, None, None)
    )
    print("faculty1 created")
except Exception as e:
    print("faculty1:", e)

try:
    db.execute(
        "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("student1", h("student123"), "student", "Demo Student", None, None, None, None, "CSE-Y3", "STU001")
    )
    print("student1 created")
except Exception as e:
    print("student1:", e)

db.commit()
db.close()
print("Done")
