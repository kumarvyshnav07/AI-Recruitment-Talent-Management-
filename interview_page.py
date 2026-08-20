import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date, time as dtime

from database import get_jobs, get_candidates, get_candidates_for_role
from ai_interview import engine, DIFFICULTY_LEVELS
from interview_db import (
    init_interview_db,
    update_candidate_stage,
    update_recruiter_notes,
    create_session,
    get_sessions,
    get_sessions_for_candidate,
    get_answers,
    update_hr_reply,
    delete_session,
)
from ui import metric_card, SIGNAL, VERDICT, CAUTION, RISK, MINT_A, MIST

DIFFICULTY_COLORS = {"Beginner": VERDICT, "Intermediate": CAUTION, "Advanced": RISK}
MAX_QUESTIONS = 8  # session auto-wraps up after this many answered turns


def _difficulty_badge(level: str) -> str:
    color = DIFFICULTY_COLORS.get(level, SIGNAL)
    return (
        f'<span style="background:{color}18; color:{color}; padding:2px 8px; '
        f'border-radius:999px; font-size:10px; font-weight:700; margin-left:6px;">{level}</span>'
    )


def _matched_job_for_candidate(candidate, jobs):
    """Best-effort lookup of the job posting a candidate applied to, so
    an interview session can be tied to a job_id."""
    return next((j for j in jobs if j.get("job_title") == candidate.get("job_role")), None)


