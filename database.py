import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load DB_* values from .env instead of hardcoding secrets in source
# (a hardcoded password in the repo is a real security liability the
# moment this code is committed anywhere, even a private repo).
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "ai_recruitment_copilot"),
}

if not DB_CONFIG["password"]:
    print(
        "Warning: DB_PASSWORD not set in .env — connecting with an empty "
        "password. Add DB_HOST/DB_USER/DB_PASSWORD/DB_NAME to a .env file."
    )


def get_connection():
    try:
        return mysql.connector.connect(
            host=DB_CONFIG["host"], user=DB_CONFIG["user"], password=DB_CONFIG["password"]
        )
    except Error as e:
        print("Database Connection Error:", e)
        return None


def init_db():
    connection = get_connection()
    if connection is None:
        return
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    connection.database = DB_CONFIG["database"]

    # Candidates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates(
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200),
        email VARCHAR(200),
        job_role VARCHAR(200),
        phone VARCHAR(50),
        education TEXT,
        experience VARCHAR(100),
        skills LONGTEXT,
        certifications LONGTEXT,
        projects LONGTEXT,
        resume_name VARCHAR(255),
        ats_score INT,
        recommendation VARCHAR(100),
        confidence VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_candidate_job (email, job_role)
    )
    """)

    # Users table (needed by auth.py's register/login — this was missing,
    # which is why login had nothing real to check against)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE,
        email VARCHAR(200) UNIQUE,
        password VARCHAR(255)
    )
    """)

    # Role column — powers the separate Recruiter / Candidate login portals.
    # Added defensively (existing accounts predate this column and default
    # to 'recruiter' so nobody already registered gets locked out).
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'recruiter'")
    except Exception:
        pass  # Column already exists

    # Job postings table (job_id, job_title, company_name, experience,
    # location, salary — per your spec — plus required_skills/qualification
    # so a posted job can feed straight into calculate_ats()).
    #
    # created_by stores the RECRUITER'S USERNAME (not a numeric user id) —
    # admin_db.get_recruiter_rows() matches job.created_by against
    # users.username directly, and recruiter_page.py's "Post a New Job"
    # form passes created_by=st.session_state["username"]. Keep this a
    # VARCHAR, matching what's actually written to it.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job(
        job_id INT AUTO_INCREMENT PRIMARY KEY,
        job_title VARCHAR(200) NOT NULL,
        company_name VARCHAR(200) NOT NULL,
        experience VARCHAR(100),
        location VARCHAR(200),
        salary DECIMAL(12,2),
        required_skills TEXT,
        qualification VARCHAR(100),
        created_by VARCHAR(150),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    connection.commit()
    cursor.close()
    connection.close()


