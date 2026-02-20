"""
Attendance Tracker - Full Stack Python Application
Features: QR-based token attendance, Admin/Faculty/Student dashboards, SMS notifications
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3, os, csv, io, time, hashlib, secrets
from datetime import datetime
import qrcode
from io import BytesIO

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
QR_VALID_SECONDS = 120
DB_PATH = "attendance.db"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE       = os.getenv("TWILIO_PHONE", "")
SMS_THRESHOLD = 75

# ─── DATABASE ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_class_from_htno(htno):
    """Derive class name from HTNO e.g. 238P1A0401 -> EEE-Y1"""
    try:
        year   = htno[3:5]   # P1 or P5
        branch = htno[6:8]   # 02=CSE, 03=ECE, 04=EEE, 05=MECH, 66=AIML
        branch_map = {'02':'CSE','03':'ECE','04':'EEE','05':'MECH','06':'CIVIL','66':'AIML'}
        b  = branch_map.get(branch, f'BR{branch}')
        yr = 'Y1' if year == 'P1' else 'Y3'
        return f'{b}-{yr}'
    except:
        return 'GENERAL'

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username  TEXT UNIQUE NOT NULL,
        password  TEXT NOT NULL,
        role      TEXT NOT NULL,
        name      TEXT NOT NULL,
        phone     TEXT,
        email     TEXT,
        gender    TEXT,
        dob       TEXT,
        class_name TEXT,
        rollno    TEXT
    );
    CREATE TABLE IF NOT EXISTS classes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        subject    TEXT NOT NULL,
        faculty_id INTEGER NOT NULL,
        class_name TEXT NOT NULL,
        FOREIGN KEY(faculty_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS qr_tokens (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        token         TEXT UNIQUE NOT NULL,
        class_id      INTEGER NOT NULL,
        faculty_id    INTEGER NOT NULL,
        created_at    REAL NOT NULL,
        expires_at    REAL NOT NULL,
        session_label TEXT,
        is_active     INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        class_id   INTEGER NOT NULL,
        token_id   INTEGER NOT NULL,
        marked_at  TEXT NOT NULL,
        status     TEXT DEFAULT 'present',
        UNIQUE(student_id, token_id),
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(class_id)   REFERENCES classes(id)
    );
    """)

    pw = lambda p: hashlib.sha256(p.encode()).hexdigest()

    # ── Seed admin & faculty ──────────────────────────────────────────────────
    base_users = [
        ("admin",    pw("admin123"),   "admin",   "Administrator", "+910000000001", None, None, None, None,    None),
        ("faculty1", pw("faculty123"), "faculty", "Dr. Sharma",    "+910000000002", None, None, None, "CSE-Y1", None),
        ("faculty2", pw("faculty123"), "faculty", "Prof. Mehta",   "+910000000003", None, None, None, "EEE-Y1", None),
        ("faculty3", pw("faculty123"), "faculty", "Dr. Reddy",     "+910000000004", None, None, None, "AIML-Y1",None),
        ("faculty4", pw("faculty123"), "faculty", "Prof. Rao",     "+910000000005", None, None, None, "ECE-Y1", None),
    ]
    for u in base_users:
        try:
            db.execute("INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)", u)
        except: pass

    # ── Seed students from your CSV data ─────────────────────────────────────
    students_csv = [
        ("238P1A0201","SATIKA AKSHAY",       "+918374070092","shyamsatika@gmail.com",   "M","2005-06-11"),
        ("238P1A0203","S DATHU KUMAR",        "+919390761758","sdathu47@gmail.com",       "M","2006-01-01"),
        ("238P1A0204","BANOTH KALYANI",       "+919381467439","rahulrox380@gmail.com",    "F","2005-01-05"),
        ("238P1A0205","DOEJOD RAHUL",         "+919381467439","rahulrox380@gmail.com",    "M","2004-06-04"),
        ("238P1A0207","KUNA SIDDU",           "+919704248361","siddukua9@gmail.com",      "M","2004-11-05"),
        ("238P1A0301","MOHD YAHIYA FURKHAN",  "+917075639624","mohdyahiyafurkha786@gmail.com","M","2004-05-27"),
        ("238P1A0401","G ASHWINI",            "+918074673065","goigeurashwii@gmail.com",  "F","2006-02-28"),
        ("238P1A0402","DIPPY RANI GAHAN",     "+916301697178","raijyothi83@gmail.com",    "F","2004-01-10"),
        ("238P1A0403","P MANASA",             "+919542500284","polemaasa767@gmail.com",   "F","2004-08-06"),
        ("238P1A0404","ALETI NARESH",         "+919398140714","yadavareshy78@gmail.com",  "M","2006-06-06"),
        ("238P1A0405","BODA PAVAN",           "+917794070258","bodapava123456@gmail.com", "M","2004-06-12"),
        ("238P1A0406","KURIMINDLA RAHUL",     "+916309349625","rahulkurimidla876@gmail.com","M","2005-08-08"),
        ("238P1A0407","PEDDI RAHUL",          "+919490720882","rahulpeddi882@gmail.com",  "M","2005-12-05"),
        ("238P1A0408","CHIDRAPU RAKESH",      "+919182424015","rakeshchidrapu@gmail.com", "M","2004-11-14"),
        ("238P1A0409","B SANDEEP",            "+917997527508","boalasadeepyadav@gmail.com","M","2006-05-15"),
        ("238P1A0410","M SANJANA",            "+918340911882","sajukuttim@gmail.com",     "F","2006-01-25"),
        ("238P1A0411","BADAVATH SANTHOSH",    "+919390627959","badavathsathosh991@gmail.com","M","2006-07-18"),
        ("238P1A0413","SARGULLA SANJANA",     "+918522873998","sargullasajaa@gmail.com",  "F","2006-06-05"),
        ("238P1A0414","PANDUGA VAMSHI KRISHNA REDDY","+919494604495","padugavamshikrishareddy213@gmail.com","M","2005-04-13"),
        ("238P1A0415","PALADI VARSHIT",       "+916304434425","yuva9848@gmail.com",       "M","2005-07-03"),
        ("238P1A0416","GUGULOTH VEERANNA",    "+918341843276","ramdasgugulothramdas8@gmail.com","M","2005-12-16"),
        ("238P1A0417","GUDAPURI YASHWANTH ALWAR","+918333061492","yashwathaalwar28@gmail.com","M","2001-06-06"),
        ("238P1A0418","MOHAMMED ZAMEER",      "+918106116205","mohammedzameer78666@gmail.com","M","2003-12-12"),
        ("238P1A0501","AKEPOGU ABHINAND",     "+919963254316","abhiadladdu@gmail.com",    "M","2005-06-28"),
        ("238P1A6601","ALENOOR ABHINAV",      "+918464090282","abhiavstar9703@gmail.com", "M","2006-01-04"),
        ("238P1A6602","G ANISH SINGH",        "+917989659447","aishs8544@gmail.com",      "M","2004-05-26"),
        ("238P1A6603","ARMAN ALI KHAN",       "+919441265746","armakha90178@gmail.com",   "M","2006-11-08"),
        ("238P1A6604","DEBASHISH NAYAK",      "+918465997817","debashish83@gmail.com",    "M","2006-03-03"),
        ("238P1A6605","BEST KRISHNA KUMAR",   "+919014946170","bkrishabkrishakumar@gmail.com","M","2004-06-13"),
        ("238P1A6607","NAVADEEP MATTAPARTHY", "+916309876827","avadeepmattaparthy2704@gmail.com","M","2005-04-17"),
        ("238P1A6608","C PRAVALIKA",          "+917993613582","chikodrapravalika900@gmail.com","F","2005-11-15"),
        ("238P1A6609","SAIFUR RAHMAN",        "+916303087613","wardasaif2@gmail.com",     "M","2005-03-24"),
        ("238P1A6611","ROHAN THANGELLA",      "+919848372566","karakarroha666@gmail.com", "M","2005-05-01"),
        ("238P1A6612","ROHIT SHINDE",         "+919390834189","rohitshide35358@gmail.com","M","2005-07-15"),
        ("238P1A6613","M SAKETH",             "+919177281717","sakethm650@gmail.com",     "M","2005-05-03"),
        ("238P1A6614","KAMBHOJA SANTHOSH",    "+917569375541","sathu1217x@gmail.com",     "M","2005-11-18"),
        ("238P1A6615","SHETTY SHIVA",         "+919392292573","shettyshiva2020@gmail.com","M","2004-02-16"),
        ("238P1A6616","SUSHAANTH RAVULA",     "+919848836268","ravulasushaath@gmail.com", "M","2006-05-21"),
        ("238P1A6617","SYED TAHAULLA HUSSAINI","+916281509389","stahaulla01@gmail.com",  "M","2005-11-25"),
        ("238P1A6618","DHARMINI VIGNYAN",     "+917993458197","vigyadharmii.g@gmail.com", "M","2005-06-14"),
        ("238P5A0201","MOTTE AKSHITH",        "+919346721784","hmr0759@gmail.com",        "M","2003-08-02"),
        ("238P5A0202","ANKANNAGARI JASHUVA",  "+919701962290","akaagarijashuva.19072001@gmail.com","M","2001-07-19"),
        ("238P5A0203","KEERTHEE BEHERA",      "+919618854077","keertheebehera@gmail.com", "F","2004-11-02"),
        ("238P5A0204","B KUSHIKA",            "+919381462874","boshagarikushika2401@gmail.com","F","2005-01-24"),
        ("238P5A0205","BUSHAM NIHITH KUMAR",  "+919441073338","ihithkumarbusham@gmail.com","M","2005-04-18"),
        ("238P5A0206","KORRA PRAJANTHI",      "+918106535315","korrasaiaik007@gmail.com", "F","2004-08-14"),
        ("238P5A0207","BURGULA SAIPRIYA",     "+919949316419","saipriyaguptha01@gmail.com","F","2004-02-16"),
        ("238P5A0208","M SHIVA TEJA",         "+919704505479","mallakshivateja@gmail.com","M","2005-08-13"),
        ("238P5A0301","ARELLI AKHIL",         "+919392778805","arellisridhar59@gmail.com","M","2005-06-15"),
        ("238P5A0302","MYLE DEEPANSH KUMAR",  "+919533309004","myledeepashkumar@gmail.com","M","2004-07-18"),
        ("238P5A0303","GADDAM MURARI",        "+917396166966","gaddammurari@gmail.com",   "M","2003-07-04"),
        ("238P5A0304","BORE SANJAY",          "+917675081886","sajubore2@gmail.com",      "M","2004-01-08"),
        ("238P5A0305","KARNIKI SIVA KRISHNA", "+919391338773","shivakrishakariki@gmail.com","M","2004-09-23"),
        ("238P5A0401","K BINDUSRI LAXMI",     "+916300005890","bidukamisetty@gmail.com",  "F","2004-08-25"),
        ("238P5A0402","J DIVYASREE",          "+919989678432","divyasreejogu30@gmail.com","F","2005-07-30"),
    ]

    for htno, name, phone, email, gender, dob in students_csv:
        username   = htno.lower()
        password   = hashlib.sha256("student123".encode()).hexdigest()
        class_name = get_class_from_htno(htno)
        try:
            db.execute(
                "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (username, password, "student", name, phone, email, gender, dob, class_name, htno)
            )
        except: pass

    # ── Seed classes / subjects ───────────────────────────────────────────────
    classes_data = [
        ("Data Structures",    2, "CSE-Y1"),
        ("Algorithms",         2, "CSE-Y1"),
        ("Circuit Theory",     3, "EEE-Y1"),
        ("Electrical Machines",3, "EEE-Y1"),
        ("Machine Learning",   4, "AIML-Y1"),
        ("Python Programming", 4, "AIML-Y1"),
        ("Signals & Systems",  5, "ECE-Y1"),
        ("Digital Electronics",5, "ECE-Y1"),
        ("Database Systems",   2, "CSE-Y3"),
        ("Computer Networks",  2, "CSE-Y3"),
        ("Power Systems",      3, "EEE-Y3"),
        ("Embedded Systems",   5, "ECE-Y3"),
        ("Engineering Mechanics",2,"MECH-Y1"),
    ]
    for c in classes_data:
        try:
            db.execute("INSERT INTO classes (subject,faculty_id,class_name) VALUES (?,?,?)", c)
        except: pass

    # ── Migrate existing DB: add missing columns if they don't exist ────────────
    for col, typedef in [("email","TEXT"), ("gender","TEXT"), ("dob","TEXT")]:
        try:
            db.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
            print(f"[DB] Migrated: added column '{col}' to users table")
        except:
            pass  # column already exists — fine

    db.commit()
    db.close()

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def send_sms(to, msg):
    if not TWILIO_ACCOUNT_SID:
        print(f"[SMS DEMO] To {to}: {msg}")
        return True
    try:
        from twilio.rest import Client
        Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(
            body=msg, from_=TWILIO_PHONE, to=to)
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False

