import streamlit as st
from datetime import datetime
import textwrap

# ===============================
# PROJECT MODULES
# ===============================
from auth import (
    login,
    register
)

from database import init_db

from candidate_page import render_candidate_dashboard
from recruiter_page import render_recruiter_dashboard
from admin_page import render_admin_dashboard
from interview_db import init_interview_db
from admin_db import init_admin_db
from ui import (
    load_css,
    sidebar_logo,
    sidebar_session,
    theme_toggle,
    footer,
    INK,
    MIST,
)

# ===============================
# PAGE CONFIGURATION
# ===============================

st.set_page_config(
    page_title="AI Recruitment Copilot",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# INITIALIZE DATABASE
# ===============================

init_db()
init_interview_db()  # runs the interview_sessions/interview_answers schema
                      # migrations (incl. the "skipped" column) at startup,
                      # so it's ready regardless of which page loads first —
                      # it used to only run when a recruiter opened the
                      # Interview Workspace page, which left candidate-only
                      # sessions hitting a missing-column error.
init_admin_db()       # audit_logs / platform_settings tables for the Admin
                      # Control Center — same "run at startup regardless of
                      # which page loads first" reasoning as above.

# ===============================
# SESSION VARIABLES
# ===============================

DEFAULT_SESSION = {
    "logged_in": False,
    "username": "",
    "user_email": "",
    "role": None,
    "portal_mode": None,
    "theme": "light",
    "page": "Dashboard",
    "selected_candidate": None,
    "refresh": False,
    "resume_file_key": None,
    "parsed_details": None,
    "resume_filename": None,
    "ats_result": None,
    "recommendation": None,
    "job_role": "",
    "viewing_job_candidates": None,
    "editing_job": None,
    "replacing_job": None,
    "bulk_results": None,
    "replacing_candidate": None,
}

for key, value in DEFAULT_SESSION.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ===============================
# LOAD UI
# ===============================

load_css()

# ===============================
# LOGIN PAGE
# ===============================

if not st.session_state.logged_in:

    hero_col, auth_col = st.columns([1.05, 0.95], gap="large")

    with hero_col:
        st.markdown(
            textwrap.dedent(f"""
            <div class="hero-panel">
                <div style="display:inline-flex; align-items:center; gap:9px; padding:8px 18px;
                    background:rgba(255,255,255,0.16); border:1px solid rgba(255,255,255,0.35);
                    border-radius:999px; font-family:'IBM Plex Mono',monospace; font-size:11px;
                    letter-spacing:2px; color:#EAFBF5; text-transform:uppercase; font-weight:600;">
                    <span style="width:7px;height:7px;border-radius:50%;background:#FFFFFF;
                        box-shadow:0 0 0 4px rgba(255,255,255,0.25);"></span>
                    AI Recruitment Copilot
                </div>
                <div style="font-family:'Space Grotesk',sans-serif; font-size:38px; font-weight:800;
                    color:#FFFFFF; line-height:1.15; letter-spacing:-0.8px; margin-top:26px;">
                    Hire smarter, faster —<br>with AI as your co-pilot.
                </div>
                <div style="font-size:14.5px; color:#E4FBF3; margin-top:14px; max-width:420px; line-height:1.6;">
                    One platform that reads every resume, scores it against the job, and runs the
                    first interview — so recruiters spend their time on people, not paperwork.
                </div>
                <div style="margin-top:40px;">
                    <div class="hero-feature">
                        <div class="hero-feature-icon">🎯</div>
                        <div>
                            <div style="color:#FFFFFF; font-weight:700; font-size:13.5px;">Resume-to-JD ATS Scoring</div>
                            <div style="color:#DFF7EE; font-size:12px; margin-top:1px;">Weighted match on skills, experience, education & more</div>
                        </div>
                    </div>
                    <div class="hero-feature">
                        <div class="hero-feature-icon">🧠</div>
                        <div>
                            <div style="color:#FFFFFF; font-weight:700; font-size:13.5px;">Adaptive AI Interviewer</div>
                            <div style="color:#DFF7EE; font-size:12px; margin-top:1px;">Difficulty adjusts live to how the candidate answers</div>
                        </div>
                    </div>
                    <div class="hero-feature">
                        <div class="hero-feature-icon">📊</div>
                        <div>
                            <div style="color:#FFFFFF; font-weight:700; font-size:13.5px;">Live Recruiter Analytics</div>
                            <div style="color:#DFF7EE; font-size:12px; margin-top:1px;">Pipeline health, top skills & hiring decisions at a glance</div>
                        </div>
                    </div>
                    <div class="hero-feature" style="margin-bottom:0;">
                        <div class="hero-feature-icon">🔒</div>
                        <div>
                            <div style="color:#FFFFFF; font-weight:700; font-size:13.5px;">Role-Based Secure Access</div>
                            <div style="color:#DFF7EE; font-size:12px; margin-top:1px;">Separate recruiter and candidate workspaces</div>
                        </div>
                    </div>
                </div>
                <div style="position:absolute; left:40px; bottom:32px; font-size:11px; color:#CFF3E6;
                    font-family:'IBM Plex Mono',monospace; letter-spacing:0.6px;">
                    ⬡ Built for the Infosys AI Challenge
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    with auth_col:

        # ==========================
        # STEP 1 — PORTAL SELECTION
        # ==========================
        if st.session_state.portal_mode is None:
            with st.container(border=True):
                st.markdown(
                    '<div class="aperture-eyebrow">● Choose Your Workspace</div>'
                    f'<div style="font-size:22px; font-weight:800; color:{INK}; '
                    'font-family:\'Space Grotesk\'; margin-bottom:6px;">Continue as</div>'
                    f'<div style="font-size:13px; color:{MIST}; margin-bottom:24px;">'
                    'Pick the portal that matches your role — each account type gets its own dashboard.</div>',
                    unsafe_allow_html=True,
                )

                pcol1, pcol2, pcol3 = st.columns(3)
                with pcol1:
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="text-align:center; padding:6px 0 12px 0;">
                                <div style="font-size:28px;">🧑‍💼</div>
                                <div style="font-weight:800; font-size:15px; margin-top:8px; color:{INK}; font-family:'Space Grotesk';">Recruiter</div>
                                <div style="font-size:11.5px; color:{MIST}; margin-top:4px;">Post jobs, screen resumes, run interviews</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("Enter Recruiter Portal →", use_container_width=True, key="portal_recruiter", type="primary"):
                            st.session_state.portal_mode = "recruiter"
                            st.rerun()
                with pcol2:
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="text-align:center; padding:6px 0 12px 0;">
                                <div style="font-size:28px;">🎓</div>
                                <div style="font-weight:800; font-size:15px; margin-top:8px; color:{INK}; font-family:'Space Grotesk';">Candidate</div>
                                <div style="font-size:11.5px; color:{MIST}; margin-top:4px;">Apply, interview, and track your status</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("Enter Candidate Portal →", use_container_width=True, key="portal_candidate", type="primary"):
                            st.session_state.portal_mode = "candidate"
                            st.rerun()
                with pcol3:
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="text-align:center; padding:6px 0 12px 0;">
                                <div style="font-size:28px;">🛡️</div>
                                <div style="font-weight:800; font-size:15px; margin-top:8px; color:{INK}; font-family:'Space Grotesk';">Admin</div>
                                <div style="font-size:11.5px; color:{MIST}; margin-top:4px;">Platform oversight & system management</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("Enter Admin Portal →", use_container_width=True, key="portal_admin", type="primary"):
                            st.session_state.portal_mode = "admin"
                            st.rerun()
            st.stop()

        # ==========================
        # STEP 2 — SIGN IN / REGISTER
        # ==========================
        portal = st.session_state.portal_mode
        portal_label = {"recruiter": "Recruiter", "candidate": "Candidate", "admin": "Admin"}[portal]
        portal_icon = {"recruiter": "🧑‍💼", "candidate": "🎓", "admin": "🛡️"}[portal]

        st.markdown(
            f'<div class="step-pill">{portal_icon} {portal_label} Portal</div>'
            f'<div style="font-size:22px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\'; margin-bottom:6px;">'
            f'Welcome back</div>',
            unsafe_allow_html=True,
        )

        # ==========================
        # "About this portal" -- what's inside, so the person knows what
        # they're signing into before they create an account.
        # ==========================
        if portal == "recruiter":
            about_items = [
                ("🗂", "Post & manage job openings", "Create roles with required skills, experience and qualification"),
                ("📤", "Screen resumes with ATS scoring", "Upload resumes and get a weighted match score against each job"),
                ("🧠", "Run AI-driven interviews", "Adaptive interview questions scored automatically per candidate"),
                ("📊", "Track pipeline & analytics", "Hiring funnel, skill demand, and shortlist recommendations at a glance"),
            ]
        elif portal == "admin":
            about_items = [
                ("👥", "Manage every account", "Activate, deactivate, or change the role of any user on the platform"),
                ("🗂", "Oversee all jobs & applications", "Full visibility across every recruiter's postings and pipelines"),
                ("📊", "Platform-wide analytics", "ATS trends, interview performance, and growth — never mock data"),
                ("🩺", "Monitor system health", "Database, AI service, and integration status at a glance"),
            ]
        else:
            about_items = [
                ("📄", "Apply with your resume", "Upload once and see your ATS match score against the role"),
                ("🧠", "Take the AI interview", "A short adaptive interview you complete yourself, at your own pace"),
                ("📈", "Track your application status", "See where you stand in the hiring pipeline in real time"),
                ("💬", "Hear back from recruiters", "Get replies and updates from recruiters directly in your portal"),
            ]

        about_rows = "".join(
            f"""
            <div style="display:flex; align-items:flex-start; gap:10px; padding:8px 0;">
                <div style="font-size:16px; line-height:1.4;">{icon}</div>
                <div>
                    <div style="font-weight:700; font-size:12.5px; color:{INK};">{title}</div>
                    <div style="font-size:11.5px; color:{MIST}; margin-top:1px;">{subtitle}</div>
                </div>
            </div>
            """
            for icon, title, subtitle in about_items
        )

        with st.expander(f"What's inside the {portal_label} Portal", expanded=False):
            st.markdown(about_rows, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ==========================
        # LOGIN — every portal gets this
        # ==========================
        def _render_login_form():
            with st.container(border=True):
                username = st.text_input("Username", placeholder="Enter username", key="login_username")
                password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")
                remember = st.checkbox("Remember Me")

                st.markdown("<br>", unsafe_allow_html=True)

                if st.button(f"🔓  Sign In to {portal_label} Portal", use_container_width=True, type="primary"):
                    row = login(username, password)
                    if row:
                        account_role = (row.get("role") or "recruiter").lower()
                        if (row.get("status") or "active").lower() != "active":
                            st.error("This account has been deactivated. Contact an administrator.")
                        elif account_role != portal:
                            st.error(
                                f"This account is registered as a {account_role.title()}. "
                                f"Please use the {account_role.title()} portal instead."
                            )
                        else:
                            st.session_state.logged_in = True
                            st.session_state.username = row["username"]
                            st.session_state.user_email = row.get("email", "")
                            st.session_state.role = account_role
                            st.success("Authentication successful.")
                            st.rerun()
                    else:
                        st.error("Invalid username or password.")

        # Admin accounts are never self-registered from this public form —
        # only Sign In is offered. New admins are created either by an
        # existing admin (User Management → Change Role) or via the
        # create_admin.py command-line utility for the very first account.
        if portal == "admin":
            st.caption("Admin accounts aren't self-registered here — ask an existing admin to grant access, "
                       "or use the create_admin.py setup script for the first account.")
            _render_login_form()
        else:
            tab1, tab2 = st.tabs(["Sign In", "Create Account"])

            with tab1:
                _render_login_form()

            # ==========================
            # REGISTER
            # ==========================
            with tab2:
                with st.container(border=True):
                    new_user = st.text_input("Username", key="new_user")
                    email = st.text_input("Email Address", key="email")
                    password = st.text_input("Password", type="password", key="pass")
                    confirm = st.text_input("Confirm Password", type="password")

                    st.markdown("<br>", unsafe_allow_html=True)

                    if st.button(f"✦  Register {portal_label} Account", use_container_width=True, type="primary"):
                        if password != confirm:
                            st.error("Passwords do not match.")
                        else:
                            ok, msg = register(new_user, email, password, role=portal)
                            if ok:
                                st.success(msg + " — you can sign in now.")
                            else:
                                st.error(msg)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Back to Portal Selection", use_container_width=True, type="secondary"):
            st.session_state.portal_mode = None
            st.rerun()

    st.stop()

# ===============================
# SIDEBAR
# ===============================

is_recruiter = st.session_state.role == "recruiter"
is_admin = st.session_state.role == "admin"

with st.sidebar:
    if is_recruiter:
        sidebar_logo()

        st.markdown("---")

        sidebar_session(st.session_state.username, "Authorized Recruiter", is_recruiter=True)

        st.markdown("---")

        nav_options = [
            "📊 Dashboard",
            "🗂 Job Postings",
            "📤 Upload Resume",
            "🎙️ Interviews",
            "📋 Candidates",
            "📈 Analytics",
            "👤 Profile"
        ]
        # Quick Actions on the dashboard (see "⚡ Quick Actions" panel below)
        # jump straight to a page by pre-seeding the radio's own session-state
        # key before it's instantiated -- Streamlit then uses that as the
        # widget's initial value on this rerun, same as a manual click would.
        if "_qa_nav" in st.session_state:
            st.session_state["nav_radio"] = st.session_state.pop("_qa_nav")
        page = st.radio(
            "Navigation",
            nav_options,
            label_visibility="collapsed",
            key="nav_radio",
        )

        st.markdown("---")

        if st.button("Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_email = ""
            st.session_state.role = None
            st.session_state.portal_mode = None
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        theme_toggle()
    else:
        # Candidates and Admins each get exactly one sidebar -- the
        # dedicated one built inside render_candidate_dashboard() /
        # render_admin_dashboard() below (avatar+name, section nav,
        # Logout). Rendering the generic logo/session-card/nav-placeholder
        # /Sign-Out block here too used to stack a second, near-duplicate
        # sidebar underneath it -- that's the "excess" spacing/duplication
        # bug.
        page = None

# ===============================
# ADMIN PORTAL
# ===============================

if is_admin:
    render_admin_dashboard({
        "username": st.session_state.username,
        "email": st.session_state.user_email,
    })
    footer()
    st.stop()

# ===============================
# CANDIDATE PORTAL
# ===============================

if not is_recruiter:
    render_candidate_dashboard({
        "username": st.session_state.username,
        "email": st.session_state.user_email,
    })
    footer()
    st.stop()

# ===============================
# RECRUITER PORTAL
# ===============================

render_recruiter_dashboard(page)

footer()