def save_candidate(candidate, ats, recommendation, resume_name, job_role):
    connection = get_connection()
    if connection is None:
        return "error"
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM candidates WHERE email=%s AND job_role=%s",
        (candidate["email"], job_role),
    )
    existing = cursor.fetchone()

    cert_str = (
        ", ".join(candidate.get("certifications", []))
        if isinstance(candidate.get("certifications"), list)
        else candidate.get("certifications", "")
    )
    proj_str = (
        ", ".join(candidate.get("projects", []))
        if isinstance(candidate.get("projects"), list)
        else candidate.get("projects", "")
    )

    if existing:
        action = "updated"
        cursor.execute(
            """
            UPDATE candidates SET
                name=%s, phone=%s, education=%s, experience=%s, skills=%s,
                certifications=%s, projects=%s, resume_name=%s, ats_score=%s,
                recommendation=%s, confidence=%s
            WHERE email=%s AND job_role=%s
            """,
            (
                candidate["name"], candidate["phone"], candidate["education"],
                candidate["experience"], candidate["skills"], cert_str, proj_str,
                resume_name, ats["ats"], recommendation["decision"],
                recommendation["confidence"], candidate["email"], job_role,
            ),
        )
    else:
        action = "inserted"
        cursor.execute(
            """
            INSERT INTO candidates (name, email, job_role, phone, education, experience,
                skills, certifications, projects, resume_name, ats_score, recommendation, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                candidate["name"], candidate["email"], job_role, candidate["phone"],
                candidate["education"], candidate["experience"], candidate["skills"],
                cert_str, proj_str, resume_name, ats["ats"], recommendation["decision"],
                recommendation["confidence"],
            ),
        )

    connection.commit()
    cursor.close()
    connection.close()
    return action


def get_candidates():
    connection = get_connection()
    if connection is None:
        return []
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM candidates ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def get_candidate(candidate_id):
    """Fetch a single candidate by primary key id."""
    connection = get_connection()
    if connection is None:
        return None
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM candidates WHERE id=%s", (candidate_id,))
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    return row


def get_candidate_by_id(email, job_role):
    """Fetch a single candidate by its (email, job_role) unique key."""
    connection = get_connection()
    if connection is None:
        return None
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM candidates WHERE email=%s AND job_role=%s", (email, job_role)
    )
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    return row


def get_candidates_for_role(job_role):
    """Fetch every candidate who was evaluated against a specific job
    role, best ATS score first. Used to show 'Candidates for this Role'
    on the Job Postings page."""
    connection = get_connection()
    if connection is None:
        return []
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM candidates WHERE job_role=%s ORDER BY ats_score DESC",
        (job_role,),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def get_candidates_by_email(email):
    """All job applications tied to one login email — a candidate can have
    more than one row (one per job_role they were evaluated against).
    Powers the Candidate portal dashboard."""
    connection = get_connection()
    if connection is None:
        return []
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM candidates WHERE email=%s ORDER BY updated_at DESC",
        (email,),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def search_candidates(query):
    """Search candidates by name, email, skills, or job_role (partial match)."""
    connection = get_connection()
    if connection is None:
        return []
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    like = f"%{query}%"
    cursor.execute(
        """
        SELECT * FROM candidates
        WHERE name LIKE %s OR email LIKE %s OR skills LIKE %s OR job_role LIKE %s
           OR education LIKE %s
        ORDER BY updated_at DESC
        """,
        (like, like, like, like, like),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def delete_candidate(email, job_role):
    """Delete a candidate application identified by (email, job_role)."""
    connection = get_connection()
    if connection is None:
        return False
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM candidates WHERE email=%s AND job_role=%s", (email, job_role)
    )
    connection.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    connection.close()
    return deleted


def create_job(job_title, company_name, experience, location, salary,
               required_skills="", qualification="Any Degree", created_by=None):
    """
    Insert a new job posting. Uses a parameterized query (%s placeholders)
    — never string-format values directly into SQL, that's how SQL
    injection happens (see the note in job_api.py).

    created_by: the posting recruiter's username (str), or None if not
    known. This was previously missing entirely from both the function
    signature and the INSERT statement — recruiter_page.py was already
    calling create_job(..., created_by=username), which would raise
    TypeError: create_job() got an unexpected keyword argument
    'created_by'. Storing it here is what lets admin_db.get_recruiter_rows()
    correctly count "Jobs Posted" per recruiter instead of always
    showing 0.

    Returns the new job_id, or None on failure.
    """
    connection = get_connection()
    if connection is None:
        return None
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO job (job_title, company_name, experience, location, salary,
            required_skills, qualification, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (job_title, company_name, experience, location, salary,
         required_skills, qualification, created_by),
    )

    connection.commit()
    new_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return new_id


def update_job(job_id, job_title, company_name, experience, location, salary,
               required_skills="", qualification="Any Degree"):
    """
    Update an existing job posting in place (parameterized query, same
    injection-safety note as create_job). Returns True if a row was
    actually updated, False if job_id didn't exist or the DB was
    unreachable.
    """
    connection = get_connection()
    if connection is None:
        return False
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE job SET
            job_title=%s, company_name=%s, experience=%s, location=%s,
            salary=%s, required_skills=%s, qualification=%s
        WHERE job_id=%s
        """,
        (job_title, company_name, experience, location, salary,
         required_skills, qualification, job_id),
    )

    connection.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    connection.close()
    return updated


def get_jobs():
    """Return all job postings, most recent first."""
    connection = get_connection()
    if connection is None:
        return []
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM job ORDER BY created_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def get_job(job_id):
    """Fetch a single job posting by job_id."""
    connection = get_connection()
    if connection is None:
        return None
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM job WHERE job_id=%s", (job_id,))
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    return row


