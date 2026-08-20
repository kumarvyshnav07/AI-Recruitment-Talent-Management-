"""
candidate_page.py
==================
Candidate-facing portal — SaaS-style dashboard with a LEFT SIDEBAR
navigation. The candidate picks one section (Overview, My Applications,
Interviews, ATS Results, Interview Reports, Messages, Profile) and only
that section renders in the main content area — nothing is stacked into
one long scrolling page.

Starting or continuing an interview from the "Interviews" section swaps
the main content area for a dedicated, focused AI Interview workspace
(two-column: progress on the left, current question + Voice/Text answer
mode on the right). Voice is a MODE inside that workspace, not its own
sidebar destination.

All data is real: every metric, card, and report traces back to
get_candidates_by_email(), the interview_db candidate helpers, or a live
job-posting lookup. Nothing here is hardcoded or invented.

Backend/database/ATS/AI logic is untouched from the previous version of
this file — this rebuild only changes how the page is organized and
rendered. The one schema change (interview_sessions.recommendation
widened from VARCHAR(50) to TEXT, in interview_db.py) exists so the
candidate's full AI interview summary — required by the Interview
Reports section — survives being re-fetched from the database instead
of only living in-memory right after the interview finishes. It's an
additive, migration-safe ALTER (existing rows are untouched), following
the same try/except pattern already used for every other column added
to these tables.

Recruiter-internal fields (recruiter_notes, internal hiring metadata)
are never imported or referenced anywhere in this file.
"""
import logging
import streamlit as st

from database import get_candidates_by_email, get_job, get_job_by_title
from ai_interview import engine
from interview_db import (
    get_answers,
    start_session,
    save_answer,
    log_skipped_question,
    finish_session,
    get_candidate_upcoming_interviews,
    get_candidate_completed_interviews,
    get_candidate_interview_stats,
)
from interview_page import MAX_QUESTIONS, _difficulty_badge
from ui import (
    metric_card, chip_list, list_card, profile_field, section_header,
    pipeline_funnel,
    SIGNAL, VERDICT, CAUTION, RISK, INK, INK_SOFT, MIST, SKY, VIOLET,
    PANEL2, LINE,
)

try:
    from ats_engine import calculate_ats
except Exception:  # pragma: no cover - defensive, ats_engine should exist
    calculate_ats = None

# ------------------------------------------------------------------
# Stage vocabulary — pipeline order matters for the funnel/donut.
# ------------------------------------------------------------------
STAGE_ORDER = ["Applied", "Screening", "Interview in progress", "Selected", "Rejected"]
STAGE_COLORS = {
    "Applied": SIGNAL,
    "Screening": CAUTION,
    "Interview in progress": SKY,
    "Selected": VERDICT,
    "Rejected": RISK,
}
STAGE_ICONS = {
    "Applied": "📝",
    "Screening": "🔍",
    "Interview in progress": "🎙️",
    "Selected": "✅",
    "Rejected": "❌",
}
ACTIVE_STAGES = ("Applied", "Screening", "Interview in progress")

# ATS weighting used by the recruiter-side engine (ats_engine.calculate_ats).
ATS_WEIGHTS = [
    ("Skills", 50), ("Experience", 20), ("Education", 10),
    ("Projects", 10), ("Certifications", 10),
]

# Left-sidebar navigation — order is the order items appear.
NAV_ITEMS = [
    ("Overview", "🏠"),
    ("My Applications", "📁"),
    ("Interviews", "🎙"),
    ("ATS Results", "🎯"),
    ("Interview Reports", "📊"),
    ("Messages", "✉"),
    ("Profile", "👤"),
]
NAV_STATE_KEY = "cand_nav_section"
ACTIVE_INTERVIEW_KEY = "cand_active_interview"


# ==================================================================
# SMALL HELPERS (unchanged from the previous version)
# ==================================================================
def _stage_badge(stage: str, size="normal"):
    stage = stage or "Applied"
    color = STAGE_COLORS.get(stage, SIGNAL)
    icon = STAGE_ICONS.get(stage, "●")
    pad = "8px 18px" if size == "normal" else "5px 12px"
    font = "14px" if size == "normal" else "12px"
    st.markdown(
        f"""
        <span style="background:{color}18; color:{color}; padding:{pad};
            border-radius:999px; font-weight:700; font-size:{font}; border:1px solid {color}44;
            display:inline-flex; align-items:center; gap:6px; white-space:nowrap;">
            {icon} {stage}
        </span>
        """,
        unsafe_allow_html=True,
    )


def _stage_badge_html(stage: str) -> str:
    stage = stage or "Applied"
    color = STAGE_COLORS.get(stage, SIGNAL)
    icon = STAGE_ICONS.get(stage, "●")
    return (
        f'<span style="background:{color}18; color:{color}; padding:5px 12px;'
        f'border-radius:999px; font-weight:700; font-size:12px; border:1px solid {color}44;'
        f'display:inline-flex; align-items:center; gap:5px; white-space:nowrap; backdrop-filter:blur(6px);">'
        f'{icon} {stage}</span>'
    )


def _fmt_dt(value, fmt="%d %b %Y"):
    if not value:
        return "—"
    try:
        return f"{value:{fmt}}"
    except (TypeError, ValueError):
        return str(value)


def _skills_list(skills_str):
    return [s.strip() for s in (skills_str or "").split(",") if s.strip()]


# ==================================================================
# VOICE ANSWER — mic capture, Whisper transcription
# ==================================================================
# Reuses the existing Groq Whisper transcription already wired up in
# ai_interview.py (engine.transcribe_audio) — no second speech-to-text
# implementation. st.audio_input is Streamlit's native browser
# microphone widget (records in-browser, returns WAV bytes).
MIN_VOICE_BYTES = 3000  # a ~WAV header plus a fraction of a second of
# audio is already a few KB; anything smaller is almost certainly a
# tap-and-release with no real speech, so we validate length BEFORE
# ever calling the transcription API.


def _transcribe_recording(audio_bytes: bytes, mime_type: str):
    """Wraps engine.transcribe_audio with graceful-degradation rules:
    never raise into the caller, always return
    (transcript_or_None, status, message_for_the_candidate)."""
    if not audio_bytes or len(audio_bytes) < MIN_VOICE_BYTES:
        return None, "failed", "That recording seems empty or very short. Please try again and speak for a few seconds."
    try:
        transcript = engine.transcribe_audio(audio_bytes, mime_type=mime_type or "audio/wav")
    except Exception as e:
        logging.getLogger(__name__).error(f"Candidate voice transcription failed: {e}")
        return None, "failed", "We couldn't transcribe that recording — the transcription service may be temporarily unavailable. Please retry or switch to typing."
    if not transcript or not transcript.strip():
        return None, "failed", "We couldn't detect any speech in that recording. Please try again, speaking a little closer to the microphone."
    return transcript.strip(), "success", None


