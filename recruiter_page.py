"""
recruiter_page.py
==================
Recruiter-facing workspace — Dashboard, Job Postings, Upload Resume,
Interviews, Candidates, Analytics, and Profile.

This is a straight extraction of the recruiter `if page == ...:` chain
that used to live directly in app.py, into its own module — mirroring
the app's existing candidate_page.py pattern so both portals are easy
to find and work on independently. No logic was changed: every
database call, ATS call, and UI call below is byte-for-byte the same
code that ran inline in app.py, just moved and wrapped in a function.

app.py now does:
    from recruiter_page import render_recruiter_dashboard
    ...
    if is_recruiter:
        render_recruiter_dashboard(page)
"""
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from database import (
    get_candidates,
    get_candidates_for_role,
    get_dashboard_stats,
    save_candidate,
    search_candidates,
    delete_candidate,
    database_version,
    get_jobs,
    create_job,
    update_job,
    delete_job,
    top_skills,
)
from job_matching import match_candidates_to_job
from resume_parser import parse_resume
from ats_engine import calculate_ats, generate_recommendation
from interview_page import render_interview_page
from interview_db import get_sessions
from ui import (
    metric_card,
    page_title,
    profile_field,
    chip_list,
    list_card,
    full_report_modal,
    INK,
    MIST,
    SIGNAL,
    VERDICT,
    CAUTION,
    RISK,
    GOLD,
    INDIGO,
    VIOLET,
    MINT_A,
    MINT_C,
    SKY,
    welcome_hero,
    ats_donut,
    pipeline_funnel,
    skill_demand_bars,
    recent_candidates_mini,
    insight_list,
)


