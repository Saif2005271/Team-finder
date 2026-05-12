"""
Team-Finder — Pydantic Models
==============================
All request bodies and response schemas used by the FastAPI application.
Pydantic automatically validates incoming JSON, produces clear error messages
when fields are missing or mistyped, and generates the OpenAPI schema.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any


# ---------------------------------------------------------------------------
# Authentication models
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    """Fields required to register a new user account."""
    email: str = Field(..., example="student@ju.edu.jo")
    password: str = Field(..., min_length=8, example="securePassword123")
    full_name: str = Field(..., min_length=2, example="Ahmad Al-Hassan")


class UserLogin(BaseModel):
    """Credentials for an existing user to authenticate."""
    email: str = Field(..., example="student@ju.edu.jo")
    password: str = Field(..., example="securePassword123")


class TokenResponse(BaseModel):
    """JWT token returned after successful login or registration."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


# ---------------------------------------------------------------------------
# Profile models
# ---------------------------------------------------------------------------

class ProfileCreate(BaseModel):
    """
    Full profile payload sent when a student first creates their profile.

    skills: mapping of skill name → proficiency level (0 = none, 5 = expert).
            These values are updated by the exam system; initial values
            may be self-reported and are flagged as 'unverified'.
    """
    major: str = Field(..., example="Computer Science")
    courses: List[str] = Field(default=[], example=["CS101", "CS201", "CS305"])
    skills: Dict[str, int] = Field(
        default={},
        example={"Python": 4, "React": 3, "SQL": 2}
    )
    availability_hours: int = Field(..., ge=1, le=40, example=15)
    bio: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, example="https://github.com/student")


class ProfileUpdate(BaseModel):
    """
    Partial profile update — all fields optional.
    Only fields that are explicitly provided will be overwritten.
    """
    major: Optional[str] = None
    courses: Optional[List[str]] = None
    skills: Optional[Dict[str, int]] = None
    availability_hours: Optional[int] = Field(None, ge=1, le=40)
    bio: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = None


class UserProfile(BaseModel):
    """Profile data returned by GET /api/profile/{user_id}."""
    user_id: str
    major: str
    courses: List[str]
    skills: Dict[str, int]
    availability_hours: int
    bio: Optional[str] = None
    github_url: Optional[str] = None
    updated_at: str


# ---------------------------------------------------------------------------
# Skill exam models
# ---------------------------------------------------------------------------

class SkillExamSubmit(BaseModel):
    """
    Payload to submit a completed skill exam.

    answers: dict mapping question_id → selected answer option (e.g. "A", "B").
    """
    skill_name: str = Field(..., example="Python")
    answers: Dict[str, str] = Field(
        ...,
        example={"q1": "A", "q2": "C", "q3": "B"}
    )


# ---------------------------------------------------------------------------
# Matching models
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    """Request parameters for the team-matching endpoint."""
    top_n: int = Field(default=10, ge=1, le=50,
                       description="Maximum number of matches to return.")


class MatchResult(BaseModel):
    """A single match result returned by the matching algorithm."""
    user_id: str
    full_name: str
    major: str
    score: float = Field(..., description="Cosine similarity score — 0.0 to 1.0")
    shared_skills: List[str]
    availability_hours: int


# ---------------------------------------------------------------------------
# Project models
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Payload to create a new student-defined project listing."""
    title: str = Field(..., max_length=120, example="E-commerce Recommendation Engine")
    description: str = Field(..., max_length=1000)
    skills_required: List[str] = Field(
        default=[],
        example=["Python", "TensorFlow", "React"]
    )


class Project(BaseModel):
    """Full project object returned by the API."""
    id: str
    title: str
    description: str
    skills_required: List[str]
    owner_id: str
    source: str  # "student" | "github" | "kaggle" | "huggingface" | "ai"
    created_at: str
    members: List[str]


# ---------------------------------------------------------------------------
# AI assistant models
# ---------------------------------------------------------------------------

class AIRequest(BaseModel):
    """
    Message sent to the Claude-powered assistant.

    conversation_history: list of prior turns — each dict has 'role' and 'content'.
                          Pass an empty list for a fresh conversation.
    """
    message: str = Field(..., max_length=2000)
    conversation_history: List[Dict[str, str]] = Field(default=[])


class AIResponse(BaseModel):
    """Response from the AI assistant."""
    reply: str