# ==================================================================
# LEFT SIDEBAR
# ==================================================================
def _render_sidebar(display_name, email, has_applications):
    """Renders the fixed left navigation and returns the active section
    key. A strong active state is a filled ("primary") button; every
    other item is an outlined ("secondary") button — no reliance on
    hand-rolled CSS that could drift from Streamlit's own button
    styling."""
    if NAV_STATE_KEY not in st.session_state:
        st.session_state[NAV_STATE_KEY] = "Overview"

    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px; padding:6px 2px 18px 2px;">
                <div style="width:42px; height:42px; min-width:42px; border-radius:12px;
                    background:linear-gradient(135deg,{SIGNAL}30,{SIGNAL}10); display:flex;
                    align-items:center; justify-content:center; font-size:16px; font-weight:800;
                    color:{SIGNAL}; font-family:'Space Grotesk'; border:1px solid {SIGNAL}40;">
                    {(display_name or "C")[:1].upper()}
                </div>
                <div style="min-width:0;">
                    <div style="font-size:14px; font-weight:800; color:{INK}; font-family:'Space Grotesk';
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_name}</div>
                    <div style="font-size:11px; color:{MIST}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{email}</div>
                    <div style="font-size:10px; color:{SIGNAL}; font-weight:700; letter-spacing:0.4px; margin-top:2px;">CANDIDATE PORTAL</div>
                </div>
            </div>
            <hr style="margin:0 0 10px 0; border-color:{LINE};">
            """,
            unsafe_allow_html=True,
        )

        if not has_applications:
            st.caption("Navigation unlocks once your first application is on file.")

        for key, icon in NAV_ITEMS:
            active = st.session_state[NAV_STATE_KEY] == key
            if st.button(
                f"{icon}  {key}", key=f"navbtn_{key}", use_container_width=True,
                type="primary" if active else "secondary",
                disabled=not has_applications,
            ):
                st.session_state[NAV_STATE_KEY] = key
                st.session_state.pop(ACTIVE_INTERVIEW_KEY, None)
                st.rerun()

        st.markdown(f"<div style='margin-top:16px; border-top:1px solid {LINE};'></div>", unsafe_allow_html=True)
        st.write("")
        if st.button("⏻  Logout", key="navbtn_logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    return st.session_state[NAV_STATE_KEY]


# ==================================================================
# SHARED DATA LOGIC (unchanged from the previous version)
# ==================================================================
def _build_dashboard_stats(applications, status_counts, ats_stats, interview_stats):
    total = len(applications)
    active = sum(status_counts.get(s, 0) for s in ACTIVE_STAGES)
    shortlisted = sum(status_counts.get(s, 0) for s in STAGE_ORDER if s != "Applied")
    selected = status_counts.get("Selected", 0)
    rejected = status_counts.get("Rejected", 0)
    pending = total - selected - rejected
    return {
        "total_applications": total,
        "active_applications": active,
        "shortlisted": shortlisted,
        "interviews": interview_stats["total_interviews"],
        "selected": selected,
        "rejected": rejected,
        "pending_decisions": max(pending, 0),
        "average_ats": ats_stats["average"],
    }


def _build_recent_activity(applications, upcoming, completed):
    events = []
    for a in applications:
        role = a.get("job_role", "a role")
        events.append((a.get("created_at"), "📝", f"Application submitted for {role}"))
        events.append((a.get("created_at"), "🎯", f"ATS analyzed for {role} — scored {a.get('ats_score', 0)}%"))
        stage = a.get("stage") or "Applied"
        if stage != "Applied":
            events.append((a.get("updated_at"), "🔍", f"{role} application moved to {stage}"))
    for s in upcoming:
        role = s.get("job_title") or "your interview"
        if s.get("status") == "In Progress":
            events.append((s.get("created_at"), "🎙️", f"Interview for {role} is in progress"))
        else:
            events.append((s.get("created_at"), "📅", f"Interview scheduled for {role}"))
    for s in completed:
        role = s.get("job_title") or "your interview"
        events.append((s.get("created_at"), "🏁", f"Interview completed for {role} — scored {s.get('overall_score', 0)}/10"))
        if s.get("recommendation"):
            events.append((s.get("created_at"), "⚙", f"Recruiter recommendation logged for {role}"))
        if s.get("hr_reply"):
            events.append((s.get("created_at"), "📨", f"HR message received for {role}"))

    events = [e for e in events if e[0]]
    events.sort(key=lambda e: e[0], reverse=True)
    return events


def _get_ats_breakdown(cand, job):
    """Single source of truth for matched/missing/additional skills,
    shared by the My Applications detail view and the ATS Results page
    so the matching logic is never duplicated. Uses ats_engine.calculate_ats
    when available and falls back to a plain case-insensitive comparison —
    never a second scoring algorithm, just the same real inputs."""
    cand_skills = set(s.lower() for s in _skills_list(cand.get("skills", "")))
    matched, missing, additional = [], [], _skills_list(cand.get("skills", ""))
    result = None

    if job and job.get("required_skills"):
        required = _skills_list(job.get("required_skills", ""))
        required_lower = {r.lower(): r for r in required}

        if calculate_ats:
            try:
                details = {
                    "name": cand.get("name"), "email": cand.get("email"),
                    "phone": cand.get("phone"), "education": cand.get("education"),
                    "experience": cand.get("experience"), "skills": cand.get("skills") or "",
                    "certifications": _skills_list(cand.get("certifications", "")),
                    "projects": _skills_list(cand.get("projects", "")),
                }
                result = calculate_ats(
                    details, job.get("required_skills", ""),
                    job.get("experience", ""), job.get("qualification", ""),
                )
            except Exception:
                result = None

        if result and (result.get("matched_skills") or result.get("missing_skills")):
            matched = result.get("matched_skills", [])
            missing = result.get("missing_skills", [])
        else:
            matched = [required_lower[r] for r in required_lower if r in cand_skills]
            missing = [required_lower[r] for r in required_lower if r not in cand_skills]

        additional = [s for s in _skills_list(cand.get("skills", "")) if s.lower() not in required_lower]

    return {"matched": matched, "missing": missing, "additional": additional, "raw": result}


def _derive_recommendation(score):
    """A label derived transparently from the already-computed ATS
    score — not a second scoring pass. Only used when ats_engine's own
    result doesn't already carry a recommendation/confidence field."""
    score = score or 0
    if score >= 80:
        return "Strong Match", VERDICT
    if score >= 60:
        return "Good Match", SIGNAL
    if score >= 40:
        return "Fair Match", CAUTION
    return "Low Match", RISK


def _next_action(applications, upcoming, completed):
    """One clear 'what do I do next' signal, in priority order, built
    only from real statuses already fetched — nothing fabricated."""
    in_progress = [s for s in upcoming if s.get("status") == "In Progress"]
    scheduled = [s for s in upcoming if s.get("status") == "Scheduled"]
    awaiting_reply = [s for s in completed if not s.get("hr_reply")]
    screening = [a for a in applications if (a.get("stage") or "Applied") == "Screening"]

    if in_progress:
        s = in_progress[0]
        return ("🎙", "Continue your interview",
                f"You're partway through the interview for {s.get('job_title') or 'a role'}. Pick up where you left off.",
                "Continue Interview", "Interviews")
    if scheduled:
        s = scheduled[0]
        return ("📅", "Complete your interview",
                f"An interview for {s.get('job_title') or 'a role'} is scheduled and ready whenever you are.",
                "Start Interview", "Interviews")
    if screening:
        return ("🔍", "Application under screening",
                f"Your application for {screening[0].get('job_role','a role')} is being reviewed. No action needed yet.",
                None, None)
    if awaiting_reply:
        return ("⏳", "Awaiting recruiter review",
                "Your interview has been submitted and is waiting on your recruiter's decision.",
                None, None)
    if applications:
        return ("✅", "You're all caught up",
                "Nothing needs your attention right now — check back after your recruiter's next update.",
                None, None)
    return ("📝", "Get started", "Submit an application to begin.", None, None)


