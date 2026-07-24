import streamlit as st

# ==========================================================
# AI RECRUITMENT COPILOT — Mint Glass, Enterprise Light Theme
# ==========================================================
# Design tokens
VOID    = "#EAF8F3"   # Page background (top of gradient) — more saturated so cards pop
PANEL   = "#FFFFFF"    # Solid white glass card surface
PANEL2  = "#F1FBF8"    # Raised glass inputs / active states (deeper mint tint)
LINE    = "#BDEEDD"    # Visible mint borders around cards/inputs
INK     = "#1F2937"    # Dark charcoal text — primary
MIST    = "#5D6E68"    # Muted mint-gray secondary text

SIGNAL  = "#14B8A6"   # Core Brand Accent (Teal — labels, icons, chips, eyebrows)
VERDICT = "#10B981"   # Success Green (Excellent Match)
CAUTION = "#D97706"   # Amber Gold (Average Match)
RISK    = "#DC2626"   # Coral Red (Low Match / Deficit)

MINT_A  = "#34D399"   # Primary Mint (buttons, sidebar, gradients)
MINT_B  = "#6EE7B7"   # Secondary Mint (gradient partner)

# Compatibility configuration
PRIMARY = SIGNAL
SUCCESS = VERDICT
WARNING = CAUTION
DANGER  = RISK
BG      = VOID
CARD    = PANEL
TEXT    = INK
MUTED   = MIST
BORDER  = LINE


def load_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background: {VOID};
    color: {INK};
}}

.stApp {{
    background: linear-gradient(160deg, #EAF8F3 0%, #DFF6ED 100%);
}}

.block-container {{
    max-width: 1600px;
    padding: 1.5rem 2rem;
}}

h1, h2, h3, h4 {{
    font-family: 'Space Grotesk', sans-serif !important;
    color: {INK} !important;
    font-weight: 700;
}}

p, span, div, label, li {{
    color: {INK};
}}

/* ---------------------------------------------------------
   NATIVE STREAMLIT CHROME — force-light so nothing clashes
   --------------------------------------------------------- */

/* Top header/toolbar strip */
header[data-testid="stHeader"] {{
    background: transparent !important;
}}
[data-testid="stToolbar"] {{
    background: transparent !important;
}}
[data-testid="stDecoration"] {{
    background: linear-gradient(90deg, {MINT_A}, {SIGNAL}) !important;
}}

/* Sidebar frame */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #F7FFFC 0%, #D6F5EA 100%) !important;
    border-right: 1px solid {LINE};
}}
[data-testid="stSidebar"] * {{
    color: {INK} !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {LINE} !important;
}}

/* Sidebar nav radio — pill-style rows */
[data-testid="stSidebar"] [role="radiogroup"] label {{
    background: rgba(255,255,255,0.55);
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 4px;
    transition: all 0.2s ease;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(255,255,255,0.9);
}}

/* Native dataframes/tables — let the theme (config.toml) handle internal
   canvas rendering; only style the outer container */
[data-testid="stDataFrame"] {{
    border: 1px solid {LINE};
    border-radius: 14px;
    overflow: hidden;
}}

/* Tabs */
.stTabs [data-baseweb="tab"] {{
    color: {MIST};
}}
.stTabs [aria-selected="true"] {{
    color: {SIGNAL} !important;
}}

/* ---------------------------------------------------------
   CUSTOM UI — cards, chips, buttons
   --------------------------------------------------------- */

/* Frosted Mint Glass Cards */
.glass {{
    background: {PANEL};
    border: 1.5px solid {LINE};
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px 0 rgba(20, 184, 166, 0.10);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}}

.glass:hover {{
    transform: translateY(-2px);
    border-color: rgba(20, 184, 166, 0.55);
    box-shadow: 0 16px 40px 0 rgba(52, 211, 153, 0.18);
}}

/* Section Headings */
.aperture-eyebrow {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: {SIGNAL};
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 6px 0 14px 0;
}}