def delete_job(job_id):
    """Delete a job posting by job_id."""
    connection = get_connection()
    if connection is None:
        return False
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()
    cursor.execute("DELETE FROM job WHERE job_id=%s", (job_id,))
    connection.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    connection.close()
    return deleted


def get_job_by_title(job_title):
    """Best-effort lookup of a job posting by its title, used to enrich a
    candidate's own application (company name, location, required skills,
    etc.) since `candidates` stores job_role as free text rather than a
    job_id foreign key. Returns the most recently posted match, or None
    if the posting no longer exists (e.g. it was deleted, or the ATS
    analysis was run as a manual entry rather than against a real
    posting) — callers must handle None gracefully rather than assume a
    job record always exists."""
    connection = get_connection()
    if connection is None:
        return None
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM job WHERE job_title=%s ORDER BY created_at DESC LIMIT 1",
        (job_title,),
    )
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    return row


# =====================================================
# CANDIDATE PORTAL — DASHBOARD STATISTICS
# =====================================================
# These helpers turn a candidate's raw application rows into the
# aggregate numbers the candidate dashboard needs, so candidate_page.py
# never has to compute stage/ATS math inline. Every function takes only
# `email` (the candidate's login identity) and returns safe defaults
# (0 / [] / None) when the candidate has no applications yet or the DB
# is unreachable.

CANDIDATE_ACTIVE_STAGES = ("Applied", "Screening", "Interview in progress")
CANDIDATE_FINAL_STAGES = ("Selected", "Rejected")


def get_candidate_status_counts(email):
    """Count of the candidate's own applications in each pipeline stage.
    Keys always present (0 if none), in pipeline order, so the caller
    can iterate a fixed, predictable status list for the status-overview
    chart and hiring funnel."""
    apps = get_candidates_by_email(email)
    counts = {
        "Applied": 0, "Screening": 0, "Interview in progress": 0,
        "Selected": 0, "Rejected": 0,
    }
    for a in apps:
        stage = a.get("stage") or "Applied"
        if stage in counts:
            counts[stage] += 1
        else:
            # Unknown/legacy stage value — still count it somewhere
            # rather than silently drop it from totals.
            counts.setdefault(stage, 0)
            counts[stage] += 1
    return counts


def get_candidate_ats_stats(email):
    """ATS score summary across every application this candidate has
    submitted. `scores` is ordered the same as get_candidates_by_email
    (most recently updated first) so a caller can chart it directly."""
    apps = get_candidates_by_email(email)
    scores = [
        {"job_role": a.get("job_role", "—"), "score": a.get("ats_score") or 0}
        for a in apps
    ]
    values = [s["score"] for s in scores]
    if not values:
        return {"average": 0, "highest": 0, "lowest": 0, "scores": []}
    return {
        "average": round(sum(values) / len(values), 1),
        "highest": max(values),
        "lowest": min(values),
        "scores": scores,
    }


def get_dashboard_stats():
    connection = get_connection()
    if connection is None:
        return {"total_candidates": 0, "shortlisted": 0, "average_ats": 0, "today_uploads": 0}
    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) total FROM candidates")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) total FROM candidates WHERE ats_score>=80")
    shortlisted = cursor.fetchone()["total"]
    cursor.execute("SELECT AVG(ats_score) avg_score FROM candidates")
    avg = cursor.fetchone()["avg_score"]
    avg = round(avg, 1) if avg else 0
    cursor.execute("SELECT COUNT(*) total FROM candidates WHERE DATE(updated_at)=CURDATE()")
    today = cursor.fetchone()["total"]

    cursor.close()
    connection.close()
    return {
        "total_candidates": total,
        "shortlisted": shortlisted,
        "average_ats": avg,
        "today_uploads": today,
    }


def top_skills():
    from collections import Counter

    counter = Counter()
    for row in get_candidates():
        skills = row["skills"]
        if not skills:
            continue
        for skill in skills.split(","):
            counter.update([skill.strip()])
    return counter.most_common(10)


def database_version():
    connection = get_connection()
    if connection is None:
        return "Unknown"
    cursor = connection.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return version
