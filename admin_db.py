"""
admin_db.py
===========
Persistence + queries for the Admin Dashboard. Mirrors the style of
database.py / interview_db.py: every function opens its own connection,
uses parameterized queries, and returns a safe default (None / [] / a
zeroed dict) on a connection failure or empty result set instead of
raising — a dropped DB connection should degrade the Admin UI, not
crash it.

Schema additions owned by this module:
  - audit_logs:        one row per administrative action (who / what /
                        target / when), read-only from the UI's point
                        of view — nothing here can be edited or deleted
                        through the app.
  - platform_settings: a small key/value table for the safe, non-code
                        settings exposed on the Admin Settings page
                        (recommendation thresholds, pagination limits,
                        etc.) — never raw SQL, never Python.

`users.status` / `users.created_at` and `job.status` / `job.created_by`
are added in database.py's init_db(), since they extend tables that
module owns.
"""
import os
from datetime import datetime, timedelta

from database import get_db_connection, get_candidates, get_jobs
from interview_db import get_sessions

# Reuse database.py's single connection function (aliased so the rest
# of this file — which already calls get_connection() everywhere —
# doesn't need to change). No more duplicate mysql.connector.connect(
# **DB_CONFIG) block living separately in this module.
get_connection = get_db_connection


def _ensure_column(cursor, table, column, ddl):
    """Add `column` to `table` if it doesn't already exist. Safe to call
    every startup - checks information_schema first instead of blindly
    running ALTER TABLE (which errors on an existing column).

    This exists because `users.status` / `users.created_at` and
    `job.status` / `job.created_by` are conceptually owned by
    database.py's init_db(), but on a database that was created before
    those columns were added to the code, CREATE TABLE IF NOT EXISTS
    silently does nothing to the already-existing table. Rather than
    depend on database.py being edited/rerun correctly, admin_db.py
    heals its own dependency here every time init_admin_db() runs."""
    cursor.execute(
        """SELECT COUNT(*) FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s""",
        (table, column),
    )
    (exists,) = cursor.fetchone()
    if not exists:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_admin_db():
    conn = get_connection()
    if conn is None:
        return
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs(
        id INT AUTO_INCREMENT PRIMARY KEY,
        actor_username VARCHAR(100),
        actor_role VARCHAR(20),
        action VARCHAR(100),
        target_type VARCHAR(50),
        target_id VARCHAR(100),
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS platform_settings(
        setting_key VARCHAR(100) PRIMARY KEY,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """)

    # Self-healing migration: make sure the columns admin_db.py's own
    # queries depend on (get_all_users, get_platform_overview, etc.)
    # actually exist on the `users` and `job` tables, regardless of
    # what database.py's init_db() did or didn't add historically.
    try:
        _ensure_column(cursor, "users", "status",
                        "status VARCHAR(20) NOT NULL DEFAULT 'active'")
        _ensure_column(cursor, "users", "created_at",
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        _ensure_column(cursor, "job", "status",
                        "status VARCHAR(20) NOT NULL DEFAULT 'Active'")
        # created_by stores the recruiter's USERNAME (recruiter_page.py
        # writes st.session_state["username"] into it, and
        # get_recruiter_rows() below compares it against users.username
        # as a string) — not a numeric user id. Add it as VARCHAR, and if
        # an earlier version of this migration already created it as INT,
        # convert it in place so old jobs aren't stuck untyped/unreadable.
        _ensure_column(cursor, "job", "created_by",
                        "created_by VARCHAR(150) NULL")
        cursor.execute("""
            SELECT DATA_TYPE FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = 'job' AND column_name = 'created_by'
        """)
        (current_type,) = cursor.fetchone()
        if current_type != "varchar":
            cursor.execute("ALTER TABLE job MODIFY COLUMN created_by VARCHAR(150) NULL")
    except Exception as e:
        print("init_admin_db migration error:", e)

    conn.commit()
    cursor.close()
    conn.close()


# =====================================================
# AUDIT LOG
# =====================================================

def log_audit(actor_username, actor_role, action, target_type="", target_id="", details=""):
    """Record an administrative action. Never store passwords, API keys,
    or full candidate PII in `details` — a short human-readable note is
    enough (e.g. 'role changed recruiter -> admin')."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO audit_logs(actor_username, actor_role, action, target_type, target_id, details)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (actor_username, actor_role, action, target_type, str(target_id), details),
        )
        conn.commit()
        ok = True
    except Exception as e:
        print("log_audit error:", e)
        ok = False
    cursor.close()
    conn.close()
    return ok


def get_audit_logs(limit=200, action_filter="All", search=""):
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if action_filter and action_filter != "All":
        query += " AND action=%s"
        params.append(action_filter)
    if search:
        query += " AND (actor_username LIKE %s OR target_type LIKE %s OR target_id LIKE %s OR details LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like, like]
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(int(limit))
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_distinct_audit_actions():
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action ASC")
    rows = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


# =====================================================
# PLATFORM SETTINGS
# =====================================================

DEFAULT_SETTINGS = {
    "app_name": "TalentOps AI",
    "default_interview_difficulty": "Medium",
    "strong_hire_threshold": "85",
    "hire_threshold": "70",
    "consider_threshold": "50",
    "pagination_limit": "25",
    "voice_screening_enabled": "true",
}


def get_settings():
    """All platform settings, falling back to DEFAULT_SETTINGS for any
    key never explicitly saved yet."""
    conn = get_connection()
    saved = {}
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setting_key, setting_value FROM platform_settings")
        for row in cursor.fetchall():
            saved[row["setting_key"]] = row["setting_value"]
        cursor.close()
        conn.close()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(saved)
    return merged


def set_setting(key, value):
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO platform_settings(setting_key, setting_value) VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)""",
            (key, str(value)),
        )
        conn.commit()
        ok = True
    except Exception as e:
        print("set_setting error:", e)
        ok = False
    cursor.close()
    conn.close()
    return ok


# =====================================================
# USER MANAGEMENT
# =====================================================

def get_all_users(role_filter="All", status_filter="All", search=""):
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, username, email, role, status, created_at FROM users WHERE 1=1"
    params = []
    if role_filter and role_filter != "All":
        query += " AND role=%s"
        params.append(role_filter.lower())
    if status_filter and status_filter != "All":
        query += " AND status=%s"
        params.append(status_filter.lower())
    if search:
        query += " AND (username LIKE %s OR email LIKE %s)"
        like = f"%{search}%"
        params += [like, like]
    query += " ORDER BY created_at DESC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_user_by_id(user_id):
    conn = get_connection()
    if conn is None:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, email, role, status, created_at FROM users WHERE id=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def count_admins():
    """Used to block an action that would leave the platform with zero
    active admin accounts."""
    conn = get_connection()
    if conn is None:
        return 0
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND status='active'")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count


def set_user_status(user_id, status):
    """status: 'active' or 'inactive'."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status=%s WHERE id=%s", (status, user_id))
        conn.commit()
        ok = True
    except Exception as e:
        print("set_user_status error:", e)
        ok = False
    cursor.close()
    conn.close()
    return ok