/* Step pill (used on Upload Resume page) */
.step-pill {{
    display: inline-flex;
    align-items: center;
    padding: 6px 14px;
    background: {SIGNAL}15;
    border: 1px solid {LINE};
    border-radius: 999px;
    color: {SIGNAL};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 4px 0 12px 0;
}}

/* Profile field cards */
.profile-field {{
    background: {PANEL2};
    border: 1px solid {LINE};
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
}}
.profile-field-label {{
    font-size: 11px;
    color: {MIST};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    margin-bottom: 4px;
}}
.profile-field-value {{
    font-size: 15px;
    color: {INK};
    font-weight: 600;
    word-break: break-word;
}}

/* Skill chips */
.chip {{
    display: inline-block;
    padding: 6px 12px;
    margin: 3px 4px 3px 0;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: {SIGNAL}16;
    border: 1px solid {SIGNAL}44;
    color: {SIGNAL};
}}

/* List cards (projects / certifications) */
.list-card-item {{
    padding: 8px 0;
    border-bottom: 1px dashed {LINE};
    color: {INK};
    font-size: 13px;
}}
.list-card-item:last-child {{
    border-bottom: none;
}}

/* Premium Mint Buttons */
.stButton>button {{
    width: 100%;
    height: 46px;
    background: linear-gradient(135deg, {MINT_A} 0%, {SIGNAL} 100%);
    color: #0B2A24;
    border: none;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
    transition: all 0.2s ease;
    box-shadow: 0 4px 15px rgba(52, 211, 153, 0.25);
}}

.stButton>button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 8px 25px rgba(20, 184, 166, 0.35);
    color: #0B2A24;
}}

/* Form inputs styling */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
    background: {PANEL2} !important;
    border: 1px solid {LINE} !important;
    border-radius: 10px !important;
    color: {INK} !important;
}}

.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {SIGNAL} !important;
    box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.18) !important;
}}

[data-testid="stFileUploader"] {{
    border: 1.5px dashed {LINE};
    border-radius: 16px;
    padding: 24px;
    background: {PANEL2};
}}

/* Progress Bar Overrides */
.stProgress > div > div {{
    background: linear-gradient(90deg, {MINT_A}, {SIGNAL}) !important;
}}
</style>
""", unsafe_allow_html=True)


def sidebar_logo():
    st.markdown(f"""
    <div class="glass" style="padding: 20px 10px; text-align: center;">
        <div style="width: 52px; height: 52px; margin: auto; border-radius: 14px; background: linear-gradient(135deg, {MINT_A} 0%, {MINT_B} 100%); display: flex; align-items: center; justify-content: center; color: #0B2A24; font-size: 22px; font-weight: 800; font-family: 'Space Grotesk';">
            🟢
        </div>
        <div style="margin-top: 12px; font-size: 18px; font-weight: 700; font-family: 'Space Grotesk'; color: {INK};">
            TalentOps AI
        </div>
        <div style="color: {MIST}; font-size: 12px; margin-top: 2px;">
            Mint Glass Copilot
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_title(title, subtitle):
    st.markdown(f"""
    <div class="glass" style="padding: 20px 24px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-size: 26px; font-weight: 700; font-family: 'Space Grotesk'; color: {INK};">{title}</div>
            <div style="margin-top: 4px; color: {MIST}; font-size: 13px;">{subtitle}</div>
        </div>
        <div style="padding: 6px 14px; background: rgba(20, 184, 166, 0.10); border: 1px solid {LINE}; border-radius: 8px; color: {SIGNAL}; font-weight: 600; font-size: 11px; font-family: 'IBM Plex Mono'; letter-spacing: 0.5px;">
            PRO CORE
        </div>
    </div>
    """, unsafe_allow_html=True)


