"""
Team-Finder Backend — FastAPI Application
==========================================
This is the main entry point for the Team-Finder REST API.
It registers all routes, configures CORS, and initialises the in-memory
database used for the prototype (swap for PostgreSQL/Supabase in production).

Run with:
    uvicorn app:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager
import jwt  
import uuid

from models import (
    UserRegister, UserLogin, ProfileCreate, ProfileUpdate,
    SkillExamSubmit, ProjectCreate, MatchRequest,
    TokenResponse, UserProfile, MatchResult, Project,
    AIRequest, AIResponse
)
from matching import compute_match_scores
from database import DB          # lightweight in-memory store
from ai_assistant import get_ai_response

# ---------------------------------------------------------------------------
# Lifespan context manager — handles startup and shutdown events
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application lifecycle (startup and shutdown).
    
    Startup (before yield):
      - Seed the in-memory database with demo data.
      - Initialize any resources needed for the app.
    
    Shutdown (after yield):
      - Clean up resources (logs, connections, etc.).
    """
    # ===== STARTUP =====
    DB.seed()
    print("✅ Team-Finder API started. Demo data seeded.")
    
    yield  # ← App runs here
    
    # ===== SHUTDOWN =====
    print("🛑 Team-Finder API shutting down.")


# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Team-Finder API",
    description="Backend for the Team-Finder university collaboration platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Allow the Next.js / HTML frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT settings — store in environment variables in production!
SECRET_KEY = "teamfinder_secret_key_change_in_production"
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

security = HTTPBearer()


# ---------------------------------------------------------------------------
# Root Route
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Welcome endpoint - API is running"""
    return {
        "message": "🚀 Team-Finder API is running!",
        "version": "1.0.0",
        "status": "operational"
    }


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def create_jwt(user_id: str, email: str) -> str:
    """Create a signed JWT token valid for TOKEN_EXPIRY_HOURS hours."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency: extract and validate the current user from the Authorization header."""
    return decode_jwt(credentials.credentials)


def require_university_email(email: str) -> bool:
    """
    Validates that the email belongs to an accepted university domain.
    Extend the ACCEPTED_DOMAINS set as needed.
    """
    ACCEPTED_DOMAINS = {"ju.edu.jo", "yahoo.com", "gmail.com"}  # demo: relaxed
    domain = email.split("@")[-1].lower()
    return domain in ACCEPTED_DOMAINS


# ---------------------------------------------------------------------------
# Authentication routes
# ---------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Authentication"])
def register(data: UserRegister):
    """
    Register a new user with a verified university email.

    Steps:
      1. Validate email domain.
      2. Check the email is not already taken.
      3. Hash the password (bcrypt in production; simplified here).
      4. Store the user and return a signed JWT.
    """
    if not require_university_email(data.email):
        raise HTTPException(
            status_code=400,
            detail="Registration is restricted to university email addresses."
        )

    if DB.get_user_by_email(data.email):
        raise HTTPException(status_code=409, detail="Email already registered.")

    user_id = str(uuid.uuid4())
    # In production, replace with: bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())
    hashed_pw = f"hashed_{data.password}"

    user = {
        "id": user_id,
        "email": data.email,
        "full_name": data.full_name,
        "password_hash": hashed_pw,
        "created_at": datetime.utcnow().isoformat(),
        "profile_complete": False
    }
    DB.save_user(user)

    token = create_jwt(user_id, data.email)
    return TokenResponse(access_token=token, user_id=user_id, email=data.email)


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(data: UserLogin):
    """
    Authenticate a user and return a JWT.

    The password check is simplified here. In production, use:
        bcrypt.checkpw(data.password.encode(), stored_hash)
    """
    user = DB.get_user_by_email(data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Simplified password check — replace with bcrypt in production
    expected_hash = f"hashed_{data.password}"
    if user["password_hash"] != expected_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_jwt(user["id"], user["email"])
    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        email=user["email"]
    )


# ---------------------------------------------------------------------------
# Profile routes
# ---------------------------------------------------------------------------

@app.post("/api/profile", response_model=UserProfile, tags=["Profile"])
def create_profile(data: ProfileCreate, user=Depends(get_current_user)):
    """
    Create or update the authenticated user's structured skill profile.

    The profile stores:
      - major: the student's field of study
      - courses: list of completed course IDs
      - skills: dict mapping skill name → proficiency level (0–5)
      - availability_hours: weekly hours available for collaboration
    """
    profile = {
        "user_id": user["sub"],
        "major": data.major,
        "courses": data.courses,
        "skills": data.skills,          # {"Python": 4, "React": 3, ...}
        "availability_hours": data.availability_hours,
        "bio": data.bio,
        "github_url": data.github_url,
        "updated_at": datetime.utcnow().isoformat()
    }
    DB.save_profile(profile)
    DB.mark_profile_complete(user["sub"])
    return UserProfile(**profile)


@app.get("/api/profile/{user_id}", response_model=UserProfile, tags=["Profile"])
def get_profile(user_id: str, user=Depends(get_current_user)):
    """Retrieve any user's profile by their user_id."""
    profile = DB.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return UserProfile(**profile)