def render_recruiter_dashboard(page: str):
    """Renders whichever recruiter section is selected in the sidebar
    nav (`page`, e.g. "📊 Dashboard", "🗂 Job Postings", ...). Called
    from app.py once `is_recruiter` and the sidebar nav radio have been
    resolved. app.py still owns login/session/sidebar/footer — this
    function only owns the main-content routing that used to be the
    long if/elif chain at the bottom of app.py.
    """

    if page == "📊 Dashboard":

        stats = get_dashboard_stats()
        all_candidates = get_candidates()
        try:
            all_sessions = get_sessions()
        except Exception:
            all_sessions = []
        dash_jobs = get_jobs()

        interview_count = len(all_sessions)
        hires_count = sum(1 for r in all_candidates if (r.get("stage") or "") == "Selected")
        rejected_count = sum(1 for r in all_candidates if (r.get("stage") or "") == "Rejected")
        awaiting_count = sum(1 for r in all_candidates if (r.get("stage") or "Applied") == "Applied")
        job_count = len(dash_jobs)
        display_name = st.session_state.get("username", "Recruiter")

        left_col, right_col = st.columns([2, 1], gap="large")

        # ==================================================================
        # LEFT COLUMN -- welcome hero, KPIs, charts, tables
        # ==================================================================
        with left_col:

            welcome_hero(
                display_name,
                subtitle="Your AI Recruitment Copilot is ready to find, evaluate and hire the best talent — 10x faster.",
                primary_label="Start Smart Hiring →",
                primary_nav="📤 Upload Resume",
                secondary_label="View Analytics",
                secondary_nav="📈 Analytics",
            )
            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

            # ---- Primary KPI row (matches reference screenshot) ----
            shortlist_pct = round(stats["shortlisted"] / stats["total_candidates"] * 100) if stats["total_candidates"] else 0
            hire_pct = round(hires_count / stats["total_candidates"] * 100) if stats["total_candidates"] else 0

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                metric_card("Total Candidates", stats["total_candidates"], icon="👥",
                            color=SKY, trend=f"+{stats['today_uploads']} today" if stats["today_uploads"] else None)
            with k2:
                metric_card("Shortlisted", stats["shortlisted"], icon="🎯",
                            color=VERDICT, trend=f"{shortlist_pct}% of pool" if stats["total_candidates"] else None)
            with k3:
                metric_card("Interviews Scheduled", interview_count, icon="🎙️",
                            color=VIOLET, trend=f"{len(all_sessions)} sessions recorded")
            with k4:
                metric_card("Hires", hires_count, icon="🏆",
                            color=GOLD, trend=f"{hire_pct}% hire rate" if stats["total_candidates"] else None)

            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

            # ---- Secondary KPI row -- fills out the full stat set the
            # milestone brief calls for (job openings, rejected, avg score) ----
            k5, k6, k7, k8 = st.columns(4)
            with k5:
                metric_card("Job Openings", job_count, icon="🗂", color=INDIGO)
            with k6:
                metric_card("Rejected", rejected_count, icon="🚫", color=RISK)
            with k7:
                metric_card("Avg. Hiring Score", f"{stats.get('average_ats', 0)}", icon="📐", color=MINT_A)
            with k8:
                metric_card("Awaiting Review", awaiting_count, icon="⏳", color=CAUTION)

            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

            # ---- ATS Score Distribution (donut) + Hiring Pipeline (funnel) ----
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.markdown('<div class="glass">', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="font-size:16px; font-weight:800; color:{INK}; '
                    f'font-family:\'Space Grotesk\'; margin-bottom:16px;">🎯 ATS Score Distribution</div>',
                    unsafe_allow_html=True,
                )
                scores = [c.get("ats_score", 0) or 0 for c in all_candidates]
                buckets = {
                    "Highly Recommended (≥85)": sum(1 for s in scores if s >= 85),
                    "Recommended (70-84)": sum(1 for s in scores if 70 <= s < 85),
                    "Consider (50-69)": sum(1 for s in scores if 50 <= s < 70),
                    "Not Recommended (<50)": sum(1 for s in scores if s < 50),
                }
                ats_donut(buckets, [VERDICT, SIGNAL, CAUTION, RISK], len(scores))
                st.markdown('</div>', unsafe_allow_html=True)

            with chart_col2:
                applied = len(all_candidates)
                screening = sum(1 for c in all_candidates if (c.get("ats_score", 0) or 0) >= 50)
                interview_stage = len({s["candidate_id"] for s in all_sessions}) if all_sessions else 0
                hired_stage = hires_count
                pipeline_funnel([
                    ("Applied", applied, SKY),
                    ("Screening", screening, VIOLET),
                    ("Interview", interview_stage, MINT_A),
                    ("Hired", hired_stage, GOLD),
                ])

            # ---- Recent Candidates + Skill Demand ----
            table_col1, table_col2 = st.columns(2)

            with table_col1:
                recent_rows = sorted(
                    all_candidates,
                    key=lambda r: r.get("updated_at") or r.get("created_at") or "",
                    reverse=True,
                )[:5]
                recent_candidates_mini(recent_rows)

            with table_col2:
                skills = top_skills()[:5]
                skill_demand_bars(skills, color=SIGNAL)

        # ==================================================================
        # RIGHT COLUMN -- AI Copilot, insights, quick actions, promo
        # ==================================================================
        with right_col:

            st.markdown(f"""
                <div class="glass copilot-card">
                    <div style="display:flex; align-items:center; justify-content:space-between;">
                        <div style="font-size:16px; font-weight:800; color:{INK}; font-family:'Space Grotesk';">✨ AI Copilot</div>
                        <span style="background:{VERDICT}18; color:{VERDICT}; padding:3px 10px; border-radius:999px;
                            font-size:11px; font-weight:700; border:1px solid {VERDICT}44;">● Online</span>
                    </div>
                    <div style="font-size:12.5px; color:{MIST}; margin-top:8px; line-height:1.5;">
                        Ask anything about candidates, ATS scoring, or hiring trends.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            copilot_q = st.text_input("Ask AI Copilot...", key="dash_copilot_input",
                                       label_visibility="collapsed",
                                       placeholder="Ask AI Copilot...")
            if copilot_q:
                q = copilot_q.lower()
                if "skill" in q:
                    top = top_skills()[:1]
                    reply = (f"The most in-demand skill right now is **{top[0][0]}**, "
                             f"appearing in {top[0][1]} candidate profiles." if top
                             else "No skill data is available yet.")
                elif "shortlist" in q:
                    reply = f"You currently have **{stats['shortlisted']}** shortlisted candidates out of {stats['total_candidates']} total."
                elif "hire" in q or "select" in q:
                    reply = f"**{hires_count}** candidates have been marked as Selected so far."
                elif "reject" in q:
                    reply = f"**{rejected_count}** candidates have been marked as Rejected so far."
                elif "job" in q or "opening" in q:
                    reply = f"There are currently **{job_count}** open job postings."
                elif "interview" in q:
                    reply = f"**{interview_count}** interview sessions have been recorded."
                elif "average" in q or "score" in q:
                    reply = f"The average ATS score across all candidates is **{stats.get('average_ats', 0)}**."
                else:
                    reply = (f"Here's a quick snapshot: **{stats['total_candidates']}** candidates, "
                             f"**{stats['shortlisted']}** shortlisted, **{job_count}** open roles, "
                             f"and **{hires_count}** hires so far.")
                st.markdown(
                    f'<div class="insight-row"><div style="font-size:15px;">🤖</div>'
                    f'<div style="color:{INK};">{reply}</div></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

            # ---- Recent AI Insights (data-derived, not fabricated copy) ----
            insight_items = []
            top_sk = top_skills()[:1]
            if top_sk:
                insight_items.append((
                    "📈",
                    f"<b>High demand for {top_sk[0][0]}</b><br>"
                    f"<span style='color:{MIST}; font-size:11px;'>{top_sk[0][1]} candidates match this skill</span>",
                    VERDICT,
                ))
            top_candidate = sorted(all_candidates, key=lambda r: r.get("ats_score", 0) or 0, reverse=True)[:1]
            if top_candidate:
                tc = top_candidate[0]
                insight_items.append((
                    "🏅",
                    f"<b>Top candidate match</b><br>"
                    f"<span style='color:{MIST}; font-size:11px;'>{tc.get('name', 'Candidate')} · "
                    f"{tc.get('ats_score', 0)}% ATS score</span>",
                    SIGNAL,
                ))
            if awaiting_count > 0:
                insight_items.append((
                    "⚠️",
                    f"<b>{awaiting_count} candidates awaiting review</b><br>"
                    f"<span style='color:{MIST}; font-size:11px;'>No hiring decision recorded yet</span>",
                    CAUTION,
                ))
            insight_list(insight_items)

            # ---- Quick Actions ----
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:16px; font-weight:800; color:{INK}; '
                f'font-family:\'Space Grotesk\'; margin-bottom:12px;">⚡ Quick Actions</div>',
                unsafe_allow_html=True,
            )
            if st.button("📤  Upload Resume", use_container_width=True, key="qa_upload"):
                st.session_state["_qa_nav"] = "📤 Upload Resume"
                st.rerun()
            if st.button("🗂  Create Job Posting", use_container_width=True, key="qa_job"):
                st.session_state["_qa_nav"] = "🗂 Job Postings"
                st.rerun()
            if st.button("📈  View Analytics", use_container_width=True, key="qa_analytics"):
                st.session_state["_qa_nav"] = "📈 Analytics"
                st.rerun()
            if st.button("👥  View Candidates", use_container_width=True, key="qa_candidates"):
                st.session_state["_qa_nav"] = "📋 Candidates"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- Promo strip ----
            st.markdown(f"""
                <div class="glass" style="background: linear-gradient(155deg, {MINT_C} 0%, {SIGNAL} 55%, {MINT_A} 120%);
                    border: none; color: #06231C;">
                    <div style="font-size:15px; font-weight:800; font-family:'Space Grotesk';">
                        Smarter Hiring. Stronger Teams.
                    </div>
                    <div style="font-size:12.5px; margin-top:6px; opacity:0.9;">
                        Let AI find the right talent for you.
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # ==================================================================
        # FINAL HIRING DECISION -- rank applicants per job by ATS score
        # ==================================================================
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:16px; font-weight:800; color:{INK}; '
            f'font-family:\'Space Grotesk\'; margin-bottom:16px;">🏁 Final Hiring Decision</div>',
            unsafe_allow_html=True,
        )

        if not dash_jobs:
            st.markdown(f'<div style="color:{MIST}; font-size:13px;">No job postings yet — create one to rank applicants.</div>',
                        unsafe_allow_html=True)
        else:
            job_labels = [f"{j.get('job_title', 'Untitled')} · {j.get('company_name', '')}" for j in dash_jobs]
            job_idx = st.selectbox("Select a job posting", options=range(len(dash_jobs)),
                                    format_func=lambda i: job_labels[i], key="fhd_job_select")
            selected_job = dash_jobs[job_idx]
            role = selected_job.get("job_title", "")

            applicants = get_candidates_for_role(role)
            applicants = sorted(applicants, key=lambda r: r.get("ats_score", 0) or 0, reverse=True)

            filter_choice = st.radio(
                "Filter",
                ["All", "Top 5", "Recommended", "Consider", "Not Recommended"],
                horizontal=True, key="fhd_filter", label_visibility="collapsed",
            )
            if filter_choice == "Top 5":
                shown = applicants[:5]
            elif filter_choice == "Recommended":
                shown = [a for a in applicants if (a.get("ats_score", 0) or 0) >= 70]
            elif filter_choice == "Consider":
                shown = [a for a in applicants if 50 <= (a.get("ats_score", 0) or 0) < 70]
            elif filter_choice == "Not Recommended":
                shown = [a for a in applicants if (a.get("ats_score", 0) or 0) < 50]
            else:
                shown = applicants

            if not shown:
                st.markdown(f'<div style="color:{MIST}; font-size:13px; padding-top:8px;">No applicants match this filter.</div>',
                            unsafe_allow_html=True)
            else:
                medals = ["🥇", "🥈", "🥉"]
                rows_html = ""
                for i, cand in enumerate(shown):
                    score = cand.get("ats_score", 0) or 0
                    if score >= 85:
                        badge_color, badge_label = VERDICT, "Highly Recommended"
                    elif score >= 70:
                        badge_color, badge_label = SIGNAL, "Recommended"
                    elif score >= 50:
                        badge_color, badge_label = CAUTION, "Consider"
                    else:
                        badge_color, badge_label = RISK, "Not Recommended"
                    rank_marker = medals[i] if i < 3 else f"#{i + 1}"
                    rows_html += f"""
                    <div class="mini-row">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <span style="font-size:16px; min-width:28px;">{rank_marker}</span>
                            <div>
                                <div class="mini-name">{cand.get('name', 'Candidate')}</div>
                                <div class="mini-sub">{cand.get('email', '')}</div>
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:14px;">
                            <span style="font-family:'Space Grotesk'; font-weight:800; color:{INK}; font-size:14px;">{score}%</span>
                            <span class="mini-badge" style="background:{badge_color}18; color:{badge_color}; border:1px solid {badge_color}44;">{badge_label}</span>
                        </div>
                    </div>
                    """
                st.markdown(rows_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

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

                    st.session_state.ats_result = None
                    st.session_state.recommendation = None

                details = st.session_state.parsed_details

                st.success("✅ Parsing complete — candidate profile extracted below.")

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
    # INTERVIEW ASSISTANT
    # ==================================
    elif page == "🎙️ Interviews":
        render_interview_page()

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