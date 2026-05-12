"""
Team-Finder — In-Memory Database
==================================
Lightweight in-memory data store for the prototype.
In production, replace every method body with a Supabase (PostgreSQL) query
using the supabase-py client. The interface (method signatures) remains the same,
so the API layer never needs to change.

This module also seeds realistic demo data used during development and testing.
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime


class InMemoryDatabase:
    """
    Singleton in-memory store. Stores users, profiles, projects, and exam data
    in plain Python dicts keyed by ID. Thread-safety is not implemented here —
    add threading.Lock() guards if running with multiple workers.
    """

    def __init__(self):
        self._users: Dict[str, dict] = {}           # user_id → user
        self._profiles: Dict[str, dict] = {}        # user_id → profile
        self._projects: List[dict] = []             # flat list
        self._exam_questions: Dict[str, List] = {}  # skill → questions
        self._exam_answers: Dict[str, Dict] = {}    # skill → {q_id: answer}

    # ------------------------------------------------------------------ Users

    def save_user(self, user: dict):
        self._users[user["id"]] = user

    def get_user_by_email(self, email: str) -> Optional[dict]:
        return next(
            (u for u in self._users.values() if u["email"].lower() == email.lower()),
            None
        )

    def get_user(self, user_id: str) -> Optional[dict]:
        return self._users.get(user_id)

    def mark_profile_complete(self, user_id: str):
        if user_id in self._users:
            self._users[user_id]["profile_complete"] = True

    # --------------------------------------------------------------- Profiles

    def save_profile(self, profile: dict):
        self._profiles[profile["user_id"]] = profile

    def get_profile(self, user_id: str) -> Optional[dict]:
        return self._profiles.get(user_id)

    def get_all_profiles(self, exclude_user_id: Optional[str] = None) -> List[dict]:
        """
        Return all profiles enriched with user display name.
        Optionally exclude the requesting user's own profile.
        """
        results = []
        for uid, profile in self._profiles.items():
            if uid == exclude_user_id:
                continue
            enriched = dict(profile)
            user = self._users.get(uid, {})
            enriched["full_name"] = user.get("full_name", "Unknown")
            results.append(enriched)
        return results

    # --------------------------------------------------------------- Projects

    def save_project(self, project: dict):
        self._projects.append(project)

    def get_projects(self, source: Optional[str] = None) -> List[dict]:
        if source:
            return [p for p in self._projects if p.get("source") == source]
        return list(self._projects)

    # ------------------------------------------------------------------ Exams

    def get_exam_questions(self, skill: str) -> Optional[List]:
        return self._exam_questions.get(skill)

    def get_exam_answers(self, skill: str) -> Optional[Dict]:
        return self._exam_answers.get(skill)

    # ------------------------------------------------------------------- Seed

    def seed(self):
        """
        Populate the store with demo users, profiles, projects, and exams.
        This makes the prototype immediately usable without a real database.
        """
        # ---- Demo users ------------------------------------------------
        demo_users = [
            {"id": "u1", "email": "sara@ju.edu.jo", "full_name": "Sara Al-Ahmad",
             "password_hash": "hashed_demo123", "profile_complete": True,
             "created_at": "2025-09-01T10:00:00"},
            {"id": "u2", "email": "omar@ju.edu.jo", "full_name": "Omar Khalil",
             "password_hash": "hashed_demo123", "profile_complete": True,
             "created_at": "2025-09-02T11:00:00"},
            {"id": "u3", "email": "lina@ju.edu.jo", "full_name": "Lina Nasser",
             "password_hash": "hashed_demo123", "profile_complete": True,
             "created_at": "2025-09-03T09:00:00"},
            {"id": "u4", "email": "rami@ju.edu.jo", "full_name": "Rami Hourani",
             "password_hash": "hashed_demo123", "profile_complete": True,
             "created_at": "2025-09-04T14:00:00"},
        ]
        for u in demo_users:
            self._users[u["id"]] = u

        # ---- Demo profiles (skill vectors) ------------------------------
        demo_profiles = [
            {
                "user_id": "u1", "major": "Computer Science",
                "courses": ["CS101", "CS201", "CS305", "CS401"],
                "skills": {"Python": 5, "Machine Learning": 4, "SQL": 3,
                           "React": 2, "Statistics": 4},
                "availability_hours": 20,
                "bio": "Passionate about AI and data science. Looking for teammates for ML projects.",
                "github_url": "https://github.com/sara-demo",
                "updated_at": "2025-11-01T10:00:00"
            },
            {
                "user_id": "u2", "major": "Software Engineering",
                "courses": ["SE101", "SE201", "CS201", "CS305"],
                "skills": {"React": 5, "TypeScript": 4, "Node.js": 4,
                           "CSS": 3, "Python": 2},
                "availability_hours": 15,
                "bio": "Full-stack developer focused on React ecosystem and modern web apps.",
                "github_url": "https://github.com/omar-demo",
                "updated_at": "2025-11-01T11:00:00"
            },
            {
                "user_id": "u3", "major": "Data Science",
                "courses": ["DS101", "DS201", "CS201", "MATH301"],
                "skills": {"Python": 4, "R": 3, "SQL": 4, "Statistics": 5,
                           "Machine Learning": 3, "Tableau": 2},
                "availability_hours": 25,
                "bio": "Data analyst interested in business intelligence and predictive modelling.",
                "github_url": None,
                "updated_at": "2025-11-02T09:00:00"
            },
            {
                "user_id": "u4", "major": "Cybersecurity",
                "courses": ["CYB101", "CYB201", "CS101", "NET201"],
                "skills": {"Python": 3, "Linux": 4, "Network Security": 5,
                           "Penetration Testing": 4, "SQL": 2},
                "availability_hours": 10,
                "bio": "CTF enthusiast and security researcher. Experienced in offensive security.",
                "github_url": "https://github.com/rami-demo",
                "updated_at": "2025-11-02T14:00:00"
            },
        ]
        for p in demo_profiles:
            self._profiles[p["user_id"]] = p

        # ---- Demo projects ----------------------------------------------
        self._projects = [
            {
                "id": "p1", "title": "University Event Scheduler",
                "description": "A web app to coordinate and RSVP for university events.",
                "skills_required": ["React", "Node.js", "SQL"],
                "owner_id": "u2", "source": "student",
                "created_at": "2025-11-10T10:00:00", "members": ["u2"]
            },
            {
                "id": "p2", "title": "Campus Food Waste Monitor",
                "description": "ML model to predict cafeteria food surplus and reduce waste.",
                "skills_required": ["Python", "Machine Learning", "Statistics"],
                "owner_id": "u1", "source": "student",
                "created_at": "2025-11-11T09:00:00", "members": ["u1", "u3"]
            },
            {
                "id": "p3", "title": "Awesome Machine Learning (GitHub)",
                "description": "Curated list of ML frameworks, datasets and tutorials.",
                "skills_required": ["Python", "TensorFlow", "PyTorch"],
                "owner_id": "GITHUB", "source": "github",
                "created_at": "2025-10-01T00:00:00", "members": []
            },
            {
                "id": "p4", "title": "Titanic Survival Prediction (Kaggle)",
                "description": "Classic Kaggle competition — predict passenger survival.",
                "skills_required": ["Python", "Pandas", "Statistics", "Machine Learning"],
                "owner_id": "KAGGLE", "source": "kaggle",
                "created_at": "2025-09-15T00:00:00", "members": []
            },
            {
                "id": "p5", "title": "Secure CTF Web Challenge (CTFtime)",
                "description": "Web exploitation challenge — SQL injection and XSS.",
                "skills_required": ["Python", "SQL", "Penetration Testing", "Network Security"],
                "owner_id": "CTFTIME", "source": "ctftime",
                "created_at": "2025-11-05T00:00:00", "members": []
            },
        ]

        # ---- Python skill exam ------------------------------------------
        self._exam_questions["Python"] = [
            {
                "id": "q1",
                "question": "What is the output of: print(type([]))?",
                "options": {
                    "A": "<class 'tuple'>",
                    "B": "<class 'list'>",
                    "C": "<class 'array'>",
                    "D": "<class 'set'>"
                }
            },
            {
                "id": "q2",
                "question": "Which keyword is used to define a generator function?",
                "options": {
                    "A": "return",
                    "B": "async",
                    "C": "yield",
                    "D": "generate"
                }
            },
            {
                "id": "q3",
                "question": "What does `list(range(2, 10, 3))` produce?",
                "options": {
                    "A": "[2, 5, 8]",
                    "B": "[2, 4, 6, 8]",
                    "C": "[2, 3, 4]",
                    "D": "[2, 5, 8, 11]"
                }
            },
            {
                "id": "q4",
                "question": "Which built-in function returns the largest item in an iterable?",
                "options": {
                    "A": "largest()",
                    "B": "top()",
                    "C": "max()",
                    "D": "ceiling()"
                }
            },
            {
                "id": "q5",
                "question": "What is the time complexity of dictionary lookup in Python?",
                "options": {
                    "A": "O(n)",
                    "B": "O(log n)",
                    "C": "O(n²)",
                    "D": "O(1) average"
                }
            },
        ]
        self._exam_answers["Python"] = {
            "q1": "B", "q2": "C", "q3": "A", "q4": "C", "q5": "D"
        }

        # ---- React skill exam -------------------------------------------
        self._exam_questions["React"] = [
            {
                "id": "q1",
                "question": "Which hook is used to manage local component state?",
                "options": {
                    "A": "useEffect",
                    "B": "useState",
                    "C": "useContext",
                    "D": "useReducer"
                }
            },
            {
                "id": "q2",
                "question": "What does the virtual DOM primarily help with?",
                "options": {
                    "A": "CSS animations",
                    "B": "Server-side rendering",
                    "C": "Efficient UI updates by minimising real DOM operations",
                    "D": "Routing between pages"
                }
            },
            {
                "id": "q3",
                "question": "Which prop is required when rendering a list in React?",
                "options": {
                    "A": "id",
                    "B": "index",
                    "C": "key",
                    "D": "ref"
                }
            },
        ]
        self._exam_answers["React"] = {"q1": "B", "q2": "C", "q3": "C"}


# Singleton instance — import this wherever database access is needed
DB = InMemoryDatabase()
