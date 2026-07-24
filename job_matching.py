"""
job_matching.py
================
Recruiter Login -> View JDs -> Select a JD -> Retrieve Required Skills
  -> Retrieve All Parsed Resumes -> for each candidate: compare skills,
     find matched/missing/additional, calculate match % -> Display Results
"""
from database import get_job, get_candidates
from skill_matcher import skill_match


def match_candidates_to_job(job_id):
    """Compare every stored candidate against one job's required skills.
    Returns results sorted best-match-first, ready for the dashboard."""
    job = get_job(job_id)
    if job is None:
        return None

    required_skills = job.get("required_skills", "")
    results = []

    for candidate in get_candidates():
        match = skill_match(candidate.get("skills", ""), required_skills)
        results.append({
            "candidate_id": candidate["id"],
            "name": candidate["name"],
            "email": candidate["email"],
            "matched_skills": match["matched"],
            "missing_skills": match["missing"],
            "additional_skills": match["additional"],
            "match_percent": match["score"],
        })

    results.sort(key=lambda r: r["match_percent"], reverse=True)
    return {"job_title": job["job_title"], "results": results}