def set_user_role(user_id, role):
    """role: 'admin' | 'recruiter' | 'candidate'."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
        conn.commit()
        ok = True
    except Exception as e:
        print("set_user_role error:", e)
        ok = False
    cursor.close()
    conn.close()
    return ok


def delete_user_admin(user_id):
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return deleted


# =====================================================
# RECRUITER MANAGEMENT
# =====================================================

def get_recruiter_rows(search=""):
    """One row per recruiter account, enriched with jobs they've posted
    (job.created_by), candidates evaluated against those job titles (the
    schema has no direct candidate->recruiter FK, so this is the closest
    real signal — candidates.job_role is matched against the recruiter's
    own posted job titles), and interviews where interview_sessions
    .interviewer matches their username."""
    users = get_all_users(role_filter="Recruiter", search=search)
    jobs = get_jobs()
    candidates = get_candidates()
    sessions = get_sessions()

    rows = []
    for u in users:
        username = u["username"]
        my_jobs = [j for j in jobs if (j.get("created_by") or "") == username]
        my_job_titles = {j["job_title"] for j in my_jobs}
        my_candidates = [c for c in candidates if c.get("job_role") in my_job_titles]
        my_interviews = [s for s in sessions if (s.get("interviewer") or "") == username]
        rows.append({
            "id": u["id"],
            "username": username,
            "email": u["email"],
            "status": u["status"],
            "created_at": u["created_at"],
            "jobs_posted": len(my_jobs),
            "candidates_managed": len(my_candidates),
            "interviews_conducted": len(my_interviews),
        })
    return rows


# =====================================================
# JOB MANAGEMENT
# =====================================================

def set_job_status(job_id, status):
    """status: 'Active' | 'Inactive' | 'Closed'."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE job SET status=%s WHERE job_id=%s", (status, job_id))
        conn.commit()
        ok = cursor.rowcount > 0
    except Exception as e:
        print("set_job_status error:", e)
        ok = False
    cursor.close()
    conn.close()
    return ok


