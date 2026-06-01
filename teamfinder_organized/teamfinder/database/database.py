"""
TeamFinder — Data access layer.

Supports both MySQL (production) and SQLite (local testing) via SQLAlchemy.

Engine selection:
    * If DB_BACKEND=mysql   -> MySQL via PyMySQL
    * Else if DB_HOST is set -> MySQL via PyMySQL (auto-detected)
    * Else                  -> Local SQLite file (./teamfinder.db)

All schema is defined with SQLAlchemy Core. Upserts use a portable
"look up, then INSERT or UPDATE" pattern instead of dialect-specific
ON DUPLICATE KEY UPDATE / ON CONFLICT clauses.
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, select, insert, update,
    MetaData, Table, Column,
    String, Boolean, Integer, Text, DateTime, ForeignKey,
)

load_dotenv()


# ---------------------------------------------------------------------------
# Engine selection
# ---------------------------------------------------------------------------

def _build_database_url() -> str:
    backend = os.getenv("DB_BACKEND", "").strip().lower()

    if not backend and os.getenv("DB_HOST"):
        backend = "mysql"
    if not backend:
        backend = "sqlite"

    if backend == "mysql":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        user = os.getenv("DB_USER", "root")
        pwd  = os.getenv("DB_PASSWORD", "")
        name = os.getenv("DB_NAME", "teamfinder")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"

    path = os.getenv("SQLITE_PATH", "teamfinder.db")
    return f"sqlite:///{path}"


DATABASE_URL = _build_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_engine_kwargs: Dict[str, Any] = {"echo": False, "pool_pre_ping": True}
if IS_SQLITE:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
metadata = MetaData()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

users_table = Table(
    "users", metadata,
    Column("email",            String(255), primary_key=True),
    Column("full_name",        String(255), nullable=False),
    Column("password_hash",    String(255), nullable=False),
    Column("profile_complete", Boolean,     default=False, nullable=False),
    Column("created_at",       DateTime,    default=datetime.utcnow, nullable=False),
)

profiles_table = Table(
    "profiles", metadata,
    Column("user_id",            String(255),
           ForeignKey("users.email", ondelete="CASCADE"), primary_key=True),
    Column("major",              String(255), default=""),
    Column("courses",            Text,        default="[]"),
    Column("skills",             Text,        default="{}"),
    Column("availability_hours", Integer,     default=0),
    Column("github_url",         String(512), nullable=True),
    Column("bio",                Text,        nullable=True),
    Column("updated_at",         DateTime,    default=datetime.utcnow,
                                              onupdate=datetime.utcnow),
)

projects_table = Table(
    "projects", metadata,
    Column("id",               Integer,     primary_key=True, autoincrement=True),
    Column("title",            String(255), nullable=False),
    Column("description",      Text,        default=""),
    Column("skills_required",  Text,        default="[]"),
    Column("owner_id",         String(255),
           ForeignKey("users.email", ondelete="SET NULL"), nullable=True),
    Column("source",           String(50),  default="student"),
    Column("created_at",       DateTime,    default=datetime.utcnow),
    Column("members",          Text,        default="[]"),
)

exams_table = Table(
    "exams", metadata,
    Column("skill_name", String(100), primary_key=True),
    Column("questions",  Text,        nullable=False),
    Column("answers",    Text,        nullable=False),
)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _p(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class Database:
    """Portable data-access layer; works on MySQL and SQLite."""

    # ── Schema lifecycle ─────────────────────────────────────────

    def init_schema(self) -> None:
        metadata.create_all(engine)

    def seed(self) -> None:
        """Create tables and insert demo data if the DB is empty."""
        self.init_schema()

        with engine.connect() as conn:
            if conn.execute(select(users_table).limit(1)).first():
                return

        # ── Demo users ───────────────────────────────────────────
        demo_users = [
            {"email": "sara@ju.edu.jo", "full_name": "Sara Al-Ahmad",
             "password_hash": self._hash("demo1234"), "profile_complete": True},
            {"email": "omar@ju.edu.jo", "full_name": "Omar Khalil",
             "password_hash": self._hash("demo1234"), "profile_complete": True},
            {"email": "lina@ju.edu.jo", "full_name": "Lina Nasser",
             "password_hash": self._hash("demo1234"), "profile_complete": True},
            {"email": "rami@ju.edu.jo", "full_name": "Rami Hourani",
             "password_hash": self._hash("demo1234"), "profile_complete": True},
        ]
        for u in demo_users:
            self.save_user(u)

        demo_profiles = [
            {"user_id": "sara@ju.edu.jo", "major": "Computer Science",
             "courses": ["CS101", "CS201", "CS305", "CS401"],
             "skills": {"Python": 5, "Machine Learning": 4, "SQL": 3, "React": 2, "Statistics": 4},
             "availability_hours": 20, "github_url": "https://github.com/sara-demo",
             "bio": "Final-year CS student. Enjoys data work and clean code."},
            {"user_id": "omar@ju.edu.jo", "major": "Software Engineering",
             "courses": ["SE101", "SE201", "CS201", "CS305"],
             "skills": {"React": 5, "TypeScript": 4, "Node.js": 4, "CSS": 3, "Python": 2},
             "availability_hours": 15, "github_url": "https://github.com/omar-demo",
             "bio": "Front-end engineer who likes pixel-perfect UIs."},
            {"user_id": "lina@ju.edu.jo", "major": "Data Science",
             "courses": ["DS101", "DS201", "CS201", "MATH301"],
             "skills": {"Python": 4, "R": 3, "SQL": 4, "Statistics": 5, "Machine Learning": 3},
             "availability_hours": 25, "github_url": None,
             "bio": "Stats-heavy data scientist; enjoys teaching."},
            {"user_id": "rami@ju.edu.jo", "major": "Cybersecurity",
             "courses": ["CYB101", "CYB201", "CS101", "NET201"],
             "skills": {"Python": 3, "Linux": 4, "Network Security": 5, "Penetration Testing": 4},
             "availability_hours": 10, "github_url": "https://github.com/rami-demo",
             "bio": "CTF player and tinkerer; mostly nights and weekends."},
        ]
        for p in demo_profiles:
            self.save_profile(p)

        demo_projects = [
            {"title": "University Event Scheduler",
             "description": "A web app to coordinate and RSVP for university events.",
             "skills_required": ["React", "Node.js", "SQL"],
             "owner_id": "omar@ju.edu.jo", "source": "student",
             "members": ["omar@ju.edu.jo"]},
            {"title": "Campus Food Waste Monitor",
             "description": "Predictive model to forecast cafeteria food surplus.",
             "skills_required": ["Python", "Machine Learning", "Statistics"],
             "owner_id": "sara@ju.edu.jo", "source": "student",
             "members": ["sara@ju.edu.jo", "lina@ju.edu.jo"]},
            {"title": "Awesome Machine Learning (GitHub)",
             "description": "Curated list of ML frameworks, datasets and tutorials.",
             "skills_required": ["Python", "TensorFlow", "PyTorch"],
             "owner_id": None, "source": "github", "members": []},
            {"title": "Titanic Survival Prediction (Kaggle)",
             "description": "Classic Kaggle competition — predict passenger survival.",
             "skills_required": ["Python", "Pandas", "Statistics", "Machine Learning"],
             "owner_id": None, "source": "kaggle", "members": []},
            {"title": "Secure CTF Web Challenge (CTFtime)",
             "description": "Web exploitation — SQL injection and XSS.",
             "skills_required": ["Python", "SQL", "Penetration Testing", "Network Security"],
             "owner_id": None, "source": "ctftime", "members": []},
        ]
        for p in demo_projects:
            self.save_project(p)

        python_questions = [
            {"id": "q1", "question": "What is the output of: print(type([]))?",
             "options": {"A": "<class 'tuple'>", "B": "<class 'list'>",
                         "C": "<class 'array'>", "D": "<class 'set'>"}},
            {"id": "q2", "question": "Which keyword defines a generator function?",
             "options": {"A": "return", "B": "async", "C": "yield", "D": "generate"}},
            {"id": "q3", "question": "What does list(range(2, 10, 3)) produce?",
             "options": {"A": "[2, 5, 8]", "B": "[2, 4, 6, 8]",
                         "C": "[2, 3, 4]", "D": "[2, 5, 8, 11]"}},
            {"id": "q4", "question": "Which built-in function returns the largest item?",
             "options": {"A": "largest()", "B": "top()", "C": "max()", "D": "ceiling()"}},
            {"id": "q5", "question": "Time complexity of Python dictionary lookup?",
             "options": {"A": "O(n)", "B": "O(log n)",
                         "C": "O(n^2)", "D": "O(1) average"}},
        ]
        python_answers = {"q1": "B", "q2": "C", "q3": "A", "q4": "C", "q5": "D"}

        react_questions = [
            {"id": "q1", "question": "Which hook manages local state in a function component?",
             "options": {"A": "useEffect", "B": "useState", "C": "useMemo", "D": "useRef"}},
            {"id": "q2", "question": "What does JSX compile to?",
             "options": {"A": "HTML strings", "B": "Web Components",
                         "C": "React.createElement calls", "D": "Native DOM nodes"}},
            {"id": "q3", "question": "Which hook runs side effects after render?",
             "options": {"A": "useState", "B": "useReducer",
                         "C": "useEffect", "D": "useContext"}},
        ]
        react_answers = {"q1": "B", "q2": "C", "q3": "C"}

        self._save_exam("Python", python_questions, python_answers)
        self._save_exam("React",  react_questions,  react_answers)

    # ── Passwords ────────────────────────────────────────────────

    @staticmethod
    def _hash(password: str) -> str:
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            return f"plain_{password}"

    @staticmethod
    def _verify(password: str, stored_hash: str) -> bool:
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except ImportError:
            return stored_hash == f"plain_{password}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        return self._verify(password, stored_hash)

    # ── Users ────────────────────────────────────────────────────

    def save_user(self, user: dict) -> None:
        email = user["email"]
        payload = {
            "email":            email,
            "full_name":        user["full_name"],
            "password_hash":    user["password_hash"],
            "profile_complete": bool(user.get("profile_complete", False)),
        }
        with engine.begin() as conn:
            existing = conn.execute(
                select(users_table).where(users_table.c.email == email)
            ).first()
            if existing:
                conn.execute(
                    update(users_table)
                    .where(users_table.c.email == email)
                    .values(**payload)
                )
            else:
                payload["created_at"] = datetime.utcnow()
                conn.execute(insert(users_table).values(**payload))

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Case-insensitive lookup that works on both MySQL and SQLite."""
        with engine.connect() as conn:
            rows = conn.execute(select(users_table)).mappings().all()
        target = email.lower()
        for r in rows:
            if r["email"].lower() == target:
                u = dict(r)
                u["id"] = u["email"]
                return u
        return None

    def get_user(self, email: str) -> Optional[dict]:
        return self.get_user_by_email(email)

    def mark_profile_complete(self, email: str) -> None:
        with engine.begin() as conn:
            conn.execute(
                update(users_table)
                .where(users_table.c.email == email)
                .values(profile_complete=True)
            )

    # ── Profiles ─────────────────────────────────────────────────

    def save_profile(self, profile: dict) -> None:
        uid = profile["user_id"]
        payload = {
            "user_id":            uid,
            "major":              profile.get("major", ""),
            "courses":            _j(profile.get("courses", [])),
            "skills":             _j(profile.get("skills", {})),
            "availability_hours": int(profile.get("availability_hours", 0)),
            "github_url":         profile.get("github_url"),
            "bio":                profile.get("bio"),
            "updated_at":         datetime.utcnow(),
        }
        with engine.begin() as conn:
            existing = conn.execute(
                select(profiles_table).where(profiles_table.c.user_id == uid)
            ).first()
            if existing:
                conn.execute(
                    update(profiles_table)
                    .where(profiles_table.c.user_id == uid)
                    .values(**payload)
                )
            else:
                conn.execute(insert(profiles_table).values(**payload))

    def get_profile(self, user_id: str) -> Optional[dict]:
        with engine.connect() as conn:
            row = conn.execute(
                select(profiles_table).where(profiles_table.c.user_id == user_id)
            ).mappings().first()
        if not row:
            return None
        p = dict(row)
        p["courses"]    = _p(p.get("courses")) or []
        p["skills"]     = _p(p.get("skills"))  or {}
        p["bio"]        = p.get("bio")
        p["updated_at"] = str(p.get("updated_at") or datetime.utcnow().isoformat())
        return p

    def get_all_profiles(self, exclude_user_id: Optional[str] = None) -> List[dict]:
        with engine.connect() as conn:
            stmt = (
                select(profiles_table, users_table.c.full_name)
                .join(users_table, users_table.c.email == profiles_table.c.user_id)
            )
            if exclude_user_id:
                stmt = stmt.where(profiles_table.c.user_id != exclude_user_id)
            rows = conn.execute(stmt).mappings().all()
        results = []
        for row in rows:
            p = dict(row)
            p["courses"]    = _p(p.get("courses")) or []
            p["skills"]     = _p(p.get("skills"))  or {}
            p["bio"]        = p.get("bio")
            p["updated_at"] = str(p.get("updated_at") or datetime.utcnow().isoformat())
            results.append(p)
        return results

    # ── Projects ─────────────────────────────────────────────────

    def save_project(self, project: dict) -> dict:
        with engine.begin() as conn:
            result = conn.execute(insert(projects_table).values(
                title=project["title"],
                description=project.get("description", ""),
                skills_required=_j(project.get("skills_required", [])),
                owner_id=project.get("owner_id"),
                source=project.get("source", "student"),
                created_at=datetime.utcnow(),
                members=_j(project.get("members", [])),
            ))
            project = dict(project)
            project["id"] = str(result.inserted_primary_key[0])
            project["created_at"] = datetime.utcnow().isoformat()
        return project

    def get_projects(self, source: Optional[str] = None) -> List[dict]:
        with engine.connect() as conn:
            stmt = select(projects_table)
            if source:
                stmt = stmt.where(projects_table.c.source == source)
            rows = conn.execute(stmt).mappings().all()
        results = []
        for row in rows:
            p = dict(row)
            p["id"]              = str(p["id"])
            p["skills_required"] = _p(p.get("skills_required")) or []
            p["members"]         = _p(p.get("members"))         or []
            p["created_at"]      = str(p.get("created_at") or "")
            p["owner_id"]        = p.get("owner_id") or ""
            results.append(p)
        return results

    # ── Exams ────────────────────────────────────────────────────

    def _save_exam(self, skill: str, questions: list, answers: dict) -> None:
        payload = {
            "skill_name": skill,
            "questions":  _j(questions),
            "answers":    _j(answers),
        }
        with engine.begin() as conn:
            existing = conn.execute(
                select(exams_table).where(exams_table.c.skill_name == skill)
            ).first()
            if existing:
                conn.execute(
                    update(exams_table)
                    .where(exams_table.c.skill_name == skill)
                    .values(**payload)
                )
            else:
                conn.execute(insert(exams_table).values(**payload))

    def get_exam_questions(self, skill: str) -> Optional[List]:
        with engine.connect() as conn:
            row = conn.execute(
                select(exams_table.c.questions).where(exams_table.c.skill_name == skill)
            ).first()
        return _p(row[0]) if row else None

    def get_exam_answers(self, skill: str) -> Optional[Dict]:
        with engine.connect() as conn:
            row = conn.execute(
                select(exams_table.c.answers).where(exams_table.c.skill_name == skill)
            ).first()
        return _p(row[0]) if row else None


DB = Database()
