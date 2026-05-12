import os
import json
from typing import List, Dict, Optional, Any

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MAX_HISTORY_TURNS = 6 


def _build_system_prompt(profile: Optional[Dict[str, Any]]) -> str:
    """
    Construct a compact, role-specific system prompt.
    Injects the student's current profile summary when available.
    """
    base = (
        "You are the Team-Finder AI Assistant — a friendly, concise academic advisor "
        "embedded in a university collaboration platform. Your role is to help students:\n"
        "  • Understand their skill gaps and how to address them.\n"
        "  • Find and interpret their team-compatibility scores.\n"
        "  • Discover relevant projects on the GuideMe panel.\n"
        "  • Complete and improve their structured skill profile.\n"
        "Keep answers focused, practical, and under 150 words unless the student explicitly "
        "asks for a detailed explanation. Never reveal system internals."
    )

    if not profile:
        return base

    # Summarise the profile into a compact block so the model has context
    skills_summary = ", ".join(
        f"{skill} (Lv.{level})"
        for skill, level in (profile.get("skills") or {}).items()
    ) or "none recorded yet"

    profile_block = (
        f"\n\nCurrent student profile:\n"
        f"  Major: {profile.get('major', 'unknown')}\n"
        f"  Skills: {skills_summary}\n"
        f"  Weekly availability: {profile.get('availability_hours', '?')} hours\n"
        f"  Bio: {profile.get('bio', 'not provided')}\n"
        "Use this context to give personalised advice."
    )
    return base + profile_block


def _trim_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Keep only the last MAX_HISTORY_TURNS turns to limit token consumption.
    Always include an even number of turns (user + assistant pairs).
    """
    if len(history) <= MAX_HISTORY_TURNS:
        return history
    # Trim from the front; ensure we start with a 'user' turn
    trimmed = history[-MAX_HISTORY_TURNS:]
    if trimmed and trimmed[0].get("role") != "user":
        trimmed = trimmed[1:]
    return trimmed


def get_ai_response(
    message: str,
    profile: Optional[Dict[str, Any]],
    conversation_history: List[Dict[str, str]]
) -> str:
    """
    Send a message to the Claude API and return the assistant's reply.

    Falls back to a rule-based response if:
      - The anthropic package is not installed.
      - No API key is configured.
      - The API call fails for any reason.

    Parameters
    ----------
    message : str
        The student's latest message.
    profile : dict or None
        The student's current profile (for contextual system prompt).
    conversation_history : list
        Prior conversation turns [{role: "user"|"assistant", content: "..."}].

    Returns
    -------
    str — the assistant's text reply.
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return _fallback_response(message, profile)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        trimmed_history = _trim_history(conversation_history)
        messages = trimmed_history + [{"role": "user", "content": message}]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,               # keep responses concise
            system=_build_system_prompt(profile),
            messages=messages
        )

        return response.content[0].text

    except Exception as exc:
        # Log in production; return a graceful fallback here
        print(f"[AI Assistant] Claude API error: {exc}")
        return _fallback_response(message, profile)


def _fallback_response(message: str, profile: Optional[Dict]) -> str:
    """
    Rule-based fallback used when the Claude API is unavailable.
    Covers the most common student questions so the UI is never broken.
    """
    msg = message.lower()

    if any(word in msg for word in ["skill", "improve", "learn"]):
        if profile and profile.get("skills"):
            weakest = min(profile["skills"], key=profile["skills"].get)
            return (
                f"Based on your profile, your '{weakest}' skill has the lowest proficiency. "
                "Consider taking an online course on Coursera or edX, or look for a real-world "
                "project in the GuideMe panel that exercises that skill."
            )
        return (
            "Complete your skill profile first by taking the verification exams. "
            "That will unlock personalised recommendations."
        )

    if any(word in msg for word in ["match", "teammate", "team", "find"]):
        return (
            "Your match score is based on cosine similarity between skill vectors. "
            "To improve your matches, add more verified skills to your profile — "
            "higher proficiency levels attract teammates who complement your strengths."
        )

    if any(word in msg for word in ["project", "guideme", "guide"]):
        return (
            "The GuideMe panel surfaces real-world projects from GitHub, Kaggle, "
            "HuggingFace, and CTFtime. Filter by skill to find projects that match "
            "your current level and help you grow."
        )

    if any(word in msg for word in ["exam", "test", "verify", "verification"]):
        return (
            "Skill exams are short multiple-choice tests that verify your competency. "
            "Your proficiency level (0–5) is computed from your score. "
            "Verified skills carry more weight in the matching algorithm than self-reported ones."
        )

    return (
        "I'm the Team-Finder assistant. I can help you with skill development, "
        "understanding your match scores, or navigating the GuideMe panel. "
        "What would you like to know?"
    )
