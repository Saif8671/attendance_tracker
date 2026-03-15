"""Seed demo faculty1 and student1 users into the database."""
from services.shared.db import get_db_standalone
from services.shared.security import hash_pw

db = get_db_standalone()

try:
    db.execute(
        "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        ("faculty1", hash_pw("faculty123"), "faculty", "Demo Faculty", None, None, None, None, None, None),
    )
    print("faculty1 created")
except Exception as e:
    print("faculty1:", e)

try:
    db.execute(
        "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        ("student1", hash_pw("student123"), "student", "Demo Student", None, None, None, None, "CSE-Y3", "STU001"),
    )
    print("student1 created")
except Exception as e:
    print("student1:", e)

db.commit()
db.close()
print("Done")