def metric_card(title, value, icon="📊", color=None):
    color = color or SIGNAL
    st.markdown(f"""
        <div class="glass" style="padding: 20px; margin-bottom: 0px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: {color}15; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                    {icon}
                </div>
                <div style="width: 8px; height: 8px; background: {MINT_A}; border-radius: 50%;"></div>
            </div>
            <div style="font-size: 11px; color: {MIST}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                {title}
            </div>
            <div style="font-size: 28px; font-weight: 700; font-family: 'IBM Plex Mono', monospace; color: {color}; margin-top: 4px;">
                {value}
            </div>
        </div>
        """, unsafe_allow_html=True)


def profile_field(label, value, icon="•"):
    """A single labeled field card, used on the extracted-profile grid."""
    display_value = value if value else "—"
    st.markdown(f"""
        <div class="profile-field">
            <div class="profile-field-label">{icon} &nbsp;{label}</div>
            <div class="profile-field-value">{display_value}</div>
        </div>
        """, unsafe_allow_html=True)


def chip_list(items, color=None):
    """Render a wrapped row of pill-shaped chips (e.g. detected skills)."""
    color = color or SIGNAL
    items = [i.strip() for i in items if i and i.strip()]
    if not items:
        st.markdown(f'<div style="color:{MIST}; font-size: 13px;">No items detected.</div>',
                    unsafe_allow_html=True)
        return
    chips_html = "".join(
        f'<span class="chip" style="background:{color}16; border-color:{color}44; color:{color};">{item}</span>'
        for item in items
    )
    st.markdown(f'<div style="margin: 6px 0 4px 0;">{chips_html}</div>', unsafe_allow_html=True)


def list_card(title, items, icon="•", color=None):
    """A glass card listing bullet items (projects, certifications, etc.)."""
    color = color or SIGNAL
    if items:
        rows = "".join(f'<div class="list-card-item">• {item}</div>' for item in items)
    else:
        rows = f'<div class="list-card-item" style="color:{MIST};">None detected</div>'

    st.markdown(f"""
        <div class="glass" style="padding: 18px 20px;">
            <div style="font-size: 14px; font-weight: 700; color: {color}; margin-bottom: 10px;">
                {icon} &nbsp;{title}
            </div>
            {rows}
        </div>
        """, unsafe_allow_html=True)


def full_report_modal(details, ats_result, recommendation, job_role):
    """
    Full candidate report. Uses st.dialog when available (Streamlit >= 1.31);
    falls back to an inline expander on older Streamlit versions.
    """
    def _render():
        st.markdown(f"**Target Role:** {job_role}")
        st.divider()

        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("ATS Score", f"{ats_result['ats']}%", "🎯", SIGNAL)
        with c2:
            metric_card("Decision", recommendation["decision"], "⚙", VERDICT)
        with c3:
            metric_card("Confidence", recommendation["confidence"], "📈", CAUTION)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Candidate Details**")
        profile_field("Full Name", details.get("name", ""), "👤")
        profile_field("Email", details.get("email", ""), "✉")
        profile_field("Phone", details.get("phone", ""), "📞")
        profile_field("Education", details.get("education", ""), "🎓")
        profile_field("Experience", details.get("experience", ""), "🧭")

        st.markdown("**Matched Skills**")
        chip_list(ats_result.get("matched_skills", []), VERDICT)

        st.markdown("**Missing Skills**")
        chip_list(ats_result.get("missing_skills", []), RISK)

        list_card("Projects", details.get("projects", []), "🧩", SIGNAL)
        list_card("Certifications", details.get("certifications", []), "🎓", VERDICT)

    if hasattr(st, "dialog"):
        @st.dialog(f"Full Analysis Report — {details.get('name', 'Candidate')}", width="large")
        def _modal():
            _render()
        _modal()
    else:
        with st.expander(f"📊 Full Analysis Report — {details.get('name', 'Candidate')}", expanded=True):
            _render()


def footer():
    st.markdown(f"""
    <div style="margin-top: 40px; padding: 16px; text-align: center; border-top: 1px solid {LINE}; color: {MIST}; font-size: 11px; font-family: 'IBM Plex Mono';">
        V2.5 • Mint Glass Variant • Enterprise Intelligence Network Engine
    </div>
    """, unsafe_allow_html=True)