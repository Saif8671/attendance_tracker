import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from utils.security import hash_pw


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class User:
    id: str
    role: str  # admin | faculty | student
    full_name: str
    username: str
    password_hash: str
    email: str = ""
    phone: str = ""
    class_name: str = ""  # student only (e.g. CSE-A)
    rollno: str = ""  # student only


@dataclass(frozen=True)
class ClassOffering:
    id: str
    subject: str
    class_name: str
    faculty_id: str


@dataclass(frozen=True)
class SessionToken:
    id: str
    token: str
    class_id: str
    session_label: str
    created_at: float
    expires_at: float
    is_active: bool


class InMemoryStore:
    """
    In-process state for demo/local use.
    No external persistence.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._users: Dict[str, User] = {}
        self._user_by_username: Dict[str, str] = {}
        self._classes: Dict[str, ClassOffering] = {}
        self._tokens_by_token: Dict[str, SessionToken] = {}
        self._tokens_by_id: Dict[str, SessionToken] = {}
        self._attendance_by_token: Dict[str, Dict[str, float]] = {}  # token_id -> student_id -> marked_at

    # -----------------
    # Users
    # -----------------

    def seed_demo(self):
        with self._lock:
            if self._users:
                return

            admin = self.create_user("admin", "admin123", "admin", full_name="Administrator")
            faculty = self.create_user("faculty1", "faculty123", "faculty", full_name="Faculty Member")
            student = self.create_user(
                "student1",
                "student123",
                "student",
                full_name="Student One",
                class_name="CSE-A",
                rollno="42",
            )

            self.create_class(subject="Mathematics", class_name="CSE-A", faculty_id=faculty.id)
            self.create_class(subject="Algorithms", class_name="CSE-A", faculty_id=faculty.id)

            _ = admin, student  # silence linters / keep references obvious

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        *,
        full_name: str,
        email: str = "",
        phone: str = "",
        class_name: str = "",
        rollno: str = "",
    ) -> User:
        username = (username or "").strip().lower()
        if not username:
            raise ValueError("username_required")
        if username in self._user_by_username:
            raise ValueError("username_taken")

        user = User(
            id=_new_id(),
            role=role,
            full_name=full_name.strip() or username,
            username=username,
            password_hash=hash_pw(password or ""),
            email=(email or "").strip(),
            phone=(phone or "").strip(),
            class_name=(class_name or "").strip().upper(),
            rollno=(rollno or "").strip(),
        )
        self._users[user.id] = user
        self._user_by_username[user.username] = user.id
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        username = (username or "").strip().lower()
        with self._lock:
            user_id = self._user_by_username.get(username)
            if not user_id:
                return None
            user = self._users.get(user_id)
            if not user:
                return None
            if user.password_hash != hash_pw(password or ""):
                return None
            return user

    def get_user(self, user_id: str) -> Optional[User]:
        with self._lock:
            return self._users.get(str(user_id))

    def list_users(self, role: Optional[str] = None) -> List[User]:
        with self._lock:
            users = list(self._users.values())
        if role:
            users = [u for u in users if u.role == role]
        users.sort(key=lambda u: (u.role, u.username))
        return users

    def reset_password(self, user_id: str, new_password: str) -> None:
        with self._lock:
            u = self._users.get(str(user_id))
            if not u:
                raise ValueError("not_found")
            self._users[u.id] = User(
                id=u.id,
                role=u.role,
                full_name=u.full_name,
                username=u.username,
                password_hash=hash_pw(new_password or ""),
                email=u.email,
                phone=u.phone,
                class_name=u.class_name,
                rollno=u.rollno,
            )

    def delete_user(self, user_id: str) -> None:
        user_id = str(user_id)
        with self._lock:
            u = self._users.pop(user_id, None)
            if not u:
                return
            self._user_by_username.pop(u.username, None)
            # remove attendance marks
            for token_id in list(self._attendance_by_token.keys()):
                self._attendance_by_token[token_id].pop(user_id, None)

    # -----------------
    # Classes
    # -----------------

    def create_class(self, *, subject: str, class_name: str, faculty_id: str) -> ClassOffering:
        with self._lock:
            c = ClassOffering(
                id=_new_id(),
                subject=(subject or "").strip() or "Untitled",
                class_name=(class_name or "").strip().upper() or "CLASS",
                faculty_id=str(faculty_id),
            )
            self._classes[c.id] = c
            return c

    def delete_class(self, class_id: str) -> None:
        class_id = str(class_id)
        with self._lock:
            self._classes.pop(class_id, None)
            # remove tokens and attendance for that class
            for t in list(self._tokens_by_id.values()):
                if t.class_id == class_id:
                    self._tokens_by_token.pop(t.token, None)
                    self._tokens_by_id.pop(t.id, None)
                    self._attendance_by_token.pop(t.id, None)

    def list_classes(self) -> List[ClassOffering]:
        with self._lock:
            classes = list(self._classes.values())
        classes.sort(key=lambda c: (c.class_name, c.subject))
        return classes

    def list_faculty_classes(self, faculty_id: str) -> List[ClassOffering]:
        faculty_id = str(faculty_id)
        with self._lock:
            classes = [c for c in self._classes.values() if c.faculty_id == faculty_id]
        classes.sort(key=lambda c: (c.class_name, c.subject))
        return classes

    # -----------------
    # Sessions / tokens
    # -----------------

    def create_token(self, *, class_id: str, session_label: str, valid_seconds: int) -> SessionToken:
        now = _now()
        t = SessionToken(
            id=_new_id(),
            token=uuid.uuid4().hex,
            class_id=str(class_id),
            session_label=(session_label or "").strip(),
            created_at=now,
            expires_at=now + max(5, int(valid_seconds)),
            is_active=True,
        )
        with self._lock:
            self._tokens_by_token[t.token] = t
            self._tokens_by_id[t.id] = t
            self._attendance_by_token.setdefault(t.id, {})
        return t

    def get_token(self, token_str: str) -> Optional[SessionToken]:
        token_str = (token_str or "").strip()
        with self._lock:
            t = self._tokens_by_token.get(token_str)
        if not t:
            return None
        # auto-expire
        if t.is_active and _now() >= t.expires_at:
            self.close_token(t.token)
            with self._lock:
                t = self._tokens_by_token.get(token_str)
        return t

    def close_token(self, token_str: str) -> bool:
        token_str = (token_str or "").strip()
        with self._lock:
            t = self._tokens_by_token.get(token_str)
            if not t:
                return False
            if not t.is_active:
                return True
            closed = SessionToken(
                id=t.id,
                token=t.token,
                class_id=t.class_id,
                session_label=t.session_label,
                created_at=t.created_at,
                expires_at=t.expires_at,
                is_active=False,
            )
            self._tokens_by_token[closed.token] = closed
            self._tokens_by_id[closed.id] = closed
            return True

    def list_tokens_for_faculty(self, faculty_id: str) -> List[SessionToken]:
        faculty_id = str(faculty_id)
        with self._lock:
            class_ids = {c.id for c in self._classes.values() if c.faculty_id == faculty_id}
            tokens = [t for t in self._tokens_by_id.values() if t.class_id in class_ids]
        tokens.sort(key=lambda t: t.created_at, reverse=True)
        return tokens[:50]

    def list_tokens_for_class(self, class_id: str) -> List[SessionToken]:
        class_id = str(class_id)
        with self._lock:
            tokens = [t for t in self._tokens_by_id.values() if t.class_id == class_id]
        tokens.sort(key=lambda t: t.created_at, reverse=True)
        return tokens[:200]

    # -----------------
    # Attendance
    # -----------------

    def mark_attendance(self, *, token_str: str, student_id: str) -> Tuple[bool, str]:
        t = self.get_token(token_str)
        if not t:
            return False, "Invalid or expired QR code."
        if not t.is_active:
            return False, "Session already closed."

        with self._lock:
            marks = self._attendance_by_token.setdefault(t.id, {})
            if str(student_id) in marks:
                return False, "Attendance already marked for this session."
            marks[str(student_id)] = _now()
        return True, "Attendance marked."

    def token_marked_count(self, token_id: str) -> int:
        with self._lock:
            return len(self._attendance_by_token.get(str(token_id), {}))

    def student_present_count_for_class(self, *, student_id: str, class_id: str) -> int:
        student_id = str(student_id)
        class_id = str(class_id)
        with self._lock:
            token_ids = [t.id for t in self._tokens_by_id.values() if t.class_id == class_id and not t.is_active]
            count = 0
            for tid in token_ids:
                if student_id in self._attendance_by_token.get(tid, {}):
                    count += 1
            return count

    def total_completed_sessions_for_class(self, class_id: str) -> int:
        class_id = str(class_id)
        with self._lock:
            return sum(1 for t in self._tokens_by_id.values() if t.class_id == class_id and not t.is_active)