def check_and_notify(student_id, class_id):
    db = get_db()
    total   = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=? AND is_active=0", (class_id,)).fetchone()["c"]
    present = db.execute("SELECT COUNT(*) as c FROM attendance WHERE student_id=? AND class_id=? AND status='present'",
                         (student_id, class_id)).fetchone()["c"]
    if total > 0:
        pct = (present / total) * 100
        if pct < SMS_THRESHOLD:
            student = db.execute("SELECT * FROM users WHERE id=?", (student_id,)).fetchone()
            cls     = db.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
            if student and student["phone"]:
                msg = (f"Attendance Alert: Dear {student['name']}, your attendance in "
                       f"{cls['subject']} is {pct:.1f}% ({present}/{total} classes). "
                       f"Minimum required: {SMS_THRESHOLD}%. Please attend regularly.")
                send_sms(student["phone"], msg)
    db.close()

# ─── AUTH ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(f"dashboard_{session['role']}"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = hash_pw(request.form["password"])
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
    db.close()
    if user:
        session["user_id"] = user["id"]
        session["role"]    = user["role"]
        session["name"]    = user["name"]
        next_scan = session.pop("next_scan", None)
        if next_scan and user["role"] == "student":
            return redirect(url_for("scan_qr", token=next_scan))
        return redirect(url_for(f"dashboard_{user['role']}"))
    return render_template("login.html", error="Invalid credentials")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ─── ADMIN ───────────────────────────────────────────────────────────────────