# ==================================================================
# OVERVIEW
# ==================================================================
def _page_overview(display_name, email, applications, status_counts, stats, upcoming, completed):
    account_badge = "🟢 Active Account" if applications else "🆕 New Account"
    st.markdown(
        f"""
        <div class="glass" style="padding:22px 26px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:14px;">
                <div>
                    <div style="font-size:24px; font-weight:800; color:{INK}; font-family:'Space Grotesk',sans-serif;">
                        Welcome back, {display_name}
                    </div>
                    <div style="color:{MIST}; font-size:13px; margin-top:4px;">
                        Track your applications, interviews and hiring progress.
                    </div>
                </div>
                <div style="padding:7px 16px; background:{PANEL2}; border:1px solid {LINE}; border-radius:999px;
                    color:{INK_SOFT}; font-weight:700; font-size:12px; white-space:nowrap;">
                    {account_badge}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ---- KPI row (compact, two rows of four) ----
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    with r1c1:
        metric_card("Total Applications", stats["total_applications"], "📁", SIGNAL)
    with r1c2:
        metric_card("Active Applications", stats["active_applications"], "⚡", SKY)
    with r1c3:
        metric_card("Shortlisted", stats["shortlisted"], "⭐", CAUTION)
    with r1c4:
        metric_card("Interviews", stats["interviews"], "🎙️", VIOLET)
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    with r2c1:
        metric_card("Selected", stats["selected"], "✅", VERDICT)
    with r2c2:
        metric_card("Rejected", stats["rejected"], "❌", RISK)
    with r2c3:
        st.empty()
    with r2c4:
        metric_card("Average ATS Score", f"{stats['average_ats']}%", "🎯", SIGNAL)
    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Next Action ----
    icon, title, subtitle, cta_label, cta_target = _next_action(applications, upcoming, completed)
    nc1, nc2 = st.columns([4, 1]) if cta_label else (st.container(), None)
    with (nc1 if cta_label else st.container()):
        st.markdown(
            f"""
            <div class="glass" style="padding:16px 20px; border-left:3px solid {SIGNAL};">
                <div style="font-size:11px; color:{MIST}; text-transform:uppercase; letter-spacing:0.5px; font-weight:700;">Next Action</div>
                <div style="font-size:15px; font-weight:800; color:{INK}; margin-top:4px;">{icon} {title}</div>
                <div style="font-size:13px; color:{INK_SOFT}; margin-top:4px;">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if cta_label:
        with nc2:
            st.write("")
            st.write("")
            if st.button(cta_label, use_container_width=True, type="primary", key="overview_next_action"):
                st.session_state[NAV_STATE_KEY] = cta_target
                st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Application Pipeline ----
    section_header("🧭", "Application Pipeline", "Applied → Screening → Interview → Selected. Rejected is shown separately.")
    applied_n = status_counts.get("Applied", 0)
    screening_n = status_counts.get("Screening", 0)
    interview_n = status_counts.get("Interview in progress", 0)
    selected_n = status_counts.get("Selected", 0)
    rejected_n = status_counts.get("Rejected", 0)
    total = stats["total_applications"]

    def _pct(n):
        return f"{round((n / total) * 100)}%" if total else "0%"

    pipeline_funnel([
        (f"Applied · {_pct(applied_n)}", applied_n, SIGNAL),
        (f"Screening · {_pct(screening_n)}", screening_n, CAUTION),
        (f"Interview · {_pct(interview_n)}", interview_n, SKY),
        (f"Selected · {_pct(selected_n)}", selected_n, VERDICT),
    ])
    if rejected_n:
        st.markdown(
            f"""
            <div class="glass" style="padding:12px 20px; border-color:{RISK}33;">
                <span style="color:{RISK}; font-weight:700;">❌ Rejected</span>
                <span style="color:{MIST}; margin-left:8px;">{rejected_n} application(s) · {_pct(rejected_n)} of total.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Recent Activity ----
    section_header("🕒", "Recent Activity", "Built from your actual application and interview timestamps.")
    activity = _build_recent_activity(applications, upcoming, completed)[:8]
    if not activity:
        st.caption("No activity recorded yet.")
    else:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        rows = ""
        for ts, icon, text in activity:
            rows += f"""
            <div class="insight-row">
                <div style="font-size:15px;">{icon}</div>
                <div style="color:{INK_SOFT};">{text}
                    <span style="color:{MIST}; font-size:11.5px; margin-left:6px;">{_fmt_dt(ts, '%d %b %Y, %I:%M %p')}</span>
                </div>
            </div>
            """
        st.markdown(rows, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ==================================================================
# MY APPLICATIONS
# ==================================================================
def _application_card_html(a, sessions_for_cand):
    role = a.get("job_role", "—")
    job = get_job_by_title(role)
    company = job["company_name"] if job else "—"
    applied = _fmt_dt(a.get("created_at"))
    updated = _fmt_dt(a.get("updated_at"))
    stage = a.get("stage") or "Applied"
    ats = a.get("ats_score") or 0

    completed = [s for s in sessions_for_cand if s.get("status") == "Completed"]
    scheduled = [s for s in sessions_for_cand if s.get("status") in ("Scheduled", "In Progress")]
    if completed:
        interview_status = f"Completed · {completed[0].get('overall_score', 0)}/10"
    elif scheduled:
        interview_status = scheduled[0].get("status", "Scheduled")
    else:
        interview_status = "Not scheduled"

    return f"""
    <div class="glass" style="padding:18px 22px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
            <div>
                <div style="font-size:16px; font-weight:800; color:{INK}; font-family:'Space Grotesk';">{role}</div>
                <div style="color:{MIST}; font-size:12.5px; margin-top:2px;">{company} &nbsp;•&nbsp; Applied {applied}</div>
            </div>
            {_stage_badge_html(stage)}
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap:14px; margin-top:14px;">
            <div><div style="color:{MIST}; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">ATS Score</div>
                <div style="color:{SIGNAL}; font-weight:800; font-size:15px; margin-top:2px;">{ats}%</div></div>
            <div><div style="color:{MIST}; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">Interview</div>
                <div style="color:{INK_SOFT}; font-weight:700; font-size:15px; margin-top:2px;">{interview_status}</div></div>
            <div><div style="color:{MIST}; font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">Last Updated</div>
                <div style="color:{INK_SOFT}; font-weight:700; font-size:15px; margin-top:2px;">{updated}</div></div>
        </div>
    </div>
    """


def _render_application_detail(cand, sessions_for_cand, on_back):
    if st.button("← Back to Applications", key="app_detail_back"):
        on_back()
        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    job = get_job_by_title(cand.get("job_role", ""))
    section_header("🔎", cand.get("job_role", "Application"), "Full ATS breakdown and skills match for this application.")

    dc1, dc2 = st.columns([3, 2])
    with dc1:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown(f"**{cand.get('job_role', '—')}**")
        if job:
            profile_field("Company", job.get("company_name", "—"), "🏢")
            profile_field("Location", job.get("location", "—"), "📍")
            profile_field("Experience Required", job.get("experience", "—"), "🧭")
            profile_field("Qualification", job.get("qualification", "—"), "🎓")
            st.markdown("**Required Skills**")
            chip_list(_skills_list(job.get("required_skills", "")), CAUTION)
        else:
            st.caption("The original job posting is no longer available — your submitted profile is still shown below.")
        profile_field("Applied On", _fmt_dt(cand.get("created_at")), "📅")
        st.markdown("**Current Hiring Stage**")
        _stage_badge(cand.get("stage") or "Applied")
        st.markdown('</div>', unsafe_allow_html=True)

    with dc2:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown("**ATS Score Breakdown**")
        metric_card("Overall ATS Score", f"{cand.get('ats_score', 0)}%", "🎯", SIGNAL)
        st.caption("Weighting used by the ATS engine:")
        legend = "".join(
            f'<div style="display:flex; justify-content:space-between; padding:4px 0; font-size:12.5px; color:{MIST};">'
            f'<span>{name}</span><span style="color:{INK_SOFT}; font-weight:700;">{weight}%</span></div>'
            for name, weight in ATS_WEIGHTS
        )
        st.markdown(legend, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("**Skills Match**")
    breakdown = _get_ats_breakdown(cand, job)
    if job and job.get("required_skills"):
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.caption("✅ Matched")
            chip_list(breakdown["matched"], VERDICT)
        with mc2:
            st.caption("⚠️ Missing")
            chip_list(breakdown["missing"], RISK)
        with mc3:
            st.caption("➕ Additional")
            chip_list(breakdown["additional"], SIGNAL)
    else:
        st.caption("Matched/missing skills need the original job posting, which isn't available for this application.")
        chip_list(breakdown["additional"], SIGNAL)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Candidate Details Submitted With This Application**")
    pc1, pc2 = st.columns(2)
    with pc1:
        profile_field("Education", cand.get("education", ""), "🎓")
        profile_field("Experience", cand.get("experience", ""), "🧭")
    with pc2:
        st.markdown("&nbsp;", unsafe_allow_html=True)
    lc1, lc2 = st.columns(2)
    with lc1:
        list_card("Certifications", _skills_list(cand.get("certifications", "")), "🎓", VERDICT)
    with lc2:
        list_card("Projects", _skills_list(cand.get("projects", "")), "🧩", SIGNAL)


def _page_applications(applications, sessions_by_candidate):
    detail_id = st.session_state.get("cand_app_detail_id")
    if detail_id is not None:
        cand = next((a for a in applications if a["id"] == detail_id), None)
        if cand is None:
            st.session_state.pop("cand_app_detail_id", None)
        else:
            _render_application_detail(
                cand, sessions_by_candidate.get(cand["id"], []),
                on_back=lambda: st.session_state.pop("cand_app_detail_id", None),
            )
            return

    section_header("📁", "My Applications", f"{len(applications)} application(s) on record.")

    fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
    with fc1:
        search = st.text_input("Search applications", placeholder="Search by job title or company...", key="app_search", label_visibility="collapsed")
    with fc2:
        status_filter = st.selectbox("Filter by status", ["All statuses"] + STAGE_ORDER, key="app_status_filter", label_visibility="collapsed")
    with fc3:
        roles = sorted({a.get("job_role", "—") for a in applications})
        role_filter = st.selectbox("Filter by job role", ["All roles"] + roles, key="app_role_filter", label_visibility="collapsed")
    with fc4:
        sort_by = st.selectbox("Sort by", ["Newest first", "Oldest first"], key="app_sort", label_visibility="collapsed")

    filtered = applications
    if search:
        needle = search.lower()
        filtered = [
            a for a in filtered
            if needle in (a.get("job_role") or "").lower()
            or needle in ((get_job_by_title(a.get("job_role", "")) or {}).get("company_name") or "").lower()
        ]
    if status_filter != "All statuses":
        filtered = [a for a in filtered if (a.get("stage") or "Applied") == status_filter]
    if role_filter != "All roles":
        filtered = [a for a in filtered if a.get("job_role") == role_filter]
    filtered = sorted(filtered, key=lambda a: a.get("created_at") or 0, reverse=(sort_by == "Newest first"))

    st.markdown("<br>", unsafe_allow_html=True)
    if not filtered:
        st.caption("No applications match these filters.")
        return

    for a in filtered:
        st.markdown(_application_card_html(a, sessions_by_candidate.get(a["id"], [])), unsafe_allow_html=True)
        bcol1, bcol2 = st.columns([5, 1])
        with bcol2:
            if st.button("View Details", key=f"view_app_{a['id']}", use_container_width=True):
                st.session_state["cand_app_detail_id"] = a["id"]
                st.rerun()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# ==================================================================
# INTERVIEWS (list / scheduling) + AI INTERVIEW WORKSPACE
# ==================================================================
def _page_interviews(applications_by_id, upcoming, completed):
    section_header("🎙", "Interviews", "Take a scheduled interview, or pick up where you left off.")

    if not upcoming:
        st.caption("No interviews scheduled right now. Your recruiter will schedule one after reviewing your application.")
    for s in upcoming:
        cand = applications_by_id.get(s["candidate_id"])
        if not cand:
            continue
        in_progress = s.get("status") == "In Progress"
        st.markdown(
            f"""
            <div class="glass" style="padding:18px 22px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                    <div>
                        <div style="font-size:16px; font-weight:800; color:{INK}; font-family:'Space Grotesk';">{s.get('job_title') or cand.get('job_role','Role')}</div>
                        <div style="color:{MIST}; font-size:12.5px; margin-top:2px;">
                            {s['interview_date']:%d %b %Y, %I:%M %p} &nbsp;•&nbsp; Interviewer: {s.get('interviewer') or 'To be confirmed'} &nbsp;•&nbsp; Difficulty: {s.get('difficulty') or '—'}
                        </div>
                    </div>
                    <span style="background:{(SIGNAL if in_progress else CAUTION)}18; color:{(SIGNAL if in_progress else CAUTION)};
                        padding:5px 12px; border-radius:999px; font-weight:700; font-size:12px; white-space:nowrap;">
                        {'In Progress' if in_progress else 'Scheduled'}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        bcol1, bcol2 = st.columns([5, 1])
        with bcol2:
            label = "Continue Interview" if in_progress else "Start Interview"
            if st.button(label, key=f"launch_iv_{s['id']}", use_container_width=True, type="primary"):
                st.session_state[ACTIVE_INTERVIEW_KEY] = {"session_id": s["id"], "candidate_id": s["candidate_id"]}
                st.rerun()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    ccol1, ccol2 = st.columns([4, 1])
    with ccol1:
        st.markdown(
            f"""
            <div class="glass" style="padding:14px 20px;">
                <span style="color:{INK_SOFT}; font-weight:700;">🏁 Completed Interviews</span>
                <span style="color:{MIST}; margin-left:8px;">{len(completed)} on record.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with ccol2:
        if completed and st.button("View Reports", use_container_width=True, key="goto_reports"):
            st.session_state[NAV_STATE_KEY] = "Interview Reports"
            st.rerun()


def _interview_progress_html(questions_asked, max_q):
    rows = ""
    for i in range(max_q):
        if i < questions_asked:
            style = f"color:{VERDICT}; font-weight:700;"
            dot = "●"
        elif i == questions_asked:
            style = f"color:{SIGNAL}; font-weight:800;"
            dot = "◉"
        else:
            style = f"color:{MIST};"
            dot = "○"
        rows += f'<div style="{style} font-size:13px; padding:4px 0;">{dot}&nbsp;&nbsp;Question {i + 1}</div>'
    return rows


def _interview_workspace(cand, session):
    session_id = session["id"]
    chat_key = f"cand_chat_{session_id}"
    eval_key = f"cand_eval_{session_id}"
    diff_key = f"cand_diff_{session_id}"
    report_key = f"cand_report_{session_id}"
    started_key = f"cand_started_{session_id}"
    skipped_key = f"cand_skipped_{session_id}"
    mode_key = f"cand_answer_mode_{session_id}"

    job = get_job(session["job_id"]) if session.get("job_id") else None
    job_role_label = job["job_title"] if job else cand.get("job_role", "the role")

    if chat_key not in st.session_state:
        skill_sample = (cand.get("skills") or "software engineering").split(",")[0].strip()
        opener_q = f"Let's start with a technical question regarding your experience with {skill_sample}."
        st.session_state[chat_key] = [{
            "role": "assistant",
            "content": f"Hello {cand.get('name', 'there')}, I'm your AI Interviewer today. {opener_q}",
            "difficulty": session.get("difficulty") or "Intermediate",
            "topic": "Opener",
        }]
    if eval_key not in st.session_state:
        st.session_state[eval_key] = []
    if diff_key not in st.session_state:
        st.session_state[diff_key] = session.get("difficulty") or "Intermediate"
    if skipped_key not in st.session_state:
        st.session_state[skipped_key] = []
    if mode_key not in st.session_state:
        st.session_state[mode_key] = "Text"

    answered_count = len(st.session_state[eval_key])
    skipped_count = len(st.session_state[skipped_key])
    questions_asked = answered_count + skipped_count
    session_full = questions_asked >= MAX_QUESTIONS

    # ---- Exit bar ----
    ex1, ex2 = st.columns([5, 1])
    with ex1:
        st.markdown(f"##### AI Interview — {job_role_label}")
    with ex2:
        if st.button("← Exit", use_container_width=True, key="iv_exit"):
            st.session_state.pop(ACTIVE_INTERVIEW_KEY, None)
            st.rerun()
    st.caption("Your progress is saved as you go — Exit and resume later with Continue Interview.")
    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1, 2])

    # ---- LEFT: progress panel ----
    with left:
        st.markdown('<div class="glass" style="padding:18px 20px;">', unsafe_allow_html=True)
        st.markdown(f"**Interview Progress**")
        st.markdown(f"<div style='color:{MIST}; font-size:12px; margin-bottom:10px;'>Question {min(questions_asked + 1, MAX_QUESTIONS)} of {MAX_QUESTIONS}</div>", unsafe_allow_html=True)
        st.markdown(_interview_progress_html(questions_asked, MAX_QUESTIONS), unsafe_allow_html=True)
        st.markdown(f"<hr style='border-color:{LINE};'>", unsafe_allow_html=True)
        profile_field("Job Title", job_role_label, "💼")
        profile_field("Difficulty", st.session_state[diff_key], "🎚️")
        profile_field("Status", session.get("status") or "Scheduled", "📶")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- RIGHT: question + answer ----
    with right:
        st.markdown('<div class="glass" style="padding:22px 24px;">', unsafe_allow_html=True)
        st.markdown(f"<div style='color:{MIST}; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700;'>AI Interviewer</div>", unsafe_allow_html=True)

        if session_full:
            st.markdown(
                f"<div style='font-size:16px; color:{INK_SOFT}; margin-top:10px;'>"
                f"That's {MAX_QUESTIONS} questions — nice work! Click <b>Finish Interview</b> below to submit your results.</div>",
                unsafe_allow_html=True,
            )
        else:
            last_assistant = next((m for m in reversed(st.session_state[chat_key]) if m["role"] == "assistant"), None)
            question_text = last_assistant["content"] if last_assistant else "…"
            question_diff = last_assistant.get("difficulty") if last_assistant else st.session_state[diff_key]
            st.markdown(
                f"<div style='font-size:19px; font-weight:700; color:{INK}; margin-top:8px; line-height:1.4;'>"
                f"{question_text} {_difficulty_badge(question_diff) if question_diff else ''}</div>",
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        def _handle_response(user_input: str, mode="text", transcript_raw=None, transcription_status=None):
            st.session_state[chat_key].append({"role": "user", "content": user_input})
            with st.spinner("Submitting your answer for AI evaluation..."):
                last_msg = next(
                    (m for m in reversed(st.session_state[chat_key][:-1]) if m["role"] == "assistant"),
                    {"content": "General Question", "difficulty": "Intermediate"},
                )
                last_q = last_msg["content"]

                eval_res = engine.evaluate_answer(last_q, user_input, job_role=job_role_label)
                st.session_state[eval_key].append({
                    "question": last_q, "answer": user_input, "evaluation": eval_res,
                    "difficulty": last_msg.get("difficulty", "Intermediate"), "mode": mode,
                })
                if not eval_res.get("ai_evaluated", True):
                    st.warning("⚠️ AI evaluation was unavailable for that answer — showing a placeholder score.")

                if not st.session_state.get(started_key):
                    start_session(session_id)
                    st.session_state[started_key] = True

                save_answer(
                    session_id, last_q, user_input, eval_res,
                    difficulty=last_msg.get("difficulty", "Intermediate"),
                    answer_mode=mode, transcript=transcript_raw, transcription_status=transcription_status,
                )

                if len(st.session_state[eval_key]) < MAX_QUESTIONS:
                    next_difficulty = engine.adapt_difficulty(st.session_state[diff_key], eval_res)
                    asked_questions = [m["content"] for m in st.session_state[chat_key] if m["role"] == "assistant"]
                    followup = engine.generate_followup_question(
                        last_q, user_input, job_role_label,
                        asked_questions=asked_questions, target_difficulty=next_difficulty,
                    )
                    st.session_state[diff_key] = followup["difficulty"]
                    st.session_state[chat_key].append({
                        "role": "assistant", "content": followup["question"],
                        "difficulty": followup["difficulty"], "topic": followup.get("topic", "General"),
                    })
                else:
                    st.session_state[chat_key].append({"role": "assistant", "content": "Interview complete."})
            st.rerun()

        def _handle_skip():
            last_msg = next(
                (m for m in reversed(st.session_state[chat_key]) if m["role"] == "assistant"),
                {"content": "General Question", "difficulty": st.session_state[diff_key]},
            )
            last_q = last_msg["content"]
            st.session_state[chat_key].append({"role": "user", "content": "(Skipped this question)"})
            st.session_state[skipped_key].append({"question": last_q, "difficulty": last_msg.get("difficulty")})

            if not st.session_state.get(started_key):
                start_session(session_id)
                st.session_state[started_key] = True
            log_skipped_question(session_id, last_q, difficulty=last_msg.get("difficulty"))

            if answered_count + skipped_count + 1 < MAX_QUESTIONS:
                asked_questions = [m["content"] for m in st.session_state[chat_key] if m["role"] == "assistant"]
                followup = engine.generate_followup_question(
                    last_q, "(The candidate chose to skip this question.)", job_role_label,
                    asked_questions=asked_questions, target_difficulty=st.session_state[diff_key],
                )
                st.session_state[chat_key].append({
                    "role": "assistant", "content": followup["question"],
                    "difficulty": followup["difficulty"], "topic": followup.get("topic", "General"),
                })
            else:
                st.session_state[chat_key].append({"role": "assistant", "content": "Interview complete."})
            st.rerun()

        if not session_full:
            _render_answer_mode(session_id, questions_asked, mode_key, _handle_response, _handle_skip)

        st.markdown("<br>", unsafe_allow_html=True)
        finish_col1, finish_col2 = st.columns([3, 1])
        with finish_col2:
            finish_clicked = st.button(
                "🏁 Finish Interview", use_container_width=True, key=f"finish_{session_id}",
                disabled=not (st.session_state[eval_key] or st.session_state[skipped_key]),
            )
        if finish_clicked:
            evaluations = [e["evaluation"] for e in st.session_state[eval_key]]
            report = engine.interview_summary(cand.get("name", "Candidate"), evaluations)
            st.session_state[report_key] = report
            # Full summary text now fits — interview_sessions.recommendation
            # was widened to TEXT in interview_db.py's migration.
            finish_session(session_id, report["overall_score"], report["final_comment"])
            st.success("Interview submitted! Your recruiter will review your results and update your hiring status.")
            st.rerun()

        if report_key in st.session_state:
            report = st.session_state[report_key]
            st.markdown("<br>", unsafe_allow_html=True)
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                metric_card("Overall Score", f"{report['overall_score']}/10", "🏁", SIGNAL)
            with rc2:
                metric_card("Questions Answered", report["questions_answered"], "❓", VERDICT)
            with rc3:
                metric_card("Questions Skipped", len(st.session_state[skipped_key]), "⏭️", CAUTION)
            if report["questions_answered"] == 0:
                st.warning("Every question was skipped, so no score could be generated for this session.")
            else:
                st.caption("Your score reflects only the questions you answered — skipped questions aren't counted against you.")
            st.info(report["final_comment"])
            if st.button("Done — Back to Interviews", use_container_width=True, key="iv_done"):
                st.session_state.pop(ACTIVE_INTERVIEW_KEY, None)
                st.rerun()


def _render_answer_mode(session_id, questions_asked, mode_key, on_submit, on_skip):
    """Voice/Text mode selector + the active mode's answer UI, per the
    AI Interview workspace spec. `on_submit(text, mode=, transcript_raw=,
    transcription_status=)` and `on_skip()` are the closures from
    _interview_workspace."""
    transcript_key = f"cand_voice_transcript_{session_id}_{questions_asked}"
    status_key = f"cand_voice_status_{session_id}_{questions_asked}"
    message_key = f"cand_voice_message_{session_id}_{questions_asked}"
    take_key = f"cand_voice_take_{session_id}_{questions_asked}"
    if take_key not in st.session_state:
        st.session_state[take_key] = 0

    mcol, scol = st.columns([3, 1])
    with mcol:
        choice = st.radio(
            "Answer method", ["🎙️ Voice", "⌨️ Text"], horizontal=True,
            key=f"mode_radio_{session_id}_{questions_asked}",
            index=0 if st.session_state[mode_key] == "Voice" else 1,
            label_visibility="collapsed",
        )
        st.session_state[mode_key] = "Voice" if "Voice" in choice else "Text"
    with scol:
        skip_clicked = st.button(
            "⏭️ Skip", use_container_width=True, key=f"skip_{session_id}_{questions_asked}",
            help="Skip this question — it won't count against your score.",
        )
    if skip_clicked:
        on_skip()
        return

    # -------- TEXT MODE --------
    if st.session_state[mode_key] == "Text":
        text_key = f"cand_text_answer_{session_id}_{questions_asked}"
        answer = st.text_area("Type your answer...", key=text_key, height=120, label_visibility="collapsed", placeholder="Type your answer...")
        submit_clicked = st.button(
            "✅ Submit Answer", type="primary", use_container_width=True,
            key=f"text_submit_{session_id}_{questions_asked}", disabled=not answer.strip(),
        )
        if submit_clicked:
            on_submit(answer.strip(), mode="text")
        return

    # -------- VOICE MODE --------
    if not hasattr(st, "audio_input"):
        st.warning("Voice recording isn't available in this version of Streamlit — please use Text instead.")
        return

    st.caption("🎙 Answer using your microphone — tap the recorder to start, tap again to stop.")
    audio_value = st.audio_input(
        "Record your answer", key=f"audio_{session_id}_{questions_asked}_{st.session_state[take_key]}",
        label_visibility="collapsed",
    )
    st.caption("Trouble with the recorder or your microphone? Switch to Text above at any time.")

    if audio_value is None:
        if status_key in st.session_state:
            st.session_state.pop(status_key, None)
            st.session_state.pop(transcript_key, None)
            st.session_state.pop(message_key, None)
        return

    audio_bytes = audio_value.getvalue()

    # Already transcribed this take -> show result / retry UI.
    if status_key in st.session_state:
        status = st.session_state.get(status_key)
        if status == "failed":
            st.error(st.session_state.get(message_key) or "Voice transcription failed. You can retry or continue using text.")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("🔁 Retry", use_container_width=True, key=f"retry_{session_id}_{questions_asked}"):
                    st.session_state.pop(status_key, None)
                    st.session_state.pop(transcript_key, None)
                    st.session_state.pop(message_key, None)
                    st.rerun()
            with rc2:
                if st.button("⌨️ Switch to Text", use_container_width=True, key=f"switchtext_{session_id}_{questions_asked}"):
                    st.session_state[mode_key] = "Text"
                    st.session_state[take_key] += 1
                    st.session_state.pop(status_key, None)
                    st.session_state.pop(transcript_key, None)
                    st.session_state.pop(message_key, None)
                    st.rerun()
            return

        # success — editable transcript
        raw_transcript = st.session_state.get(transcript_key) or ""
        st.success("Transcribed — review and edit your answer below before submitting.")
        edited = st.text_area(
            "Your transcript", value=raw_transcript,
            key=f"voice_edit_{session_id}_{questions_asked}", height=110,
        )
        vc1, vc2 = st.columns(2)
        with vc1:
            rerecord_clicked = st.button("🔁 Re-record", use_container_width=True, key=f"voice_rerecord_{session_id}_{questions_asked}")
        with vc2:
            submit_clicked = st.button(
                "✅ Submit Answer", type="primary", use_container_width=True,
                key=f"voice_submit_{session_id}_{questions_asked}", disabled=not edited.strip(),
            )
        if submit_clicked:
            on_submit(edited.strip(), mode="voice", transcript_raw=raw_transcript, transcription_status="success")
        elif rerecord_clicked:
            st.session_state[take_key] += 1
            st.session_state.pop(status_key, None)
            st.session_state.pop(transcript_key, None)
            st.session_state.pop(message_key, None)
            st.rerun()
        return

    # Recorded, not yet transcribed — validate length before allowing the API call.
    too_short = len(audio_bytes) < MIN_VOICE_BYTES
    if too_short:
        st.warning("That recording seems empty or very short — please re-record and speak for a few seconds before transcribing.")
    rc1, rc2 = st.columns(2)
    with rc1:
        rerecord_clicked = st.button("🔁 Re-record", use_container_width=True, key=f"voice_prererecord_{session_id}_{questions_asked}")
    with rc2:
        transcribe_clicked = st.button(
            "📝 Transcribe Answer", type="primary", use_container_width=True,
            key=f"transcribe_{session_id}_{questions_asked}", disabled=too_short,
        )
    if transcribe_clicked:
        with st.spinner("Transcribing your answer..."):
            transcript, status, message = _transcribe_recording(audio_bytes, audio_value.type)
        st.session_state[status_key] = status
        st.session_state[transcript_key] = transcript
        st.session_state[message_key] = message
        st.rerun()
    elif rerecord_clicked:
        st.session_state[take_key] += 1
        st.rerun()


# ==================================================================
# ATS RESULTS
# ==================================================================
def _page_ats_results(applications):
    section_header("🎯", "ATS Results", "How strongly your resume matched each role you applied to.")

    labels = [f"{a.get('job_role', 'Role')} — Applied {_fmt_dt(a.get('created_at'))}" for a in applications]
    idx = st.selectbox("Application", range(len(applications)), format_func=lambda i: labels[i], label_visibility="collapsed") if len(applications) > 1 else 0
    cand = applications[idx]
    job = get_job_by_title(cand.get("job_role", ""))
    breakdown = _get_ats_breakdown(cand, job)
    score = cand.get("ats_score") or 0

    st.markdown("<br>", unsafe_allow_html=True)
    top1, top2 = st.columns([1, 2])
    with top1:
        metric_card("Overall ATS Score", f"{score}%", "🎯", SIGNAL)
    with top2:
        raw = breakdown["raw"] or {}
        rec_label, rec_color = (raw.get("recommendation"), None) if raw.get("recommendation") else _derive_recommendation(score)
        conf_label = raw.get("confidence") if raw and raw.get("confidence") else None
        st.markdown('<div class="glass" style="padding:16px 20px; height:100%;">', unsafe_allow_html=True)
        st.markdown(f"<div style='color:{MIST}; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700;'>Recommendation</div>", unsafe_allow_html=True)
        color = rec_color or SIGNAL
        st.markdown(f"<div style='font-size:16px; font-weight:800; color:{color}; margin-top:4px;'>{rec_label}</div>", unsafe_allow_html=True)
        if conf_label:
            st.markdown(f"<div style='color:{MIST}; font-size:12px; margin-top:6px;'>Confidence: <b style=\"color:{INK_SOFT}\">{conf_label}</b></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Score Breakdown**")
    st.markdown('<div class="glass" style="padding:16px 20px;">', unsafe_allow_html=True)
    raw = breakdown["raw"] or {}
    category_keys = {
        "Skills": ("skills_score", "skill_score"),
        "Experience": ("experience_score",),
        "Education": ("education_score",),
        "Projects": ("projects_score", "project_score"),
        "Certifications": ("certifications_score", "certification_score"),
    }
    for name, weight in ATS_WEIGHTS:
        cat_score = None
        for k in category_keys.get(name, ()):
            if raw.get(k) is not None:
                cat_score = raw.get(k)
                break
        row_val = f"{cat_score}%" if cat_score is not None else f"{weight}% weight"
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; padding:6px 0; font-size:13px; color:{MIST}; '
            f'border-bottom:1px solid {LINE};"><span>{name}</span><span style="color:{INK_SOFT}; font-weight:700;">{row_val}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
    if not any(raw.get(k) is not None for keys in category_keys.values() for k in keys):
        st.caption("Per-category scores aren't exposed by the ATS engine's current return value — showing the weighting used instead of the overall score.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Skills Match**")
    if job and job.get("required_skills"):
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.caption("✅ Matched")
            chip_list(breakdown["matched"], VERDICT)
        with mc2:
            st.caption("⚠️ Missing")
            chip_list(breakdown["missing"], RISK)
        with mc3:
            st.caption("➕ Additional")
            chip_list(breakdown["additional"], SIGNAL)
    else:
        st.caption("The original job posting isn't available for this application.")
        chip_list(breakdown["additional"], SIGNAL)


# ==================================================================
# INTERVIEW REPORTS
# ==================================================================
def _page_interview_reports(applications_by_id, completed):
    section_header("📊", "Interview Reports", "Your completed interviews and full AI-scored feedback.")
    if not completed:
        st.caption("No completed interviews yet. Results and feedback will appear here once you finish one.")
        return

    for s in completed:
        role = s.get("job_title") or "Interview"
        label = f"{role} — {_fmt_dt(s.get('interview_date'))} — {s.get('overall_score', 0)}/10"
        with st.expander(label):
            answers = get_answers(s["id"])
            scored = [a for a in answers if not a.get("skipped")]

            def _avg(field):
                vals = [a.get(field) for a in scored if a.get(field) is not None]
                return round(sum(vals) / len(vals), 1) if vals else 0

            rc1, rc2, rc3, rc4, rc5 = st.columns(5)
            with rc1:
                metric_card("Overall", f"{s.get('overall_score', 0)}/10", "🏁", SIGNAL)
            with rc2:
                metric_card("Technical", f"{_avg('technical_score')}/10", "🧠", SKY)
            with rc3:
                metric_card("Communication", f"{_avg('communication_score')}/10", "💬", VERDICT)
            with rc4:
                metric_card("Confidence", f"{_avg('confidence_score')}/10", "🎯", CAUTION)
            with rc5:
                metric_card("Problem Solving", f"{_avg('problem_solving_score')}/10", "🧩", VIOLET)

            if s.get("recommendation"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Final AI Interview Summary**")
                st.info(s["recommendation"])

            if s.get("hr_reply"):
                st.markdown("**Message from your Recruiter**")
                st.markdown(
                    f"""<div class="glass" style="padding:14px 18px; border-left:3px solid {VERDICT};">
                        <div style="color:{INK_SOFT}; font-size:14px;">{s['hr_reply']}</div></div>""",
                    unsafe_allow_html=True,
                )

            if answers:
                st.markdown("<br>", unsafe_allow_html=True)
                skipped_n = sum(1 for a in answers if a.get("skipped"))
                header = "**Question-by-Question Results**"
                if skipped_n:
                    header += f" <span style='color:{MIST}; font-weight:400; font-size:12px;'>({skipped_n} skipped)</span>"
                st.markdown(header, unsafe_allow_html=True)
                for a in answers:
                    mode_tag = "🎙️ VOICE" if a.get("answer_mode") == "voice" else "⌨️ TEXT"
                    st.markdown(
                        f"**Q:** {a['question']} "
                        f"<span style='background:{PANEL2}; color:{INK_SOFT}; padding:2px 8px; border-radius:999px; "
                        f"font-size:10px; font-weight:700; margin-left:6px;'>{mode_tag}</span>",
                        unsafe_allow_html=True,
                    )
                    if a.get("skipped"):
                        st.caption("⏭️ Skipped — not counted toward the score.")
                    else:
                        st.write(f"**A:** {a.get('answer', '')}")
                        if a.get("strengths"):
                            st.success(f"Strengths: {a['strengths']}")
                        if a.get("weaknesses"):
                            st.warning(f"Areas to improve: {a['weaknesses']}")
                        if a.get("suggestion"):
                            st.info(f"Improvement: {a['suggestion']}")
                    st.markdown("---")


# ==================================================================
# MESSAGES
# ==================================================================
def _page_messages(completed):
    section_header("✉", "Messages", "Replies your recruiter has sent about a completed interview.")
    replies = [s for s in completed if s.get("hr_reply")]
    if not replies:
        st.caption("No recruiter messages yet.")
        return
    for s in replies:
        role = s.get("job_title") or "Interview"
        st.markdown(
            f"""
            <div class="glass" style="padding:18px 22px; border-left:3px solid {VERDICT};">
                <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                    <div style="font-weight:800; color:{INK}; font-family:'Space Grotesk';">{role}</div>
                    <div style="color:{MIST}; font-size:12px;">{_fmt_dt(s.get('created_at'))} · Score: {s.get('overall_score', 0)}/10</div>
                </div>
                <div style="margin-top:10px; color:{INK_SOFT}; font-size:14px; line-height:1.5;">{s['hr_reply']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# ==================================================================
# PROFILE
# ==================================================================
def _page_profile(applications):
    section_header("👤", "Profile", "Parsed from the resume submitted with your application. Read-only.")

    if len(applications) > 1:
        labels = [f"{a.get('job_role', 'Role')} — Applied {_fmt_dt(a.get('created_at'))}" for a in applications]
        idx = st.selectbox("Application on file for", range(len(applications)), format_func=lambda i: labels[i])
    else:
        idx = 0
    cand = applications[idx]

    st.markdown('<div class="glass">', unsafe_allow_html=True)
    pc1, pc2 = st.columns(2)
    with pc1:
        profile_field("Candidate Name", cand.get("name", ""), "👤")
        profile_field("Email", cand.get("email", ""), "✉")
        profile_field("Phone", cand.get("phone", ""), "📞")
    with pc2:
        profile_field("Education", cand.get("education", ""), "🎓")
        profile_field("Experience", cand.get("experience", ""), "🧭")
    st.markdown("**Core Skills**")
    chip_list(_skills_list(cand.get("skills", "")), SIGNAL)
    lc1, lc2 = st.columns(2)
    with lc1:
        list_card("Certifications", _skills_list(cand.get("certifications", "")), "🎓", VERDICT)
    with lc2:
        list_card("Projects", _skills_list(cand.get("projects", "")), "🧩", SIGNAL)
    st.markdown('</div>', unsafe_allow_html=True)


def _render_empty_state():
    st.markdown(
        f"""
        <div class="glass" style="padding:44px 32px; text-align:center;">
            <div style="font-size:15px; font-weight:800; color:{INK}; font-family:'Space Grotesk';">
                Your hiring journey starts here.
            </div>
            <div style="color:{MIST}; font-size:14px; margin-top:10px; max-width:480px; margin-left:auto; margin-right:auto;">
                You haven't submitted an application yet. Once your resume is processed against
                a job posting, your dashboard will appear here.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==================================================================
# MAIN ENTRY POINT
# ==================================================================
def render_candidate_dashboard(user: dict):
    email = user.get("email", "")
    applications = get_candidates_by_email(email)

    display_name = applications[0].get("name") if applications else None
    display_name = display_name or user.get("username", "Candidate")

    active_section = _render_sidebar(display_name, email, bool(applications))

    if not applications:
        _render_empty_state()
        return

    # ------------------------------------------------------------
    # Fetch everything once per render.
    # ------------------------------------------------------------
    candidate_ids = [a["id"] for a in applications]
    applications_by_id = {a["id"]: a for a in applications}

    status_counts = {label: 0 for label in STAGE_ORDER}
    for a in applications:
        stage = a.get("stage") or "Applied"
        status_counts[stage] = status_counts.get(stage, 0) + 1

    ats_values = [a.get("ats_score") or 0 for a in applications]
    ats_stats = {
        "average": round(sum(ats_values) / len(ats_values), 1) if ats_values else 0,
        "highest": max(ats_values) if ats_values else 0,
        "lowest": min(ats_values) if ats_values else 0,
        "scores": [{"job_role": a.get("job_role", "—"), "score": a.get("ats_score") or 0} for a in applications],
    }

    upcoming = get_candidate_upcoming_interviews(candidate_ids)
    completed = get_candidate_completed_interviews(candidate_ids)
    interview_stats = get_candidate_interview_stats(candidate_ids)

    sessions_by_candidate = {}
    for s in upcoming + completed:
        sessions_by_candidate.setdefault(s["candidate_id"], []).append(s)

    stats = _build_dashboard_stats(applications, status_counts, ats_stats, interview_stats)

    # ------------------------------------------------------------
    # Focused AI Interview workspace takes over the main content area
    # entirely when active — never shown stacked under other sections.
    # ------------------------------------------------------------
    active_interview = st.session_state.get(ACTIVE_INTERVIEW_KEY)
    if active_interview and active_section == "Interviews":
        cand = applications_by_id.get(active_interview["candidate_id"])
        session = next(
            (s for s in upcoming if s["id"] == active_interview["session_id"]),
            None,
        )
        if cand and session:
            _interview_workspace(cand, session)
            return
        st.session_state.pop(ACTIVE_INTERVIEW_KEY, None)

    # ------------------------------------------------------------
    # Route to exactly one section.
    # ------------------------------------------------------------
    if active_section == "Overview":
        _page_overview(display_name, email, applications, status_counts, stats, upcoming, completed)
    elif active_section == "My Applications":
        _page_applications(applications, sessions_by_candidate)
    elif active_section == "Interviews":
        _page_interviews(applications_by_id, upcoming, completed)
    elif active_section == "ATS Results":
        _page_ats_results(applications)
    elif active_section == "Interview Reports":
        _page_interview_reports(applications_by_id, completed)
    elif active_section == "Messages":
        _page_messages(completed)
    elif active_section == "Profile":
        _page_profile(applications)