@app.patch("/api/profile", response_model=UserProfile, tags=["Profile"])
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    """Partially update the current user's profile (only provided fields are changed)."""
    existing = DB.get_profile(user["sub"])
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    # Merge only the non-None fields from the request
    update_data = data.dict(exclude_none=True)
    existing.update(update_data)
    existing["updated_at"] = datetime.utcnow().isoformat()
    DB.save_profile(existing)
    return UserProfile(**existing)


# ---------------------------------------------------------------------------
# Skill exam / verification routes
# ---------------------------------------------------------------------------

@app.post("/api/skills/exam", tags=["Skills"])
def submit_exam(data: SkillExamSubmit, user=Depends(get_current_user)):
    """
    Submit answers for a skill verification exam.

    Scoring logic:
      - Each correct answer scores 1 point.
      - Proficiency level is assigned on a 0–5 scale:
          0 = 0–20%, 1 = 21–40%, 2 = 41–60%, 3 = 61–70%, 4 = 71–85%, 5 = 86–100%.

    The resulting proficiency is stored in the user's skill vector.
    """
    EXAM_ANSWERS = DB.get_exam_answers(data.skill_name)
    if not EXAM_ANSWERS:
        raise HTTPException(status_code=404, detail=f"No exam found for skill: {data.skill_name}")

    total = len(EXAM_ANSWERS)
    correct = sum(
        1 for q_id, answer in data.answers.items()
        if EXAM_ANSWERS.get(q_id) == answer
    )
    score_pct = (correct / total) * 100

    # Map percentage to proficiency level (0–5)
    if score_pct <= 20:
        proficiency = 0
    elif score_pct <= 40:
        proficiency = 1
    elif score_pct <= 60:
        proficiency = 2
    elif score_pct <= 70:
        proficiency = 3
    elif score_pct <= 85:
        proficiency = 4
    else:
        proficiency = 5

    # Persist the verified proficiency into the user's profile
    profile = DB.get_profile(user["sub"]) or {}
    profile.setdefault("skills", {})[data.skill_name] = proficiency
    profile["user_id"] = user["sub"]
    DB.save_profile(profile)

    return {
        "skill": data.skill_name,
        "score_percent": round(score_pct, 1),
        "proficiency_level": proficiency,
        "message": f"You scored {correct}/{total} — Proficiency Level {proficiency}/5 awarded."
    }


@app.get("/api/skills/exam/{skill_name}", tags=["Skills"])
def get_exam(skill_name: str, user=Depends(get_current_user)):
    """Return the questions for a skill exam (without answers)."""
    questions = DB.get_exam_questions(skill_name)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No exam found for skill: {skill_name}")
    return {"skill": skill_name, "questions": questions}


# ---------------------------------------------------------------------------
# Matching routes
# ---------------------------------------------------------------------------

@app.post("/api/match", tags=["Matching"])
def find_matches(data: MatchRequest, user=Depends(get_current_user)):
    """
    Find the most compatible teammates using cosine similarity.

    Algorithm summary:
      1. Load the requester's skill vector.
      2. Load all other users' skill vectors from the database.
      3. Compute the cosine similarity score between each pair.
      4. Return the top-N matches sorted by descending score.

    See matching.py for the full implementation with detailed comments.
    """
    my_profile = DB.get_profile(user["sub"])
    if not my_profile:
        raise HTTPException(status_code=400, detail="Complete your profile before finding matches.")

    all_profiles = DB.get_all_profiles(exclude_user_id=user["sub"])
    matches = compute_match_scores(my_profile, all_profiles, top_n=data.top_n)
    return {"matches": matches, "total_users_searched": len(all_profiles)}


# ---------------------------------------------------------------------------
# Projects routes
# ---------------------------------------------------------------------------

@app.get("/api/projects", tags=["Projects"])
def list_projects(
    source: Optional[str] = None,  # "student" | "github" | "kaggle" | "ai"
    user=Depends(get_current_user)
):
    """
    Return projects filtered by source.
    In production this endpoint fetches from the prefetcher microservice
    that polls GitHub, Kaggle, HuggingFace and CTFtime APIs.
    """
    projects = DB.get_projects(source=source)
    return {"projects": projects, "count": len(projects)}


@app.post("/api/projects", response_model=Project, tags=["Projects"])
def create_project(data: ProjectCreate, user=Depends(get_current_user)):
    """Create a new student-defined project listing."""
    project = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "skills_required": data.skills_required,
        "owner_id": user["sub"],
        "source": "student",
        "created_at": datetime.utcnow().isoformat(),
        "members": [user["sub"]]
    }
    DB.save_project(project)
    return Project(**project)


# ---------------------------------------------------------------------------
# AI Assistant route
# ---------------------------------------------------------------------------

@app.post("/api/ai/chat", response_model=AIResponse, tags=["AI Assistant"])
def chat_with_ai(data: AIRequest, user=Depends(get_current_user)):
    """
    Send a message to the Claude-powered AI assistant.

    The assistant has access to the user's current profile so it can
    provide contextual guidance on:
      - Which skills to add or improve
      - Which projects match the user's background
      - How to improve their match score
    """
    profile = DB.get_profile(user["sub"])
    response_text = get_ai_response(data.message, profile, data.conversation_history)
    return AIResponse(reply=response_text)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
def health_check():
    """Simple health endpoint for monitoring and load-balancer probes."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}