def _render_live_score_chart(eval_log):
    """Line chart of every scored dimension across the session so far,
    with difficulty markers underneath — the recruiter can watch the
    candidate trend up/down turn-by-turn instead of only seeing averages."""
    x = list(range(1, len(eval_log) + 1))
    series = {
        "Technical": ([e["evaluation"].get("technical_score", 0) for e in eval_log], SIGNAL),
        "Communication": ([e["evaluation"].get("communication_score", 0) for e in eval_log], VERDICT),
        "Confidence": ([e["evaluation"].get("confidence_score", 0) for e in eval_log], CAUTION),
        "Problem Solving": ([e["evaluation"].get("problem_solving_score", 0) for e in eval_log], MINT_A),
    }

    fig = go.Figure()
    for label, (values, color) in series.items():
        fig.add_trace(go.Scatter(
            x=x, y=values, mode="lines+markers", name=label,
            line=dict(color=color, width=2.5), marker=dict(size=7),
        ))

    difficulties = [e.get("difficulty", "Intermediate") for e in eval_log]
    fig.add_trace(go.Scatter(
        x=x, y=[-0.6] * len(x), mode="markers+text", name="Difficulty",
        marker=dict(size=10, color=[DIFFICULTY_COLORS.get(d, SIGNAL) for d in difficulties], symbol="diamond"),
        text=difficulties, textposition="bottom center", textfont=dict(size=10, color=MIST),
        hoverinfo="text", showlegend=False,
    ))

    fig.update_layout(
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        xaxis=dict(title="Question #", tickmode="linear", dtick=1, showgrid=False),
        yaxis=dict(title="Score /10", range=[-1.2, 10.5], gridcolor="#D7F2E6"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_interview_page():
    init_interview_db()

    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="font-size: 28px; font-weight: 800; color: #24473B;">Interview Workspace</div>
            <div style="font-size: 14px; color: #5C7A6E;">Generate interview questions, run live sessions, and review AI-scored evaluations</div>
        </div>
    """, unsafe_allow_html=True)

    jobs = get_jobs()
    candidates = get_candidates()

    if not jobs:
        st.warning("Please create a job posting first under Job Postings.")
        return

    # Three Recruiter Tabs: live interview workspace, scored evaluations,
    # and the interview pipeline (scheduling + candidate status + replies)
    tab_ppt_layout, tab_evaluations, tab_pipeline = st.tabs([
        "🎙️ Live Interview",
        "📊 Evaluation & Hiring Decision",
        "📋 Interview Pipeline"
    ])

    # ==========================================================
    # TAB 1: LIVE INTERVIEW WORKSPACE
    # ==========================================================
    with tab_ppt_layout:
        # ------------------------------------------------------
        # MODULE 1: INTERVIEW QUESTION GENERATOR
        # ------------------------------------------------------
        st.markdown("""
            <div class="glass" style="padding:16px; margin-bottom:15px;">
                <div style="font-size: 18px; font-weight: 700; color: #0F2B22;">❓ Interview Question Generator</div>
            </div>
        """, unsafe_allow_html=True)

        q1, q2 = st.columns(2)
        with q1:
            job_titles = [j['job_title'] for j in jobs]
            selected_job_title = st.selectbox("Job Position", job_titles, key="rec_job_select")
            selected_job = next(j for j in jobs if j['job_title'] == selected_job_title)
        with q2:
            question_type = st.selectbox(
                "Question Type",
                ["All Types", "Technical Skills", "Behavioural", "Situational"],
                key="rec_q_type"
            )

        d1, d2 = st.columns(2)
        with d1:
            difficulty = st.select_slider(
                "Generate Around Difficulty",
                options=DIFFICULTY_LEVELS,
                value="Intermediate"
            )
        with d2:
            difficulty_filter = st.selectbox(
                "Filter Displayed Questions",
                ["All Levels"] + DIFFICULTY_LEVELS,
                key="rec_difficulty_filter"
            )

        role_candidates = get_candidates_for_role(selected_job_title)
        cand_names = [f"{c['name']} (ATS: {c['ats_score']}%)" for c in role_candidates] if role_candidates else ["Generic Profile"]
        selected_cand_idx = st.selectbox("Select Candidate Profile", range(len(cand_names)), format_func=lambda x: cand_names[x])
        selected_candidate = role_candidates[selected_cand_idx] if role_candidates else {
            "name": "Generic Candidate", "experience": "2 Years", "ats_score": 75,
            "skills": selected_job.get("required_skills", ""), "projects": [], "certifications": []
        }

        if st.button("⚡ Generate AI Questions", use_container_width=True, type="primary"):
            with st.spinner("Analyzing candidate profile & job requirements..."):
                try:
                    st.session_state["generated_questions"] = engine.generate_questions(
                        candidate=selected_candidate,
                        job=selected_job,
                        difficulty=difficulty
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("<br>", unsafe_allow_html=True)

        if "generated_questions" in st.session_state:
            qs = st.session_state["generated_questions"]

            def _passes_filter(item):
                return difficulty_filter == "All Levels" or item["difficulty"] == difficulty_filter

            flat_q = []
            if question_type in ["All Types", "Technical Skills"]:
                flat_q.extend([(q["question"], "Technical", "Experience-based", "3-5 min response", q["difficulty"])
                               for q in qs.get("technical", []) if _passes_filter(q)])
            if question_type in ["All Types", "Behavioural"]:
                flat_q.extend([(q["question"], "Behavioral", "Communication", "2-4 min response", q["difficulty"])
                               for q in qs.get("behavioural", []) if _passes_filter(q)])
            if question_type in ["All Types", "Situational"]:
                flat_q.extend([(q["question"], "Situational", "Scenario-based", "4-6 min response", q["difficulty"])
                               for q in qs.get("situational", []) if _passes_filter(q)])

            if not flat_q:
                st.info("No questions match the current type/difficulty filters.")

            for idx, (q_text, cat, tag, est, level) in enumerate(flat_q, start=1):
                st.markdown(f"""
                    <div style="background:#F1FBF7; border:1px solid #BFEBDA; border-radius:10px; padding:12px; margin-bottom:10px;">
                        <div style="display:flex; gap:10px; align-items:flex-start;">
                            <span style="background:#0DAF9C; color:white; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:bold; flex-shrink:0;">
                                {idx}
                            </span>
                            <div style="font-size:13px; color:#24473B; font-weight:600; line-height:1.4;">
                                {q_text} {_difficulty_badge(level)}
                            </div>
                        </div>
                        <div style="margin-top:6px; font-size:11px; color:#5C7A6E; margin-left:32px;">
                            {cat} • {tag} • {est}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            follow_ups = qs.get("follow_up", [])
            if follow_ups:
                with st.expander(f"🔁 AI Follow-up Questions ({len(follow_ups)}) — skill-probing, ask after an initial answer"):
                    for i, fq in enumerate(follow_ups, start=1):
                        st.markdown(f"**{i}.** {fq}")

    # ==========================================================
    # TAB 2: RECRUITER AI EVALUATION & SELECTION DASHBOARD
    # ==========================================================
    with tab_evaluations:
        st.markdown("""
            <div class="glass" style="padding:16px; margin-bottom:15px;">
                <div style="font-size: 18px; font-weight: 700; color: #0F2B22;">🎯 AI Response Scoring & Candidate Selection</div>
                <div style="font-size: 12px; color: #5C7A6E;">View live interview scores, AI performance feedback, and update selection status</div>
            </div>
        """, unsafe_allow_html=True)

        if candidates:
            cand_labels = [f"{c['name']} ({c.get('job_role', 'Applicant')})" for c in candidates]
            chosen_cand_idx = st.selectbox(
                "Select Candidate to Inspect",
                range(len(candidates)),
                format_func=lambda x: cand_labels[x],
                key="eval_inspect_select"
            )
            inspect_cand = candidates[chosen_cand_idx]

            eval_logs = st.session_state.get(f"eval_history_{inspect_cand['id']}", [])

            if not eval_logs:
                st.info("No interview responses submitted by this candidate yet.")
            else:
                # Average live metrics calculated by AI
                tech_avg = round(sum(e["evaluation"].get("technical_score", 0) for e in eval_logs) / len(eval_logs), 1)
                comm_avg = round(sum(e["evaluation"].get("communication_score", 0) for e in eval_logs) / len(eval_logs), 1)
                conf_avg = round(sum(e["evaluation"].get("confidence_score", 0) for e in eval_logs) / len(eval_logs), 1)

                m1, m2, m3 = st.columns(3)
                with m1: metric_card("Technical Score", f"{tech_avg}/10", "⚡", SIGNAL)
                with m2: metric_card("Communication", f"{comm_avg}/10", "🗣", VERDICT)
                with m3: metric_card("Confidence", f"{conf_avg}/10", "📈", CAUTION)

                st.markdown("<br>", unsafe_allow_html=True)
                st.write("**Question-by-Question AI Evaluations**")

                for idx, log in enumerate(eval_logs, start=1):
                    ev = log["evaluation"]
                    with st.expander(f"Question #{idx}: {log['question'][:50]}..."):
                        if not ev.get("ai_evaluated", True):
                            st.warning("⚠️ Placeholder score — Gemini call failed for this turn, not a real AI evaluation.")
                        st.write(f"**Question:** {log['question']}")
                        st.write(f"**Answer:** {log['answer']}")
                        st.write(f"**Scores:** Tech: {ev.get('technical_score', 0)}/10 | Comm: {ev.get('communication_score', 0)}/10")
                        if ev.get("strengths"): st.success(f"**Strengths:** {', '.join(ev.get('strengths', []))}")
                        if ev.get("weaknesses"): st.warning(f"**Weaknesses:** {', '.join(ev.get('weaknesses', []))}")
                        if ev.get("improvement"): st.info(f"**Improvement:** {', '.join(ev.get('improvement', []))}")

            # Module 3: final interview performance report, if one was generated
            report = st.session_state.get(f"report_{inspect_cand['id']}")
            if report:
                st.markdown("---")
                st.markdown("### 🏁 Interview Performance Report")
                pr1, pr2, pr3, pr4 = st.columns(4)
                with pr1: metric_card("Overall Score", f"{report['overall_score']}/10", "🏁", SIGNAL)
                with pr2: metric_card("Technical Avg", f"{report['average_technical_score']}/10", "⚡", VERDICT)
                with pr3: metric_card("Communication Avg", f"{report['average_communication_score']}/10", "🗣", CAUTION)
                with pr4: metric_card("Problem Solving Avg", f"{report['average_problem_solving_score']}/10", "🧩", RISK)

                pcol1, pcol2 = st.columns(2)
                with pcol1:
                    st.write("**Key Strengths**")
                    for s in report["strengths"] or ["—"]:
                        st.write(f"✅ {s}")
                with pcol2:
                    st.write("**Areas to Improve**")
                    for w in report["weaknesses"] or ["—"]:
                        st.write(f"⚠️ {w}")

                st.info(report["final_comment"])

            # Past, persisted sessions for this candidate (survives refresh/relogin).
            # Each completed session opens into the full report Milestone 4
            # requires: every question, the candidate's answer/transcript,
            # text/voice mode, per-question scores, and the final verdict —
            # not just the one-line summary this used to show.
            past_sessions = get_sessions_for_candidate(inspect_cand["id"])
            completed_sessions = [s for s in past_sessions if s.get("status") == "Completed"]
            if completed_sessions:
                st.markdown(f"**🗂 Interview History** ({len(completed_sessions)} completed session(s))")
                for s in completed_sessions:
                    with st.expander(
                        f"{s['created_at']:%d %b %Y} — Score: {s.get('overall_score', 0)}/10"
                        f"{' — ' + s.get('recommendation', '') if s.get('recommendation') else ''}"
                    ):
                        session_answers = get_answers(s["id"])
                        if not session_answers:
                            st.caption("No per-question answers were logged for this session.")
                        for a in session_answers:
                            mode = a.get("answer_mode") or "text"
                            mode_tag = "🎙️ Voice" if mode == "voice" else "💬 Text"
                            st.write(f"**Q:** {a['question']}  ·  {mode_tag}")
                            if a.get("skipped"):
                                st.caption("⏭️ Skipped — not counted toward the score.")
                                st.markdown("---")
                                continue
                            st.write(f"**Answer:** {a.get('answer', '—')}")
                            if mode == "voice" and a.get("transcript") and a.get("transcript") != a.get("answer"):
                                st.caption(f"Raw transcript (before candidate edits): {a['transcript']}")
                            if mode == "voice" and a.get("transcription_status") == "failed":
                                st.caption("⚠️ Transcription failed for this turn — see answer text for what was ultimately scored.")
                            sc1, sc2, sc3, sc4 = st.columns(4)
                            sc1.metric("Technical", f"{a.get('technical_score', 0)}/10")
                            sc2.metric("Communication", f"{a.get('communication_score', 0)}/10")
                            sc3.metric("Confidence", f"{a.get('confidence_score', 0)}/10")
                            sc4.metric("Problem Solving", f"{a.get('problem_solving_score', 0)}/10")
                            if a.get("strengths"): st.success(f"Strengths: {a['strengths']}")
                            if a.get("weaknesses"): st.warning(f"Areas to improve: {a['weaknesses']}")
                            if a.get("suggestion"): st.info(f"Suggestion: {a['suggestion']}")
                            st.markdown("---")

            # Recruiter notes — Module 2: "manage recruiter feedback"
            st.markdown("---")
            st.markdown("### 📝 Recruiter Notes")
            notes_value = st.text_area(
                "Internal notes about this candidate (not shown to the candidate)",
                value=inspect_cand.get("recruiter_notes") or "",
                key=f"notes_{inspect_cand['id']}",
                height=100,
            )
            if st.button("💾 Save Notes", key=f"save_notes_{inspect_cand['id']}"):
                if update_recruiter_notes(inspect_cand["id"], notes_value):
                    st.success("Recruiter notes saved.")
                else:
                    st.error("Could not save notes — check the database connection.")

            # Recruiter Decision & Stage Selection
            st.markdown("---")
            st.markdown("### 🏆 Candidate Selection Decision")
            c1, c2 = st.columns([2, 1])
            with c1:
                current_stage = inspect_cand.get("stage", "Interview in progress")
                stages = ["Applied", "Screening", "Interview in progress", "Selected", "Rejected"]
                default_idx = stages.index(current_stage) if current_stage in stages else 2
                new_stage = st.selectbox("Candidate Hiring Status", stages, index=default_idx)
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Save Selection Decision", use_container_width=True, type="primary"):
                    update_candidate_stage(inspect_cand["id"], new_stage)
                    st.success(f"Candidate '{inspect_cand['name']}' set to '{new_stage}'.")
                    st.rerun()

    # ==========================================================
    # TAB 3: INTERVIEW PIPELINE — scheduling, status, HR replies
    # ==========================================================
    with tab_pipeline:
        st.markdown("""
            <div class="glass" style="padding:16px; margin-bottom:15px;">
                <div style="font-size: 18px; font-weight: 700; color: #0F2B22;">🗂 Candidate Interview Pipeline</div>
                <div style="font-size: 12px; color: #5C7A6E;">Schedule interviews, track every candidate's status, and reply once they've finished</div>
            </div>
        """, unsafe_allow_html=True)

        # ------------------------------------------------------
        # Schedule an Interview — centered
        # ------------------------------------------------------
        sp_l, sp_c, sp_r = st.columns([1, 2, 1])
        with sp_c:
            st.markdown("""
                <div class="glass" style="padding:16px;">
                    <div style="font-size: 16px; font-weight: 700; color: #0F2B22;">📅 Schedule an Interview</div>
                </div>
            """, unsafe_allow_html=True)

            if candidates:
                cand_labels_p = [f"{c['name']} ({c.get('job_role', 'Applicant')})" for c in candidates]
                sched_cand_idx = st.selectbox(
                    "Candidate", range(len(candidates)),
                    format_func=lambda x: cand_labels_p[x],
                    key="sched_cand_select_pipeline"
                )
                sched_cand = candidates[sched_cand_idx]
                sched_job = _matched_job_for_candidate(sched_cand, jobs)

                sc1, sc2 = st.columns(2)
                with sc1:
                    sched_date = st.date_input("Interview Date", value=date.today(), key="sched_date_p")
                    sched_interviewer = st.text_input(
                        "Interviewer", value=st.session_state.get("username", ""), key="sched_interviewer_p"
                    )
                with sc2:
                    sched_time = st.time_input("Interview Time", value=dtime(hour=10, minute=0), key="sched_time_p")
                    sched_difficulty = st.selectbox("Planned Difficulty", DIFFICULTY_LEVELS, key="sched_difficulty_p")

                if st.button("📅 Schedule Interview", use_container_width=True, key="schedule_btn_p", type="primary"):
                    scheduled_dt = datetime.combine(sched_date, sched_time)
                    new_session_id = create_session(
                        candidate_id=sched_cand["id"],
                        job_id=sched_job["job_id"] if sched_job else None,
                        interviewer=sched_interviewer.strip() or "Recruiter",
                        difficulty=sched_difficulty,
                        interview_date=scheduled_dt,
                        status="Scheduled",
                    )
                    if new_session_id:
                        st.success(f"Interview scheduled for {sched_cand['name']} on {scheduled_dt:%d %b %Y, %I:%M %p}.")
                        st.rerun()
                    else:
                        st.error("Could not schedule the interview — check the database connection.")
            else:
                st.info("No candidates yet — process a resume first under Upload Resume.")

        st.markdown("---")

        # ------------------------------------------------------
        # Candidate Interview Status — filterable list
        # ------------------------------------------------------
        st.markdown("### 📋 Candidate Interview Status")

        f1, f2 = st.columns(2)
        with f1:
            status_filter = st.selectbox(
                "Filter by Interview Status", ["All", "Upcoming", "In Progress", "Completed"], key="pipeline_status_filter"
            )
        with f2:
            stage_filter = st.selectbox(
                "Filter by Hiring Stage",
                ["All", "Applied", "Screening", "Interview in progress", "Selected", "Rejected"],
                key="pipeline_stage_filter"
            )

        all_sessions = get_sessions()
        cand_by_id = {c["id"]: c for c in candidates}
        STATUS_LABELS = {"Scheduled": "Upcoming", "In Progress": "In Progress", "Completed": "Completed"}
        STATUS_COLORS = {"Upcoming": CAUTION, "In Progress": SIGNAL, "Completed": VERDICT}

        rows = []
        for s in all_sessions:
            c = cand_by_id.get(s["candidate_id"])
            if not c:
                continue
            display_status = STATUS_LABELS.get(s.get("status"), s.get("status"))
            if status_filter != "All" and display_status != status_filter:
                continue
            stage = c.get("stage") or "Applied"
            if stage_filter != "All" and stage != stage_filter:
                continue
            rows.append((s, c, display_status, stage))

        if not rows:
            st.caption("No interviews match the current filters.")
        else:
            for s, c, display_status, stage in rows:
                status_color = STATUS_COLORS.get(display_status, MIST)
                st.markdown(f"""
                    <div class="glass" style="padding:14px 18px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                            <div>
                                <div style="font-weight:700; font-size:15px; color:#0F2B22;">
                                    {c['name']} <span style="font-weight:400; color:#5C7A6E; font-size:12px;">— {c.get('job_role','')}</span>
                                </div>
                                <div style="font-size:12px; color:#5C7A6E; margin-top:2px;">
                                    {s['interview_date']:%d %b %Y, %I:%M %p} • Interviewer: {s.get('interviewer') or '—'}
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <span style="background:{status_color}18; color:{status_color}; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:700;">
                                    {display_status}
                                </span>
                                <div style="font-size:11px; color:#5C7A6E; margin-top:4px;">Stage: {stage}</div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if s.get("status") == "Completed":
                    with st.expander(f"💬 AI Score: {s.get('overall_score', 0)}/10 — Reply to {c['name']}"):
                        reply_val = st.text_area(
                            "Message to candidate — they will see this on their dashboard",
                            value=s.get("hr_reply") or "",
                            key=f"reply_{s['id']}",
                            height=80,
                        )
                        if st.button("💾 Send Reply", key=f"send_reply_{s['id']}", use_container_width=True):
                            if update_hr_reply(s["id"], reply_val):
                                st.success("Reply sent to candidate.")
                                st.rerun()
                            else:
                                st.error("Could not save the reply — check the database connection.")
                else:
                    dcol1, dcol2 = st.columns([4, 1])
                    with dcol2:
                        if st.button("🗑️ Delete", key=f"del_sess_{s['id']}", use_container_width=True):
                            if delete_session(s["id"]):
                                st.success("Interview removed from the schedule.")
                                st.rerun()
                            else:
                                st.error("Could not delete — check the database connection.")
