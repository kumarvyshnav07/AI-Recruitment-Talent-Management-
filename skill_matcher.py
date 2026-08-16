"""
skill_matcher.py
=================
Compares a candidate's skills against a job's required skills.
Used by both ats_engine.py and job_matching.py.

Change from the original version: both sides are now normalized through
skills_database.normalize_skill(), so aliases/abbreviations line up.
Previously "JS" (resume) vs "JavaScript" (job posting) would never
match because it was a plain lower-cased string comparison; now both
resolve to the same canonical "JavaScript" before comparing.
"""
import re

from skills_database import normalize_skill


def clean_skills(skills):
    """Turn a comma/semicolon/newline separated skills string (or list)
    into a clean, de-duplicated list of CANONICAL skill names (order
    preserved). Uses normalize_skill so abbreviations/aliases resolve
    to the same skill as their full name."""
    if isinstance(skills, list):
        items = skills
    else:
        items = re.split(r"[,;/\n|•]+", str(skills))

    cleaned = []
    seen = set()
    for item in items:
        item = item.strip()
        if not item:
            continue
        canonical = normalize_skill(item)
        key = canonical.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(canonical)
    return cleaned


def skill_match(candidate_skills, required_skills):
    """
    Compare candidate skills to a job's required skills.

    matched     -> skills the candidate has that the job needs
    missing     -> skills the job needs that the candidate doesn't have
    additional  -> skills the candidate has beyond what the job asked for
    score       -> % of required skills matched (0-100)
    """
    candidate = clean_skills(candidate_skills)
    required = clean_skills(required_skills)

    candidate_lower = {s.lower() for s in candidate}
    required_lower = {s.lower(): s for s in required}  # lower -> canonical display

    matched = [required_lower[s] for s in required_lower if s in candidate_lower]
    missing = [required_lower[s] for s in required_lower if s not in candidate_lower]
    additional = [s for s in candidate if s.lower() not in required_lower]

    score = round(len(matched) / len(required) * 100) if required else 0

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "additional": additional,
    }
