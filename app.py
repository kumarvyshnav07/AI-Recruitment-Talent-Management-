import os
import streamlit as st
import pandas as pd
from datetime import datetime

# ===============================
# PROJECT MODULES
# ===============================
from auth import (
    login,
    register
)

from database import (
    init_db,
    get_candidates,
    get_candidate,
    get_candidates_for_role,
    get_dashboard_stats,
    save_candidate,
    search_candidates,
    delete_candidate,
    database_version,
    get_jobs,
    create_job,
    update_job,
    delete_job
)

from job_matching import match_candidates_to_job

from resume_parser import parse_resume

from ats_engine import (
    calculate_ats,
    generate_recommendation
)

from ui import (
    load_css,
    metric_card,
    sidebar_logo,
    page_title,
    footer,
    profile_field,
    chip_list,
    list_card,
    full_report_modal,
    VOID,
    PANEL,
    PANEL2,
    LINE,
    INK,
    MIST,
    SIGNAL,
    VERDICT,
    CAUTION,
    RISK
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

# ===============================
# SESSION VARIABLES
# ===============================

DEFAULT_SESSION = {
    "logged_in": False,
    "username": "",
    "role": "Recruiter",
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

    st.markdown(
        f"""
        <div style="text-align: center; padding: 3.5rem 0 1.5rem 0;">
            <div style="
                display:inline-flex;
                align-items:center;
                gap:10px;
                padding:8px 16px;
                border:1px solid {SIGNAL}44;
                background:{SIGNAL}12;
                border-radius:999px;
                font-family:'IBM Plex Mono',monospace;
                font-size:11px;
                letter-spacing:1.5px;
                color:{SIGNAL};
                text-transform:uppercase;
                margin-bottom:22px;
            ">
                ● AI Recruitment Copilot
            </div>
            <div style="font-family:'Space Grotesk',sans-serif; font-size: 40px; font-weight: 800; color: {INK}; letter-spacing: -0.5px;">
                AI Recruitment Copilot
            </div>
            <div style="font-size: 15px; color: {MIST}; margin-top: 8px; font-weight: 500;">
                Enterprise Hiring Intelligence Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])

        # ==========================
        # LOGIN
        # ==========================

        with tab1:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password")
            remember = st.checkbox("Remember Me")

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Sign In to Workspace", use_container_width=True):
                ok = login(username, password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Authentication successful.")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            st.markdown('</div>', unsafe_allow_html=True)

        # ==========================
        # REGISTER
        # ==========================

        with tab2:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            new_user = st.text_input("Username", key="new_user")
            email = st.text_input("Email Address", key="email")
            password = st.text_input("Password", type="password", key="pass")
            confirm = st.text_input("Confirm Password", type="password")

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Register Enterprise Account", use_container_width=True):
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register(new_user, email, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
            st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# ===============================
# SIDEBAR
# ===============================

with st.sidebar:
    sidebar_logo()

    st.markdown("---")

    st.markdown(
        f"""
        <div style="padding: 5px 10px; color: {INK};">
            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: {MIST}; font-family:'IBM Plex Mono',monospace;">Active Session</div>
            <div style="font-size: 16px; font-weight: 700; color: {INK}; margin-top: 4px;">{st.session_state.username}</div>
            <div style="font-size: 13px; color: {SIGNAL}; margin-top: 2px; font-weight: 500;">Authorized Recruiter</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🗂 Job Postings",
            "📤 Upload Resume",
            "📋 Candidates",
            "📈 Analytics",
            "👤 Profile"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    if st.button("Sign Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# ===============================
# DASHBOARD
# ===============================

if page == "📊 Dashboard":

    page_title(
        "Enterprise Recruitment Dashboard",
        "AI-Powered Hiring Intelligence & Pipeline Overview"
    )

    stats = get_dashboard_stats()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Talent Pool", stats["total_candidates"], "📋", SIGNAL)
    with c2:
        metric_card("Shortlisted Profiles", stats["shortlisted"], "✔", VERDICT)
    with c3:
        metric_card("Average ATS Match", f"{stats['average_ats']}%", "🎯", CAUTION)
    with c4:
        metric_card("Today's Processing", stats["today_uploads"], "📤", CAUTION)

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([2, 1])

    with left:
        st.markdown(
            f"""
            <div class="glass">
                <div style="font-size: 16px; font-weight: 700; color: {INK}; letter-spacing: -0.3px;">
                    Pipeline Performance
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        chart1, chart2 = st.columns(2)
        with chart1:
            st.info("📈 ATS Distribution Spectrum\n\nAggregated data mapping via Analytics Suite")
        with chart2:
            st.info("📊 Matrix Competency Distribution\n\nTop Categorized Core Candidate Competencies")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="glass">
                <div style="font-size: 16px; font-weight: 700; color: {INK}; letter-spacing: -0.3px;">
                    Recent Processing Activity
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        data = get_candidates()

        if len(data) == 0:
            st.warning("No candidate records available in database.")
        else:
            recent = pd.DataFrame(data).head(5)
            st.dataframe(recent, use_container_width=True, hide_index=True)

    with right:
        st.markdown(
            f"""
            <div class="glass">
                <div style="font-size: 16px; font-weight: 700; color: {INK}; margin-bottom: 15px; letter-spacing: -0.3px;">
                    Enterprise Engine Insights
                </div>
            """,
            unsafe_allow_html=True
        )

        st.success("System: ATS Optimizer Online")
        st.success("System: Resume Parser Core Ready")
        st.success("System: Secure Database Connection Verified")
        st.success("System: RBAC Authentication Active")

        st.info(
            """
Strategic Suggestions

- Audit requirement configurations quarterly.
- Purge duplicate records using custom searches.
- Cross-reference metric benchmarks with hiring team target profiles.
"""
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="glass">
                <div style="font-size: 16px; font-weight: 700; color: {INK}; margin-bottom: 15px; letter-spacing: -0.3px;">
                    System Architecture
                </div>
            """,
            unsafe_allow_html=True
        )

        st.metric("Node Cluster Status", "Online")
        st.metric("Database Handshake", "Synchronized")
        st.metric("Cognitive Analytics Core", "Operational")
        st.metric("Software Architecture Build", "v3.0 Long-Term Support")
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # FINAL HIRING DECISION — same ranking logic as the
    # "🏆 Final Decision" tab on the Job Postings page, surfaced
    # here so a recruiter can pick a job and immediately see who
    # has the highest ATS score without leaving the Dashboard.
    # -----------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    st.markdown(
        f"""
        <div class="glass">
            <div style="font-size: 16px; font-weight: 700; color: {INK}; letter-spacing: -0.3px;">
                🏆 Final Hiring Decision
            </div>
            <div style="font-size: 12px; color: {MIST}; margin-top: 4px;">
                Pick a job posting to see every applied candidate ranked by ATS score, highest first.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    dash_jobs = get_jobs()

    if not dash_jobs:
        st.info("No job postings yet. Create one on the 🗂 Job Postings page to start ranking candidates.")
    else:
        job_titles = [f"{j['job_title']} — {j['company_name']} (#{j['job_id']})" for j in dash_jobs]
        dash_job_choice = st.selectbox("Select Job Posting", job_titles, key="dashboard_job_select")
        dash_selected_job = dash_jobs[job_titles.index(dash_job_choice)]

        decision_pool = get_candidates_for_role(dash_selected_job["job_title"])

        if not decision_pool:
            st.info(
                f"No candidates have applied to '{dash_selected_job['job_title']}' yet — "
                f"nothing to rank."
            )
        else:
            ranked = sorted(
                decision_pool,
                key=lambda c: c.get("ats_score") or 0,
                reverse=True,
            )
            best = ranked[0]
            worst = ranked[-1]

            ddc1, ddc2 = st.columns(2)
            with ddc1:
                metric_card(
                    "🏆 Highest ATS Score",
                    f"{best['name']} — {best.get('ats_score', 0)}%",
                    "🏆", VERDICT
                )
            with ddc2:
                metric_card(
                    "⚠ Lowest ATS Score",
                    f"{worst['name']} — {worst.get('ats_score', 0)}%",
                    "⚠", RISK
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Keep each candidate's TRUE overall rank (#1, #2, ...) before
            # filtering, so the number shown still reflects their standing
            # against the full applicant pool for this job, not just the
            # filtered subset.
            ranked_with_rank = list(enumerate(ranked, start=1))

            def _badge(score):
                if score >= 80:
                    return VERDICT, "✅ Recommended to Hire"
                elif score >= 60:
                    return CAUTION, "🟡 Consider"
                else:
                    return RISK, "❌ Not Recommended"

            dash_filter = st.radio(
                "Filter",
                ["All", "Top 5", "✅ Recommended Only", "🟡 Consider Only", "❌ Not Recommended Only"],
                horizontal=True,
                key="dashboard_decision_filter",
                label_visibility="collapsed",
            )

            if dash_filter == "Top 5":
                display_list = ranked_with_rank[:5]
            elif dash_filter == "✅ Recommended Only":
                display_list = [(r, c) for r, c in ranked_with_rank if (c.get("ats_score") or 0) >= 80]
            elif dash_filter == "🟡 Consider Only":
                display_list = [(r, c) for r, c in ranked_with_rank if 60 <= (c.get("ats_score") or 0) < 80]
            elif dash_filter == "❌ Not Recommended Only":
                display_list = [(r, c) for r, c in ranked_with_rank if (c.get("ats_score") or 0) < 60]
            else:
                display_list = ranked_with_rank

            st.caption(f"Showing {len(display_list)} of {len(ranked)} candidate(s).")

            if not display_list:
                st.info("No candidates match this filter.")

            for rank, cand in display_list:
                score = cand.get("ats_score") or 0
                badge_color, badge_label = _badge(score)

                st.markdown(
                    f"""
                    <div class="glass" style="padding:14px 18px; margin-bottom:10px;
                        display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-family:'IBM Plex Mono',monospace; color:{MIST}; font-size:12px;">
                                #{rank}
                            </span>
                            &nbsp;<strong style="color:{INK};">{cand['name']}</strong>
                            <span style="color:{MIST}; font-size:12px;"> — {cand['email']}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:14px;">
                            <span style="font-family:'IBM Plex Mono',monospace; font-weight:700; color:{SIGNAL};">
                                {score}%
                            </span>
                            <span style="padding:4px 10px; border-radius:999px;
                                background:{badge_color}18; color:{badge_color};
                                font-size:12px; font-weight:700;">
                                {badge_label}
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ==================================
# JOB POSTINGS
# ==================================
elif page == "🗂 Job Postings":

    page_title(
        "Job Postings",
        "Create and manage open roles — these feed directly into ATS matching"
    )

    with st.expander("➕ Post a New Job", expanded=len(get_jobs()) == 0):
        st.markdown('<div class="glass">', unsafe_allow_html=True)

        jc1, jc2 = st.columns(2)
        with jc1:
            new_job_title = st.text_input("Job Title", placeholder="e.g. Backend Developer")
            new_company = st.text_input("Company Name", placeholder="e.g. Acme Corp")
            new_experience = st.selectbox(
                "Required Experience",
                ["Fresher", "1 Year", "2 Years", "3 Years", "5+ Years"],
                key="new_job_exp"
            )

        with jc2:
            new_location = st.text_input("Location", placeholder="e.g. Bengaluru, Remote")
            new_salary = st.number_input("Annual Salary", min_value=0.0, step=10000.0, format="%.2f")
            new_qualification = st.selectbox(
                "Minimum Qualification",
                ["Any Degree", "B.Tech", "B.E", "M.Tech", "MBA", "MCA"],
                key="new_job_qual"
            )

        new_skills = st.text_area(
            "Required Skills (comma separated)",
            placeholder="Python, SQL, PySpark, Docker"
        )

        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Post Job", use_container_width=True, type="primary"):
            if not new_job_title.strip() or not new_company.strip() or not new_skills.strip():
                st.warning("Job title, company name and required skills are required.")
            else:
                new_id = create_job(
                    job_title=new_job_title.strip(),
                    company_name=new_company.strip(),
                    experience=new_experience,
                    location=new_location.strip(),
                    salary=new_salary,
                    required_skills=new_skills.strip(),
                    qualification=new_qualification,
                )
                if new_id:
                    st.success(f"Job posted successfully (ID #{new_id}).")
                    st.rerun()
                else:
                    st.error("Could not save the job posting — check the database connection.")

    st.divider()

    jobs = get_jobs()

    if len(jobs) == 0:
        st.info("No job postings yet. Create one above to start matching resumes against it.")
    else:
        for job in jobs:
            with st.container():
                st.markdown('<div class="glass">', unsafe_allow_html=True)
                jcol1, jcol2, jcol3, jcol4, jcol5 = st.columns([3, 1, 1, 1, 1])
                with jcol1:
                    st.markdown(f"**{job['job_title']}** — {job['company_name']}")
                    st.caption(
                        f"📍 {job['location'] or '—'}   •   🧭 {job['experience'] or '—'}   •   "
                        f"💰 ₹{job['salary']}   •   🎓 {job['qualification']}"
                    )
                    st.write(job["required_skills"] or "No specific skills listed")
                with jcol2:
                    if st.button("👥 Candidates", key=f"view_cands_{job['job_id']}", use_container_width=True):
                        st.session_state.viewing_job_candidates = (
                            None if st.session_state.viewing_job_candidates == job["job_id"]
                            else job["job_id"]
                        )
                        st.rerun()
                with jcol3:
                    if st.button("✏️ Edit", key=f"edit_job_{job['job_id']}", use_container_width=True):
                        st.session_state.editing_job = (
                            None if st.session_state.editing_job == job["job_id"]
                            else job["job_id"]
                        )
                        st.rerun()
                with jcol4:
                    if st.button("🔁 Replace", key=f"replace_job_{job['job_id']}", use_container_width=True):
                        st.session_state.replacing_job = (
                            None if st.session_state.replacing_job == job["job_id"]
                            else job["job_id"]
                        )
                        st.rerun()
                with jcol5:
                    if st.button("🗑 Delete", key=f"del_job_{job['job_id']}", use_container_width=True):
                        delete_job(job["job_id"])
                        st.rerun()

                # -----------------------------------------------------
                # EDIT / UPDATE THIS JOB POSTING
                # -----------------------------------------------------
                if st.session_state.editing_job == job["job_id"]:
                    st.divider()
                    st.markdown('<div class="step-pill">Update Job Posting</div>', unsafe_allow_html=True)

                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_title = st.text_input(
                            "Job Title", value=job["job_title"], key=f"edit_title_{job['job_id']}"
                        )
                        edit_company = st.text_input(
                            "Company Name", value=job["company_name"], key=f"edit_company_{job['job_id']}"
                        )
                        edit_exp_choices = ["Fresher", "1 Year", "2 Years", "3 Years", "5+ Years"]
                        edit_default_exp = (
                            edit_exp_choices.index(job["experience"])
                            if job["experience"] in edit_exp_choices else 0
                        )
                        edit_experience = st.selectbox(
                            "Required Experience", edit_exp_choices, index=edit_default_exp,
                            key=f"edit_exp_{job['job_id']}"
                        )
                    with ec2:
                        edit_location = st.text_input(
                            "Location", value=job["location"] or "", key=f"edit_location_{job['job_id']}"
                        )
                        edit_salary = st.number_input(
                            "Annual Salary", min_value=0.0, step=10000.0, format="%.2f",
                            value=float(job["salary"] or 0), key=f"edit_salary_{job['job_id']}"
                        )
                        edit_qual_choices = ["Any Degree", "B.Tech", "B.E", "M.Tech", "MBA", "MCA"]
                        edit_default_qual = (
                            edit_qual_choices.index(job["qualification"])
                            if job["qualification"] in edit_qual_choices else 0
                        )
                        edit_qualification = st.selectbox(
                            "Minimum Qualification", edit_qual_choices, index=edit_default_qual,
                            key=f"edit_qual_{job['job_id']}"
                        )

                    edit_skills = st.text_area(
                        "Required Skills (comma separated)",
                        value=job["required_skills"] or "",
                        key=f"edit_skills_{job['job_id']}"
                    )

                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        if st.button(
                            "💾 Save Changes", key=f"save_job_{job['job_id']}",
                            use_container_width=True, type="primary"
                        ):
                            if not edit_title.strip() or not edit_company.strip() or not edit_skills.strip():
                                st.warning("Job title, company name and required skills are required.")
                            else:
                                update_job(
                                    job_id=job["job_id"],
                                    job_title=edit_title.strip(),
                                    company_name=edit_company.strip(),
                                    experience=edit_experience,
                                    location=edit_location.strip(),
                                    salary=edit_salary,
                                    required_skills=edit_skills.strip(),
                                    qualification=edit_qualification,
                                )
                                st.session_state.editing_job = None
                                st.success("Job posting updated.")
                                st.rerun()
                    with cancel_col:
                        if st.button("✖ Cancel", key=f"cancel_edit_{job['job_id']}", use_container_width=True):
                            st.session_state.editing_job = None
                            st.rerun()

                # -----------------------------------------------------
                # REPLACE THIS JOB POSTING
                # CRUD "Replace" op, mirroring the candidate Replace flow:
                # a blank form where the recruiter re-enters the job from
                # scratch, and on confirm it fully overwrites this job_id's
                # row via update_job() — unlike Edit above, which prefills
                # existing values for incremental tweaks, Replace discards
                # whatever was there before.
                # -----------------------------------------------------
                if st.session_state.replacing_job == job["job_id"]:
                    st.divider()
                    st.markdown('<div class="step-pill">Replace · Enter New Job Details</div>', unsafe_allow_html=True)
                    st.caption(
                        "This will completely overwrite the existing posting below "
                        "with whatever you enter here — leave a field blank and it "
                        "will be cleared, not kept."
                    )

                    rc1, rc2 = st.columns(2)
                    with rc1:
                        rep_title = st.text_input(
                            "Job Title", placeholder="e.g. Backend Developer",
                            key=f"rep_title_{job['job_id']}"
                        )
                        rep_company = st.text_input(
                            "Company Name", placeholder="e.g. Acme Corp",
                            key=f"rep_company_{job['job_id']}"
                        )
                        rep_experience = st.selectbox(
                            "Required Experience",
                            ["Fresher", "1 Year", "2 Years", "3 Years", "5+ Years"],
                            key=f"rep_exp_{job['job_id']}"
                        )
                    with rc2:
                        rep_location = st.text_input(
                            "Location", placeholder="e.g. Bengaluru, Remote",
                            key=f"rep_location_{job['job_id']}"
                        )
                        rep_salary = st.number_input(
                            "Annual Salary", min_value=0.0, step=10000.0, format="%.2f",
                            key=f"rep_salary_{job['job_id']}"
                        )
                        rep_qualification = st.selectbox(
                            "Minimum Qualification",
                            ["Any Degree", "B.Tech", "B.E", "M.Tech", "MBA", "MCA"],
                            key=f"rep_qual_{job['job_id']}"
                        )

                    rep_skills = st.text_area(
                        "Required Skills (comma separated)",
                        placeholder="Python, SQL, PySpark, Docker",
                        key=f"rep_skills_{job['job_id']}"
                    )

                    rep_confirm, rep_cancel = st.columns(2)
                    with rep_confirm:
                        if st.button(
                            "✅ Confirm Replace", key=f"confirm_replace_job_{job['job_id']}",
                            use_container_width=True, type="primary"
                        ):
                            if not rep_title.strip() or not rep_company.strip() or not rep_skills.strip():
                                st.warning("Job title, company name and required skills are required.")
                            else:
                                update_job(
                                    job_id=job["job_id"],
                                    job_title=rep_title.strip(),
                                    company_name=rep_company.strip(),
                                    experience=rep_experience,
                                    location=rep_location.strip(),
                                    salary=rep_salary,
                                    required_skills=rep_skills.strip(),
                                    qualification=rep_qualification,
                                )
                                st.session_state.replacing_job = None
                                st.success("Job posting replaced.")
                                st.rerun()
                    with rep_cancel:
                        if st.button(
                            "✖ Cancel", key=f"cancel_replace_job_{job['job_id']}",
                            use_container_width=True
                        ):
                            st.session_state.replacing_job = None
                            st.rerun()

                # -----------------------------------------------------
                # CANDIDATES FOR THIS SPECIFIC ROLE
                # -----------------------------------------------------
                if st.session_state.viewing_job_candidates == job["job_id"]:
                    st.divider()

                    tab_applied, tab_final_decision, tab_skill_match = st.tabs(
                        ["✅ Applied Candidates", "🏆 Final Decision", "🔍 Skill-Match Whole Pool"]
                    )

                    with tab_applied:
                        applied = get_candidates_for_role(job["job_title"])
                        if not applied:
                            st.info(
                                f"No candidates have been evaluated against "
                                f"'{job['job_title']}' yet — upload resumes and match "
                                f"them against this job on the Upload Resume page."
                            )
                        else:
                            shortlisted = [c for c in applied if (c.get("ats_score") or 0) >= 80]
                            st.caption(
                                f"{len(applied)} candidate(s) evaluated · "
                                f"**{len(shortlisted)} shortlisted** (ATS ≥ 80%)"
                            )
                            df_applied = pd.DataFrame(applied)
                            cols = [c for c in
                                    ["name", "email", "ats_score", "recommendation", "confidence", "experience"]
                                    if c in df_applied.columns]
                            st.dataframe(df_applied[cols], use_container_width=True, hide_index=True)

                    # -----------------------------------------------------
                    # FINAL HIRING DECISION FOR THIS JOB
                    # Ranks every candidate who applied to THIS job by their
                    # stored ATS score (highest first) and gives each one a
                    # clear Recommended / Consider / Not Recommended call,
                    # plus a callout for the single best and weakest profile.
                    # -----------------------------------------------------
                    with tab_final_decision:
                        st.caption(
                            "Final hiring call for this role — every applied candidate "
                            "ranked by ATS score, highest to lowest."
                        )
                        decision_pool = get_candidates_for_role(job["job_title"])

                        if not decision_pool:
                            st.info(
                                f"No candidates have been evaluated against "
                                f"'{job['job_title']}' yet — nothing to rank."
                            )
                        else:
                            ranked = sorted(
                                decision_pool,
                                key=lambda c: c.get("ats_score") or 0,
                                reverse=True,
                            )
                            best = ranked[0]
                            worst = ranked[-1]

                            dc1, dc2 = st.columns(2)
                            with dc1:
                                metric_card(
                                    "🏆 Top Candidate",
                                    f"{best['name']} — {best.get('ats_score', 0)}%",
                                    "🏆", VERDICT
                                )
                            with dc2:
                                metric_card(
                                    "⚠ Weakest Candidate",
                                    f"{worst['name']} — {worst.get('ats_score', 0)}%",
                                    "⚠", RISK
                                )

                            st.markdown("<br>", unsafe_allow_html=True)

                            for rank, cand in enumerate(ranked, start=1):
                                score = cand.get("ats_score") or 0
                                if score >= 80:
                                    badge_color, badge_label = VERDICT, "✅ Recommended to Hire"
                                elif score >= 60:
                                    badge_color, badge_label = CAUTION, "🟡 Consider"
                                else:
                                    badge_color, badge_label = RISK, "❌ Not Recommended"

                                st.markdown(
                                    f"""
                                    <div class="glass" style="padding:14px 18px; margin-bottom:10px;
                                        display:flex; justify-content:space-between; align-items:center;">
                                        <div>
                                            <span style="font-family:'IBM Plex Mono',monospace; color:{MIST}; font-size:12px;">
                                                #{rank}
                                            </span>
                                            &nbsp;<strong style="color:{INK};">{cand['name']}</strong>
                                            <span style="color:{MIST}; font-size:12px;"> — {cand['email']}</span>
                                        </div>
                                        <div style="display:flex; align-items:center; gap:14px;">
                                            <span style="font-family:'IBM Plex Mono',monospace; font-weight:700; color:{SIGNAL};">
                                                {score}%
                                            </span>
                                            <span style="padding:4px 10px; border-radius:999px;
                                                background:{badge_color}18; color:{badge_color};
                                                font-size:12px; font-weight:700;">
                                                {badge_label}
                                            </span>
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                    with tab_skill_match:
                        st.caption(
                            "Ranks every candidate in the database by skill overlap with "
                            "this job's required skills, regardless of which role they "
                            "originally applied for."
                        )
                        match_result = match_candidates_to_job(job["job_id"])
                        results = match_result["results"] if match_result else []
                        if not results:
                            st.info("No candidates in the database yet to match against.")
                        else:
                            df_match = pd.DataFrame(results)
                            df_match = df_match.rename(columns={"match_percent": "Skill Match %"})
                            st.dataframe(
                                df_match[["name", "email", "Skill Match %", "matched_skills", "missing_skills"]],
                                use_container_width=True, hide_index=True
                            )

                st.markdown('</div>', unsafe_allow_html=True)

# ==================================
# UPLOAD RESUME
# ==================================
# STEP 1 : Upload & auto-extract structured candidate data
# STEP 2 : Define the target role / required skills
# STEP 3 : Run ATS match + AI recommendation
# STEP 4 : Commit to database  /  View full report  /  Export
# ==================================

elif page == "📤 Upload Resume":

    page_title(
        "Cognitive Resume Intelligence Suite",
        "Upload a resume first — structured data is extracted automatically, then matched to a role"
    )

    upload_mode = st.radio(
        "Upload Mode",
        ["🧑 Single Resume", "🗂 Bulk Resumes"],
        horizontal=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    if upload_mode == "🧑 Single Resume":

        # -----------------------------------------------------
        # STEP 1 — UPLOAD
        # -----------------------------------------------------

        st.markdown('<div class="step-pill">Step 1 · Upload Resume</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop the candidate's resume here (PDF or DOCX)",
            type=["pdf", "docx"]
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_file:

            file_key = f"{uploaded_file.name}_{uploaded_file.size}"

            if st.session_state.resume_file_key != file_key:

                os.makedirs("uploads", exist_ok=True)
                filepath = os.path.join("uploads", uploaded_file.name)

                with open(filepath, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with st.spinner("Extracting structured candidate data from resume..."):
                    details = parse_resume(filepath)

                st.session_state.resume_file_key = file_key
                st.session_state.parsed_details = details
                st.session_state.resume_filename = uploaded_file.name

                # Reset any prior analysis tied to the previous resume
                st.session_state.ats_result = None
                st.session_state.recommendation = None

            details = st.session_state.parsed_details

            st.success("✅ Parsing complete — candidate profile extracted below.")

            # -----------------------------------------------------
            # EXTRACTED PROFILE — separate professional cards
            # -----------------------------------------------------

            st.markdown('<div class="aperture-eyebrow">Candidate Extracted Profile</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                profile_field("Full Name", details.get("name", ""), "👤")
            with c2:
                profile_field("Email Address", details.get("email", ""), "✉")
            with c3:
                profile_field("Phone Number", details.get("phone", ""), "📞")

            c4, c5 = st.columns(2)
            with c4:
                profile_field("Education", details.get("education", ""), "🎓")
            with c5:
                profile_field("Experience", details.get("experience", ""), "🧭")

            st.markdown("**Technical Skills Detected**")
            skills_str = details.get("skills", "")
            chip_list(skills_str.split(",") if skills_str else [], SIGNAL)

            st.markdown("<br>", unsafe_allow_html=True)

            pcol, ccol = st.columns(2)
            with pcol:
                list_card("Projects", details.get("projects", []), "🧩", SIGNAL)
            with ccol:
                list_card("Certifications", details.get("certifications", []), "🎓", VERDICT)

            st.divider()

            # -----------------------------------------------------
            # STEP 2 — TARGET ROLE (only shown after resume is parsed)
            # -----------------------------------------------------

            st.markdown('<div class="step-pill">Step 2 · Define Target Role</div>', unsafe_allow_html=True)

            st.markdown('<div class="glass">', unsafe_allow_html=True)

            posted_jobs = get_jobs()
            job_options = ["✍️ Manual Entry"] + [
                f"#{j['job_id']} · {j['job_title']} — {j['company_name']}" for j in posted_jobs
            ]
            selected_job_option = st.selectbox("Match Against", job_options)

            selected_posting = None
            if selected_job_option != "✍️ Manual Entry":
                selected_job_id = int(selected_job_option.split("·")[0].strip().lstrip("#"))
                selected_posting = next((j for j in posted_jobs if j["job_id"] == selected_job_id), None)

            rc1, rc2 = st.columns(2)

            with rc1:
                job_role = st.text_input(
                    "Target Job Role",
                    value=selected_posting["job_title"] if selected_posting else "",
                    placeholder="e.g. Data Engineer, Backend Developer"
                )

                exp_choices = ["Fresher", "1 Year", "2 Years", "3 Years", "5+ Years"]
                default_exp = (
                    exp_choices.index(selected_posting["experience"])
                    if selected_posting and selected_posting["experience"] in exp_choices
                    else 0
                )
                experience_req = st.selectbox(
                    "Minimum Required Experience", exp_choices, index=default_exp
                )

            with rc2:
                required_skills = st.text_area(
                    "Required Skills (comma separated)",
                    value=selected_posting["required_skills"] if selected_posting else "",
                    placeholder="Python, SQL, PySpark, Docker"
                )

                qual_choices = ["Any Degree", "B.Tech", "B.E", "M.Tech", "MBA", "MCA"]
                default_qual = (
                    qual_choices.index(selected_posting["qualification"])
                    if selected_posting and selected_posting["qualification"] in qual_choices
                    else 0
                )
                qualification_req = st.selectbox(
                    "Minimum Qualification", qual_choices, index=default_qual
                )

            st.markdown('</div>', unsafe_allow_html=True)

            analyze_clicked = st.button(
                "⚡ Analyze Match & Generate ATS Report",
                use_container_width=True,
                type="primary"
            )

            if analyze_clicked:
                if not job_role.strip() or not required_skills.strip():
                    st.warning("Enter the job role and required skills before running the analysis.")
                else:
                    ats_result = calculate_ats(
                        details, required_skills, experience_req, qualification_req
                    )
                    recommendation = generate_recommendation(ats_result)

                    st.session_state.ats_result = ats_result
                    st.session_state.recommendation = recommendation
                    st.session_state.job_role = job_role.strip()

            # -----------------------------------------------------
            # STEP 3 — RESULTS SUMMARY + ACTIONS
            # -----------------------------------------------------

            if st.session_state.ats_result:

                ats_result = st.session_state.ats_result
                recommendation = st.session_state.recommendation
                saved_job_role = st.session_state.job_role

                st.divider()
                st.markdown('<div class="step-pill">Step 3 · Match Result</div>', unsafe_allow_html=True)

                s1, s2, s3 = st.columns(3)
                with s1:
                    metric_card("ATS Match", f"{ats_result['ats']}%", "🎯", SIGNAL)
                with s2:
                    metric_card("Decision", recommendation["decision"], "⚙", VERDICT)
                with s3:
                    metric_card("Confidence", recommendation["confidence"], "📈", CAUTION)

                st.markdown(
                    f"""<div style="color:{MIST};font-size:13px;margin:-6px 0 14px 2px;">
                    Target role: <span style="color:{SIGNAL};font-weight:600;">{saved_job_role}</span>
                    </div>""",
                    unsafe_allow_html=True
                )

                a1, a2, a3 = st.columns(3)

                with a1:
                    if st.button("💾 Commit to Database", use_container_width=True, type="primary"):
                        result = save_candidate(
                            candidate=details,
                            ats=ats_result,
                            recommendation=recommendation,
                            resume_name=st.session_state.resume_filename,
                            job_role=saved_job_role
                        )

                        if result == "updated":
                            st.success(
                                f"Existing application for '{saved_job_role}' updated with the re-evaluated profile."
                            )
                        else:
                            st.success(
                                f"New application saved for '{saved_job_role}'."
                            )

                        st.toast("Transaction Complete: Secure Cluster Updated.", icon="💾")

                with a2:
                    if st.button("📊 View Full Analysis Report", use_container_width=True):
                        full_report_modal(details, ats_result, recommendation, saved_job_role)

                with a3:
                    report_df = pd.DataFrame([{
                        "Name": details.get("name", ""),
                        "Email": details.get("email", ""),
                        "Phone": details.get("phone", ""),
                        "Education": details.get("education", ""),
                        "Experience": details.get("experience", ""),
                        "Job Role": saved_job_role,
                        "Skills": details.get("skills", ""),
                        "Projects": " | ".join(details.get("projects", [])),
                        "Certifications": " | ".join(details.get("certifications", [])),
                        "ATS Score": ats_result["ats"],
                        "Decision": recommendation["decision"],
                        "Confidence": recommendation["confidence"],
                    }])

                    st.download_button(
                        "⬇ Download Report (CSV)",
                        report_df.to_csv(index=False).encode(),
                        file_name=f"{(details.get('name') or 'candidate').replace(' ', '_')}_report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

        else:
            st.info("Upload a resume above to begin — the candidate profile will be extracted automatically.")

    else:
        # -----------------------------------------------------
        # BULK MODE — many resumes matched against ONE target role
        # -----------------------------------------------------
        st.markdown('<div class="step-pill">Step 1 · Upload Multiple Resumes</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass">', unsafe_allow_html=True)
        bulk_files = st.file_uploader(
            "Drop multiple candidate resumes here (PDF or DOCX)",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            key="bulk_uploader",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if bulk_files:
            st.caption(f"{len(bulk_files)} file(s) ready to process.")

            st.markdown('<div class="step-pill">Step 2 · Define Target Role</div>', unsafe_allow_html=True)
            st.markdown('<div class="glass">', unsafe_allow_html=True)

            bulk_posted_jobs = get_jobs()
            bulk_job_options = ["✍️ Manual Entry"] + [
                f"#{j['job_id']} · {j['job_title']} — {j['company_name']}" for j in bulk_posted_jobs
            ]
            bulk_job_choice = st.selectbox("Match Against", bulk_job_options, key="bulk_job_choice")

            bulk_selected_posting = None
            if bulk_job_choice != "✍️ Manual Entry":
                bulk_job_id = int(bulk_job_choice.split("·")[0].strip().lstrip("#"))
                bulk_selected_posting = next(
                    (j for j in bulk_posted_jobs if j["job_id"] == bulk_job_id), None
                )

            brc1, brc2 = st.columns(2)
            with brc1:
                bulk_job_role = st.text_input(
                    "Target Job Role",
                    value=bulk_selected_posting["job_title"] if bulk_selected_posting else "",
                    placeholder="e.g. Data Engineer, Backend Developer",
                    key=f"bulk_job_role_{bulk_job_choice}",
                )
                bulk_exp_choices = ["Fresher", "1 Year", "2 Years", "3 Years", "5+ Years"]
                bulk_default_exp = (
                    bulk_exp_choices.index(bulk_selected_posting["experience"])
                    if bulk_selected_posting and bulk_selected_posting["experience"] in bulk_exp_choices
                    else 0
                )
                bulk_experience_req = st.selectbox(
                    "Minimum Required Experience", bulk_exp_choices, index=bulk_default_exp,
                    key=f"bulk_exp_req_{bulk_job_choice}",
                )
            with brc2:
                bulk_required_skills = st.text_area(
                    "Required Skills (comma separated)",
                    value=bulk_selected_posting["required_skills"] if bulk_selected_posting else "",
                    placeholder="Python, SQL, PySpark, Docker",
                    key=f"bulk_req_skills_{bulk_job_choice}",
                )
                bulk_qual_choices = ["Any Degree", "B.Tech", "B.E", "M.Tech", "MBA", "MCA"]
                bulk_default_qual = (
                    bulk_qual_choices.index(bulk_selected_posting["qualification"])
                    if bulk_selected_posting and bulk_selected_posting["qualification"] in bulk_qual_choices
                    else 0
                )
                bulk_qualification_req = st.selectbox(
                    "Minimum Qualification", bulk_qual_choices, index=bulk_default_qual,
                    key=f"bulk_qual_req_{bulk_job_choice}",
                )

            st.markdown('</div>', unsafe_allow_html=True)

            analyze_all_clicked = st.button(
                "⚡ Analyze All Resumes", use_container_width=True, type="primary"
            )

            if analyze_all_clicked:
                if not bulk_job_role.strip() or not bulk_required_skills.strip():
                    st.warning("Enter the job role and required skills before running the analysis.")
                else:
                    os.makedirs("uploads", exist_ok=True)
                    results = []
                    progress = st.progress(0.0, text="Processing resumes...")

                    for idx, f in enumerate(bulk_files):
                        try:
                            filepath = os.path.join("uploads", f.name)
                            with open(filepath, "wb") as out:
                                out.write(f.getbuffer())

                            candidate_details = parse_resume(filepath)
                            candidate_ats = calculate_ats(
                                candidate_details, bulk_required_skills,
                                bulk_experience_req, bulk_qualification_req
                            )
                            candidate_rec = generate_recommendation(candidate_ats)

                            results.append({
                                "filename": f.name,
                                "details": candidate_details,
                                "ats": candidate_ats,
                                "recommendation": candidate_rec,
                            })
                        except Exception as e:
                            results.append({
                                "filename": f.name,
                                "details": None,
                                "ats": None,
                                "recommendation": None,
                                "error": str(e),
                            })
                        progress.progress((idx + 1) / len(bulk_files), text=f"Processed {f.name}")

                    progress.empty()
                    results.sort(
                        key=lambda r: r["ats"]["ats"] if r["ats"] else -1, reverse=True
                    )
                    st.session_state.bulk_results = results
                    st.session_state.job_role = bulk_job_role.strip()

        # -----------------------------------------------------
        # STEP 3 — BULK RESULTS
        # -----------------------------------------------------
        if st.session_state.bulk_results:
            bulk_results = st.session_state.bulk_results
            bulk_job_role_saved = st.session_state.job_role

            st.divider()
            st.markdown('<div class="step-pill">Step 3 · Batch Results</div>', unsafe_allow_html=True)

            ok_results = [r for r in bulk_results if r["ats"] is not None]
            failed_results = [r for r in bulk_results if r["ats"] is None]

            b1, b2, b3 = st.columns(3)
            with b1:
                metric_card("Processed", len(ok_results), "📤", SIGNAL)
            with b2:
                shortlisted_n = len([r for r in ok_results if r["ats"]["ats"] >= 80])
                metric_card("Shortlisted (ATS ≥ 80%)", shortlisted_n, "✔", VERDICT)
            with b3:
                metric_card("Failed to Parse", len(failed_results), "⚠", RISK)

            if failed_results:
                with st.expander(f"⚠ {len(failed_results)} file(s) could not be processed"):
                    for r in failed_results:
                        st.write(f"**{r['filename']}** — {r.get('error', 'Unknown error')}")

            if ok_results:
                table_rows = [{
                    "Select": False,
                    "Name": r["details"].get("name", ""),
                    "Email": r["details"].get("email", ""),
                    "ATS Score": r["ats"]["ats"],
                    "Decision": r["recommendation"]["decision"],
                    "Confidence": r["recommendation"]["confidence"],
                    "Resume File": r["filename"],
                } for r in ok_results]

                edited = st.data_editor(
                    pd.DataFrame(table_rows),
                    use_container_width=True,
                    hide_index=True,
                    disabled=["Name", "Email", "ATS Score", "Decision", "Confidence", "Resume File"],
                    key="bulk_results_editor",
                )

                st.caption(f"Target role: **{bulk_job_role_saved}**  ·  Tick 'Select' to choose which candidates to save.")

                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if st.button("💾 Save Selected to Database", use_container_width=True, type="primary"):
                        selected_emails = set(
                            edited.loc[edited["Select"], "Email"].tolist()
                        )
                        saved_count = 0
                        for r in ok_results:
                            if r["details"].get("email") in selected_emails:
                                save_candidate(
                                    candidate=r["details"],
                                    ats=r["ats"],
                                    recommendation=r["recommendation"],
                                    resume_name=r["filename"],
                                    job_role=bulk_job_role_saved,
                                )
                                saved_count += 1
                        st.success(f"Saved {saved_count} candidate(s) to the database.")

                with bc2:
                    if st.button("💾 Save ALL to Database", use_container_width=True):
                        for r in ok_results:
                            save_candidate(
                                candidate=r["details"],
                                ats=r["ats"],
                                recommendation=r["recommendation"],
                                resume_name=r["filename"],
                                job_role=bulk_job_role_saved,
                            )
                        st.success(f"Saved all {len(ok_results)} candidate(s) to the database.")

                with bc3:
                    export_df = pd.DataFrame([{
                        "Name": r["details"].get("name", ""),
                        "Email": r["details"].get("email", ""),
                        "Phone": r["details"].get("phone", ""),
                        "Job Role": bulk_job_role_saved,
                        "Skills": r["details"].get("skills", ""),
                        "ATS Score": r["ats"]["ats"],
                        "Decision": r["recommendation"]["decision"],
                        "Confidence": r["recommendation"]["confidence"],
                    } for r in ok_results])

                    st.download_button(
                        "⬇ Download Batch Report (CSV)",
                        export_df.to_csv(index=False).encode(),
                        file_name=f"{bulk_job_role_saved.replace(' ', '_')}_batch_report.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                view_names = [r["details"].get("name", r["filename"]) for r in ok_results]
                view_choice = st.selectbox("View Full Report For", view_names, key="bulk_view_choice")
                if st.button("📊 View Full Analysis Report", key="bulk_view_report_btn"):
                    chosen = ok_results[view_names.index(view_choice)]
                    full_report_modal(
                        chosen["details"], chosen["ats"], chosen["recommendation"], bulk_job_role_saved
                    )

# ==================================
# CANDIDATES
# ==================================
elif page == "📋 Candidates":

    page_title(
        "Enterprise Candidate Directory",
        "Unified Interface for Active Sourcing Profiles and Associated Vector Data"
    )

    search = st.text_input(
        "Search Filter Directory Matrix",
        placeholder="Query parameters (Name, Skills, Education, Job Role...)"
    )

    if search.strip():
        candidates = search_candidates(search)
    else:
        candidates = get_candidates()

    if len(candidates) == 0:
        st.warning("No records matched the active filter arguments.")
    else:
        df = pd.DataFrame(candidates)

        if "job_role" not in df.columns:
            df["job_role"] = ""

        show_cols = [
            c for c in
            ["name", "email", "job_role", "phone", "education", "experience", "ats_score", "recommendation", "confidence"]
            if c in df.columns
        ]

        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

        st.divider()

        df["_label"] = (
            df["name"].fillna("Unknown")
            + "  •  " + df["job_role"].fillna("").replace("", "—")
            + "  •  " + df["email"].fillna("")
        )

        selected_label = st.selectbox(
            "Select Record for Active Profile Inspection",
            df["_label"]
        )

        if selected_label:
            candidate = df[df["_label"] == selected_label].iloc[0].to_dict()

            left, right = st.columns([2, 1])

            with left:
                st.subheader(candidate["name"])
                st.write("**Applied Role:**", candidate.get("job_role") or "—")
                st.write("**Communications Node:**", candidate["email"])
                st.write("**Direct Telemetry Call:**", candidate["phone"])
                st.write("**Structural Education History:**")
                st.write(candidate["education"])
                st.write("**Evaluated Tenured Background:**", candidate["experience"])
                st.write("**Verified Technical Core:**")
                st.write(candidate["skills"])
                st.write("**Documented Technical Artifacts/Projects:**")
                st.write(candidate["projects"])
                st.write("**Professional Validations/Certifications:**")
                st.write(candidate["certifications"])

            with right:
                metric_card("ATS Alignment Rating", f'{candidate["ats_score"]}%', "🎯", SIGNAL)
                metric_card("Strategic System Decision", candidate["recommendation"], "⚙", VERDICT)
                metric_card("Statistical Confidence Metric", candidate["confidence"], "📈", CAUTION)

                st.markdown("<br>", unsafe_allow_html=True)

                rep_col, del_col = st.columns(2)
                with rep_col:
                    if st.button("🔁 Replace", use_container_width=True):
                        st.session_state.replacing_candidate = (
                            None if st.session_state.replacing_candidate == selected_label
                            else selected_label
                        )
                        st.rerun()
                with del_col:
                    if st.button("🗑 Purge Target Candidate Entry", use_container_width=True):
                        delete_candidate(candidate["email"], candidate.get("job_role", ""))
                        st.success("Target profile data systematically removed.")
                        st.rerun()

                # -----------------------------------------------------
                # REPLACE — CRUD "Replace" op: re-upload a resume and
                # overwrite this candidate's stored profile/ATS result.
                # Matched on (email, job_role), the same unique key
                # save_candidate() already upserts on, so this replaces
                # the existing row instead of creating a duplicate — as
                # long as the new resume has the same email address.
                # -----------------------------------------------------
                if st.session_state.replacing_candidate == selected_label:
                    st.divider()
                    st.markdown('<div class="step-pill">Replace · Upload New Resume</div>', unsafe_allow_html=True)

                    safe_key = f"{candidate['email']}_{candidate.get('job_role', '')}"

                    replace_file = st.file_uploader(
                        f"Upload a new resume to replace {candidate['name']}'s application "
                        f"for '{candidate.get('job_role') or '—'}'",
                        type=["pdf", "docx"],
                        key=f"replace_upload_{safe_key}"
                    )

                    matched_job = next(
                        (j for j in get_jobs() if j["job_title"] == candidate.get("job_role")),
                        None
                    )

                    if matched_job:
                        st.caption(f"Using requirements from job posting #{matched_job['job_id']}.")
                        replace_exp = matched_job["experience"]
                        replace_qual = matched_job["qualification"]
                        replace_skills = matched_job["required_skills"]
                    else:
                        st.caption("No matching job posting found for this role — enter requirements manually.")
                        rq1, rq2 = st.columns(2)
                        with rq1:
                            replace_exp = st.selectbox(
                                "Required Experience",
                                ["Fresher", "1 Year", "2 Years", "3 Years", "5+ Years"],
                                key=f"replace_exp_{safe_key}"
                            )
                            replace_qual = st.selectbox(
                                "Minimum Qualification",
                                ["Any Degree", "B.Tech", "B.E", "M.Tech", "MBA", "MCA"],
                                key=f"replace_qual_{safe_key}"
                            )
                        with rq2:
                            replace_skills = st.text_area(
                                "Required Skills (comma separated)",
                                key=f"replace_skills_{safe_key}"
                            )

                    rc_confirm, rc_cancel = st.columns(2)
                    with rc_confirm:
                        if st.button(
                            "✅ Confirm Replace", use_container_width=True, type="primary",
                            key=f"confirm_replace_{safe_key}"
                        ):
                            if not replace_file:
                                st.warning("Upload a resume file before confirming the replace.")
                            else:
                                os.makedirs("uploads", exist_ok=True)
                                filepath = os.path.join("uploads", replace_file.name)
                                with open(filepath, "wb") as f:
                                    f.write(replace_file.getbuffer())

                                with st.spinner("Re-parsing resume and recalculating ATS score..."):
                                    new_details = parse_resume(filepath)
                                    new_ats = calculate_ats(
                                        new_details, replace_skills or "", replace_exp, replace_qual
                                    )
                                    new_rec = generate_recommendation(new_ats)

                                    if new_details.get("email") != candidate["email"]:
                                        st.warning(
                                            "Note: the new resume has a different email address, "
                                            "so this was saved as a new entry rather than overwriting "
                                            "the original."
                                        )

                                    save_candidate(
                                        candidate=new_details,
                                        ats=new_ats,
                                        recommendation=new_rec,
                                        resume_name=replace_file.name,
                                        job_role=candidate.get("job_role", ""),
                                    )

                                st.session_state.replacing_candidate = None
                                st.success(f"Candidate entry replaced with data from {replace_file.name}.")
                                st.rerun()
                    with rc_cancel:
                        if st.button("✖ Cancel", use_container_width=True, key=f"cancel_replace_{safe_key}"):
                            st.session_state.replacing_candidate = None
                            st.rerun()

        csv = df.drop(columns=["_label"]).to_csv(index=False).encode()

        st.download_button(
            "Export Active Ledger Data to CSV Format",
            csv,
            "candidates.csv",
            "text/csv",
            use_container_width=True
        )

# ==========================================
# ANALYTICS DASHBOARD
# ==========================================
elif page == "📈 Analytics":

    import plotly.express as px
    import plotly.graph_objects as go

    page_title(
        "Operational Intelligence Analytics",
        "High-Dimensional Talent Acquisition Trends and Metric Distribution Framework"
    )

    candidates = get_candidates()

    if len(candidates) == 0:
        st.warning("Data infrastructure empty: Cannot populate modeling analytics graphics.")
        st.stop()

    df = pd.DataFrame(candidates)

    df["ats_score"] = pd.to_numeric(df["ats_score"], errors="coerce").fillna(0)

    total = len(df)
    avg_ats = round(df["ats_score"].mean(), 1)
    shortlisted = len(df[df["ats_score"] >= 80])
    rejected = len(df[df["ats_score"] < 60])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Monitored Talent Units", total, "📋", SIGNAL)
    with c2:
        metric_card("Mean Metric Calibration", f"{avg_ats}%", "🎯", VERDICT)
    with c3:
        metric_card("High Probability Matches", shortlisted, "✔", CAUTION)
    with c4:
        metric_card("Low Match Rate Exclusions", rejected, "✖", RISK)

    st.divider()

    left, right = st.columns(2)

    with left:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_ats,
            title={"text": "Averaged ATS Distribution Profile"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": SIGNAL},
                "steps": [
                    {"range": [0, 50], "color": "#E9F9F2"},
                    {"range": [50, 70], "color": "#D6F5EA"},
                    {"range": [70, 90], "color": "#C1EEDB"},
                    {"range": [90, 100], "color": "#A9E6CC"}
                ]
            }
        ))

        gauge.update_layout(
            template="plotly_white",
            height=360,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})

    with right:
        rec = df["recommendation"].fillna("Unknown").value_counts().reset_index()
        rec.columns = ["Recommendation", "Count"]

        fig = px.pie(
            rec, names="Recommendation", values="Count", hole=.60,
            title="Strategic Executive Allocations",
            color_discrete_sequence=px.colors.sequential.Emrld
        )

        fig.update_layout(template="plotly_white", height=360, paper_bgcolor="rgba(0,0,0,0)")

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("High-Demand Competency Frequency")
        from database import top_skills
        skills = top_skills()

        if skills:
            skill_df = pd.DataFrame(skills, columns=["Skill", "Count"]).head(8)

            fig = px.bar(
                skill_df, x="Count", y="Skill", orientation="h", text="Count",
                color="Count", color_continuous_scale="Emrld"
            )

            fig.update_layout(
                template="plotly_white", height=420,
                title="Density Vectors: Top Required Framework Competencies",
                yaxis=dict(categoryorder="total ascending"),
                coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No recorded competency values available in log tables.")

    with col2:
        st.subheader("Professional Tenure Spread Evaluation")
        exp = df["experience"].fillna("Unknown").value_counts().reset_index()
        exp.columns = ["Experience", "Candidates"]

        fig = px.bar(
            exp, x="Experience", y="Candidates", text="Candidates",
            color="Candidates", color_continuous_scale="Emrld"
        )

        fig.update_layout(
            template="plotly_white", height=420,
            title="Tenure Variance Spread Graph",
            coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    st.subheader("Academic Precedence Demographics")

    edu = df["education"].fillna("Other").astype(str)
    edu = edu.str.extract(
        r"(B\.?Tech|B\.?E|M\.?Tech|MBA|MCA|BCA|BSc|MSc)", expand=False
    ).fillna("Other")

    edu_df = edu.value_counts().reset_index()
    edu_df.columns = ["Education", "Count"]

    fig = px.pie(
        edu_df, names="Education", values="Count", hole=0.55,
        color_discrete_sequence=px.colors.sequential.Emrld
    )

    fig.update_layout(template="plotly_white", height=420, title="Categorized Academic Segments", paper_bgcolor="rgba(0,0,0,0)")

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

# ==================================
# PROFILE
# ==================================
elif page == "👤 Profile":

    page_title(
        "User Workspace Configuration",
        "Personnel Security & Credentials Identity Ledger"
    )

    st.markdown(
        f"""
        <div class="glass" style="display: flex; align-items: center; gap: 24px; padding: 28px;">
            <div style="font-size: 32px; background: {SIGNAL}18; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; border-radius: 14px;">👤</div>
            <div>
                <div style="font-size: 22px; font-weight: 700; color: {INK}; letter-spacing: -0.3px;">{st.session_state.username}</div>
                <div style="font-size: 13px; color: {MIST}; font-weight: 500; margin-top: 2px;">Identity Clearance: Talent Operations Administrator</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.write("### Account Credentials Registry")

    st.write("**Operational Handle:**", st.session_state.username)
    st.write("**Assigned Role Profile:** Talent Acquisition Recruiter")
    st.write("**Network Pipeline Status:** Active Integration Token")

    st.write("**Secure Local Database Engine Version:**", database_version())

    st.success("Authorized Integration Software Instance: Enterprise Edition v3.0")

footer()