def job_has_activity(job_id, job_title):
    """True if deleting this job would silently orphan real records —
    candidates evaluated against it (matched by title, since candidates
    has no job_id FK) or interview sessions scheduled against its job_id.
    The Admin UI uses this to force soft-delete (Closed) instead of a
    hard DELETE whenever there's real history attached."""
    candidates = [c for c in get_candidates() if c.get("job_role") == job_title]
    sessions = [s for s in get_sessions() if s.get("job_id") == job_id]
    return bool(candidates or sessions)


def delete_job_admin(job_id):
    from database import delete_job
    return delete_job(job_id)


# =====================================================
# PLATFORM OVERVIEW / KPIs
# =====================================================

def get_platform_overview():
    users = get_all_users()
    jobs = get_jobs()
    candidates = get_candidates()
    sessions = get_sessions()

    total_recruiters = sum(1 for u in users if u["role"] == "recruiter")
    total_candidates_accts = sum(1 for u in users if u["role"] == "candidate")
    total_admins = sum(1 for u in users if u["role"] == "admin")

    active_jobs = sum(1 for j in jobs if (j.get("status") or "Active") == "Active")
    closed_jobs = sum(1 for j in jobs if (j.get("status") or "Active") in ("Closed", "Inactive"))

    completed = [s for s in sessions if s.get("status") == "Completed"]
    pending = [s for s in sessions if s.get("status") in ("Scheduled", "In Progress")]

    selected = sum(1 for c in candidates if (c.get("stage") or "") == "Selected")
    rejected = sum(1 for c in candidates if (c.get("stage") or "") == "Rejected")

    ats_scores = [c.get("ats_score") for c in candidates if c.get("ats_score") is not None]
    avg_ats = round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else 0

    interview_scores = [s.get("overall_score") for s in completed if s.get("overall_score")]
    avg_interview = round(sum(interview_scores) / len(interview_scores), 1) if interview_scores else 0

    return {
        "total_users": len(users),
        "total_recruiters": total_recruiters,
        "total_candidates": total_candidates_accts,
        "total_admins": total_admins,
        "total_jobs": len(jobs),
        "active_jobs": active_jobs,
        "closed_jobs": closed_jobs,
        "total_applications": len(candidates),
        "total_interviews": len(sessions),
        "completed_interviews": len(completed),
        "pending_interviews": len(pending),
        "selected_candidates": selected,
        "rejected_candidates": rejected,
        "average_ats_score": avg_ats,
        "average_interview_score": avg_interview,
        "average_job_match": avg_ats,  # no separate match% is persisted; ATS score is the closest real proxy
    }


# =====================================================
# ATS ANALYTICS
# =====================================================

def get_ats_analytics():
    candidates = get_candidates()
    scores = [c.get("ats_score") or 0 for c in candidates]
    if not scores:
        return {
            "average": 0, "highest": 0, "lowest": 0,
            "by_recommendation": {}, "by_range": {}, "top_skills": [], "missing_skills": [],
        }

    by_recommendation = {}
    for c in candidates:
        rec = c.get("recommendation") or "Unrated"
        by_recommendation[rec] = by_recommendation.get(rec, 0) + 1

    ranges = {"0-49": 0, "50-69": 0, "70-84": 0, "85-100": 0}
    for s in scores:
        if s < 50:
            ranges["0-49"] += 1
        elif s < 70:
            ranges["50-69"] += 1
        elif s < 85:
            ranges["70-84"] += 1
        else:
            ranges["85-100"] += 1

    from collections import Counter
    skill_counter = Counter()
    for c in candidates:
        raw = c.get("skills") or ""
        for skill in raw.split(","):
            skill = skill.strip()
            if skill:
                skill_counter[skill] += 1

    return {
        "average": round(sum(scores) / len(scores), 1),
        "highest": max(scores),
        "lowest": min(scores),
        "by_recommendation": by_recommendation,
        "by_range": ranges,
        "top_skills": skill_counter.most_common(10),
        # "Most missing" would need per-job required_skills diffed against
        # each candidate's skills — that diff already happens once, inside
        # ats_engine.calculate_ats(), per application. We don't recompute
        # it here to avoid drifting from that scoring logic; leaving this
        # empty rather than guessing keeps the section honest.
        "missing_skills": [],
    }


