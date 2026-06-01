"""
TeamFinder — Pydantic request/response models.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    email: str = Field(..., examples=["student@ju.edu.jo"])
    password: str = Field(..., min_length=8, examples=["securePassword123"])
    full_name: str = Field(..., min_length=2, examples=["Ahmad Al-Hassan"])


class UserLogin(BaseModel):
    email: str = Field(..., examples=["student@ju.edu.jo"])
    password: str = Field(..., examples=["securePassword123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

class ProfileCreate(BaseModel):
    major: str = Field(..., examples=["Computer Science"])
    courses: List[str] = Field(default=[], examples=[["CS101", "CS201"]])
    skills: Dict[str, int] = Field(default={}, examples=[{"Python": 4}])
    availability_hours: int = Field(..., ge=1, le=40, examples=[15])
    bio: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, examples=["https://github.com/me"])


class ProfileUpdate(BaseModel):
    major: Optional[str] = None
    courses: Optional[List[str]] = None
    skills: Optional[Dict[str, int]] = None
    availability_hours: Optional[int] = Field(None, ge=1, le=40)
    bio: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = None


class UserProfile(BaseModel):
    user_id: str
    major: str
    courses: List[str]
    skills: Dict[str, int]
    availability_hours: int
    bio: Optional[str] = None
    github_url: Optional[str] = None
    updated_at: str


# ---------------------------------------------------------------------------
# Skill exams
# ---------------------------------------------------------------------------

class SkillExamSubmit(BaseModel):
    skill_name: str = Field(..., examples=["Python"])
    answers: Dict[str, str] = Field(..., examples=[{"q1": "A", "q2": "C"}])


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    top_n: int = Field(default=10, ge=1, le=50,
                       description="Maximum number of matches to return.")


class MatchResult(BaseModel):
    user_id: str
    full_name: str
    major: str
    score: float
    shared_skills: List[str]
    availability_hours: int


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    title: str = Field(..., max_length=120)
    description: str = Field(..., max_length=1000)
    skills_required: List[str] = Field(default=[])


class Project(BaseModel):
    id: str
    title: str
    description: str
    skills_required: List[str]
    owner_id: Optional[str] = None
    source: str
    created_at: str
    members: List[str]


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------

class AIRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    conversation_history: List[Dict[str, str]] = Field(default=[])


class AIResponse(BaseModel):
    reply: str
