"""
interview_db.py
================
Persistence for Milestone 3:
  - interview_sessions / interview_answers: a real, durable record of
    every AI interview run (Module 3's "generate an interview
    performance report" + "display interview summary in the recruiter
    dashboard" - these need to survive a page refresh, not just live in
    Streamlit session state).
  - candidates.stage / candidates.recruiter_notes: Module 2's pipeline
    tracking and recruiter feedback.

Every function here returns a safe default (None / [] / False) on a
connection failure instead of raising, matching database.py's style -
a dropped DB connection should degrade the UI, not crash the app.
"""
from datetime import datetime
from database import get_db_connection

# Reuse database.py's single connection function (aliased so the rest
# of this file — which already calls get_connection() everywhere —
# doesn't need to change). No more duplicate mysql.connector.connect(
# **DB_CONFIG) block living separately in this module.
get_connection = get_db_connection


def init_interview_db():
    conn = get_connection()
    if conn is None:
        return
    cursor = conn.cursor()

    # Session table - one row per completed/in-progress interview
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_sessions(
        id INT AUTO_INCREMENT PRIMARY KEY,
        candidate_id INT,
        job_id INT,
        interviewer VARCHAR(100),
        difficulty VARCHAR(30),
        interview_date DATETIME,
        overall_score FLOAT DEFAULT 0,
        recommendation VARCHAR(50),
        status VARCHAR(30) DEFAULT 'Scheduled',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Answer log - one row per question asked within a session
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_answers(
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id INT,
        question TEXT,
        answer LONGTEXT,
        technical_score FLOAT,
        communication_score FLOAT,
        confidence_score FLOAT,
        problem_solving_score FLOAT,
        difficulty VARCHAR(30),
        strengths LONGTEXT,
        weaknesses LONGTEXT,
        suggestion LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Pipeline / recruiter-feedback columns on candidates (Module 2)
    try:
        cursor.execute("ALTER TABLE candidates ADD COLUMN stage VARCHAR(50) DEFAULT 'Applied'")
    except Exception:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE candidates ADD COLUMN recruiter_notes TEXT")
    except Exception:
        pass  # Column already exists

    # 'status' was added after some deployments may already have the
    # table from an earlier version of this app - add it defensively too.
    try:
        cursor.execute("ALTER TABLE interview_sessions ADD COLUMN status VARCHAR(30) DEFAULT 'Scheduled'")
    except Exception:
        pass

    # HR reply — a message the recruiter sends to the candidate about a
    # completed interview (distinct from recruiter_notes, which stays
    # internal). Shown on the candidate's own dashboard once set.
    try:
        cursor.execute("ALTER TABLE interview_sessions ADD COLUMN hr_reply TEXT")
    except Exception:
        pass

    # Adaptive-difficulty + full scoring columns - added after some
    # deployments may already have the table from an earlier version.
    for ddl in (
        "ALTER TABLE interview_answers ADD COLUMN problem_solving_score FLOAT",
        "ALTER TABLE interview_answers ADD COLUMN difficulty VARCHAR(30)",
        # Lets a candidate skip a question instead of being forced to answer
        # every one. Skipped turns are logged (so the recruiter can see a
        # question was skipped, not silently dropped) but carry NULL scores
        # so they never get pulled into the score averages in
        # interview_summary() — the rating reflects only what was answered.
        "ALTER TABLE interview_answers ADD COLUMN skipped BOOLEAN DEFAULT FALSE",
        # Voice screening (Milestone 4, Module 2). `answer_mode` records
        # whether the candidate typed or spoke this turn ('text'/'voice'),
        # `transcript` holds the Whisper-generated text for a voice turn
        # (kept separate from `answer` so a future edit-before-submit flow
        # can diff what was transcribed vs. what was actually scored —
        # today they're the same string), and `transcription_status`
        # records whether that transcription succeeded ('success',
        # 'failed', or NULL for text answers, which never call Whisper).
        # Defaulting answer_mode to 'text' keeps every row inserted by the
        # pre-Milestone-4 code path (and any other existing installation)
        # correctly labeled without a backfill.
        "ALTER TABLE interview_answers ADD COLUMN answer_mode VARCHAR(10) DEFAULT 'text'",
        "ALTER TABLE interview_answers ADD COLUMN transcript LONGTEXT",
        "ALTER TABLE interview_answers ADD COLUMN transcription_status VARCHAR(20)",
        # Widened from VARCHAR(50) so the candidate's full AI interview
        # summary (Interview Reports section of the candidate portal)
        # survives being re-fetched from the database, not just shown
        # once right after the interview finishes. Existing rows keep
        # their (already-truncated) text unchanged; only new sessions
        # benefit from the extra room.
        "ALTER TABLE interview_sessions MODIFY COLUMN recommendation TEXT",
    ):
        try:
            cursor.execute(ddl)
        except Exception:
            pass  # Column already exists

    conn.commit()
    cursor.close()
    conn.close()


# =====================================================
# MODULE 2: PIPELINE / RECRUITER FEEDBACK
# =====================================================

def update_candidate_stage(candidate_id: int, stage: str) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE candidates SET stage=%s WHERE id=%s", (stage, candidate_id))
        conn.commit()
        # rowcount reflects *changed* rows for UPDATE (MySQL default), so
        # re-saving the same value would look like "0 rows updated" even
        # though the query succeeded — treat "no exception" as success.
        updated = True
    except Exception as e:
        print("update_candidate_stage error:", e)
        updated = False
    cursor.close()
    conn.close()
    return updated


def update_recruiter_notes(candidate_id: int, notes: str) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE candidates SET recruiter_notes=%s WHERE id=%s", (notes, candidate_id))
        conn.commit()
        updated = True
    except Exception as e:
        print("update_recruiter_notes error:", e)
        updated = False
    cursor.close()
    conn.close()
    return updated


# =====================================================
# MODULE 3: INTERVIEW SESSIONS & PERFORMANCE REPORTS
# =====================================================

def create_session(candidate_id, job_id, interviewer, difficulty, interview_date=None, status="In Progress"):
    """Start (or schedule) an interview session. Pass a future
    interview_date to schedule ahead; omit it to log a session starting
    now. Returns the new session_id, or None on failure."""
    conn = get_connection()
    if conn is None:
        return None
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO interview_sessions(candidate_id, job_id, interviewer, difficulty, interview_date, status)
    VALUES(%s, %s, %s, %s, %s, %s)
    """, (candidate_id, job_id, interviewer, difficulty, interview_date or datetime.now(), status))
    conn.commit()
    session_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return session_id


def save_answer(session_id, question, answer, result, difficulty=None,
                 answer_mode="text", transcript=None, transcription_status=None):
    """Log one evaluated Q&A turn against a session. `result` is the
    dict returned by ai_interview.engine.evaluate_answer(). `difficulty`
    is the adaptive difficulty level that question was pitched at, so the
    persisted history can chart difficulty progression, not just scores.

    `answer_mode` is 'text' or 'voice'. For a voice turn, `answer` is the
    (possibly candidate-edited) final text that was actually scored,
    `transcript` is the raw Whisper output before any edits, and
    `transcription_status` is 'success' or 'failed'. All three default
    to plain-text values so every existing call site (text-only answers)
    keeps working unchanged."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO interview_answers(session_id, question, answer, technical_score, communication_score, confidence_score, problem_solving_score, difficulty, strengths, weaknesses, suggestion, answer_mode, transcript, transcription_status)
    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        session_id, question, answer,
        result.get("technical_score", 0),
        result.get("communication_score", 0),
        result.get("confidence_score", 0),
        result.get("problem_solving_score", 0),
        difficulty,
        ", ".join(result.get("strengths", []) or []),
        ", ".join(result.get("weaknesses", []) or []),
        ", ".join(result.get("improvement", []) or []),
        answer_mode or "text", transcript, transcription_status,
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return True


def log_skipped_question(session_id, question, difficulty=None):
    """Log a question the candidate chose to skip instead of answer.
    Stored with NULL scores and skipped=True so it shows up in the
    recruiter's Q&A history ("skipped", not silently missing) but is
    excluded from every score average — interview_summary() only ever
    sees the evaluations list, which skipped turns never join."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO interview_answers(session_id, question, answer, difficulty, skipped)
    VALUES(%s, %s, %s, %s, TRUE)
    """, (session_id, question, "(Skipped by candidate)", difficulty))
    conn.commit()
    cursor.close()
    conn.close()
    return True


def start_session(session_id):
    """Flip a Scheduled session to In Progress the moment the candidate
    submits their first answer, so the recruiter can see it's underway."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interview_sessions SET status='In Progress' WHERE id=%s AND status='Scheduled'",
        (session_id,),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return updated


def finish_session(session_id, score, recommendation, status="Completed"):
    """Close out a session with its final aggregate score (from
    engine.interview_summary()'s "overall_score") and a recommendation
    label. Returns True unless the DB connection/query actually failed."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE interview_sessions SET overall_score=%s, recommendation=%s, status=%s WHERE id=%s
        """, (score, recommendation, status, session_id))
        conn.commit()
        updated = True
    except Exception as e:
        print("finish_session error:", e)
        updated = False
    cursor.close()
    conn.close()
    return updated


def get_sessions():
    """All interview sessions, most recent first."""
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM interview_sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def update_hr_reply(session_id, message):
    """Save (or clear) the recruiter's message to the candidate about this
    completed interview. Visible on the candidate's own dashboard —
    separate from recruiter_notes, which stays internal. Returns True
    unless the DB connection/query actually failed (re-saving the same
    text is still a success, not a failure)."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE interview_sessions SET hr_reply=%s WHERE id=%s",
            (message, session_id),
        )
        conn.commit()
        updated = True
    except Exception as e:
        print("update_hr_reply error:", e)
        updated = False
    cursor.close()
    conn.close()
    return updated


def delete_session(session_id):
    """Remove a scheduled/in-progress interview outright (e.g. recruiter
    cancels it). Also clears its logged answers so nothing orphaned is
    left behind."""
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interview_answers WHERE session_id=%s", (session_id,))
    cursor.execute("DELETE FROM interview_sessions WHERE id=%s", (session_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return deleted


def get_sessions_for_candidate(candidate_id):
    """Every session run against one candidate, most recent first - the
    persisted history behind the "Interview Summary" view in Module 3."""
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM interview_sessions WHERE candidate_id=%s ORDER BY created_at DESC",
        (candidate_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_answers(session_id):
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM interview_answers WHERE session_id=%s ORDER BY id ASC",
        (session_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# =====================================================
# CANDIDATE PORTAL — INTERVIEWS ACROSS ALL APPLICATIONS
# =====================================================
# A candidate can have multiple applications (one candidates.id per
# job_role), and interview_sessions.candidate_id points at that
# per-application id — so "all of this candidate's interviews" means
# every session across *all* of their candidate ids, not just one.
# Each helper takes that list once and returns a safe default
# ([] / a zeroed stats dict) for an empty list or a dropped connection,
# so candidate_page.py never has to branch on "no applications yet".

def _in_clause(candidate_ids):
    ids = [i for i in (candidate_ids or []) if i is not None]
    if not ids:
        return None, []
    placeholders = ", ".join(["%s"] * len(ids))
    return placeholders, ids


def get_candidate_upcoming_interviews(candidate_ids):
    """Scheduled or in-progress sessions across every application this
    candidate owns, soonest first, each carrying job_title/company_name
    so the UI doesn't need a second lookup per row."""
    placeholders, ids = _in_clause(candidate_ids)
    if not ids:
        return []
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT s.*, j.job_title, j.company_name
        FROM interview_sessions s
        LEFT JOIN job j ON j.job_id = s.job_id
        WHERE s.candidate_id IN ({placeholders}) AND s.status IN ('Scheduled', 'In Progress')
        ORDER BY s.interview_date ASC
    """, tuple(ids))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_candidate_completed_interviews(candidate_ids):
    """Completed sessions across every application this candidate owns,
    most recent first, each carrying job_title/company_name."""
    placeholders, ids = _in_clause(candidate_ids)
    if not ids:
        return []
    conn = get_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT s.*, j.job_title, j.company_name
        FROM interview_sessions s
        LEFT JOIN job j ON j.job_id = s.job_id
        WHERE s.candidate_id IN ({placeholders}) AND s.status = 'Completed'
        ORDER BY s.interview_date DESC, s.created_at DESC
    """, tuple(ids))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_candidate_interview_stats(candidate_ids):
    """Aggregate interview performance across every application this
    candidate owns: totals, completion, best/average score, and how
    many questions were answered vs. skipped. Scores only ever come
    from Completed sessions — Scheduled/In Progress rows keep the
    default overall_score of 0, which would otherwise drag the average
    down and misrepresent performance."""
    placeholders, ids = _in_clause(candidate_ids)
    empty = {
        "total_interviews": 0, "completed_interviews": 0,
        "average_score": 0, "best_score": 0,
        "questions_answered": 0, "questions_skipped": 0,
    }
    if not ids:
        return empty
    conn = get_connection()
    if conn is None:
        return empty
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        f"SELECT COUNT(*) total FROM interview_sessions WHERE candidate_id IN ({placeholders})",
        tuple(ids),
    )
    total_interviews = cursor.fetchone()["total"]

    cursor.execute(
        f"""SELECT COUNT(*) completed, AVG(overall_score) avg_score, MAX(overall_score) best_score
            FROM interview_sessions
            WHERE candidate_id IN ({placeholders}) AND status='Completed'""",
        tuple(ids),
    )
    row = cursor.fetchone()
    completed = row["completed"] or 0
    avg_score = round(row["avg_score"], 1) if row["avg_score"] else 0
    best_score = round(row["best_score"], 1) if row["best_score"] else 0

    cursor.execute(
        f"""SELECT
                SUM(CASE WHEN a.skipped=0 OR a.skipped IS NULL THEN 1 ELSE 0 END) answered,
                SUM(CASE WHEN a.skipped=1 THEN 1 ELSE 0 END) skipped
            FROM interview_answers a
            JOIN interview_sessions s ON s.id = a.session_id
            WHERE s.candidate_id IN ({placeholders})""",
        tuple(ids),
    )
    qrow = cursor.fetchone()

    cursor.close()
    conn.close()
    return {
        "total_interviews": total_interviews,
        "completed_interviews": completed,
        "average_score": avg_score,
        "best_score": best_score,
        "questions_answered": qrow["answered"] or 0,
        "questions_skipped": qrow["skipped"] or 0,
    }


def get_session_report(session_id):
    """Convenience combo: one session row + its full list of answers, in
    a single call - exactly what a 'view past interview report' screen
    needs."""
    conn = get_connection()
    if conn is None:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM interview_sessions WHERE id=%s", (session_id,))
    session = cursor.fetchone()
    cursor.close()
    conn.close()
    if session is None:
        return None
    return {"session": session, "answers": get_answers(session_id)}