# =====================================================
# INTERVIEW ANALYTICS
# =====================================================

def get_interview_analytics():
    sessions = get_sessions()
    completed = [s for s in sessions if s.get("status") == "Completed"]

    if not sessions:
        return {
            "average_score": 0, "completion_rate": 0,
            "strong_hire_pct": 0, "hire_pct": 0, "consider_pct": 0, "not_recommended_pct": 0,
            "total_sessions": 0, "completed_sessions": 0,
        }

    overall_scores = [s.get("overall_score") or 0 for s in completed]
    avg_score = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0
    completion_rate = round((len(completed) / len(sessions)) * 100, 1)

    def pct(label_fragment):
        if not completed:
            return 0
        matches = sum(1 for s in completed if label_fragment.lower() in (s.get("recommendation") or "").lower())
        return round((matches / len(completed)) * 100, 1)

    return {
        "average_score": avg_score,
        "completion_rate": completion_rate,
        "strong_hire_pct": pct("strong"),
        "hire_pct": pct("hire") - pct("strong"),  # avoid double counting "Strong Hire" inside "Hire"
        "consider_pct": pct("consider"),
        "not_recommended_pct": pct("not recommend"),
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
    }


# =====================================================
# PLATFORM ANALYTICS (growth over time)
# =====================================================

def _since(range_label):
    now = datetime.now()
    return {
        "Today": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "7 Days": now - timedelta(days=7),
        "30 Days": now - timedelta(days=30),
        "90 Days": now - timedelta(days=90),
        "All Time": datetime.min,
    }.get(range_label, datetime.min)


def get_platform_growth(range_label="30 Days"):
    cutoff = _since(range_label)
    users = get_all_users()
    jobs = get_jobs()
    candidates = get_candidates()
    sessions = get_sessions()

    def after(dt):
        if dt is None:
            return False
        try:
            return dt >= cutoff
        except TypeError:
            return True  # datetime.min comparison edge case guard

    return {
        "new_recruiters": sum(1 for u in users if u["role"] == "recruiter" and after(u.get("created_at"))),
        "new_candidates": sum(1 for u in users if u["role"] == "candidate" and after(u.get("created_at"))),
        "jobs_created": sum(1 for j in jobs if after(j.get("created_at"))),
        "applications_submitted": sum(1 for c in candidates if after(c.get("created_at"))),
        "interviews_started": sum(1 for s in sessions if after(s.get("created_at"))),
        "interviews_completed": sum(1 for s in sessions if s.get("status") == "Completed" and after(s.get("created_at"))),
        "selections": sum(1 for c in candidates if (c.get("stage") or "") == "Selected" and after(c.get("updated_at"))),
        "rejections": sum(1 for c in candidates if (c.get("stage") or "") == "Rejected" and after(c.get("updated_at"))),
    }


# =====================================================
# SYSTEM HEALTH
# =====================================================

def get_system_health():
    """Checks real connectivity/config — never returns hardcoded 'OK'.
    API keys are reported as Configured/Not Configured only, never their
    actual value."""
    db_ok = get_connection() is not None

    groq_configured = bool(os.getenv("GROQ_API_KEY"))

    try:
        import resume_parser  # noqa: F401
        parser_ok = True
    except Exception:
        parser_ok = False

    ocr_ok = False
    try:
        import pytesseract  # noqa: F401
        ocr_ok = True
    except Exception:
        try:
            import easyocr  # noqa: F401
            ocr_ok = True
        except Exception:
            ocr_ok = False

    try:
        import ai_interview  # noqa: F401
        interview_engine_ok = True
    except Exception:
        interview_engine_ok = False

    required_env = ["DB_HOST", "DB_USER", "DB_NAME", "GROQ_API_KEY"]
    env_status = {var: bool(os.getenv(var)) for var in required_env}

    return {
        "database": db_ok,
        "authentication": db_ok,  # auth.py reads/writes the same DB connection
        "groq_ai": groq_configured,
        "resume_parser": parser_ok,
        "ocr": ocr_ok,
        "interview_engine": interview_engine_ok,
        "env_vars": env_status,
    }
