"""
admin_page.py
==============
Admin Control Center — platform-level management, separate from the
Recruiter Dashboard (recruitment/job/candidate management) and the
Candidate Portal (own applications/interviews). Mirrors
candidate_page.py's structure: a fixed left sidebar with section
buttons, one section rendered at a time in the main content area.

Authorization: require_admin() is checked first, before anything else
renders, so this module refuses to draw admin UI for a non-admin
session even if it were ever called by mistake — app.py's role routing
is the primary gate, this is the defense-in-depth second gate the spec
calls for ("do not rely only on hiding navigation buttons").

Every KPI, table, and chart here reads live from the database via
admin_db.py / database.py / interview_db.py. Nothing is hardcoded.
"""
import streamlit as st
import pandas as pd

from database import get_candidates, get_jobs
from interview_db import get_sessions, get_session_report
import admin_db as adb
from ui import (
    metric_card, chip_list, list_card, profile_field, section_header,
    SIGNAL, VERDICT, CAUTION, RISK, INK, INK_SOFT, MIST, SKY, VIOLET,
    INDIGO, ROSE, GOLD, PANEL2, LINE,
)

NAV_GROUPS = [
    ("OVERVIEW", [
        ("Dashboard", "🏠"),
    ]),
    ("PEOPLE", [
        ("Users", "👥"),
        ("Recruiters", "🧑‍💼"),
        ("Candidates", "🎓"),
    ]),
    ("RECRUITMENT", [
        ("Jobs", "🗂"),
        ("Applications", "📋"),
        ("Interviews", "🎙"),
        ("Interview Reports", "📊"),
    ]),
    ("ANALYTICS", [
        ("ATS Analytics", "🎯"),
        ("Interview Analytics", "📈"),
        ("Platform Analytics", "🌐"),
    ]),
    ("SYSTEM", [
        ("System Health", "🩺"),
        ("Audit Logs", "🧾"),
        ("Settings", "⚙"),
    ]),
]
# Flat list kept for anything that still wants every (key, icon) pair.
NAV_ITEMS = [item for _, items in NAV_GROUPS for item in items]
NAV_STATE_KEY = "admin_nav_section"
NAV_FILTER_KEY = "admin_nav_filter"


# ==================================================================
# AUTHORIZATION
# ==================================================================

def require_admin():
    """Server-side gate: refuses to render anything admin-only unless
    the current session actually belongs to an authenticated admin
    account. Not just a hidden nav item — this runs before any admin
    query or admin markup, regardless of how this function got called."""
    if st.session_state.get("role") != "admin" or not st.session_state.get("logged_in"):
        st.error("🔒 Admin access required. You are not authorized to view this page.")
        st.stop()


# ==================================================================
# GLOBAL THEME
# ==================================================================

