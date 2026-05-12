"""
Team-Finder — Matching Algorithm
==================================
Implements cosine similarity over skill vectors to compute compatibility
scores between students. This module is intentionally isolated so the
algorithm can be tested independently and swapped without touching the API.

Background — Why Cosine Similarity?
-------------------------------------
A student's skills can be represented as a vector in an N-dimensional skill
space, where N is the number of distinct skills known to the system. Each
dimension holds the student's verified proficiency level (0–5) for that skill.

  Alice: {"Python": 4, "SQL": 2, "React": 0, "ML": 3}  → [4, 2, 0, 3]
  Bob:   {"Python": 3, "SQL": 0, "React": 4, "ML": 1}  → [3, 0, 4, 1]

Cosine similarity measures the angle between two vectors:

                    A · B
  cosine(A, B) = ---------
                  |A| × |B|

A score of 1.0 means perfect overlap in skills and proficiency levels.
A score of 0.0 means completely disjoint skill sets.

We prefer cosine over Euclidean distance because it is magnitude-invariant:
a student with Python=2 and a student with Python=4 are still "similar" in
the sense that both know Python, just at different depths.
"""

import math
from typing import Dict, List, Any


# ---------------------------------------------------------------------------
# Skill vector utilities
# ---------------------------------------------------------------------------

def build_skill_vector(skills: Dict[str, int], all_skills: List[str]) -> List[float]:
    """
    Convert a skill dict into a fixed-length numerical vector aligned to
    the global skill universe `all_skills`.

    Example:
        all_skills = ["Python", "React", "SQL", "ML"]
        skills     = {"Python": 4, "SQL": 2}
        result     → [4.0, 0.0, 2.0, 0.0]

    Zero is used for any skill not present in the student's profile, which
    means absent skills do not penalize the cosine score — only shared skills
    contribute positively.
    """
    return [float(skills.get(skill, 0)) for skill in all_skills]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute the cosine similarity between two equal-length numeric vectors.

    Returns a float in [0.0, 1.0]. Returns 0.0 if either vector is all-zero
    (a student with no recorded skills cannot be meaningfully compared).
    """
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a ** 2 for a in vec_a))
    magnitude_b = math.sqrt(sum(b ** 2 for b in vec_b))

    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0

    # Clamp to [0, 1] to guard against floating-point drift above 1.0
    return min(1.0, dot_product / (magnitude_a * magnitude_b))


# ---------------------------------------------------------------------------
# Shared-skill extraction
# ---------------------------------------------------------------------------

def find_shared_skills(skills_a: Dict[str, int], skills_b: Dict[str, int]) -> List[str]:
    """
    Return the list of skills that both students have recorded (level > 0).
    Useful for explaining *why* two students are a good match.
    """
    return [
        skill for skill in skills_a
        if skill in skills_b and skills_a[skill] > 0 and skills_b[skill] > 0
    ]


# ---------------------------------------------------------------------------
# Availability bonus
# ---------------------------------------------------------------------------

def availability_bonus(hours_a: int, hours_b: int) -> float:
    """
    Compute a small additive bonus (0.0–0.05) based on how similar two
    students' weekly availability is. This nudges the final score slightly
    in favour of pairs who can actually work together.

    Formula: bonus = 0.05 × (1 − |h_a − h_b| / max(h_a, h_b))
    """
    if max(hours_a, hours_b, 1) == 0:
        return 0.0
    diff_ratio = abs(hours_a - hours_b) / max(hours_a, hours_b, 1)
    return 0.05 * (1 - diff_ratio)


# ---------------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------------

def compute_match_scores(
    my_profile: Dict[str, Any],
    other_profiles: List[Dict[str, Any]],
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Compute similarity scores between `my_profile` and every profile in
    `other_profiles`. Return the top-N matches in descending score order.

    Parameters
    ----------
    my_profile : dict
        The authenticated user's profile (must contain a `skills` dict).
    other_profiles : list of dict
        All other user profiles fetched from the database.
    top_n : int
        How many results to return.

    Returns
    -------
    list of dicts — each containing:
        user_id, full_name, major, score, shared_skills, availability_hours

    Algorithm steps:
        1. Collect all distinct skill names across all profiles.
        2. Build a fixed-length vector for every profile.
        3. For each candidate, compute cosine similarity + availability bonus.
        4. Sort descending and take top_n.
    """
    if not other_profiles:
        return []

    # Step 1: Build the global skill universe (union of all known skills)
    all_skills: set = set(my_profile.get("skills", {}).keys())
    for profile in other_profiles:
        all_skills.update(profile.get("skills", {}).keys())
    all_skills_list = sorted(all_skills)  # sorted for deterministic ordering

    # Step 2: Build the requester's vector once (reused for every comparison)
    my_skills = my_profile.get("skills", {})
    my_vec = build_skill_vector(my_skills, all_skills_list)
    my_hours = my_profile.get("availability_hours", 0)

    results = []

    for profile in other_profiles:
        other_skills = profile.get("skills", {})
        other_vec = build_skill_vector(other_skills, all_skills_list)
        other_hours = profile.get("availability_hours", 0)

        # Step 3: Compute combined score
        cos_score = cosine_similarity(my_vec, other_vec)
        bonus = availability_bonus(my_hours, other_hours)
        final_score = min(1.0, cos_score + bonus)  # keep in [0, 1]

        shared = find_shared_skills(my_skills, other_skills)

        results.append({
            "user_id": profile.get("user_id"),
            "full_name": profile.get("full_name", "Unknown"),
            "major": profile.get("major", "Unknown"),
            "score": round(final_score, 4),
            "score_percent": round(final_score * 100, 1),
            "shared_skills": shared,
            "availability_hours": other_hours,
            "bio": profile.get("bio", ""),
            "github_url": profile.get("github_url", "")
        })

    # Step 4: Sort by score descending and return top_n
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
