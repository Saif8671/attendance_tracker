import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import g, current_app, has_app_context

def _database_url():
    if has_app_context():
        return current_app.config.get("DATABASE_URL")
    return os.getenv("DATABASE_URL")

class DbWrapper:
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=DictCursor)

    def execute(self, query, params=None):
        q = query.replace("?", "%s")
        self.cur.execute(q, params or ())
        return self

    def fetchone(self):
        try:
            res = self.cur.fetchone()
            return dict(res) if res else None
        except psycopg2.ProgrammingError:
            return None

    def fetchall(self):
        try:
            res = self.cur.fetchall()
            return [dict(r) for r in res]
        except psycopg2.ProgrammingError:
            return []

    def executescript(self, script):
        self.cur.execute(script)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()

def get_db():
    if "db" not in g:
        conn = psycopg2.connect(_database_url())
        conn.autocommit = True
        g.db = DbWrapper(conn)
    return g.db

def get_db_standalone():
    conn = psycopg2.connect(_database_url())
    conn.autocommit = True
    return DbWrapper(conn)

def init_db():
    db = get_db_standalone()
    try:
        # 1. Extensions and core tables
        db.executescript("""
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";

        CREATE TABLE IF NOT EXISTS profiles (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            role VARCHAR(50) NOT NULL CHECK (role IN ('student', 'faculty', 'admin')),
            full_name VARCHAR(255) NOT NULL,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL, -- Storing hashed password for manual auth
            phone VARCHAR(50),
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS departments (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL UNIQUE,
            semester INT NOT NULL CHECK (semester BETWEEN 1 AND 8),
            credits INT NOT NULL DEFAULT 3,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS classes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
            section VARCHAR(50) NOT NULL DEFAULT 'A',
            semester INT NOT NULL CHECK (semester BETWEEN 1 AND 8),
            academic_year_start DATE NOT NULL,
            academic_year_end DATE NOT NULL,
            room VARCHAR(255),
            max_students INT DEFAULT 60,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (department_id, section, semester, academic_year_start)
        );

        CREATE TABLE IF NOT EXISTS student_profiles (
            id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
            roll_no VARCHAR(100) UNIQUE NOT NULL,
            class_id UUID NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
            dob DATE,
            address TEXT,
            guardian VARCHAR(255),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS faculty_profiles (
            id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
            employee_id VARCHAR(100) UNIQUE,
            department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
            designation VARCHAR(255) DEFAULT 'Assistant Professor',
            joined_date DATE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS faculty_assignments (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            faculty_id UUID NOT NULL REFERENCES faculty_profiles(id) ON DELETE CASCADE,
            class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (faculty_id, class_id, subject_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            assignment_id UUID NOT NULL REFERENCES faculty_assignments(id) ON DELETE CASCADE,
            session_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            topic TEXT,
            session_type VARCHAR(50) NOT NULL DEFAULT 'lecture' CHECK (session_type IN ('lecture','lab','tutorial','exam')),
            status VARCHAR(50) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled','ongoing','completed','cancelled')),
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS qr_tokens (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS attendance_records (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            student_id UUID NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
            qr_token_id UUID REFERENCES qr_tokens(id) ON DELETE SET NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'present' CHECK (status IN ('present','absent','late','excused')),
            method VARCHAR(50) NOT NULL DEFAULT 'qr' CHECK (method IN ('qr','manual','proxy_blocked')),
            device_info JSONB,
            marked_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (session_id, student_id)
        );
        """)
        
        # 2. Add some default indexing
        db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_profiles_role        ON profiles(role);
            CREATE INDEX IF NOT EXISTS idx_student_profiles_class ON student_profiles(class_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_date        ON sessions(session_date);
            CREATE INDEX IF NOT EXISTS idx_attendance_records_student ON attendance_records(student_id);
            CREATE INDEX IF NOT EXISTS idx_attendance_records_session ON attendance_records(session_id);
        """)

        # 3. Seed initial data
        import hashlib
        pw = lambda p: hashlib.sha256(p.encode()).hexdigest()
        db.execute(
            "INSERT INTO profiles (full_name, username, password, role) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
            ("Administrator", "admin", pw("admin123"), "admin"),
        )
        db.commit()

        # Seed initial departments if none exist
        db.executescript("""
            INSERT INTO departments (name, code) VALUES
            ('Computer Science & Engineering', 'CSE'),
            ('Computer Science & AI/ML', 'CSM'),
            ('Electronics & Communication Eng', 'ECE'),
            ('Mechanical Engineering', 'MECH')
            ON CONFLICT (code) DO NOTHING;
        """)
        db.commit()

    except Exception as e:
        print(f"DB Init Error: {e}")
    finally:
        db.close()

