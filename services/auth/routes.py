from flask import Blueprint, render_template, request, redirect, url_for, session
from services.shared.db import get_db
from services.shared.security import hash_pw
from services.crm.helpers import get_dashboard_data

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(f"crm.dashboard_{session['role']}"))
    return render_template("login.html")

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for(f"crm.dashboard_{session['role']}"))

    if request.method == "GET":
        return render_template("signup.html", form={})

    role = request.form.get("role", "").strip().lower()
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    class_name = request.form.get("class_name", "").strip()
    rollno = request.form.get("rollno", "").strip()

    form = {
        "role": role,
        "name": name,
        "username": username,
        "email": email,
        "phone": phone,
        "class_name": class_name,
        "rollno": rollno,
    }

    if role not in {"student", "faculty"}:
        return render_template("signup.html", error="Please choose Student or Faculty", form=form)
    if not name or not username or not password:
        return render_template("signup.html", error="Name, username, and password are required", form=form)
    if password != confirm_password:
        return render_template("signup.html", error="Passwords do not match", form=form)
    if role == "student" and not class_name:
        return render_template("signup.html", error="Class name is required for students", form=form)

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username=%s", (username,)).fetchone()
    if existing:
        return render_template("signup.html", error="Username already taken", form=form)

    db.execute(
        "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (username, hash_pw(password), role, name, phone, email, "", "", class_name if role == "student" else "", rollno),
    )
    db.commit()

    user = db.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
    if user:
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        return redirect(url_for(f"crm.dashboard_{user['role']}"))

    return render_template("signup.html", error="Signup failed. Please try again.", form=form)

@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip().lower()
    password = hash_pw(request.form["password"])
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, password),
    ).fetchone()

    if user:
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        next_scan = session.pop("next_scan", None)
        if next_scan and user["role"] == "student":
            return redirect(url_for("crm.scan_qr", token=next_scan))
        return redirect(url_for(f"crm.dashboard_{user['role']}"))
    return render_template("login.html", error="Invalid username or password")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))

@auth_bp.route("/admin/reset_password/<int:user_id>", methods=["POST"])
def reset_password(user_id):
    if session.get("role") != "admin":
        return redirect("/")
    new_pw = request.form.get("new_password", "").strip()
    if not new_pw:
        return redirect(url_for("crm.dashboard_admin") + "?msg=Password+cannot+be+empty")
    db = get_db()
    db.execute("UPDATE users SET password=%s WHERE id=%s", (hash_pw(new_pw), user_id))
    db.commit()
    return redirect(url_for("crm.dashboard_admin") + "?msg=Password+reset+successfully")

@auth_bp.route("/reset_my_password", methods=["POST"])
def reset_my_password():
    if "user_id" not in session:
        return redirect("/")
    old_pw = request.form.get("old_password", "")
    new_pw = request.form.get("new_password", "").strip()
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id=%s AND password=%s",
        (session["user_id"], hash_pw(old_pw)),
    ).fetchone()
    if not user:
        role = session["role"]
        return render_template(f"{role}.html", pw_error="Current password is incorrect", **get_dashboard_data(role))
    db.execute("UPDATE users SET password=%s WHERE id=%s", (hash_pw(new_pw), session["user_id"]))
    db.commit()
    return redirect(url_for(f"crm.dashboard_{session['role']}") + "?msg=Password+changed+successfully")
