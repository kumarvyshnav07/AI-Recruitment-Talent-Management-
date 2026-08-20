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
    'Fresher'. Returns 0 for fresher, None if nothing usable is found.

    NOTE: this returns 0 (not None) for 'Fresher'. Callers must check
    for None explicitly (`is None`), not falsiness (`not x`) - 0 is a
    legitimate, meaningful value here, not a "missing data" marker."""
    text = (text or "").strip().lower()
    if not text or "fresher" in text:
        return 0
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def score_experience(candidate_experience, required_experience):
    required_years = parse_years(required_experience)
    candidate_years = parse_years(candidate_experience)

    # BUG FIX #1: previously `if not required_years:` - since
    # parse_years("Fresher") returns 0, and 0 is falsy in Python, a
    # Fresher-level job requirement made EVERY candidate score 100 on
    # experience regardless of their actual level. Must check `is None`
    # (truly unparseable) separately from `== 0` (explicitly Fresher).
    if required_years is None:      # job's required experience wasn't parseable
        return 100
    if required_years == 0:         # job explicitly asks for "Fresher"
        # A fresher-level job still shouldn't penalize experienced
        # candidates, but it also shouldn't be a blind 100 - reward an
        # exact Fresher match highest, and still credit real experience.
        if candidate_years == 0:
            return 100
        if candidate_years is None:
            return 90              # "Experienced" (unspecified) - clearly not entry-level-inexperienced, but unquantified
        return 90                  # has real years - still a strong, qualified fit

    # BUG FIX #2: previously, ANY candidate whose experience label had
    # no explicit number (e.g. resume_parser.py's "Experienced" - a
    # real category, not missing data) fell into `candidate_years is
    # None` and got a flat 50, indistinguishable from a true Fresher
    # against the same job. "Experienced" means "a real work/internship
    # section was found, but no number was stated" - treat it as
    # roughly comparable to meeting a modest (1-2 yr) requirement
    # rather than as an unknown.
    if candidate_years is None:
        if "experienced" in (candidate_experience or "").lower():
            candidate_years = min(required_years, 2)   # credit as "some real experience"
        else:
            return 50               # genuinely unparseable/unexpected input - fall back safely

    shortfall = required_years - candidate_years

    if shortfall <= 0:
        return 100
    elif shortfall <= 2:
        return max(70, 90 - (shortfall - 1) * 10)
    else:
        return max(40, 50 - (shortfall - 3) * 5)
