import re
import fitz
import easyocr
import numpy as np
from io import BytesIO
from PIL import Image
import pdfplumber
from PyPDF2 import PdfReader
from docx import Document
from skill_extractor import extract_skills

ocr_reader = easyocr.Reader(["en"], gpu=False)

def read_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        pass

    if len(text.split()) < 80:
        try:
            doc = fitz.open(file_path)
            fitz_text = ""
            for page in doc:
                blocks = page.get_text("blocks")
                blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
                for block in blocks:
                    if len(block) >= 5:
                        fitz_text += block[4] + "\n"
            doc.close()
            if len(fitz_text) > len(text):
                text = fitz_text
        except Exception:
            pass

    if len(text.split()) < 80:
        try:
            doc = fitz.open(file_path)
            ocr_text = ""
            for page in doc:
                pix = page.get_pixmap(dpi=350)
                image = Image.open(BytesIO(pix.tobytes("png")))
                image = np.array(image)
                result = ocr_reader.readtext(image, detail=0, paragraph=True)
                ocr_text += "\n".join(result) + "\n"
            doc.close()
            if len(ocr_text) > len(text):
                text = ocr_text
        except Exception:
            pass

    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def read_docx(file_path):
    text = ""
    try:
        document = Document(file_path)
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
    except Exception:
        pass
    return text

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def extract_email(text):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""

def extract_phone(text):
    patterns = [r"(\+91[\-\s]?)?[6-9]\d{9}", r"\(\d{3}\)\s*\d{3}[- ]\d{4}", r"\d{3}[-.\s]\d{3}[-.\s]\d{4}"]
    for p in patterns:
        match = re.search(p, text)
        if match: return match.group()
    return ""

def extract_name(text):
    blacklist = {"resume", "curriculum", "vitae", "summary", "objective", "profile", "contact"}
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines[:12]:
        if len(line) < 3 or len(line.split()) > 5 or any(w in line.lower() for w in blacklist) or re.search(r"\d", line) or "@" in line:
            continue
        return line.title()
    return "Unknown Candidate"

def extract_education(text):
    keywords = ["b.tech", "b.e", "bachelor", "computer science", "mba", "mca", "university", "college"]
    # Section headings that mark where the Education section ENDS, so we
    # don't keep capturing into Experience/Skills/etc.
    next_section_words = [
        "experience", "work experience", "projects", "skills",
        "technical skills", "certifications", "achievements", "internship",
        "internships", "objective", "summary", "profile", "declaration",
        "hobbies", "interests", "languages", "publications", "references",
    ]
    lines = [line.strip() for line in text.split("\n")]

    # Find a genuine "Education" HEADING line (short, not a sentence that
    # merely mentions the word) rather than matching "education" anywhere.
    heading_idx = None
    for i, line in enumerate(lines):
        if "education" in line.lower() and len(line.split()) <= 4:
            heading_idx = i
            break

    education = []

    if heading_idx is not None:
        for line in lines[heading_idx + 1:]:
            if not line:
                break
            lower = line.lower().rstrip(":")
            if any(lower == w or lower.startswith(w + " ") for w in next_section_words):
                break
            education.append(line)
    else:
        for line in lines:
            if line and any(k in line.lower() for k in keywords):
                education.append(line)

    education = list(dict.fromkeys(education))
    return "\n".join(education[:3]) if education else "Degree Not Explicitly Indicated"

def extract_section(text, headings):
    lines = text.split("\n")
    start = -1
    for i, line in enumerate(lines):
        if any(h.lower() in line.strip().lower() for h in headings):
            start = i + 1
            break
    if start == -1: return []

    stop_words = ["education", "experience", "projects", "skills", "certifications", "interests"]
    data = []
    for line in lines[start:]:
        clean = line.strip()
        if not clean: continue
        if any(clean.lower().startswith(word) for word in stop_words):
            break
        data.append(clean)
    return data

def extract_experience(text):
    """
    Determine experience level.

    1. If the resume explicitly states a number of years ("3 Years",
       "5+ years"), use that directly - most reliable signal.
    2. Otherwise, look for an actual EXPERIENCE / WORK EXPERIENCE /
       INTERNSHIP section with real, substantive entries in it. Only
       then is "Experienced" justified.
    3. Fall back to "Fresher" by default.

    NOTE ON THE BUG THIS FIXES: the previous version fell back to
    scanning the *entire resume* for the words "developer", "engineer",
    or "analyst" and called the candidate "Experienced" if any of those
    words appeared ANYWHERE in the text. That's a false-positive trap -
    virtually every resume contains one of those words somewhere (a
    career objective like "seeking a Software Engineer role", a skills
    section, a project description) even when the candidate is a
    fresher with zero work history. That's why every candidate was
    coming back "Experienced". This version instead requires a real
    Experience/Internship section with actual content before making
    that claim.
    """
    lower = text.lower()

    match = re.search(r"(\d+)\+?\s*year", lower)
    if match:
        years = int(match.group(1))
        return "1 Year" if years == 1 else f"{years} Years"

    if "fresher" in lower:
        return "Fresher"

    work_section = extract_section(
        text,
        ["experience", "work experience", "professional experience",
         "internship", "internships"]
    )
    # Require at least two real lines of substance (not just a heading
    # echo or a single stray word) before calling someone "Experienced".
    substantive_lines = [line for line in work_section if len(line) >= 15]
    if len(substantive_lines) >= 2:
        return "Experienced"

    return "Fresher"

def extract_projects(text):
    proj = extract_section(text, ["projects", "academic projects", "personal projects"])
    return [p for p in proj if len(p) >= 5]

def extract_certifications(text):
    certs = extract_section(text, ["certifications", "certificates", "professional certifications"])
    return [c for c in certs if len(c) >= 5]

def parse_resume(file_path):

    if file_path.lower().endswith(".pdf"):
        text = read_pdf(file_path)

    elif file_path.lower().endswith(".docx"):
        text = read_docx(file_path)

    else:
        raise ValueError("Unsupported file format")

    skills = extract_skills(text)

    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "education": extract_education(text),
        "experience": extract_experience(text),
        "skills": ", ".join(skills),
        "projects": extract_projects(text),
        "certifications": extract_certifications(text)
    }