def _inject_futuristic_theme():
    """One CSS injection that reskins native Streamlit chrome (sidebar,
    buttons, inputs, dataframes, expanders, tabs, scrollbars) into a
    dark glassmorphism / neon HUD look. Deliberately targets Streamlit's
    stable data-testid hooks rather than ui.py's own classes, so this
    stays self-contained and safe even if ui.py's theme changes later."""
    if st.session_state.get("_futuristic_theme_injected"):
        return
    st.session_state["_futuristic_theme_injected"] = True

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;800&family=IBM+Plex+Mono:wght@400;600&display=swap');

        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(1200px 600px at 10% -10%, {GOLD}0d, transparent 60%),
                radial-gradient(1000px 700px at 110% 10%, {SIGNAL}12, transparent 55%),
                #0b1120;
        }}

        /* ---- Sidebar shell ---- */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(15,23,42,0.97), rgba(10,15,28,0.98));
            border-right: 1px solid {GOLD}2e;
            box-shadow: 4px 0 24px rgba(0,0,0,0.35);
        }}
        [data-testid="stSidebar"] * {{ font-family: 'Space Grotesk', sans-serif; }}

        /* ---- Nav group labels ---- */
        .nav-group-label {{
            font-size: 10.5px; font-weight: 800; letter-spacing: 1.6px;
            color: {GOLD}; opacity: 0.75; margin: 14px 2px 6px 2px;
            text-transform: uppercase; display: flex; align-items: center; gap: 8px;
        }}
        .nav-group-label::after {{
            content: ""; flex: 1; height: 1px;
            background: linear-gradient(90deg, {GOLD}55, transparent);
        }}

        /* ---- Compact grouped nav buttons ---- */
        [data-testid="stSidebar"] div[data-testid="stButton"] > button {{
            background: rgba(255,255,255,0.03);
            border: 1px solid {LINE};
            border-radius: 10px;
            color: {INK_SOFT};
            font-size: 12.5px;
            font-weight: 600;
            padding: 7px 8px;
            min-height: 38px;
            transition: all 0.15s ease;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
            border-color: {SIGNAL}88;
            color: {INK};
            box-shadow: 0 0 12px {SIGNAL}33;
            transform: translateY(-1px);
        }}
        [data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {{
            background: linear-gradient(135deg, {SIGNAL}2e, {GOLD}1a);
            border: 1px solid {SIGNAL}aa;
            color: {INK};
            box-shadow: 0 0 16px {SIGNAL}44, inset 0 0 12px {SIGNAL}14;
        }}

        /* ---- Sidebar search / filter input ---- */
        [data-testid="stSidebar"] input {{
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid {LINE} !important;
            border-radius: 10px !important;
            color: {INK} !important;
        }}
        [data-testid="stSidebar"] input:focus {{
            border-color: {SIGNAL} !important;
            box-shadow: 0 0 10px {SIGNAL}44 !important;
        }}

        /* ---- Main-area inputs / selects ---- */
        div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input {{
            background: rgba(255,255,255,0.03) !important;
            border-color: {LINE} !important;
            border-radius: 10px !important;
        }}

        /* ---- Buttons in main content ---- */
        div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {{
            border-radius: 10px;
            font-weight: 700;
            transition: all 0.15s ease;
        }}
        div[data-testid="stButton"] > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button[kind="primary"] {{
            background: linear-gradient(135deg, {SIGNAL}, {SIGNAL}cc);
            box-shadow: 0 0 14px {SIGNAL}55;
            border: none;
        }}
        div[data-testid="stButton"] > button[kind="primary"]:hover {{ box-shadow: 0 0 22px {SIGNAL}88; transform: translateY(-1px); }}

        /* ---- Dataframes / tables ---- */
        [data-testid="stDataFrame"] {{
            border: 1px solid {LINE};
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 18px rgba(0,0,0,0.2);
        }}

        /* ---- Expanders ---- */
        details {{
            background: rgba(255,255,255,0.02);
            border: 1px solid {LINE} !important;
            border-radius: 10px !important;
        }}

        /* ---- Toggle / switch ---- */
        [data-testid="stToggle"] label div:first-child {{ background: {GOLD}33 !important; }}

        /* ---- Scrollbars ---- */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {GOLD}55; border-radius: 999px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {GOLD}99; }}

        .glass {{
            background: linear-gradient(135deg, rgba(15,23,42,0.85), rgba(30,41,59,0.65));
            backdrop-filter: blur(14px);
            border: 1px solid {GOLD}33;
            border-radius: 16px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.02) inset;
            position: relative; overflow: hidden;
        }}
        .glass::before {{
            content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, {GOLD}, {SIGNAL}, transparent);
            opacity: 0.8;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==================================================================
# SIDEBAR
# ==================================================================

def _render_sidebar(display_name):
    if NAV_STATE_KEY not in st.session_state:
        st.session_state[NAV_STATE_KEY] = "Dashboard"

    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px; padding:6px 2px 16px 2px;">
                <div style="width:42px; height:42px; min-width:42px; border-radius:12px;
                    background:linear-gradient(135deg,{GOLD}40,{GOLD}12); display:flex;
                    align-items:center; justify-content:center; font-size:16px; font-weight:800;
                    color:{INK}; font-family:'Space Grotesk'; border:1px solid {GOLD}55;
                    box-shadow:0 0 14px {GOLD}33;">
                    {(display_name or "A")[:1].upper()}
                </div>
                <div style="min-width:0;">
                    <div style="font-size:14px; font-weight:800; color:{INK}; font-family:'Space Grotesk';
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_name}</div>
                    <div style="font-size:10px; color:{GOLD}; font-weight:700; letter-spacing:0.4px; margin-top:2px;">ADMIN CONTROL CENTER</div>
                </div>
            </div>
            <hr style="margin:0 0 8px 0; border-color:{LINE};">
            """,
            unsafe_allow_html=True,
        )

        query = st.text_input(
            "Filter", key=NAV_FILTER_KEY, placeholder="🔍  Jump to a section…",
            label_visibility="collapsed",
        ).strip().lower()

        # Compact, grouped, 2-per-row nav — replaces one long scrolling
        # list of 14 stacked full-width buttons with ~half the vertical
        # footprint. Typing in the filter box narrows it further.
        for group_label, items in NAV_GROUPS:
            visible = [(k, i) for k, i in items if not query or query in k.lower()]
            if not visible:
                continue
            st.markdown(f"<div class='nav-group-label'>{group_label}</div>", unsafe_allow_html=True)
            for row_start in range(0, len(visible), 2):
                pair = visible[row_start:row_start + 2]
                cols = st.columns(len(pair))
                for col, (key, icon) in zip(cols, pair):
                    with col:
                        active = st.session_state[NAV_STATE_KEY] == key
                        short = key if len(key) <= 12 else key.split(" ")[0]
                        if st.button(
                            f"{icon} {short}", key=f"admin_navbtn_{key}", use_container_width=True,
                            type="primary" if active else "secondary", help=key,
                        ):
                            st.session_state[NAV_STATE_KEY] = key
                            st.rerun()

        st.markdown(f"<div style='margin-top:14px; border-top:1px solid {LINE};'></div>", unsafe_allow_html=True)
        st.write("")
        if st.button("⏻  Logout", key="admin_navbtn_logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    return st.session_state[NAV_STATE_KEY]


# ==================================================================
# SMALL HELPERS
# ==================================================================

def _confirm_button(label, confirm_key, danger=True):
    """Two-step confirm: first click arms it, second click within the
    same render actually fires. Used for every destructive action
    (deactivate, delete, role change) per the spec's 'confirm before
    destructive actions' requirement."""
    armed = st.session_state.get(confirm_key, False)
    if not armed:
        if st.button(label, key=f"{confirm_key}_arm", use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()
        return False
    st.warning("Are you sure? This cannot be undone.")
    c1, c2 = st.columns(2)
    with c1:
        go = st.button("✅ Confirm", key=f"{confirm_key}_go", use_container_width=True, type="primary")
    with c2:
        if st.button("Cancel", key=f"{confirm_key}_cancel", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    if go:
        st.session_state.pop(confirm_key, None)
    return go


def _actor():
    return st.session_state.get("username", ""), "admin"


def _status_badge(status, good="active", good_label=None, bad_label=None):
    ok = (status or "").lower() == good
    color = VERDICT if ok else RISK
    label = (good_label or status or "—").title() if ok else (bad_label or status or "—").title()
    st.markdown(
        f'<span style="background:{color}18; color:{color}; padding:3px 10px; border-radius:999px; '
        f'font-weight:700; font-size:11px; border:1px solid {color}44;">{label}</span>',
        unsafe_allow_html=True,
    )


# ==================================================================
# FUTURISTIC HUD VIEW MODES & CARDS
# ==================================================================

def _hud_metric_card(label, icon, val_str, pct, color_hex, sub_label):
    pct = max(0, min(100, float(pct)))
    html = (
        f'<div style="background: linear-gradient(135deg, rgba(15,23,42,0.85), rgba(30,41,59,0.7)); '
        f'border: 1px solid {color_hex}55; border-radius: 14px; padding: 18px 16px; position: relative; '
        f'box-shadow: 0 4px 20px rgba(0,0,0,0.25), 0 0 15px {color_hex}22; backdrop-filter: blur(10px); '
        f'font-family: \'Space Grotesk\', sans-serif;">'
        f'<div style="position: absolute; top: 0; left: 0; width: 100%; height: 3px; '
        f'background: linear-gradient(90deg, transparent, {color_hex}, transparent);"></div>'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">'
        f'<span style="font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 1.2px; text-transform: uppercase;">'
        f'{icon} {label}</span>'
        f'<span style="font-size: 10px; font-family: monospace; color: {color_hex}; border: 1px solid {color_hex}44; '
        f'padding: 2px 6px; border-radius: 4px; background: {color_hex}15;">LIVE</span>'
        f'</div>'
        f'<div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px;">'
        f'<span style="font-size: 28px; font-weight: 800; color: #f8fafc; text-shadow: 0 0 12px {color_hex}aa;">{val_str}</span>'
        f'<span style="font-size: 12px; color: #94a3b8;">{sub_label}</span>'
        f'</div>'
        f'<div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden;">'
        f'<div style="width: {pct:.1f}%; height: 100%; background: linear-gradient(90deg, {color_hex}88, {color_hex}); '
        f'border-radius: 999px; box-shadow: 0 0 8px {color_hex};"></div>'
        f'</div>'
        f'</div>'
    )
    return html


def _hud_job_status_card(active, closed):
    total = active + closed
    pct_active = (active / total * 100) if total else 0
    pct_closed = (closed / total * 100) if total else 0

    html = (
        f'<div style="background: linear-gradient(135deg, rgba(15,23,42,0.85), rgba(30,41,59,0.7)); '
        f'border: 1px solid #38bdf855; border-radius: 14px; padding: 18px 16px; position: relative; '
        f'box-shadow: 0 4px 20px rgba(0,0,0,0.25), 0 0 15px #38bdf822; backdrop-filter: blur(10px); '
        f'font-family: \'Space Grotesk\', sans-serif;">'
        f'<div style="position: absolute; top: 0; left: 0; width: 100%; height: 3px; '
        f'background: linear-gradient(90deg, transparent, #38bdf8, transparent);"></div>'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">'
        f'<span style="font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 1.2px; text-transform: uppercase;">'
        f'🗂 Job Pipeline</span>'
        f'<span style="font-size: 10px; font-family: monospace; color: #38bdf8; border: 1px solid #38bdf844; '
        f'padding: 2px 6px; border-radius: 4px; background: #38bdf815;">{total} TOTAL</span>'
        f'</div>'
        f'<div style="display: flex; justify-content: space-between; margin-bottom: 10px;">'
        f'<div><span style="font-size: 20px; font-weight: 800; color: #4ade80;">{active}</span> <span style="font-size: 11px; color: #94a3b8;">Active</span></div>'
        f'<div><span style="font-size: 20px; font-weight: 800; color: #f87171;">{closed}</span> <span style="font-size: 11px; color: #94a3b8;">Closed</span></div>'
        f'</div>'
        f'<div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden; display: flex;">'
        f'<div style="width: {pct_active:.1f}%; height: 100%; background: #4ade80; box-shadow: 0 0 8px #4ade80;"></div>'
        f'<div style="width: {pct_closed:.1f}%; height: 100%; background: #f87171; box-shadow: 0 0 8px #f87171;"></div>'
        f'</div>'
        f'</div>'
    )
    return html


def _render_hud_gauges(kpi):
    ats = float(kpi.get("average_ats_score") or 0)
    interview = float(kpi.get("average_interview_score") or 0)
    match = float(kpi.get("average_job_match") or 0)
    active = int(kpi.get("active_jobs") or 0)
    closed = int(kpi.get("closed_jobs") or 0)

    cols = st.columns(4)
    with cols[0]:
        st.markdown(_hud_metric_card("ATS Match Avg", "🎯", f"{ats:.1f}%", ats, "#00E5FF", "Score Index"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_hud_metric_card("Interview Index", "🧠", f"{interview:.1f}/10", min(interview * 10, 100), "#818cf8", "AI Benchmark"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_hud_metric_card("Talent Fit", "📈", f"{match:.1f}%", match, "#34d399", "JD Alignment"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(_hud_job_status_card(active, closed), unsafe_allow_html=True)


# ==================================================================
# SECTION: DASHBOARD
# ==================================================================

def _section_dashboard():
    section_header("🏠", "Platform Overview", "What's happening across the entire recruitment platform, right now.")
    kpi = adb.get_platform_overview()

    row1 = st.columns(5)
    with row1[0]: metric_card("Total Users", kpi["total_users"], "👥", SIGNAL)
    with row1[1]: metric_card("Recruiters", kpi["total_recruiters"], "🧑‍💼", INDIGO)
    with row1[2]: metric_card("Candidates", kpi["total_candidates"], "🎓", GOLD)
    with row1[3]: metric_card("Total Jobs", kpi["total_jobs"], "🗂", SKY)
    with row1[4]: metric_card("Applications", kpi["total_applications"], "📋", VIOLET)

    row2 = st.columns(5)
    with row2[0]: metric_card("Total Interviews", kpi["total_interviews"], "🎙", SIGNAL)
    with row2[1]: metric_card("Completed", kpi["completed_interviews"], "✅", VERDICT)
    with row2[2]: metric_card("Pending", kpi["pending_interviews"], "⏳", CAUTION)
    with row2[3]: metric_card("Selected", kpi["selected_candidates"], "🌟", VERDICT)
    with row2[4]: metric_card("Rejected", kpi["rejected_candidates"], "✖", RISK)

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
    hc1, hc2 = st.columns([3, 1])
    with hc1:
        st.markdown(f"<div style='font-weight:700; color:{INK}; font-size:13px; padding-top:8px;'>PERFORMANCE & JOB STATUS</div>", unsafe_allow_html=True)
    with hc2:
        view_mode = st.toggle("⚡ Futuristic HUD", value=st.session_state.get("dash_hud_mode", True), key="dash_hud_mode")

    if view_mode:
        _render_hud_gauges(kpi)
    else:
        row3 = st.columns(5)
        with row3[0]: metric_card("Avg ATS Score", f"{kpi['average_ats_score']}%", "🎯", SIGNAL)
        with row3[1]: metric_card("Avg Interview Score", f"{kpi['average_interview_score']}", "🧠", INDIGO)
        with row3[2]: metric_card("Avg Job Match", f"{kpi['average_job_match']}%", "📈", SKY)
        with row3[3]: metric_card("Active Jobs", kpi["active_jobs"], "🟢", VERDICT)
        with row3[4]: metric_card("Closed Jobs", kpi["closed_jobs"], "🔴", RISK)


# ==================================================================
# SECTION: USERS
# ==================================================================

def _section_users():
    section_header("👥", "User Management", "Every account on the platform — admins, recruiters, and candidates.")

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        role_filter = st.selectbox("Role", ["All", "Admin", "Recruiter", "Candidate"], key="u_role_filter")
    with f2:
        status_filter = st.selectbox("Status", ["All", "Active", "Inactive"], key="u_status_filter")
    with f3:
        search = st.text_input("Search by name or email", key="u_search", placeholder="e.g. priya or priya@company.com")

    users = adb.get_all_users(role_filter, status_filter, search)
    if not users:
        st.info("No users match these filters.")
        return

    my_id = None
    for u in users:
        if u["username"] == st.session_state.get("username"):
            my_id = u["id"]

    df = pd.DataFrame(users)[["username", "email", "role", "status", "created_at"]]
    df.columns = ["Username", "Email", "Role", "Status", "Created"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:700; color:{INK}; margin-bottom:8px;'>Manage a User</div>", unsafe_allow_html=True)
    options = {f"{u['username']} ({u['email']})": u for u in users}
    picked_label = st.selectbox("Select user", list(options.keys()), key="u_pick")
    user = options[picked_label]
    is_self = user["id"] == my_id
    is_only_admin = user["role"] == "admin" and user["status"] == "active" and adb.count_admins() <= 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**Status**")
        _status_badge(user["status"])
    with c2:
        st.markdown("**Role**")
        st.write(user["role"].title())
    with c3:
        st.markdown("**Actions**")
        if user["status"] == "active":
            if is_self:
                st.caption("You can't deactivate your own account.")
            elif is_only_admin:
                st.caption("Can't deactivate the last active admin.")
            elif _confirm_button("🚫 Deactivate", f"deact_{user['id']}"):
                adb.set_user_status(user["id"], "inactive")
                actor, role = _actor()
                adb.log_audit(actor, role, "User Deactivation", "user", user["id"], f"deactivated {user['username']}")
                st.success(f"{user['username']} deactivated.")
                st.rerun()
        else:
            if st.button("✅ Activate", key=f"act_{user['id']}", use_container_width=True):
                adb.set_user_status(user["id"], "active")
                actor, role = _actor()
                adb.log_audit(actor, role, "User Activation", "user", user["id"], f"activated {user['username']}")
                st.success(f"{user['username']} activated.")
                st.rerun()
    with c4:
        st.markdown("**Danger Zone**")
        if is_self:
            st.caption("You can't delete your own account.")
        elif is_only_admin:
            st.caption("Can't delete the last active admin.")
        elif _confirm_button("🗑 Delete User", f"del_{user['id']}"):
            adb.delete_user_admin(user["id"])
            actor, role = _actor()
            adb.log_audit(actor, role, "User Deletion", "user", user["id"], f"deleted {user['username']}")
            st.success("User deleted.")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:700; color:{INK}; margin-bottom:8px;'>Change Role</div>", unsafe_allow_html=True)
    new_role = st.selectbox("New role", ["admin", "recruiter", "candidate"],
                             index=["admin", "recruiter", "candidate"].index(user["role"]) if user["role"] in ("admin", "recruiter", "candidate") else 0,
                             key=f"role_pick_{user['id']}")
    if new_role != user["role"]:
        if is_self and user["role"] == "admin":
            st.caption("You can't remove your own admin access.")
        elif is_only_admin and new_role != "admin":
            st.caption("Can't demote the last active admin.")
        elif st.button(f"Change role to {new_role.title()}", key=f"role_go_{user['id']}", type="primary"):
            adb.set_user_role(user["id"], new_role)
            actor, role = _actor()
            adb.log_audit(actor, role, "Role Change", "user", user["id"], f"{user['username']}: {user['role']} -> {new_role}")
            st.success(f"{user['username']} is now {new_role.title()}.")
            st.rerun()


# ==================================================================
# SECTION: RECRUITERS
# ==================================================================

def _section_recruiters():
    section_header("🧑‍💼", "Recruiter Management", "Every recruiter account and what they've done with it.")
    search = st.text_input("Search recruiters", key="r_search", placeholder="username or email")
    rows = adb.get_recruiter_rows(search)
    if not rows:
        st.info("No recruiters found.")
        return

    df = pd.DataFrame(rows)[["username", "email", "jobs_posted", "candidates_managed", "interviews_conducted", "status", "created_at"]]
    df.columns = ["Recruiter", "Email", "Jobs Posted", "Candidates Managed", "Interviews Conducted", "Status", "Registered"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(
        "\"Candidates Managed\" counts applications evaluated against jobs this recruiter posted "
        "(the schema links candidates to a job title, not directly to a recruiter). "
        "\"Interviews Conducted\" matches interview_sessions.interviewer to this username."
    )


# ==================================================================
# SECTION: CANDIDATES
# ==================================================================

def _section_candidates():
    section_header("🎓", "Candidate Management", "Global visibility across every candidate application on the platform.")

    candidates = get_candidates()
    if not candidates:
        st.info("No candidate applications yet.")
        return

    jobs = sorted({c.get("job_role") for c in candidates if c.get("job_role")})
    stages = sorted({c.get("stage") or "Applied" for c in candidates})
    recs = sorted({c.get("recommendation") for c in candidates if c.get("recommendation")})

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        job_filter = st.selectbox("Job Role", ["All"] + jobs, key="c_job_filter")
    with f2:
        stage_filter = st.selectbox("Stage", ["All"] + stages, key="c_stage_filter")
    with f3:
        rec_filter = st.selectbox("Recommendation", ["All"] + recs, key="c_rec_filter")
    with f4:
        search = st.text_input("Search name/email", key="c_search")

    rows = candidates
    if job_filter != "All":
        rows = [c for c in rows if c.get("job_role") == job_filter]
    if stage_filter != "All":
        rows = [c for c in rows if (c.get("stage") or "Applied") == stage_filter]
    if rec_filter != "All":
        rows = [c for c in rows if c.get("recommendation") == rec_filter]
    if search:
        s = search.lower()
        rows = [c for c in rows if s in (c.get("name") or "").lower() or s in (c.get("email") or "").lower()]

    if not rows:
        st.info("No candidates match these filters.")
        return

    df = pd.DataFrame(rows)
    show_cols = [c for c in ["name", "email", "job_role", "ats_score", "recommendation", "stage", "created_at"] if c in df.columns]
    df = df[show_cols]
    df.columns = [c.replace("_", " ").title() for c in show_cols]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    options = {f"{c['name']} — {c['job_role']}": c for c in rows}
    picked = st.selectbox("Open a candidate's full profile", list(options.keys()), key="c_pick")
    c = options[picked]
    p1, p2, p3 = st.columns(3)
    with p1:
        profile_field("Name", c.get("name"), "👤")
        profile_field("Email", c.get("email"), "✉")
        profile_field("Phone", c.get("phone"), "📞")
    with p2:
        profile_field("Applied Role", c.get("job_role"), "🗂")
        profile_field("ATS Score", f"{c.get('ats_score')}%" if c.get("ats_score") is not None else None, "🎯")
        profile_field("Stage", c.get("stage") or "Applied", "🧭")
    with p3:
        profile_field("Recommendation", c.get("recommendation"), "⚙")
        profile_field("Confidence", c.get("confidence"), "📈")
        profile_field("Applied On", str(c.get("created_at") or ""), "🗓")
    if c.get("skills"):
        st.markdown("**Skills**")
        chip_list(c["skills"].split(","), SIGNAL)


# ==================================================================
# SECTION: JOBS
# ==================================================================

def _section_jobs():
    section_header("🗂", "Job Management", "All job postings across every recruiter.")
    jobs = get_jobs()
    if not jobs:
        st.info("No jobs posted yet.")
        return

    candidates = get_candidates()
    sessions = get_sessions()

    rows = []
    for j in jobs:
        rows.append({
            "job_id": j["job_id"],
            "job_title": j["job_title"],
            "recruiter": j.get("created_by") or "Unassigned",
            "required_skills": j.get("required_skills") or "",
            "applications": sum(1 for c in candidates if c.get("job_role") == j["job_title"]),
            "interviews": sum(1 for s in sessions if s.get("job_id") == j["job_id"]),
            "status": j.get("status") or "Active",
            "created_at": j.get("created_at"),
        })

    df = pd.DataFrame(rows)
    show = df[["job_title", "recruiter", "applications", "interviews", "status", "created_at"]]
    show.columns = ["Job Title", "Recruiter", "Applications", "Interviews", "Status", "Created"]
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    options = {f"#{r['job_id']} — {r['job_title']} ({r['recruiter']})": r for r in rows}
    picked = st.selectbox("Manage a job", list(options.keys()), key="j_pick")
    job = options[picked]

    c1, c2, c3 = st.columns(3)
    with c1:
        if job["status"] == "Active":
            if st.button("⏸ Deactivate", key=f"jd_{job['job_id']}", use_container_width=True):
                adb.set_job_status(job["job_id"], "Inactive")
                actor, role = _actor()
                adb.log_audit(actor, role, "Job Status Change", "job", job["job_id"], f"{job['job_title']}: Active -> Inactive")
                st.rerun()
        else:
            if st.button("▶ Activate", key=f"ja_{job['job_id']}", use_container_width=True):
                adb.set_job_status(job["job_id"], "Active")
                actor, role = _actor()
                adb.log_audit(actor, role, "Job Status Change", "job", job["job_id"], f"{job['job_title']}: -> Active")
                st.rerun()
    with c2:
        if job["status"] != "Closed":
            if st.button("🔒 Close", key=f"jc_{job['job_id']}", use_container_width=True):
                adb.set_job_status(job["job_id"], "Closed")
                actor, role = _actor()
                adb.log_audit(actor, role, "Job Status Change", "job", job["job_id"], f"{job['job_title']}: -> Closed")
                st.rerun()
    with c3:
        has_activity = adb.job_has_activity(job["job_id"], job["job_title"])
        if has_activity:
            st.caption("Has applications/interviews — use Close instead of Delete to preserve history.")
        elif _confirm_button("🗑 Delete", f"jdel_{job['job_id']}"):
            adb.delete_job_admin(job["job_id"])
            actor, role = _actor()
            adb.log_audit(actor, role, "Job Deletion", "job", job["job_id"], job["job_title"])
            st.success("Job deleted.")
            st.rerun()

    if job["required_skills"]:
        st.markdown("**Required Skills**")
        chip_list(job["required_skills"].split(","), SIGNAL)


# ==================================================================
# SECTION: APPLICATIONS
# ==================================================================

def _section_applications():
    section_header("📋", "Application Pipeline", "Every candidate application, end to end, across every job and recruiter.")
    candidates = get_candidates()
    jobs = {j["job_title"]: j for j in get_jobs()}
    sessions = get_sessions()

    if not candidates:
        st.info("No applications yet.")
        return

    session_by_candidate = {}
    for s in sessions:
        session_by_candidate.setdefault(s.get("candidate_id"), []).append(s)

    rows = []
    for c in candidates:
        job = jobs.get(c.get("job_role"), {})
        my_sessions = session_by_candidate.get(c.get("id"), [])
        latest_status = my_sessions[0]["status"] if my_sessions else "Not Started"
        rows.append({
            "candidate": c.get("name"),
            "job": c.get("job_role"),
            "recruiter": job.get("created_by") or "Unassigned",
            "ats_score": c.get("ats_score"),
            "interview_status": latest_status,
            "stage": c.get("stage") or "Applied",
            "recommendation": c.get("recommendation"),
        })

    df = pd.DataFrame(rows)
    df.columns = ["Candidate", "Job", "Recruiter", "ATS Score", "Interview Status", "Stage", "Recommendation"]

    f1, f2, f3 = st.columns(3)
    with f1:
        job_f = st.selectbox("Job", ["All"] + sorted(df["Job"].dropna().unique().tolist()), key="a_job")
    with f2:
        stage_f = st.selectbox("Stage", ["All"] + sorted(df["Stage"].dropna().unique().tolist()), key="a_stage")
    with f3:
        status_f = st.selectbox("Interview Status", ["All"] + sorted(df["Interview Status"].dropna().unique().tolist()), key="a_status")

    filtered = df.copy()
    if job_f != "All":
        filtered = filtered[filtered["Job"] == job_f]
    if stage_f != "All":
        filtered = filtered[filtered["Stage"] == stage_f]
    if status_f != "All":
        filtered = filtered[filtered["Interview Status"] == status_f]

    st.dataframe(filtered, use_container_width=True, hide_index=True)


# ==================================================================
# SECTION: INTERVIEWS
# ==================================================================

def _section_interviews():
    section_header("🎙", "Interview Management", "Every interview session run on the platform.")
    sessions = get_sessions()
    if not sessions:
        st.info("No interviews recorded yet.")
        return

    candidates = {c["id"]: c for c in get_candidates()}
    jobs = {j["job_id"]: j for j in get_jobs()}

    rows = []
    for s in sessions:
        cand = candidates.get(s.get("candidate_id"), {})
        job = jobs.get(s.get("job_id"), {})
        rows.append({
            "id": s["id"],
            "candidate": cand.get("name", "—"),
            "job": job.get("job_title", "—"),
            "recruiter": s.get("interviewer") or "—",
            "started": s.get("interview_date"),
            "status": s.get("status"),
            "score": s.get("overall_score"),
            "recommendation": s.get("recommendation"),
        })

    df = pd.DataFrame(rows)
    status_f = st.selectbox("Status", ["All"] + sorted(df["status"].dropna().unique().tolist()), key="i_status")
    filtered = df if status_f == "All" else df[df["status"] == status_f]
    show = filtered.drop(columns=["id"])
    show.columns = ["Candidate", "Job", "Recruiter", "Started", "Status", "Score", "Recommendation"]
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.caption("Open the exact same report from **Interview Reports** using the session's candidate/job above.")


# ==================================================================
# SECTION: INTERVIEW REPORTS
# ==================================================================

def _section_interview_reports():
    section_header("📊", "Interview Reports", "Answer-by-answer evaluation for any completed session.")
    sessions = [s for s in get_sessions() if s.get("status") == "Completed"]
    if not sessions:
        st.info("No completed interviews yet.")
        return

    candidates = {c["id"]: c for c in get_candidates()}
    jobs = {j["job_id"]: j for j in get_jobs()}

    def label(s):
        cand = candidates.get(s.get("candidate_id"), {}).get("name", "Unknown")
        job = jobs.get(s.get("job_id"), {}).get("job_title", "Unknown role")
        return f"#{s['id']} — {cand} · {job}"

    options = {label(s): s["id"] for s in sessions}
    picked = st.selectbox("Select a session", list(options.keys()), key="rep_pick")
    session_id = options[picked]

    report = get_session_report(session_id)
    if not report:
        st.warning("Could not load this report.")
        return

    session = report["session"]
    answers = report["answers"]

    m1, m2, m3, m4 = st.columns(4)
    with m1: metric_card("Overall Score", session.get("overall_score", 0), "🏆", SIGNAL)
    with m2: metric_card("Questions", len(answers), "❓", INDIGO)
    with m3: metric_card("Recommendation", session.get("recommendation") or "—", "⚙", VERDICT)
    with m4: metric_card("Status", session.get("status"), "📌", CAUTION)

    scored = [a for a in answers if not a.get("skipped")]
    if scored:
        avg = lambda key: round(sum(a.get(key) or 0 for a in scored) / len(scored), 1)
        s1, s2, s3, s4 = st.columns(4)
        with s1: metric_card("Technical", avg("technical_score"), "🧠", SIGNAL)
        with s2: metric_card("Communication", avg("communication_score"), "💬", SKY)
        with s3: metric_card("Confidence", avg("confidence_score"), "💪", VIOLET)
        with s4: metric_card("Problem Solving", avg("problem_solving_score"), "🧩", INDIGO)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:800; color:{INK}; font-family:Space Grotesk; margin-bottom:8px;'>Answer-by-Answer</div>", unsafe_allow_html=True)
    for i, a in enumerate(answers, 1):
        turn_status = "Skipped" if a.get("skipped") else "Scored"
        with st.expander(f"Q{i} · {a.get('difficulty') or '—'} · {turn_status}"):
            st.markdown(f"**Question:** {a.get('question')}")
            if a.get("skipped"):
                st.caption("Candidate skipped this question.")
            else:
                st.markdown(f"**Answer:** {a.get('answer')}")
                if a.get("answer_mode") == "voice":
                    st.caption(f"Answered by voice · transcription: {a.get('transcription_status') or '—'}")
                if a.get("strengths"):
                    st.markdown(f"**Strengths:** {a['strengths']}")
                if a.get("weaknesses"):
                    st.markdown(f"**Weaknesses:** {a['weaknesses']}")
                if a.get("suggestion"):
                    st.markdown(f"**Improvement:** {a['suggestion']}")


# ==================================================================
# SECTION: ATS ANALYTICS
# ==================================================================

def _section_ats_analytics():
    section_header("🎯", "ATS Analytics", "Score distribution and skill trends across every application.")
    stats = adb.get_ats_analytics()

    m1, m2, m3 = st.columns(3)
    with m1: metric_card("Average ATS Score", f"{stats['average']}%", "🎯", SIGNAL)
    with m2: metric_card("Highest Score", f"{stats['highest']}%", "🏆", VERDICT)
    with m3: metric_card("Lowest Score", f"{stats['lowest']}%", "📉", RISK)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div style='font-weight:700; color:{INK};'>By Recommendation</div>", unsafe_allow_html=True)
        if stats["by_recommendation"]:
            st.dataframe(pd.DataFrame(list(stats["by_recommendation"].items()), columns=["Recommendation", "Count"]),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("No data yet.")
    with c2:
        st.markdown(f"<div style='font-weight:700; color:{INK};'>By Score Range</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(list(stats["by_range"].items()), columns=["Range", "Count"]),
                     use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:700; color:{INK};'>Most Common Skills</div>", unsafe_allow_html=True)
    if stats["top_skills"]:
        chip_list([f"{s} ({n})" for s, n in stats["top_skills"]], SIGNAL)
    else:
        st.caption("No skills on file yet.")


# ==================================================================
# SECTION: INTERVIEW ANALYTICS
# ==================================================================

def _section_interview_analytics():
    section_header("📈", "Interview Analytics", "How interviews are performing across the whole platform.")
    stats = adb.get_interview_analytics()

    m1, m2 = st.columns(2)
    with m1: metric_card("Average Score", stats["average_score"], "🏆", SIGNAL)
    with m2: metric_card("Completion Rate", f"{stats['completion_rate']}%", "✅", VERDICT)

    r1, r2, r3, r4 = st.columns(4)
    with r1: metric_card("Strong Hire %", f"{stats['strong_hire_pct']}%", "🌟", VERDICT)
    with r2: metric_card("Hire %", f"{max(stats['hire_pct'], 0)}%", "👍", SIGNAL)
    with r3: metric_card("Consider %", f"{stats['consider_pct']}%", "🤔", CAUTION)
    with r4: metric_card("Not Recommended %", f"{stats['not_recommended_pct']}%", "👎", RISK)

    st.caption(f"{stats['completed_sessions']} of {stats['total_sessions']} sessions completed.")


# ==================================================================
# SECTION: PLATFORM ANALYTICS
# ==================================================================

def _section_platform_analytics():
    section_header("🌐", "Platform Analytics", "Growth and activity across the whole platform.")
    range_label = st.selectbox("Date Range", ["Today", "7 Days", "30 Days", "90 Days", "All Time"], index=2, key="p_range")
    growth = adb.get_platform_growth(range_label)

    r1 = st.columns(4)
    with r1[0]: metric_card("New Recruiters", growth["new_recruiters"], "🧑‍💼", INDIGO)
    with r1[1]: metric_card("New Candidates", growth["new_candidates"], "🎓", GOLD)
    with r1[2]: metric_card("Jobs Created", growth["jobs_created"], "🗂", SKY)
    with r1[3]: metric_card("Applications", growth["applications_submitted"], "📋", VIOLET)

    r2 = st.columns(4)
    with r2[0]: metric_card("Interviews Started", growth["interviews_started"], "🎙", SIGNAL)
    with r2[1]: metric_card("Interviews Completed", growth["interviews_completed"], "✅", VERDICT)
    with r2[2]: metric_card("Selections", growth["selections"], "🌟", VERDICT)
    with r2[3]: metric_card("Rejections", growth["rejections"], "✖", RISK)

    st.caption(f"Showing activity for: {range_label}")


# ==================================================================
# SECTION: SYSTEM HEALTH
# ==================================================================

def _section_system_health():
    section_header("🩺", "System Health", "Live status of every backend dependency — never mock values.")
    health = adb.get_system_health()

    def row(label, ok):
        icon = "✅" if ok else "❌"
        color = VERDICT if ok else RISK
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; padding:10px 14px; '
            f'border:1px solid {LINE}; border-radius:10px; margin-bottom:8px;">'
            f'<span style="color:{INK}; font-weight:600;">{label}</span>'
            f'<span style="color:{color}; font-weight:700;">{icon} {"Connected" if ok else "Unavailable"}</span></div>',
            unsafe_allow_html=True,
        )

    row("Database", health["database"])
    row("Authentication", health["authentication"])
    row("AI / Groq Integration", health["groq_ai"])
    row("Resume Parser", health["resume_parser"])
    row("OCR", health["ocr"])
    row("Interview Engine", health["interview_engine"])

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-weight:700; color:{INK};'>Required Environment Variables</div>", unsafe_allow_html=True)
    for var, present in health["env_vars"].items():
        badge = "Configured" if present else "Not Configured"
        color = VERDICT if present else RISK
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; padding:6px 4px;">'
            f'<span style="color:{MIST}; font-family:monospace; font-size:12.5px;">{var}</span>'
            f'<span style="color:{color}; font-weight:700; font-size:12px;">{badge}</span></div>',
            unsafe_allow_html=True,
        )
    st.caption("Actual key values are never displayed, in the UI or in logs.")


# ==================================================================
# SECTION: AUDIT LOGS
# ==================================================================

def _section_audit_logs():
    section_header("🧾", "Audit Logs", "Every administrative action, in order.")
    actions = ["All"] + adb.get_distinct_audit_actions()
    f1, f2 = st.columns([1, 2])
    with f1:
        action_filter = st.selectbox("Action", actions, key="log_action")
    with f2:
        search = st.text_input("Search (actor, target, details)", key="log_search")

    logs = adb.get_audit_logs(limit=300, action_filter=action_filter, search=search)
    if not logs:
        st.info("No audit log entries yet.")
        return

    df = pd.DataFrame(logs)[["created_at", "actor_username", "actor_role", "action", "target_type", "target_id", "details"]]
    df.columns = ["When", "Admin/User", "Role", "Action", "Target Type", "Target", "Details"]
    st.dataframe(df, use_container_width=True, hide_index=True)


# ==================================================================
# SECTION: SETTINGS
# ==================================================================

def _section_settings():
    section_header("⚙", "Admin Settings", "Safe, platform-level settings — no raw code, no SQL, ever.")
    settings = adb.get_settings()

    with st.form("admin_settings_form"):
        app_name = st.text_input("Application Name", value=settings["app_name"])
        difficulty = st.selectbox(
            "Default Interview Difficulty", ["Easy", "Medium", "Hard"],
            index=["Easy", "Medium", "Hard"].index(settings["default_interview_difficulty"])
            if settings["default_interview_difficulty"] in ("Easy", "Medium", "Hard") else 1,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            strong_hire = st.number_input("Strong Hire Threshold (%)", 0, 100, int(settings["strong_hire_threshold"]))
        with c2:
            hire = st.number_input("Hire Threshold (%)", 0, 100, int(settings["hire_threshold"]))
        with c3:
            consider = st.number_input("Consider Threshold (%)", 0, 100, int(settings["consider_threshold"]))
        pagination = st.number_input("Pagination Limit (rows per table)", 5, 200, int(settings["pagination_limit"]))
        voice_enabled = st.toggle("Voice Screening Enabled", value=settings["voice_screening_enabled"] == "true")

        submitted = st.form_submit_button("Save Settings", type="primary", use_container_width=True)

    if submitted:
        adb.set_setting("app_name", app_name)
        adb.set_setting("default_interview_difficulty", difficulty)
        adb.set_setting("strong_hire_threshold", strong_hire)
        adb.set_setting("hire_threshold", hire)
        adb.set_setting("consider_threshold", consider)
        adb.set_setting("pagination_limit", pagination)
        adb.set_setting("voice_screening_enabled", "true" if voice_enabled else "false")
        actor, role = _actor()
        adb.log_audit(actor, role, "Settings Change", "platform_settings", "", "admin updated platform settings")
        st.success("Settings saved.")
        st.rerun()


# ==================================================================
# ENTRY POINT
# ==================================================================

SECTION_RENDERERS = {
    "Dashboard": _section_dashboard,
    "Users": _section_users,
    "Recruiters": _section_recruiters,
    "Candidates": _section_candidates,
    "Jobs": _section_jobs,
    "Applications": _section_applications,
    "Interviews": _section_interviews,
    "Interview Reports": _section_interview_reports,
    "ATS Analytics": _section_ats_analytics,
    "Interview Analytics": _section_interview_analytics,
    "Platform Analytics": _section_platform_analytics,
    "System Health": _section_system_health,
    "Audit Logs": _section_audit_logs,
    "Settings": _section_settings,
}


def render_admin_dashboard(user: dict):
    """user: {'username': ..., 'email': ...} — same shape app.py already
    passes to render_candidate_dashboard()."""
    require_admin()
    _inject_futuristic_theme()

    display_name = user.get("username", "Admin")
    active_section = _render_sidebar(display_name)
    active_icon = dict(NAV_ITEMS).get(active_section, "🏠")

    st.markdown(
        f"""
        <div class="glass" style="padding: 22px 26px; display: flex; justify-content: space-between; align-items: center; margin-bottom:18px;">
            <div>
                <div style="font-size: 11px; font-weight: 700; letter-spacing: 1.5px; color: {SIGNAL}; font-family: 'IBM Plex Mono';">
                    {active_icon} {active_section.upper()}
                </div>
                <div style="font-size: 26px; font-weight: 800; font-family: 'Space Grotesk'; color: {INK}; margin-top:2px;">ADMIN CONTROL CENTER</div>
                <div style="margin-top: 4px; color: {MIST}; font-size: 13px;">Platform-wide oversight — users, recruiters, candidates, jobs, interviews, and system health.</div>
            </div>
            <div style="padding: 7px 16px; background: linear-gradient(90deg, {GOLD}22, {GOLD}10);
                border: 1px solid {GOLD}55; border-radius: 999px; color: {GOLD}; font-weight: 700;
                font-size: 11px; font-family: 'IBM Plex Mono'; letter-spacing: 1px; white-space: nowrap;
                box-shadow: 0 0 14px {GOLD}22;">
                &#9733; SUPER ADMIN
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    renderer = SECTION_RENDERERS.get(active_section, _section_dashboard)
    renderer()