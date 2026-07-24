

"""
experience_scorer.py
=====================
Scores how well a candidate's experience matches the job's requirement:
    meets or exceeds requirement   -> 100
    slightly below (1-2 yrs short) -> 70-90
    much lower (3+ yrs short)      -> 40-50
"""
import re


def parse_years(text):
    """Pull a number of years out of text like '3 Years', '5+ Years',
    'Fresher'. Returns 0 for fresher, None if nothing usable is found."""
    text = (text or "").strip().lower()
    if not text or "fresher" in text:
        return 0
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def score_experience(candidate_experience, required_experience):
    required_years = parse_years(required_experience)
    candidate_years = parse_years(candidate_experience)

    if not required_years:          # job just asks for "Fresher"
        return 100
    if candidate_years is None:     # resume didn't have a clear number
        return 50

    shortfall = required_years - candidate_years

    if shortfall <= 0:
        return 100
    elif shortfall <= 2:
        return max(70, 90 - (shortfall - 1) * 10)
    else:
        return max(40, 50 - (shortfall - 3) * 5)