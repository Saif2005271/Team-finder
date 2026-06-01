"""
TeamFinder backend (FastAPI).

Single-port deployment: serves the index.html frontend at the root path and
the JSON API under /api/*. JWT-based authentication; every page beyond the
home/auth screens requires a valid token, and the API endpoints enforce it
server-side.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .ai_assistant import get_advisor_reply
from database import DB
from .matching import compute_match_scores
from .models import (
    AIRequest, AIResponse,
    MatchRequest, Project, ProjectCreate,
    ProfileCreate, ProfileUpdate,
    SkillExamSubmit,
    TokenResponse, UserLogin, UserProfile, UserRegister,
)


# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "teamfinder_dev_secret_change_me")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

ACCEPTED_EMAIL_DOMAINS = {
    d.strip().lower()
    for d in os.getenv(
        "ACCEPTED_EMAIL_DOMAINS",
        "ju.edu.jo,gmail.com,yahoo.com,outlook.com,hotmail.com",
    ).split(",")
    if d.strip()
}

security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    DB.seed()
    print("TeamFinder API started.")
    yield
    print("TeamFinder API shutting down.")


app = FastAPI(title="TeamFinder API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_jwt(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    return decode_jwt(credentials.credentials)


def _accepted_email(email: str) -> bool:
    if "@" not in email:
        return False
    return email.split("@")[-1].lower() in ACCEPTED_EMAIL_DOMAINS


# ---------------------------------------------------------------------------
# Static frontend (HTML / CSS / JS / SVG)
# ---------------------------------------------------------------------------

FRONTEND_DIR  = Path(__file__).resolve().parent.parent / "frontend"
FRONTEND_FILE = FRONTEND_DIR / "index.html"


@app.get("/", include_in_schema=False)
def serve_frontend():
    if FRONTEND_FILE.exists():
        return FileResponse(FRONTEND_FILE)
    return {"message": "TeamFinder API is running. index.html not found."}


@app.get("/styles.css", include_in_schema=False)
def serve_styles():
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def serve_app_js():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/logo.svg", include_in_schema=False)
def serve_logo():
    return FileResponse(FRONTEND_DIR / "logo.svg", media_type="image/svg+xml")


@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Auth"])
def register(data: UserRegister):
    if not _accepted_email(data.email):
        raise HTTPException(
            status_code=400,
            detail="Please use an accepted email address.",
        )
    if DB.get_user_by_email(data.email):
        raise HTTPException(status_code=409, detail="Email already registered.")

    DB.save_user({
        "email":            data.email,
        "full_name":        data.full_name,
        "password_hash":    DB._hash(data.password),
        "profile_complete": False,
    })
    token = create_jwt(data.email)
    return TokenResponse(access_token=token, user_id=data.email, email=data.email)


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(data: UserLogin):
    user = DB.get_user_by_email(data.email)
    if not user or not DB.verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_jwt(user["email"])
    return TokenResponse(access_token=token, user_id=user["email"], email=user["email"])


@app.get("/api/auth/me", tags=["Auth"])
def auth_me(user=Depends(get_current_user)):
    """Validate the current token and return the user record."""
    record = DB.get_user_by_email(user["sub"])
    if not record:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "email":            record["email"],
        "full_name":        record["full_name"],
        "profile_complete": bool(record.get("profile_complete", False)),
    }


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

@app.post("/api/profile", response_model=UserProfile, tags=["Profile"])
def create_profile(data: ProfileCreate, user=Depends(get_current_user)):
    profile = {
        "user_id":            user["sub"],
        "major":              data.major,
        "courses":            data.courses,
        "skills":             data.skills,
        "availability_hours": data.availability_hours,
        "github_url":         data.github_url,
        "bio":                data.bio,
        "updated_at":         datetime.utcnow().isoformat(),
    }
    DB.save_profile(profile)
    DB.mark_profile_complete(user["sub"])
    return UserProfile(**profile)


@app.get("/api/profile/me", response_model=UserProfile, tags=["Profile"])
def get_my_profile(user=Depends(get_current_user)):
    profile = DB.get_profile(user["sub"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return UserProfile(**profile)


@app.get("/api/profile/{user_email:path}", response_model=UserProfile, tags=["Profile"])
def get_profile(user_email: str, user=Depends(get_current_user)):
    profile = DB.get_profile(user_email)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return UserProfile(**profile)


@app.patch("/api/profile", response_model=UserProfile, tags=["Profile"])
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    existing = DB.get_profile(user["sub"])
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found.")
    existing.update({k: v for k, v in data.model_dump(exclude_none=True).items()})
    existing["updated_at"] = datetime.utcnow().isoformat()
    DB.save_profile(existing)
    return UserProfile(**existing)


# ---------------------------------------------------------------------------
# Skill exams
# ---------------------------------------------------------------------------

@app.get("/api/skills/exam/{skill_name}", tags=["Skills"])
def get_exam(skill_name: str, user=Depends(get_current_user)):
    questions = DB.get_exam_questions(skill_name)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No exam for: {skill_name}")
    return {"skill": skill_name, "questions": questions}


@app.post("/api/skills/exam", tags=["Skills"])
def submit_exam(data: SkillExamSubmit, user=Depends(get_current_user)):
    answers = DB.get_exam_answers(data.skill_name)
    if not answers:
        raise HTTPException(status_code=404, detail=f"No exam for: {data.skill_name}")

    total = len(answers)
    correct = sum(
        1 for qid, ans in data.answers.items()
        if answers.get(qid, "").strip().upper() == str(ans).strip().upper()
    )
    pct = (correct / total) * 100 if total else 0

    if   pct <= 20: level = 0
    elif pct <= 40: level = 1
    elif pct <= 60: level = 2
    elif pct <= 70: level = 3
    elif pct <= 85: level = 4
    else:           level = 5

    profile = DB.get_profile(user["sub"]) or {
        "user_id":            user["sub"],
        "major":              "",
        "courses":            [],
        "skills":             {},
        "availability_hours": 0,
    }
    profile.setdefault("skills", {})[data.skill_name] = level
    DB.save_profile(profile)

    return {
        "skill":             data.skill_name,
        "score_percent":     round(pct, 1),
        "proficiency_level": level,
        "message":           f"Scored {correct}/{total} — Level {level}/5",
    }


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@app.post("/api/match", tags=["Matching"])
def find_matches(data: MatchRequest, user=Depends(get_current_user)):
    my_profile = DB.get_profile(user["sub"])
    if not my_profile:
        raise HTTPException(status_code=400, detail="Complete your profile first.")
    all_profiles = DB.get_all_profiles(exclude_user_id=user["sub"])
    matches = compute_match_scores(my_profile, all_profiles, top_n=data.top_n)
    return {"matches": matches, "total_users_searched": len(all_profiles)}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/api/projects", tags=["Projects"])
def list_projects(source: Optional[str] = None, user=Depends(get_current_user)):
    projects = DB.get_projects(source=source)
    return {"projects": projects, "count": len(projects)}


@app.post("/api/projects", response_model=Project, tags=["Projects"])
def create_project(data: ProjectCreate, user=Depends(get_current_user)):
    saved = DB.save_project({
        "title":           data.title,
        "description":     data.description,
        "skills_required": data.skills_required,
        "owner_id":        user["sub"],
        "source":          "student",
        "members":         [user["sub"]],
    })
    return Project(**saved)


# ---------------------------------------------------------------------------
# Advisor chat
# ---------------------------------------------------------------------------

@app.post("/api/advisor/chat", response_model=AIResponse, tags=["Advisor"])
def advisor_chat(data: AIRequest, user=Depends(get_current_user)):
    profile = DB.get_profile(user["sub"])
    reply = get_advisor_reply(data.message, profile, data.conversation_history)
    return AIResponse(reply=reply)


# Backwards-compatibility alias (older clients used /api/ai/chat)
@app.post("/api/ai/chat", response_model=AIResponse, include_in_schema=False)
def advisor_chat_alias(data: AIRequest, user=Depends(get_current_user)):
    return advisor_chat(data, user)