@app.route("/admin")
def dashboard_admin():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) as c FROM users WHERE role='student'").fetchone()["c"],
        "faculty":  db.execute("SELECT COUNT(*) as c FROM users WHERE role='faculty'").fetchone()["c"],
        "classes":  db.execute("SELECT COUNT(*) as c FROM classes").fetchone()["c"],
        "sessions": db.execute("SELECT COUNT(*) as c FROM qr_tokens").fetchone()["c"],
    }
    students = db.execute("""
        SELECT u.*,
        (SELECT COUNT(*) FROM attendance a WHERE a.student_id=u.id AND a.status='present') as present_count,
        (SELECT COUNT(*) FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE c.class_name=u.class_name AND q.is_active=0) as total_sessions
        FROM users u WHERE u.role='student' ORDER BY u.class_name, u.rollno
    """).fetchall()
    faculty_list = db.execute("SELECT * FROM users WHERE role='faculty' ORDER BY name").fetchall()
    classes = db.execute("SELECT c.*, u.name as faculty_name FROM classes c JOIN users u ON c.faculty_id=u.id ORDER BY c.class_name, c.subject").fetchall()
    db.close()
    msg = request.args.get("msg", "")
    return render_template("admin.html", stats=stats, students=students, classes=classes,
                           faculty_list=faculty_list, msg=msg)

