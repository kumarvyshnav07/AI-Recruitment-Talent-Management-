"""
skill_extractor.py
===================
Extracts skills from raw resume text.

Approach
--------
Two passes, combined and de-duplicated:

1. WHOLE-DOCUMENT TAXONOMY SCAN
   Look for every skill/alias in skills_database.SKILL_ALIASES anywhere
   in the resume - not just under a "Skills" heading. This catches
   skills only mentioned inside project descriptions or the summary
   (e.g. "built a REST API in Flask" still detects Flask + REST API).
   Matching is boundary-safe (won't match "java" inside "javascript",
   or "r" inside "regarding") and alias-aware (JS -> JavaScript).

2. EXPLICIT "SKILLS" SECTION FALLBACK
   Also parses the dedicated Skills/Technical Skills section (comma /
   bullet / pipe separated) and normalizes each entry through the same
   alias table. This picks up anything the candidate listed that isn't
   in our curated taxonomy yet (e.g. a niche library), so it still
   shows up instead of being silently dropped.

This is intentionally a fast, deterministic, no-API-key-needed approach
(no LLM calls) - see skills_database.py for how to add more skills.
"""
import re

from skills_database import ALL_TERMS_BY_LENGTH, ALIAS_LOOKUP, normalize_skill

# Section headings that introduce a candidate's skill list.
_SKILL_HEADINGS = [
    "technical skills", "core skills", "key skills", "skills",
    "technical proficiencies", "competencies", "areas of expertise",
]

# Headings that mark the START of the NEXT section (so we know where the
# skills section ends). Kept broad on purpose - a heading we fail to
# recognize here means everything after it (dates, project blurbs,
# internship descriptions...) gets swept in as "skills" by Pass 2 below.
_NEXT_SECTION_HEADINGS = [
    "education", "experience", "work experience", "internship",
    "internships", "projects", "certifications", "achievements",
    "awards", "training", "summary", "objective", "profile",
    "interests", "hobbies", "languages", "extracurricular",
    "publications", "references", "volunteer", "declaration",
    "personal details",
]

# Lines/sub-lines inside the Skills section are often labeled, e.g.
# "Programming Languages: Java, Python" or "Tech Stack - HTML, CSS".
# Strip the label so the values survive instead of the whole line
# ("Programming Languages: Java" would otherwise become a bogus "skill").
_LABEL_PREFIX = re.compile(
    r"^(programming\s+languages?|tech(nical)?\s+stack|technologies|"
    r"frameworks?|tools?|databases?|libraries|platforms?)\s*[:\-]\s*",
    re.IGNORECASE,
)

# Words that only ever show up as connective tissue in a sentence, never
# as a skill name on their own. If any word in a candidate item matches
# one of these, the item is a sentence fragment, not a skill.
_PROSE_WORDS = {
    "and", "or", "the", "a", "an", "in", "on", "at", "with", "for", "of",
    "to", "from", "using", "resulting", "improving", "achieved",
    "achieving", "developed", "developing", "built", "building",
    "created", "led", "managed", "responsible", "including", "such",
    "as", "into", "by",
}

_DELIMS = re.compile(r"[,;/\n|•\u2022]+")
_LEADING_BULLET = re.compile(r"^[-*\u2022]\s*")


def _compile_patterns():
    """One compiled regex per known skill term, boundary-safe so 'r'
    doesn't match inside 'regarding' and 'go' doesn't match inside
    'going'. Boundaries are defined as 'not alphanumeric', which works
    even for terms containing punctuation like 'C++', 'C#', 'Node.js'."""
    patterns = {}
    for term in ALL_TERMS_BY_LENGTH:
        escaped = re.escape(term)
        pattern = re.compile(
            r"(?<![A-Za-z0-9])" + escaped + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        patterns[term] = pattern
    return patterns


_PATTERNS = _compile_patterns()


def _scan_document(text):
    """Pass 1: find every taxonomy skill anywhere in the resume text."""
    found = set()
    for term, pattern in _PATTERNS.items():
        if pattern.search(text):
            found.add(ALIAS_LOOKUP[term])
    return found


def _extract_skills_section(text):
    """Pass 2: isolate the Skills section (if present) and normalize
    every comma/bullet-separated entry, so custom/niche skills the
    candidate listed still surface even if they're not in our taxonomy."""
    lines = text.split("\n")
    start = -1
    for i, line in enumerate(lines):
        clean = line.strip().lower().rstrip(":")
        if clean in _SKILL_HEADINGS:
            start = i + 1
            break
    if start == -1:
        return set()

    section_lines = []
    for line in lines[start:]:
        clean = line.strip()
        if not clean:
            continue
        if any(clean.lower().rstrip(":").startswith(h) for h in _NEXT_SECTION_HEADINGS):
            break
        clean = _LEADING_BULLET.sub("", clean)
        clean = _LABEL_PREFIX.sub("", clean)
        section_lines.append(clean)

    raw_items = _DELIMS.split(", ".join(section_lines))
    extracted = set()
    for item in raw_items:
        item = item.strip(" .-–")
        # Skip empties, stray numbers/bullets, and overly long lines that
        # are clearly not a single skill (e.g. a leaked sentence).
        if not item or len(item) < 2 or len(item.split()) > 4:
            continue
        words = item.lower().split()
        # Reject date fragments and anything with a bare numeric token
        # (years, date ranges like "2024 - 06", stray "40%" / "05").
        if any(w.strip("().,%").isdigit() for w in words):
            continue
        # Reject sentence fragments leaked from prose (project blurbs,
        # summaries) rather than an actual skills list.
        if any(w in _PROSE_WORDS for w in words):
            continue
        extracted.add(normalize_skill(item))
    return extracted


def extract_skills(text):
    """Return a sorted, de-duplicated list of skill names found in the
    resume text. Combines the whole-document taxonomy scan with the
    explicit Skills-section fallback."""
    if not text or not text.strip():
        return []

    taxonomy_hits = _scan_document(text)
    section_hits = _extract_skills_section(text)

    all_skills = taxonomy_hits | section_hits
    return sorted(all_skills, key=lambda s: s.lower())