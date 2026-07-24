"""
ats_engine.py
=============
Weighted ATS score (0-100):
    skills 50% | experience 20% | education 10% | projects 10% | certs 10%
"""
from skill_matcher import skill_match
from experience_scorer import score_experience


def calculate_ats(details, required_skills, required_experience, required_education):
    skills = skill_match(details.get("skills", ""), required_skills)
    experience = score_experience(details.get("experience", ""), required_experience)

    education_score = 100 if required_education.lower() == "any degree" else 90

    project_count = len(details.get("projects", []))
    project_score = 100 if project_count >= 3 else 70 if project_count >= 1 else 40

    cert_count = len(details.get("certifications", []))
    cert_score = 100 if cert_count >= 2 else 75 if cert_count >= 1 else 40

    ats = round(
        skills["score"] * 0.50
        + experience * 0.20
        + education_score * 0.10
        + project_score * 0.10
        + cert_score * 0.10
    )
    ats = max(0, min(ats, 100))

    return {
        "ats": ats,
        "rating": round(ats / 10, 1),
        "matched": len(skills["matched"]),
        "missing": len(skills["missing"]),
        "matched_skills": skills["matched"],
        "missing_skills": skills["missing"],
        "additional_skills": skills["additional"],
    }


def generate_recommendation(ats_result):
    score = ats_result["ats"]
    if score >= 85:
        return {"decision": "Highly Recommended", "risk": "Low", "confidence": "96%"}
    elif score >= 70:
        return {"decision": "Consider Context", "risk": "Medium", "confidence": "84%"}
    else:
        return {"decision": "Not Recommended", "risk": "High", "confidence": "70%"}