@app.route("/admin/add_user", methods=["POST"])
def add_user():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    try:
        db.execute("INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (request.form["username"], hash_pw(request.form["password"]),
             request.form["role"], request.form["name"],
             request.form.get("phone",""), request.form.get("email",""),
             request.form.get("gender",""), request.form.get("dob",""),
             request.form.get("class_name",""), request.form.get("rollno","")))
        db.commit()
    except: pass
    db.close()
    return redirect(url_for("dashboard_admin") + "?msg=User+added+successfully")

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    db.execute("DELETE FROM attendance WHERE student_id=?", (user_id,))
    db.execute("DELETE FROM qr_tokens WHERE faculty_id=?", (user_id,))
    db.execute("DELETE FROM classes WHERE faculty_id=?", (user_id,))
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()
    return redirect(url_for("dashboard_admin") + "?msg=User+deleted")

# ─── IMPORT CSV ──────────────────────────────────────────────────────────────
@app.route("/admin/import_csv", methods=["POST"])
def import_csv():
    if session.get("role") != "admin": return redirect("/")
    file = request.files.get("csv_file")
    role = request.form.get("role", "student")

    if not file or not file.filename.endswith(".csv"):
        return redirect(url_for("dashboard_admin") + "?msg=Invalid+file.+Please+upload+a+.csv+file")

    # Try multiple encodings to handle Excel-saved CSVs
    raw = file.read()
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            content = raw.decode(enc)
            break
        except:
            content = None
    if not content:
        return redirect(url_for("dashboard_admin") + "?msg=Could+not+read+file.+Save+as+CSV+UTF-8")

    reader  = csv.DictReader(io.StringIO(content))
    headers = [h.strip() for h in (reader.fieldnames or [])]

    db = get_db()
    success  = 0
    skipped  = 0
    errors   = []   # collect per-row error details

    for i, raw_row in enumerate(reader, start=2):  # row 1 = header
        # Strip whitespace from all keys and values
        row = {k.strip(): (v.strip() if v else "") for k, v in raw_row.items() if k}

        # ── flexible column detection (handles many real-world CSV formats) ───
        htno   = (row.get("HTNO") or row.get("htno") or row.get("Hall Ticket No") or
                  row.get("Roll No") or row.get("rollno") or row.get("RollNo") or "")
        name   = (row.get("Name") or row.get("name") or row.get("Student Name") or
                  row.get("Full Name") or "").title()
        phone  = (row.get("Phone No") or row.get("phone") or row.get("Phone") or
                  row.get("Mobile") or row.get("Mobile No") or row.get("Contact") or "")
        email  = (row.get("Email ID") or row.get("email") or row.get("Email") or
                  row.get("Mail") or "")
        gender = (row.get("Gender") or row.get("gender") or row.get("Sex") or "")
        dob    = (row.get("Date of Birth") or row.get("dob") or row.get("DOB") or
                  row.get("Birth Date") or "")
        pwd    = (row.get("password") or row.get("Password") or "student123")
        uname  = (row.get("username") or row.get("Username") or "")
        class_name_csv = (row.get("class_name") or row.get("Class") or
                          row.get("Section") or row.get("Branch") or "")

        # Skip completely empty rows
        if not any(row.values()):
            continue

        # Validate required fields
        if not name:
            errors.append(f"Row {i}: skipped — Name is empty")
            skipped += 1
            continue

        # Build username: prefer explicit > htno > name-based
        if not uname:
            if htno:
                uname = htno.lower().strip()
            else:
                uname = name.replace(" ", "").lower()[:15]

        if not uname:
            errors.append(f"Row {i} ({name}): skipped — could not generate username")
            skipped += 1
            continue

        # Normalise phone: add +91 if looks like Indian number without code
        if phone and not phone.startswith("+"):
            digits = "".join(c for c in phone if c.isdigit())
            if len(digits) == 10:
                phone = "+91" + digits
            elif len(digits) == 12 and digits.startswith("91"):
                phone = "+" + digits
            else:
                phone = "+91" + digits  # best guess

        # Derive class_name: from HTNO if present, otherwise from CSV column
        if htno:
            class_name = get_class_from_htno(htno)
        elif class_name_csv:
            class_name = class_name_csv
        else:
            class_name = "GENERAL"

        try:
            db.execute(
                "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (uname, hash_pw(pwd), role, name, phone, email, gender, dob, class_name, htno or uname)
            )
            success += 1
        except sqlite3.IntegrityError:
            # Username already exists → try htno_name combo
            alt_uname = uname + "_" + str(i)
            try:
                db.execute(
                    "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (alt_uname, hash_pw(pwd), role, name, phone, email, gender, dob, class_name, htno or uname)
                )
                success += 1
            except Exception as e2:
                errors.append(f"Row {i} ({name}): duplicate username '{uname}' — skipped")
                skipped += 1
        except Exception as e:
            errors.append(f"Row {i} ({name}): error — {str(e)}")
            skipped += 1

    db.commit()
    db.close()

    # Store errors in session to show on dashboard
    session["csv_errors"] = errors[:20]  # cap at 20 to avoid giant URLs
    msg = f"CSV+imported:+{success}+added"
    if skipped:
        msg += f",+{skipped}+skipped"
    return redirect(url_for("dashboard_admin") + f"?msg={msg}&tab=import")

