import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import g, current_app, has_app_context

DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:USER%40supabase%408671@db.lnomjnooexjxlrkfgfvk.supabase.co:5432/postgres",
)


def _database_url():
    if has_app_context():
        return current_app.config["DATABASE_URL"]
    return DEFAULT_DATABASE_URL


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
        db.executescript(
            """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            email VARCHAR(255),
            gender VARCHAR(50),
            dob VARCHAR(50),
            class_name VARCHAR(100),
            rollno VARCHAR(100)
        );
        CREATE TABLE IF NOT EXISTS classes (
            id SERIAL PRIMARY KEY,
            subject VARCHAR(255) NOT NULL,
            faculty_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            class_name VARCHAR(255) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS qr_tokens (
            id SERIAL PRIMARY KEY,
            token VARCHAR(255) UNIQUE NOT NULL,
            class_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            expires_at DOUBLE PRECISION NOT NULL,
            session_label VARCHAR(255),
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            token_id INTEGER NOT NULL,
            marked_at VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'present',
            UNIQUE(student_id, token_id)
        );
        """
        )
    except Exception:
        pass

    try:
        db.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_users_role       ON users(role);
            CREATE INDEX IF NOT EXISTS idx_users_class      ON users(class_name);
            CREATE INDEX IF NOT EXISTS idx_users_username   ON users(username);
            CREATE INDEX IF NOT EXISTS idx_att_student      ON attendance(student_id, class_id);
            CREATE INDEX IF NOT EXISTS idx_att_token        ON attendance(token_id);
            CREATE INDEX IF NOT EXISTS idx_att_status       ON attendance(student_id, class_id, status);
            CREATE INDEX IF NOT EXISTS idx_qr_class_active  ON qr_tokens(class_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_qr_faculty       ON qr_tokens(faculty_id);
            CREATE INDEX IF NOT EXISTS idx_qr_token         ON qr_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_classes_faculty   ON classes(faculty_id);
            CREATE INDEX IF NOT EXISTS idx_classes_classname ON classes(class_name);
        """
        )
    except Exception:
        pass

    import hashlib

    pw = lambda p: hashlib.sha256(p.encode()).hexdigest()
    try:
        db.execute(
            "INSERT INTO users (username,password,role,name,phone,email,gender,dob,class_name,rollno) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING",
            ("admin", pw("admin123"), "admin", "Administrator", None, None, None, None, None, None),
        )
    except Exception:
        pass

    db.commit()
    db.close()