@app.route("/admin/preview_csv", methods=["POST"])
def preview_csv():
    """Return JSON preview of what the CSV contains before importing"""
    if session.get("role") != "admin": return jsonify({"error": "unauthorized"})
    file = request.files.get("csv_file")
    if not file: return jsonify({"error": "no file"})
    raw = file.read()
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try: content = raw.decode(enc); break
        except: content = None
    if not content: return jsonify({"error": "encoding error"})
    reader = csv.DictReader(io.StringIO(content))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows = []
    for i, row in enumerate(reader):
        if i >= 5: break  # preview first 5 rows only
        rows.append({k.strip(): v.strip() for k, v in row.items() if k})
    return jsonify({"headers": headers, "preview": rows, "total_hint": "(showing first 5 rows)"})

# ─── ADMIN SUBJECTS ──────────────────────────────────────────────────────────
@app.route("/admin/add_subject", methods=["POST"])
def add_subject():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    try:
        db.execute("INSERT INTO classes (subject,faculty_id,class_name) VALUES (?,?,?)",
            (request.form["subject"], int(request.form["faculty_id"]), request.form["class_name"]))
        db.commit()
    except: pass
    db.close()
    return redirect(url_for("dashboard_admin") + "?msg=Subject+added")

@app.route("/admin/delete_subject/<int:class_id>", methods=["POST"])
def delete_subject(class_id):
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    db.execute("DELETE FROM attendance WHERE class_id=?", (class_id,))
    db.execute("DELETE FROM qr_tokens WHERE class_id=?", (class_id,))
    db.execute("DELETE FROM classes WHERE id=?", (class_id,))
    db.commit()
    db.close()
    return redirect(url_for("dashboard_admin") + "?msg=Subject+deleted")

# ─── ADMIN MANUAL ATTENDANCE ─────────────────────────────────────────────────
@app.route("/admin/manual_attendance", methods=["GET"])
def manual_attendance_page():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    students     = db.execute("SELECT * FROM users WHERE role='student' ORDER BY class_name, rollno").fetchall()
    classes      = db.execute("SELECT c.*, u.name as faculty_name FROM classes c JOIN users u ON c.faculty_id=u.id ORDER BY c.class_name, c.subject").fetchall()
    sessions_list = db.execute("""
        SELECT q.id, q.session_label, q.created_at, c.subject, c.class_name, q.class_id
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id ORDER BY q.created_at DESC
    """).fetchall()
    db.close()
    msg = request.args.get("msg", "")
    return render_template("manual_attendance.html", students=students, classes=classes,
                           sessions=sessions_list, msg=msg)

@app.route("/admin/manual_attendance", methods=["POST"])
def manual_attendance_submit():
    if session.get("role") != "admin": return redirect("/")
    student_id = int(request.form["student_id"])
    class_id   = int(request.form["class_id"])
    token_id   = int(request.form["token_id"])
    status     = request.form.get("status", "present")
    db = get_db()
    try:
        db.execute("INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (?,?,?,?,?)",
                   (student_id, class_id, token_id, datetime.now().isoformat(), status))
        db.commit()
        msg = "Attendance+marked+successfully"
    except sqlite3.IntegrityError:
        db.execute("UPDATE attendance SET status=?, marked_at=? WHERE student_id=? AND token_id=?",
                   (status, datetime.now().isoformat(), student_id, token_id))
        db.commit()
        msg = "Attendance+updated+successfully"
    except Exception as e:
        msg = f"Error:+{e}"
    db.close()
    return redirect(url_for("manual_attendance_page") + f"?msg={msg}")

@app.route("/admin/attendance_report")
def attendance_report():
    if session.get("role") != "admin": return redirect("/")
    db = get_db()
    report = db.execute("""
        SELECT u.name, u.rollno, u.class_name, c.subject,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present,
               COUNT(q.id) as total,
               ROUND(COUNT(CASE WHEN a.status='present' THEN 1 END)*100.0/MAX(COUNT(q.id),1),1) as pct
        FROM users u
        JOIN classes c ON c.class_name=u.class_name
        LEFT JOIN qr_tokens q ON q.class_id=c.id AND q.is_active=0
        LEFT JOIN attendance a ON a.student_id=u.id AND a.token_id=q.id
        WHERE u.role='student'
        GROUP BY u.id, c.id ORDER BY u.class_name, c.subject, u.name
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in report])

@app.route("/admin/get_sessions/<int:class_id>")
def get_sessions_for_class(class_id):
    if session.get("role") != "admin": return jsonify([])
    db = get_db()
    rows = db.execute("SELECT id, session_label, created_at FROM qr_tokens WHERE class_id=? ORDER BY created_at DESC", (class_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/admin/get_students_for_class/<int:class_id>")
def get_students_for_class(class_id):
    if session.get("role") != "admin": return jsonify([])
    db = get_db()
    cls = db.execute("SELECT class_name FROM classes WHERE id=?", (class_id,)).fetchone()
    if not cls: return jsonify([])
    rows = db.execute("SELECT id, name, rollno FROM users WHERE class_name=? AND role='student' ORDER BY rollno", (cls["class_name"],)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

# ─── FACULTY ─────────────────────────────────────────────────────────────────
@app.route("/faculty")
def dashboard_faculty():
    if session.get("role") != "faculty": return redirect("/")
    db = get_db()
    classes = db.execute("SELECT * FROM classes WHERE faculty_id=?", (session["user_id"],)).fetchall()
    recent_tokens = db.execute("""
        SELECT q.*, c.subject, c.class_name,
               (SELECT COUNT(*) FROM attendance a WHERE a.token_id=q.id) as marked_count
        FROM qr_tokens q JOIN classes c ON q.class_id=c.id
        WHERE q.faculty_id=? ORDER BY q.created_at DESC LIMIT 10
    """, (session["user_id"],)).fetchall()
    db.close()
    return render_template("faculty.html", classes=classes, recent_tokens=recent_tokens,
                           now=time.time(), qr_valid=QR_VALID_SECONDS)

@app.route("/faculty/generate_qr", methods=["POST"])
def generate_qr():
    if session.get("role") != "faculty": return redirect("/")
    class_id = request.form["class_id"]
    label    = request.form.get("label", datetime.now().strftime("%d %b %Y %H:%M"))
    db = get_db()
    db.execute("UPDATE qr_tokens SET is_active=0 WHERE class_id=? AND faculty_id=?", (class_id, session["user_id"]))
    token = secrets.token_urlsafe(32)
    now   = time.time()
    db.execute("INSERT INTO qr_tokens (token,class_id,faculty_id,created_at,expires_at,session_label,is_active) VALUES (?,?,?,?,?,?,1)",
               (token, class_id, session["user_id"], now, now + QR_VALID_SECONDS, label))
    db.commit()
    db.close()
    return redirect(url_for("show_qr", token=token))

@app.route("/qr/<token>")
def show_qr(token):
    db = get_db()
    t = db.execute("SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=?", (token,)).fetchone()
    db.close()
    if not t: return "Invalid token", 404
    return render_template("qr_display.html", token=dict(t), now=time.time(), qr_valid=QR_VALID_SECONDS)

@app.route("/qr_image/<token>")
def qr_image(token):
    scan_url = request.host_url + f"scan/{token}"
    img = qrcode.make(scan_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/faculty/attendance/<int:class_id>")
def faculty_attendance(class_id):
    if session.get("role") != "faculty": return redirect("/")
    db = get_db()
    cls = db.execute("SELECT * FROM classes WHERE id=? AND faculty_id=?", (class_id, session["user_id"])).fetchone()
    if not cls: return redirect(url_for("dashboard_faculty"))
    sessions_list = db.execute("SELECT * FROM qr_tokens WHERE class_id=? ORDER BY created_at DESC", (class_id,)).fetchall()
    students = db.execute("""
        SELECT u.*, COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count
        FROM users u
        LEFT JOIN attendance a ON a.student_id=u.id AND a.class_id=?
        WHERE u.class_name=? AND u.role='student'
        GROUP BY u.id ORDER BY u.rollno
    """, (class_id, cls["class_name"])).fetchall()
    total_sessions = db.execute("SELECT COUNT(*) as c FROM qr_tokens WHERE class_id=? AND is_active=0", (class_id,)).fetchone()["c"]
    db.close()
    return render_template("faculty_attendance.html", cls=dict(cls), sessions=sessions_list,
                           students=students, total=total_sessions)

# ─── STUDENT ─────────────────────────────────────────────────────────────────
@app.route("/student")
def dashboard_student():
    if session.get("role") != "student": return redirect("/")
    db = get_db()
    student = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    attendance = db.execute("""
        SELECT c.subject, c.class_name, c.id as class_id,
               COUNT(CASE WHEN a.status='present' THEN 1 END) as present_count,
               (SELECT COUNT(*) FROM qr_tokens q2 WHERE q2.class_id=c.id AND q2.is_active=0) as total_sessions
        FROM classes c
        LEFT JOIN attendance a ON a.class_id=c.id AND a.student_id=?
        WHERE c.class_name=?
        GROUP BY c.id
    """, (session["user_id"], student["class_name"])).fetchall()
    recent = db.execute("""
        SELECT a.marked_at, a.status, c.subject, q.session_label
        FROM attendance a
        JOIN qr_tokens q ON a.token_id=q.id
        JOIN classes c ON a.class_id=c.id
        WHERE a.student_id=? ORDER BY a.marked_at DESC LIMIT 10
    """, (session["user_id"],)).fetchall()
    db.close()
    return render_template("student.html", student=dict(student), attendance=attendance, recent=recent)

@app.route("/student/scanner")
def student_scanner():
    if session.get("role") != "student": return redirect("/")
    return render_template("student_scanner.html")

# ─── QR SCAN ─────────────────────────────────────────────────────────────────
@app.route("/scan/<token>")
def scan_qr(token):
    if "user_id" not in session:
        session["next_scan"] = token
        return redirect(url_for("index"))
    if session.get("role") != "student":
        return render_template("scan_result.html", success=False, msg="Only students can mark attendance.")
    db = get_db()
    t = db.execute("SELECT q.*, c.subject, c.class_name FROM qr_tokens q JOIN classes c ON q.class_id=c.id WHERE q.token=? AND q.is_active=1", (token,)).fetchone()
    if not t:
        db.close()
        return render_template("scan_result.html", success=False, msg="Invalid or expired QR code.")
    if time.time() > t["expires_at"]:
        db.execute("UPDATE qr_tokens SET is_active=0 WHERE token=?", (token,))
        db.commit()
        db.close()
        return render_template("scan_result.html", success=False, msg="QR Code has expired! Ask your faculty to generate a new one.")
    student = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if student["class_name"] != t["class_name"]:
        db.close()
        return render_template("scan_result.html", success=False, msg="You are not enrolled in this class.")
    try:
        db.execute("INSERT INTO attendance (student_id,class_id,token_id,marked_at,status) VALUES (?,?,?,?,?)",
                   (session["user_id"], t["class_id"], t["id"], datetime.now().isoformat(), "present"))
        db.commit()
        check_and_notify(session["user_id"], t["class_id"])
        db.close()
        return render_template("scan_result.html", success=True,
                               msg=f"Attendance marked for {t['subject']}!",
                               subject=t["subject"], label=t["session_label"])
    except sqlite3.IntegrityError:
        db.close()
        return render_template("scan_result.html", success=False, msg="Attendance already marked for this session.")

@app.route("/api/token_status/<token>")
def token_status(token):
    db = get_db()
    t  = db.execute("SELECT * FROM qr_tokens WHERE token=?", (token,)).fetchone()
    db.close()
    if not t: return jsonify({"valid": False})
    remaining = max(0, t["expires_at"] - time.time())
    return jsonify({"valid": t["is_active"] == 1 and remaining > 0, "remaining": int(remaining)})

if __name__ == "__main__":
    init_db()
    print("\n Attendance Tracker Running!")
    print("URL: http://localhost:5000")
    print("Admin:   admin / admin123")
    print("Faculty: faculty1 / faculty123")
    print("Student: 238p1a0401 / student123  (HTNO as username)")
    app.run(debug=True, port=5000)