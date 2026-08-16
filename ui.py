import streamlit as st

# ==========================================================
# AI RECRUITMENT COPILOT — "Luminous Mint" Enterprise Theme
# ==========================================================
# Design language: deep emerald ink on a lit mint-glass surface, a
# luminous mint->jade "shine" that actually glows (soft radiant box
# shadows, a moving shine sweep, a gentle pulse) rather than sitting
# flat, plus a warm gold hairline used sparingly for premium/verdict
# signals.

# ---- Core surface ----
VOID    = "#EFFBF6"   # Page background (top of gradient)
VOID2   = "#DCF3E8"   # Page background (bottom of gradient)
PANEL   = "#FFFFFF"   # Glass card surface
PANEL2  = "#F1FBF7"   # Raised / inset surface (inputs, active rows)
LINE    = "#BFEBDA"   # Hairline borders
LINE_SOFT = "#D7F2E6" # Fainter divider

# ---- Ink ----
INK     = "#0F2B22"   # Primary text -- deep forest ink (richer than gray)
INK_SOFT= "#24473B"   # Secondary heading ink
MIST    = "#5C7A6E"   # Muted secondary text

# ---- Signal colors ----
SIGNAL  = "#0DAF9C"   # Core brand mint-teal -- labels, icons, eyebrows, primary CTAs
VERDICT = "#0E9F6E"   # Success / excellent match
CAUTION = "#B9820F"   # Warm gold -- average / attention
RISK    = "#DC4C4C"   # Coral red -- low match / deficit

# ---- Mint gradient family (the "glow") ----
MINT_A  = "#3FF2C4"   # Bright luminous mint -- the glow color
MINT_B  = "#A6FCE0"   # Pale mint shine
MINT_C  = "#0B7F73"   # Deep teal (gradient anchor / hover)
GOLD    = "#D4AF37"   # Reserved accent -- premium badges only

# ---- Extended accent family (sidebar nav variety, secondary chips) ----
INDIGO  = "#6366F1"
VIOLET  = "#8B5CF6"
ROSE    = "#DB5A8C"
SKY     = "#0EA5E9"

# Per-item accent for the recruiter sidebar nav, in the exact order the
# nav items are declared in app.py (Dashboard, Job Postings, Upload
# Resume, Interviews, Candidates, Analytics, Profile) -- a harmonious
# but varied palette so the sidebar isn't monochrome, while every item
# still shares the same pill shape, spacing and hover motion.
NAV_ACCENTS = [SIGNAL, INDIGO, VIOLET, ROSE, CAUTION, VERDICT, SKY]

# ---- Night Mode surfaces (see _inject_night_mode_css in load_css) ----
# Deep-space navy/black glass, matching the reference dashboard screenshot.
NIGHT_PANEL  = "#0E141B"   # Card surface
NIGHT_PANEL2 = "#141C24"   # Raised / inset surface (inputs)
NIGHT_LINE   = "#22303A"   # Hairline borders
NIGHT_TEXT   = "#E7F5EF"   # Primary text on dark
NIGHT_MUTED  = "#7C93A0"   # Muted secondary text on dark

# Compatibility aliases (used across other modules)
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
    # Per-item accent CSS for the sidebar nav (see NAV_ACCENTS above) --
    # built here as plain CSS text and dropped into the stylesheet below,
    # so each nav pill gets its own hover/active hue via CSS custom
    # properties instead of everything being one flat teal.
    nav_accent_css = "".join(
        f'[data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type({i}) {{ '
        f'--nav-solid: {c}; --nav-wash: {c}22; --nav-wash2: {c}12; '
        f'--nav-border: {c}55; --nav-border-soft: {c}40; }}\n'
        for i, c in enumerate(NAV_ACCENTS, start=1)
    )

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700;800&family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background: {VOID};
    color: {INK};
}}

.stApp {{
    background:
        radial-gradient(1100px 520px at 12% -8%, rgba(63,242,196,0.30), transparent 60%),
        radial-gradient(900px 460px at 105% 8%, rgba(212,175,55,0.18), transparent 55%),
        radial-gradient(750px 540px at 90% 90%, rgba(14,159,110,0.18), transparent 60%),
        radial-gradient(600px 420px at 0% 75%, rgba(220,76,76,0.06), transparent 55%),
        repeating-linear-gradient(120deg, rgba(13,175,156,0.035) 0px, rgba(13,175,156,0.035) 1px, transparent 1px, transparent 34px),
        linear-gradient(165deg, {VOID} 0%, {VOID2} 100%);
    background-attachment: fixed;
}}

.block-container {{
    max-width: 1600px;
    padding: 1.5rem 2rem 3rem 2rem;
}}

h1, h2, h3, h4 {{
    font-family: 'Space Grotesk', sans-serif !important;
    color: {INK} !important;
    font-weight: 700;
    letter-spacing: -0.3px;
}}

p, span, div, label, li {{ color: {INK}; }}

::selection {{ background: {MINT_A}55; color: {INK}; }}

::-webkit-scrollbar {{ width: 9px; height: 9px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {MINT_A}66; border-radius: 8px; }}
::-webkit-scrollbar-thumb:hover {{ background: {SIGNAL}88; }}

/* ---------------------------------------------------------
   NATIVE STREAMLIT CHROME
   --------------------------------------------------------- */
header[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stToolbar"] {{ background: transparent !important; }}
[data-testid="stDecoration"] {{
    background: linear-gradient(90deg, {MINT_C}, {MINT_A}, {GOLD}) !important;
    height: 3px !important;
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(190deg, #FFFFFF 0%, #E4F7ED 55%, #CDEEDF 100%) !important;
    border-right: 1px solid {LINE};
    box-shadow: 6px 0 24px rgba(13,175,156,0.06);
}}
[data-testid="stSidebar"] * {{ color: {INK} !important; }}
[data-testid="stSidebar"] hr {{
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, {LINE} 20%, {LINE} 80%, transparent);
    margin: 14px 0;
}}

[data-testid="stSidebar"] [role="radiogroup"] {{
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 4px;
}}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    box-sizing: border-box;
    background: rgba(255,255,255,0.55);
    border: 1px solid transparent;
    border-radius: 13px;
    padding: 11px 14px 11px 16px;
    margin-bottom: 0;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s cubic-bezier(0.25,0.8,0.25,1);
}}
{nav_accent_css}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: #FFFFFF;
    border-color: var(--nav-border-soft, {LINE});
    transform: translateX(3px);
    box-shadow: 0 4px 14px rgba(13,175,156,0.10);
}}
[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {{
    background: linear-gradient(90deg, var(--nav-wash, {MINT_A}22), var(--nav-wash2, {SIGNAL}12));
    border-color: var(--nav-border, {SIGNAL}55);
    box-shadow: 0 6px 18px rgba(13,175,156,0.14);
}}
[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"]::before {{
    content: "";
    position: absolute;
    left: 0; top: 20%; bottom: 20%;
    width: 3px;
    border-radius: 0 4px 4px 0;
    background: var(--nav-solid, {SIGNAL});
}}
[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] p {{
    color: var(--nav-solid, {MINT_C}) !important;
    font-weight: 700 !important;
}}

.sidebar-session-card {{
    padding: 16px 16px 14px 16px !important;
    margin-bottom: 4px;
}}
.sidebar-logo-card {{
    margin-bottom: 4px !important;
}}
[data-testid="stSidebar"] .stButton>button {{
    background: {PANEL2} !important;
    color: {RISK} !important;
    border: 1.5px solid {RISK}35 !important;
    box-shadow: none !important;
    font-weight: 700 !important;
    animation: none !important;
}}
[data-testid="stSidebar"] .stButton>button:hover {{
    background: {RISK}12 !important;
    border-color: {RISK}70 !important;
    transform: translateY(-1px);
}}

[data-testid="stDataFrame"] {{
    border: 1px solid {LINE};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 6px 20px rgba(13,175,156,0.06);
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {PANEL2};
    padding: 5px;
    border-radius: 13px;
    border: 1px solid {LINE};
}}
.stTabs [data-baseweb="tab"] {{
    color: {MIST};
    font-weight: 700;
    font-size: 13.5px;
    border-radius: 9px !important;
    padding: 9px 20px !important;
    transition: color 0.18s ease;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: {INK_SOFT}; }}
.stTabs [aria-selected="true"] {{
    color: {SIGNAL} !important;
    background: #FFFFFF;
    box-shadow: 0 4px 14px -2px {SIGNAL}35;
}}
.stTabs [data-baseweb="tab-highlight"] {{ background: transparent !important; }}
.stTabs [data-baseweb="tab-border"] {{ background: transparent !important; }}

/* ---------------------------------------------------------
   CARDS -- glass with a hairline "shine" edge on top
   --------------------------------------------------------- */
.glass {{
    position: relative;
    background: {PANEL};
    border: 1.5px solid {LINE};
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px 0 rgba(13,175,156,0.09);
    transition: all 0.28s cubic-bezier(0.25, 0.8, 0.25, 1);
    overflow: hidden;
}}
.glass::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {MINT_C}, {MINT_A} 45%, {GOLD} 100%);
    opacity: 0.0;
    transition: opacity 0.25s ease;
}}
.glass:hover {{
    transform: translateY(-3px);
    border-color: rgba(13,175,156,0.45);
    box-shadow: 0 18px 44px 0 rgba(63,242,196,0.20);
}}
.glass:hover::before {{ opacity: 1; }}

.glass-flat {{
    background: {PANEL};
    border: 1.5px solid {LINE};
    border-radius: 18px;
    padding: 18px 20px;
}}

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

.hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 9px 20px;
    background: linear-gradient(90deg, {MINT_A}14, {SIGNAL}10);
    border: 1px solid {SIGNAL}3d;
    border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11.5px;
    letter-spacing: 2px;
    color: {MINT_C};
    text-transform: uppercase;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(13,175,156,0.10);
}}
.hero-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: {MINT_A};
    box-shadow: 0 0 0 0 rgba(63,242,196,0.6);
    animation: pulseDot 2s infinite;
}}
@keyframes pulseDot {{
    0%   {{ box-shadow: 0 0 0 0 rgba(63,242,196,0.55); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(63,242,196,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(63,242,196,0); }}
}}

.shine-text {{
    background: linear-gradient(100deg, {MINT_C} 0%, {SIGNAL} 35%, {MINT_A} 60%, {MINT_C} 100%);
    background-size: 220% auto;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shineMove 7s ease-in-out infinite;
}}
@keyframes shineMove {{
    0% {{ background-position: 0% center; }}
    50% {{ background-position: 100% center; }}
    100% {{ background-position: 0% center; }}
}}

.step-pill {{
    display: inline-flex;
    align-items: center;
    padding: 7px 16px;
    background: {SIGNAL}14;
    border: 1px solid {LINE};
    border-radius: 999px;
    color: {MINT_C};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin: 4px 0 14px 0;
}}

.profile-field {{
    background: {PANEL2};
    border: 1px solid {LINE};
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.2s ease;
}}
.profile-field:hover {{ border-color: {SIGNAL}55; }}
.profile-field-label {{
    font-size: 11px;
    color: {MIST};
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 700;
    margin-bottom: 4px;
}}
.profile-field-value {{
    font-size: 15px;
    color: {INK};
    font-weight: 600;
    word-break: break-word;
}}

.chip {{
    display: inline-block;
    padding: 6px 13px;
    margin: 3px 4px 3px 0;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    background: {SIGNAL}14;
    border: 1px solid {SIGNAL}40;
    color: {MINT_C};
    transition: all 0.15s ease;
}}
.chip:hover {{ background: {SIGNAL}22; transform: translateY(-1px); }}

.list-card-item {{
    padding: 9px 0;
    border-bottom: 1px dashed {LINE};
    color: {INK};
    font-size: 13px;
}}
.list-card-item:last-child {{ border-bottom: none; }}

/* ---------------------------------------------------------
   BUTTONS -- primary (solid signal gradient + glow), secondary
   (ghost outline that fills on hover), and a quiet icon-scale
   press response shared by both. Every state has a visible
   focus ring for keyboard users.
   --------------------------------------------------------- */
.stButton>button {{
    position: relative;
    width: 100%;
    height: 48px;
    background: linear-gradient(135deg, {MINT_A} 0%, {SIGNAL} 55%, {MINT_C} 100%);
    background-size: 170% 170%;
    background-position: 0% 0%;
    color: #06231C;
    border: none;
    border-radius: 12px;
    font-size: 14.5px;
    font-weight: 700;
    letter-spacing: 0.2px;
    transition: transform 0.16s cubic-bezier(0.25,0.8,0.25,1),
                box-shadow 0.22s ease, background-position 0.35s ease;
    box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset,
                0 8px 20px -4px {SIGNAL}70,
                0 0 22px -4px {MINT_A}80;
    animation: buttonGlowPulse 2.8s ease-in-out infinite;
}}
.stButton>button p {{ color: #06231C !important; font-weight: 700 !important; }}
.stButton>button:hover {{
    transform: translateY(-2px);
    background-position: 100% 100%;
    box-shadow: 0 1px 0 rgba(255,255,255,0.45) inset,
                0 14px 30px -6px {SIGNAL}85,
                0 0 34px -2px {MINT_A}b0;
}}
.stButton>button:active {{ transform: translateY(0px) scale(0.985); }}
.stButton>button:focus-visible {{
    outline: none;
    box-shadow: 0 0 0 3px {PANEL}, 0 0 0 6px {SIGNAL}80, 0 0 26px -2px {MINT_A}90;
}}
@keyframes buttonGlowPulse {{
    0%, 100% {{ box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset, 0 8px 20px -4px {SIGNAL}70, 0 0 16px -4px {MINT_A}60; }}
    50%      {{ box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset, 0 8px 24px -4px {SIGNAL}80, 0 0 30px -4px {MINT_A}a0; }}
}}

/* Secondary / ghost buttons -- quiet by design, so the one primary
   action on a screen still reads as the thing to press. */
button[kind="secondary"] {{
    background: {PANEL} !important;
    color: {MINT_C} !important;
    border: 1.5px solid {LINE} !important;
    box-shadow: none !important;
    font-weight: 700 !important;
    animation: none !important;
}}
button[kind="secondary"] p {{ color: {MINT_C} !important; font-weight: 700 !important; }}
button[kind="secondary"]:hover {{
    background: {SIGNAL}0F !important;
    border-color: {SIGNAL}70 !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 18px -6px {MINT_A}60 !important;
}}
button[kind="secondary"]:focus-visible {{
    outline: none;
    box-shadow: 0 0 0 3px {PANEL}, 0 0 0 6px {SIGNAL}55 !important;
}}

/* Every primary (solid) button gets a slow luminous shine sweep on
   top of the glow-pulse above, so the call-to-action reads as lit
   from within -- most noticeable on the sign-in / register CTAs. */
.stButton>button {{ overflow: hidden; }}
.stButton>button::after {{
    content: "";
    position: absolute;
    top: 0; left: -60%;
    width: 40%; height: 100%;
    background: linear-gradient(100deg, transparent, rgba(255,255,255,0.55) 50%, transparent);
    transform: skewX(-20deg);
    animation: authSheen 3.6s ease-in-out infinite;
    pointer-events: none;
}}
button[kind="secondary"]::after {{ display: none; }}
@keyframes authSheen {{
    0%   {{ left: -60%; }}
    55%  {{ left: 140%; }}
    100% {{ left: 140%; }}
}}

.stTextInput input, .stTextArea textarea,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"],
.stDateInput input, .stTimeInput input {{
    background: {PANEL2} !important;
    border: 1.5px solid {LINE} !important;
    border-radius: 11px !important;
    color: {INK} !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}}
.stTextInput input:hover, .stTextArea textarea:hover {{ border-color: {SIGNAL}60 !important; }}
.stTextInput input:focus, .stTextArea textarea:focus {{
    background: {PANEL} !important;
    border-color: {SIGNAL} !important;
    box-shadow: 0 0 0 3px {SIGNAL}22 !important;
}}
.stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label,
.stDateInput label, .stTimeInput label {{
    font-weight: 600 !important;
    font-size: 13px !important;
    color: {INK_SOFT} !important;
}}

[data-testid="stFileUploader"] {{
    border: 1.5px dashed {SIGNAL}55;
    border-radius: 16px;
    padding: 26px;
    background: {PANEL2};
    transition: border-color 0.2s ease, background 0.2s ease;
}}
[data-testid="stFileUploader"]:hover {{ border-color: {SIGNAL}; background: {SIGNAL}0A; }}

.stProgress > div > div {{
    background: linear-gradient(90deg, {MINT_C}, {SIGNAL}, {GOLD}) !important;
}}

.stCheckbox label p {{ font-size: 13px !important; color: {MIST} !important; }}

[data-testid="stAlert"] {{
    border-radius: 14px !important;
    border: 1px solid {LINE} !important;
}}

div[role="radiogroup"] label {{
    background: {PANEL2};
    border: 1px solid {LINE};
    border-radius: 999px !important;
    padding: 6px 14px !important;
    margin-right: 6px !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    transition: all 0.16s ease;
}}

/* ---------------------------------------------------------
   NATIVE BORDERED CONTAINERS (st.container(border=True))
   Used instead of the raw-HTML open/close-div trick, which
   cannot actually wrap real widgets — restyle Streamlit's own
   bordered container to look like our glass cards instead.
   --------------------------------------------------------- */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {PANEL} !important;
    border: 1.5px solid {LINE} !important;
    border-radius: 20px !important;
    box-shadow: 0 10px 30px 0 rgba(13,175,156,0.09) !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {{
    gap: 0.6rem;
}}

/* Split-hero landing panel (left brand column) */
.hero-panel {{
    position: relative;
    border-radius: 26px;
    padding: 46px 40px;
    height: 100%;
    min-height: 560px;
    background:
        radial-gradient(520px 320px at 15% 0%, rgba(255,255,255,0.16), transparent 60%),
        radial-gradient(420px 300px at 100% 100%, rgba(212,175,55,0.22), transparent 55%),
        linear-gradient(155deg, {MINT_C} 0%, {SIGNAL} 55%, {MINT_A} 120%);
    box-shadow: 0 24px 60px rgba(11,127,115,0.28);
    overflow: hidden;
}}
.hero-panel::after {{
    content: "";
    position: absolute;
    right: -60px; bottom: -60px;
    width: 240px; height: 240px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.14), transparent 70%);
}}
.hero-feature {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
}}
.hero-feature-icon {{
    width: 30px; height: 30px; min-width: 30px; border-radius: 9px;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.3);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
}}

/* ---------------------------------------------------------
   KPI / METRIC CARDS -- color-matched glass with a moving
   glow bar, a diagonal shine sweep, and a pulsing icon ring.
   Colors are supplied per-card via inline CSS custom
   properties (--kpi-*) so this one ruleset drives every KPI
   card on every page, whatever its accent color is.
   --------------------------------------------------------- */
.kpi-card {{
    position: relative;
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 0;
    border: 1.5px solid var(--kpi-border, {LINE});
    background: var(--kpi-bg, {PANEL});
    box-shadow: var(--kpi-shadow, 0 10px 30px 0 rgba(13,175,156,0.09));
    overflow: hidden;
    transition: transform 0.3s cubic-bezier(0.25,0.8,0.25,1), box-shadow 0.3s ease;
}}
.kpi-card:hover {{
    transform: translateY(-5px);
    box-shadow: var(--kpi-shadow-hover, 0 18px 44px 0 rgba(63,242,196,0.20));
}}
.kpi-top-bar {{
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: var(--kpi-bar);
    background-size: 200% auto;
    animation: kpiBarMove 3.2s linear infinite;
}}
@keyframes kpiBarMove {{
    0%   {{ background-position: 0% center; }}
    100% {{ background-position: 200% center; }}
}}
.kpi-shine {{
    position: absolute;
    top: 0; left: -160%;
    width: 55%; height: 100%;
    background: linear-gradient(100deg, transparent, var(--kpi-sheen, rgba(255,255,255,0.5)) 50%, transparent);
    transform: skewX(-20deg);
    animation: kpiSweep 5s ease-in-out infinite;
    pointer-events: none;
}}
@keyframes kpiSweep {{
    0%   {{ left: -160%; }}
    45%  {{ left: 160%; }}
    100% {{ left: 160%; }}
}}
.kpi-icon {{
    width: 46px; height: 46px; border-radius: 13px;
    display: flex; align-items: center; justify-content: center;
    font-size: 21px;
    position: relative; z-index: 1;
    background: var(--kpi-icon-bg);
    border: 1px solid var(--kpi-border, transparent);
    animation: kpiIconGlow 2.6s ease-in-out infinite;
}}
@keyframes kpiIconGlow {{
    0%, 100% {{ box-shadow: 0 0 0 0 var(--kpi-ring, rgba(0,0,0,0)); }}
    50%      {{ box-shadow: 0 0 0 7px var(--kpi-ring, rgba(0,0,0,0)); }}
}}
.kpi-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--kpi-solid, {MINT_A});
    box-shadow: 0 0 0 4px var(--kpi-ring, rgba(63,242,196,0.15));
    position: relative; z-index: 1;
}}
.kpi-value {{
    position: relative; z-index: 1;
}}

/* ---------------------------------------------------------
   WELCOME HERO -- big "AI Recruitment Copilot" style banner
   with a soft radial glow behind the greeting.
   --------------------------------------------------------- */
.hero-welcome {{
    position: relative;
    border-radius: 22px;
    padding: 28px 32px;
    border: 1.5px solid {LINE};
    background:
        radial-gradient(480px 240px at 92% -10%, {SKY}22, transparent 60%),
        radial-gradient(420px 260px at 100% 100%, {VIOLET}18, transparent 55%),
        linear-gradient(150deg, {MINT_C}12 0%, {PANEL} 55%, {SIGNAL}0A 100%);
    box-shadow: 0 12px 34px 0 rgba(13,175,156,0.10);
    overflow: hidden;
}}
.hero-welcome-orb {{
    position: absolute; right: -40px; top: -40px;
    width: 220px; height: 220px; border-radius: 50%;
    background: radial-gradient(circle, {SKY}28, transparent 70%);
    filter: blur(4px);
}}

/* ---------------------------------------------------------
   ATS DONUT -- pure-CSS conic-gradient ring + side legend,
   matching the reference layout exactly and needing no chart
   library, so it repaints for free under Night Mode.
   --------------------------------------------------------- */
.ats-donut-wrap {{ display:flex; align-items:center; gap: 22px; }}
.ats-donut {{
    width: 128px; height: 128px; min-width: 128px; border-radius: 50%;
    display:flex; align-items:center; justify-content:center;
    box-shadow: 0 6px 20px rgba(13,175,156,0.10);
}}
.ats-donut-inner {{
    width: 88px; height: 88px; border-radius: 50%;
    background: {PANEL};
    display:flex; flex-direction:column; align-items:center; justify-content:center;
}}
.ats-donut-value {{ font-size: 22px; font-weight: 800; font-family:'Space Grotesk'; color: {INK}; }}
.ats-donut-label {{ font-size: 10px; color: {MIST}; margin-top: 2px; text-align:center; }}
.ats-legend {{ font-size: 12.5px; line-height: 2.1; color: {INK_SOFT}; }}
.ats-legend .dot {{
    display:inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;
}}
.ats-legend .pct {{ color: {MIST}; font-weight: 600; }}

/* ---------------------------------------------------------
   HIRING PIPELINE FUNNEL -- horizontal tapered bars, widest
   stage first, each labeled with its count.
   --------------------------------------------------------- */
.funnel-row {{ margin-bottom: 12px; }}
.funnel-label {{
    display: flex; justify-content: space-between; align-items: baseline;
    font-size: 12.5px; font-weight: 700; color: {MIST}; margin-bottom: 5px;
}}
.funnel-label b {{ color: {INK}; font-size: 13.5px; font-family:'Space Grotesk'; }}
.funnel-track {{
    height: 14px; border-radius: 8px;
    background: {PANEL2}; border: 1px solid {LINE};
    overflow: hidden;
}}
.funnel-fill {{
    height: 100%; border-radius: 8px;
    transition: width 0.4s ease;
}}

/* ---------------------------------------------------------
   SKILL DEMAND -- ranked horizontal bars.
   --------------------------------------------------------- */
.skill-row {{ margin-bottom: 11px; }}
.skill-label {{
    display: flex; justify-content: space-between;
    font-size: 12.5px; font-weight: 600; color: {INK_SOFT}; margin-bottom: 4px;
}}
.skill-track {{
    height: 9px; border-radius: 6px;
    background: {PANEL2}; border: 1px solid {LINE};
    overflow: hidden;
}}
.skill-fill {{ height: 100%; border-radius: 6px; }}

/* ---------------------------------------------------------
   RECENT CANDIDATES mini table + AI insight rows
   --------------------------------------------------------- */
.mini-row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 2px; border-bottom: 1px solid {LINE_SOFT};
    font-size: 13px;
}}
.mini-row:last-child {{ border-bottom: none; }}
.mini-name {{ font-weight: 700; color: {INK}; }}
.mini-sub {{ color: {MIST}; font-size: 11.5px; margin-top: 1px; }}
.mini-badge {{
    padding: 4px 11px; border-radius: 999px; font-size: 11px; font-weight: 700;
    white-space: nowrap;
}}

.insight-row {{
    display: flex; align-items: flex-start; gap: 10px;
    padding: 11px 12px; border-radius: 12px;
    background: {PANEL2}; border: 1px solid {LINE};
    margin-bottom: 8px; font-size: 12.5px;
}}
.insight-row:last-child {{ margin-bottom: 0; }}

/* Dashboard "Recent AI Insights" mini-cards (icon-on-top layout, distinct
   from .insight-row's flex-row layout). Given a real class so the night
   mode layer below can repaint it -- previously these were raw inline
   `style="background:{PANEL2}..."` divs with no class, which nothing in
   night mode could target, so they stayed light-mode white with
   near-invisible text on top. */
.ai-insight-card {{
    background: {PANEL2}; border: 1px solid {LINE}; border-radius: 14px;
    padding: 12px 14px; height: 100%;
}}

/* Decorative (non-functional) AI Copilot input mock */
.copilot-card {{ display: flex; flex-direction: column; height: 100%; }}
.copilot-input-mock {{
    margin-top: 12px;
    padding: 11px 14px;
    border-radius: 12px;
    background: {PANEL2};
    border: 1px solid {LINE};
    color: {MIST};
    font-size: 12.5px;
    display: flex; align-items: center; justify-content: space-between;
}}

/* ---------------------------------------------------------
   CANDIDATE OVERVIEW -- horizontal pipeline stepper, dashboard
   mini list-cards ("Recent Activity" / "Upcoming Interviews" /
   "Messages from Recruiters" / "Recent Applications"), and the
   small quote card next to the welcome banner.
   --------------------------------------------------------- */
.quote-card {{
    height: 100%;
    display: flex; align-items: center; justify-content: center;
    text-align: center;
    padding: 18px 20px;
}}
.quote-card-text {{
    color: {MIST}; font-size: 12.5px; font-style: italic; line-height: 1.55;
}}

.stepper-row {{
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 2px; padding: 2px 4px 6px 4px;
}}
.stepper-node {{
    display: flex; flex-direction: column; align-items: center; text-align: center;
    min-width: 60px; flex: 1;
}}
.stepper-circle {{
    width: 50px; height: 50px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 19px; border: 1.5px solid; margin-bottom: 8px;
}}
.stepper-label {{ font-size: 11.5px; color: {MIST}; font-weight: 700; }}
.stepper-count {{
    font-size: 19px; font-weight: 800; color: {INK};
    font-family: 'Space Grotesk', sans-serif; margin-top: 2px;
}}
.stepper-arrow {{
    color: {LINE}; font-size: 17px; margin-top: 17px; flex-shrink: 0;
}}
.rejected-mini-card {{
    display: flex; align-items: center; gap: 12px;
    background: {RISK}0d; border: 1px solid {RISK}30; border-radius: 14px;
    padding: 10px 16px; margin-top: 16px; max-width: 55%;
}}

.view-all-link {{ color: {SIGNAL}; font-size: 11.5px; font-weight: 700; white-space: nowrap; }}

.list-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid {LINE_SOFT};
}}
.list-row:last-child {{ border-bottom: none; }}
.list-row-icon {{
    width: 36px; height: 36px; min-width: 36px; border-radius: 11px;
    display: flex; align-items: center; justify-content: center; font-size: 15px;
}}
.list-row-text {{ flex: 1; min-width: 0; }}
.list-row-title {{
    font-weight: 700; color: {INK}; font-size: 12.5px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.list-row-sub {{
    color: {MIST}; font-size: 11px; margin-top: 1px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.list-row-badge {{
    padding: 4px 10px; border-radius: 999px; font-size: 10px; font-weight: 700;
    border: 1px solid; white-space: nowrap;
}}
.card-footer-link {{
    margin-top: 10px; padding-top: 10px; border-top: 1px solid {LINE_SOFT};
    text-align: center; color: {SIGNAL}; font-size: 12px; font-weight: 700;
}}

.tip-banner {{
    padding: 16px 24px; background: {SIGNAL}0d; border-color: {SIGNAL}30 !important;
    display: flex; align-items: center; gap: 14px; height: 100%;
}}
</style>
""", unsafe_allow_html=True)

    if st.session_state.get("dark_mode"):
        _inject_night_mode_css()


def _inject_night_mode_css():
    """Night Mode override layer -- deep-space navy/black surfaces with a
    neon mint-teal glow, matching the reference dashboard screenshot.
    Layered on TOP of load_css()'s normal stylesheet via !important rules
    targeting the same class names (.glass, .glass-flat, sidebar, etc.)
    rather than rewriting every f-string color everywhere in the app --
    those still bake in the light-theme hex values, but !important on an
    external rule beats a plain (non-!important) inline style, so this
    repaints every surface without touching the 15+ files that call
    metric_card() / render inline HTML with the light palette."""
    st.markdown(f"""
<style>
.stApp {{
    background:
        radial-gradient(1200px 600px at 75% -10%, rgba(14,165,233,0.10), transparent 55%),
        radial-gradient(900px 500px at 15% 90%, rgba(139,92,246,0.10), transparent 55%),
        radial-gradient(800px 560px at 100% 60%, rgba(63,242,196,0.07), transparent 60%),
        linear-gradient(165deg, #02050B 0%, #050A14 55%, #070B0E 100%) !important;
    background-attachment: fixed !important;
}}
html, body, [class*="css"] {{ background: transparent !important; color: {NIGHT_TEXT} !important; }}
p, span, div, label, li, td, th {{ color: {NIGHT_TEXT} !important; }}
h1, h2, h3, h4 {{ color: {NIGHT_TEXT} !important; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {NIGHT_MUTED} !important; }}

[data-testid="stSidebar"] {{
    background: linear-gradient(190deg, #090D11 0%, #0C1319 55%, #0A0F13 100%) !important;
    border-right: 1px solid {NIGHT_LINE} !important;
}}
[data-testid="stSidebar"] * {{ color: {NIGHT_TEXT} !important; }}

.glass, .glass-flat {{
    background: linear-gradient(160deg, {NIGHT_PANEL} 0%, {NIGHT_PANEL2} 100%) !important;
    border: 1.5px solid {NIGHT_LINE} !important;
    box-shadow: 0 10px 30px 0 rgba(63,242,196,0.06) !important;
}}
.glass:hover {{ border-color: {MINT_A}66 !important; box-shadow: 0 18px 44px 0 rgba(63,242,196,0.16) !important; }}

[data-testid="stMetric"], .stDataFrame, .stTable, [data-testid="stExpander"], [data-testid="stForm"] {{
    background: {NIGHT_PANEL} !important;
    border: 1px solid {NIGHT_LINE} !important;
    border-radius: 14px !important;
    color: {NIGHT_TEXT} !important;
}}
[data-testid="stExpander"] summary {{ color: {NIGHT_TEXT} !important; }}

input, textarea, select, .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] > div {{
    background: {NIGHT_PANEL2} !important;
    color: {NIGHT_TEXT} !important;
    border-color: {NIGHT_LINE} !important;
}}
.stButton button, .stDownloadButton button {{
    background: {NIGHT_PANEL2} !important;
    color: {NIGHT_TEXT} !important;
    border: 1px solid {NIGHT_LINE} !important;
}}
.stButton button[kind="primary"], .stButton button[data-testid="baseButton-primary"] {{
    background: linear-gradient(90deg, {MINT_C}, {SIGNAL}) !important;
    color: #04120E !important;
    border: none !important;
}}
[data-testid="stChatInput"], [data-testid="stChatMessage"] {{
    background: {NIGHT_PANEL2} !important;
    color: {NIGHT_TEXT} !important;
    border-color: {NIGHT_LINE} !important;
}}
hr {{ border-color: {NIGHT_LINE} !important; background: {NIGHT_LINE} !important; }}

/* --- Tabs (Live Interview / Evaluation & Hiring Decision / Interview
   Pipeline, etc.) -- load_css() bakes light-theme PANEL2/white into
   these, so without this repaint the tab bar stays a bright white
   strip floating on the dark page. --- */
.stTabs [data-baseweb="tab-list"] {{
    background: {NIGHT_PANEL2} !important;
    border-color: {NIGHT_LINE} !important;
}}
.stTabs [data-baseweb="tab"] {{ color: {NIGHT_MUTED} !important; }}
.stTabs [data-baseweb="tab"]:hover {{ color: {NIGHT_TEXT} !important; }}
.stTabs [aria-selected="true"] {{
    color: {MINT_A} !important;
    background: {NIGHT_PANEL} !important;
    box-shadow: 0 4px 14px -2px rgba(63,242,196,0.25) !important;
}}

/* --- Other native Streamlit chrome that shares the same
   never-repainted-for-night-mode gap as the tabs above. --- */
[data-testid="stFileUploader"] {{
    background: {NIGHT_PANEL2} !important;
    border-color: {SIGNAL}55 !important;
}}
[data-testid="stFileUploader"]:hover {{ background: {SIGNAL}14 !important; border-color: {SIGNAL} !important; }}
[data-testid="stAlert"] {{
    background: {NIGHT_PANEL2} !important;
    border-color: {NIGHT_LINE} !important;
    color: {NIGHT_TEXT} !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {NIGHT_PANEL} !important;
    border-color: {NIGHT_LINE} !important;
    box-shadow: 0 10px 30px 0 rgba(63,242,196,0.06) !important;
}}
div[role="radiogroup"] label {{
    background: {NIGHT_PANEL2} !important;
    border-color: {NIGHT_LINE} !important;
    color: {NIGHT_MUTED} !important;
}}
/* The generic rule above is !important, which -- regardless of selector
   specificity -- beats the sidebar nav's own (non-!important) pill
   background/hover/checked rules in load_css(), flattening the nav
   pills into bare radio bullets. Restore them here, explicitly, after
   the generic rule so these win both on !important and source order. */
[data-testid="stSidebar"] [role="radiogroup"] label {{
    background: rgba(255,255,255,0.04) !important;
    border-color: transparent !important;
    color: {NIGHT_TEXT} !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(255,255,255,0.08) !important;
    border-color: var(--nav-border-soft, {NIGHT_LINE}) !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {{
    background: linear-gradient(90deg, var(--nav-wash, {MINT_A}22), var(--nav-wash2, {SIGNAL}12)) !important;
    border-color: var(--nav-border, {SIGNAL}55) !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] p {{
    color: var(--nav-solid, {MINT_A}) !important;
}}
.stCheckbox label p {{ color: {NIGHT_MUTED} !important; }}

/* --- Date / Time pickers -- load_css() never styled .stDateInput /
   .stTimeInput at all (only text/number/select inputs), so these have
   always rendered as bare browser-default white fields; it just didn't
   show against the light theme. Fixing for both modes matters, but the
   night-mode !important repaint is what makes it visible here. --- */
.stDateInput input, .stTimeInput input,
.stDateInput [data-baseweb="input"], .stTimeInput [data-baseweb="input"],
.stDateInput [data-baseweb="base-input"], .stTimeInput [data-baseweb="base-input"] {{
    background: {NIGHT_PANEL2} !important;
    color: {NIGHT_TEXT} !important;
    border-color: {NIGHT_LINE} !important;
}}
.stDateInput svg, .stTimeInput svg {{ fill: {NIGHT_MUTED} !important; }}

/* --- Dashboard widgets for the "AI Recruitment Copilot" layout ---
   These bake light-theme hex values into their inline styles just like
   the rest of the app, so they need the same !important repaint here. */
.kpi-card {{
    background: linear-gradient(160deg, {NIGHT_PANEL} 0%, {NIGHT_PANEL2} 100%) !important;
    border-color: {NIGHT_LINE} !important;
}}
.hero-welcome {{
    background:
        radial-gradient(480px 240px at 92% -10%, rgba(35,152,255,0.20), transparent 60%),
        radial-gradient(420px 260px at 100% 100%, rgba(123,85,255,0.16), transparent 55%),
        linear-gradient(150deg, #07101D 0%, #091526 60%, #070E17 100%) !important;
    border-color: {NIGHT_LINE} !important;
}}
.hero-welcome-orb {{ background: radial-gradient(circle, rgba(35,152,255,0.30), transparent 70%) !important; }}
.ats-donut-inner {{ background: {NIGHT_PANEL} !important; }}
.chip {{ filter: brightness(1.15); }}
.funnel-track {{ background: {NIGHT_PANEL2} !important; border-color: {NIGHT_LINE} !important; }}
.skill-track {{ background: {NIGHT_PANEL2} !important; border-color: {NIGHT_LINE} !important; }}
.mini-row {{ border-bottom-color: {NIGHT_LINE} !important; }}
.copilot-input-mock {{
    background: {NIGHT_PANEL2} !important;
    border-color: {NIGHT_LINE} !important;
    color: {NIGHT_MUTED} !important;
}}
.insight-row {{ border-color: {NIGHT_LINE} !important; background: {NIGHT_PANEL2} !important; }}
.ai-insight-card {{ border-color: {NIGHT_LINE} !important; background: {NIGHT_PANEL2} !important; }}
.js-plotly-plot .legendtext, .js-plotly-plot text {{ fill: {NIGHT_TEXT} !important; }}

/* --- Candidate Overview: stepper, mini list-cards, quote/tip banners --- */
.stepper-arrow {{ color: {NIGHT_LINE} !important; }}
.rejected-mini-card {{ background: rgba(220,76,76,0.10) !important; border-color: rgba(220,76,76,0.30) !important; }}
.list-row {{ border-bottom-color: {NIGHT_LINE} !important; }}
.card-footer-link {{ border-top-color: {NIGHT_LINE} !important; }}
.tip-banner {{ background: rgba(13,175,156,0.10) !important; border-color: rgba(13,175,156,0.30) !important; }}
</style>
""", unsafe_allow_html=True)


def sidebar_logo():
    st.markdown(f"""
    <div class="glass sidebar-logo-card" style="padding: 22px 10px; text-align: center;">
        <div class="kpi-top-bar" style="--kpi-bar: linear-gradient(90deg, {MINT_C}00, {MINT_A}, {GOLD}, {SIGNAL}, {MINT_C}00);"></div>
        <div style="width: 54px; height: 54px; margin: auto; border-radius: 15px;
            background: linear-gradient(135deg, {MINT_A} 0%, {SIGNAL} 60%, {MINT_C} 100%);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 20px rgba(13,175,156,0.30);
            color: #06231C; font-size: 22px; font-weight: 800; font-family: 'Space Grotesk';
            animation: kpiIconGlow 2.6s ease-in-out infinite; --kpi-ring: {MINT_A}40;">
            &#11049;
        </div>
        <div style="margin-top: 13px; font-size: 18px; font-weight: 800; font-family: 'Space Grotesk'; color: {INK};">
            TalentOps <span style="color:{SIGNAL};">AI</span>
        </div>
        <div style="color: {MIST}; font-size: 11.5px; margin-top: 2px; letter-spacing: 0.4px;">
            Enterprise Hiring Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)


def sidebar_session(username, role_display, is_recruiter=True):
    """Premium replacement for the old plain-text 'Active Session' block:
    an avatar chip (first letter of the username), a live status dot,
    and a color-matched role pill -- teal for recruiters, gold for
    candidates -- inside the same glass-card language as the rest of
    the app."""
    initial = (username or "U").strip()[:1].upper() or "U"
    role_color = SIGNAL if is_recruiter else GOLD
    st.markdown(f"""
        <div class="glass-flat sidebar-session-card">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="position:relative; width:42px; height:42px; min-width:42px;">
                    <div style="width:42px; height:42px; border-radius:12px;
                        background: linear-gradient(135deg, {role_color}2e, {role_color}12);
                        border: 1px solid {role_color}40;
                        display:flex; align-items:center; justify-content:center;
                        font-family:'Space Grotesk'; font-weight:800; font-size:17px; color:{role_color};">
                        {initial}
                    </div>
                    <div style="position:absolute; right:-2px; bottom:-2px; width:11px; height:11px;
                        border-radius:50%; background:{VERDICT}; border:2px solid #FFFFFF;
                        box-shadow:0 0 0 3px {VERDICT}22;"></div>
                </div>
                <div style="min-width:0;">
                    <div style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1.2px;
                        color:{MIST}; font-family:'IBM Plex Mono',monospace;">Active Session</div>
                    <div style="font-size:15px; font-weight:800; color:{INK}; margin-top:2px;
                        overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{username}</div>
                </div>
            </div>
            <div style="margin-top:12px; display:inline-flex; align-items:center; gap:6px;
                padding:4px 11px; border-radius:999px; background:{role_color}14; border:1px solid {role_color}38;
                font-size:11px; font-weight:700; color:{role_color};">
                <span style="width:6px; height:6px; border-radius:50%; background:{role_color};"></span>
                {role_display}
            </div>
        </div>
        """, unsafe_allow_html=True)


def theme_toggle():
    """Night Mode switch -- shared by both the recruiter and candidate
    sidebars (called once, before the role branch, in app.py) so either
    portal can flip the whole app into the dark 'glass in space' theme
    from the reference screenshot. State lives in st.session_state, so
    it persists across reruns/page changes for the rest of the session."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    is_dark = st.session_state.dark_mode
    label = "🌙 Night Mode" if not is_dark else "☀️ Day Mode"
    if st.button(label, key="theme_toggle_btn", use_container_width=True):
        st.session_state.dark_mode = not is_dark
        st.rerun()


def page_title(title, subtitle):
    st.markdown(f"""
    <div class="glass" style="padding: 22px 26px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-size: 26px; font-weight: 800; font-family: 'Space Grotesk'; color: {INK};">{title}</div>
            <div style="margin-top: 4px; color: {MIST}; font-size: 13px;">{subtitle}</div>
        </div>
        <div style="padding: 7px 16px; background: linear-gradient(90deg, {SIGNAL}14, {GOLD}12);
            border: 1px solid {LINE}; border-radius: 999px; color: {MINT_C}; font-weight: 700;
            font-size: 11px; font-family: 'IBM Plex Mono'; letter-spacing: 1px; white-space: nowrap;">
            &#11049; PRO CORE
        </div>
    </div>
    """, unsafe_allow_html=True)


def metric_card(title, value, icon="📊", color=None, trend=None):
    """trend: optional short string like '+12% this week' shown under the value.

    Card is fully color-matched to `color`: tinted glass background, a
    moving glow bar along the top edge, a diagonal shine sweep, and a
    pulsing ring around the icon -- all driven by CSS custom properties
    set inline below, so one shared stylesheet ruleset (see .kpi-card
    in load_css) animates every KPI card on every page consistently.
    """
    color = color or SIGNAL
    trend_html = (
        f'<div class="kpi-value" style="font-size:11px; color:{color}; font-weight:600; margin-top:6px;">{trend}</div>'
        if trend else ""
    )
    card_vars = (
        f"--kpi-bg: linear-gradient(160deg, {color}14 0%, #FFFFFF 55%, {color}0A 100%); "
        f"--kpi-border: {color}35; "
        f"--kpi-shadow: 0 10px 28px 0 {color}1f; "
        f"--kpi-shadow-hover: 0 18px 42px 0 {color}30; "
        f"--kpi-bar: linear-gradient(90deg, {color}00, {color}, {GOLD}, {color}, {color}00); "
        f"--kpi-sheen: {color}2e; "
        f"--kpi-icon-bg: linear-gradient(135deg, {color}30, {color}10); "
        f"--kpi-ring: {color}30; "
        f"--kpi-solid: {color};"
    )
    st.markdown(f"""
        <div class="kpi-card" style="{card_vars}">
            <div class="kpi-top-bar"></div>
            <div class="kpi-shine"></div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-dot"></div>
            </div>
            <div class="kpi-value" style="font-size: 11px; color: {MIST}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px;">
                {title}
            </div>
            <div class="kpi-value" style="font-size: 28px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; color: {color}; margin-top: 4px; text-shadow: 0 0 22px {color}2a;">
                {value}
            </div>
            {trend_html}
        </div>
        """, unsafe_allow_html=True)


def welcome_hero(username, subtitle=None, primary_label=None, primary_nav=None,
                  secondary_label=None, secondary_nav=None):
    """Big greeting banner ('Welcome, {username}!') for the top of the
    dashboard, in the style of the reference 'AI Recruitment Copilot'
    layout. `primary_nav`/`secondary_nav` are page labels — if given,
    the buttons stash a `_qa_nav` redirect the same way the existing
    Quick Actions panel does."""
    subtitle = subtitle or "Your AI Recruitment Copilot is ready to find, evaluate and hire the best talent."
    st.markdown(f"""
        <div class="hero-welcome">
            <div class="hero-welcome-orb"></div>
            <div class="hero-badge" style="margin-bottom:14px;"><span class="hero-dot"></span> Live Pipeline</div>
            <div style="position:relative; font-family:'Space Grotesk',sans-serif; font-size: 27px;
                font-weight: 800; letter-spacing: -0.5px; color:{INK};">
                Welcome, {username}!
            </div>
            <div style="position:relative; font-size: 13.5px; color: {MIST}; margin-top: 6px; max-width:640px;">
                {subtitle}
            </div>
        </div>
        """, unsafe_allow_html=True)

    if primary_label or secondary_label:
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        bcols = st.columns([1, 1, 3]) if secondary_label else st.columns([1, 3])
        if primary_label:
            with bcols[0]:
                if st.button(primary_label, use_container_width=True, key="hero_primary_btn"):
                    if primary_nav:
                        st.session_state["_qa_nav"] = primary_nav
                        st.rerun()
        if secondary_label:
            with bcols[1]:
                if st.button(secondary_label, use_container_width=True, key="hero_secondary_btn"):
                    if secondary_nav:
                        st.session_state["_qa_nav"] = secondary_nav
                        st.rerun()


def ats_donut(buckets, colors, total, center_label="Total Candidates"):
    """Pure-CSS conic-gradient donut + legend, replacing the old Plotly
    pie so the ATS Score Distribution card matches the reference layout
    exactly and never needs separate dark-mode chart theming.

    buckets: dict {label: count}, in the order they should appear.
    colors:  list of hex colors, same length/order as buckets.
    total:   sum shown in the donut's center.
    """
    if total <= 0:
        st.markdown(f'<div style="color:{MIST}; font-size:13px; padding:8px 0;">No candidates processed yet — the distribution will appear here once resumes are scored.</div>', unsafe_allow_html=True)
        return

    stops = []
    running = 0.0
    for (label, count), color in zip(buckets.items(), colors):
        start_pct = (running / total) * 100
        running += count
        end_pct = (running / total) * 100
        stops.append(f"{color} {start_pct:.2f}% {end_pct:.2f}%")
    conic = ", ".join(stops)

    legend_rows = ""
    for (label, count), color in zip(buckets.items(), colors):
        pct = round((count / total) * 100)
        legend_rows += (
            f'<div><span class="dot" style="background:{color};"></span>'
            f'{label} <span class="pct">· {pct}%</span></div>'
        )

    st.markdown(f"""
        <div class="ats-donut-wrap">
            <div class="ats-donut" style="background: conic-gradient({conic});">
                <div class="ats-donut-inner">
                    <div class="ats-donut-value">{total}</div>
                    <div class="ats-donut-label">{center_label}</div>
                </div>
            </div>
            <div class="ats-legend">{legend_rows}</div>
        </div>
        """, unsafe_allow_html=True)


def pipeline_funnel(stages):
    """stages: list of (label, count, color) tuples, widest/first stage
    first. Each bar's width is scaled relative to the first stage's
    count so the funnel visually tapers."""
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:16px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\'; margin-bottom:16px;">'
        f'🧭 Hiring Pipeline</div>',
        unsafe_allow_html=True,
    )
    base = max((s[1] for s in stages), default=0) or 1
    rows = ""
    for label, count, color in stages:
        pct = max(4, round((count / base) * 100))
        rows += f"""
        <div class="funnel-row">
            <div class="funnel-label"><span>{label}</span><b>{count}</b></div>
            <div class="funnel-track"><div class="funnel-fill" style="width:{pct}%; background:linear-gradient(90deg, {color}AA, {color});"></div></div>
        </div>
        """
    st.markdown(rows, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def pipeline_stepper(stages, rejected_count=0, rejected_label="Rejected"):
    """stages: list of (icon, label, count, color) tuples, in pipeline
    order. Renders a horizontal stepper -- circular icon nodes joined
    by arrows -- with a separate small Rejected card underneath, in
    the style of the candidate Overview reference layout.

    Every HTML chunk below is emitted as a SINGLE-LINE string in its
    own st.markdown call. Streamlit's markdown parser treats a run of
    HTML as a raw passthrough block only until it hits a blank (or
    whitespace-only) line -- after that it reverts to normal Markdown
    rules, and any line indented 4+ spaces gets rendered as a literal
    code block instead of HTML. Pretty-printed multi-line f-strings
    are exactly how that blank line sneaks in, so everything here is
    built as one line per call."""
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:16px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\'; margin-bottom:14px;">🧭 Application Pipeline</div>',
        unsafe_allow_html=True,
    )
    nodes = ""
    for i, (icon, label, count, color) in enumerate(stages):
        nodes += (
            f'<div class="stepper-node">'
            f'<div class="stepper-circle" style="background:{color}18; border-color:{color}55; color:{color};">{icon}</div>'
            f'<div class="stepper-label">{label}</div>'
            f'<div class="stepper-count">{count}</div>'
            f'</div>'
        )
        if i < len(stages) - 1:
            nodes += '<div class="stepper-arrow">&#8594;</div>'
    st.markdown(f'<div class="stepper-row">{nodes}</div>', unsafe_allow_html=True)
    if rejected_count:
        st.markdown(
            f'<div class="rejected-mini-card">'
            f'<div class="stepper-circle" style="width:38px; height:38px; font-size:15px; '
            f'background:{RISK}18; border-color:{RISK}55; color:{RISK}; margin-bottom:0;">❌</div>'
            f'<div><div style="font-weight:800; color:{INK}; font-size:13px;">{rejected_label}</div>'
            f'<div style="color:{MIST}; font-size:11px;">{rejected_count} application(s)</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def dashboard_list_row(icon, icon_color, title, subtitle, badge_text=None, badge_color=None):
    """Builds one row of HTML for a dashboard_list_card — icon chip on
    the left, title/subtitle in the middle, an optional status pill on
    the right. Emitted as one continuous line (no embedded newlines) so
    concatenating many of these never introduces a blank line that
    would break Streamlit's HTML passthrough (see pipeline_stepper's
    docstring for why that matters)."""
    badge = ""
    if badge_text:
        bc = badge_color or SIGNAL
        badge = (
            f'<span class="list-row-badge" style="background:{bc}18; color:{bc}; border-color:{bc}44;">'
            f'{badge_text}</span>'
        )
    return (
        f'<div class="list-row">'
        f'<div class="list-row-icon" style="background:{icon_color}18; color:{icon_color};">{icon}</div>'
        f'<div class="list-row-text">'
        f'<div class="list-row-title">{title}</div>'
        f'<div class="list-row-sub">{subtitle}</div>'
        f'</div>{badge}</div>'
    )


def dashboard_list_card(icon, title, rows_html="", view_all=True, empty_text="Nothing here yet.", footer_label=None):
    """Small dashboard card used for Recent Activity / Upcoming
    Interviews / Messages from Recruiters / Recent Applications --
    a header (with an optional 'View All' label), a stack of
    dashboard_list_row rows, and an optional footer link label.

    Each section is its own st.markdown call (matching the pattern
    already used by list_card/insight_list elsewhere in this file)
    rather than one big pretty-printed f-string -- that's what keeps
    the footer link from ever landing after a blank line and getting
    rendered as a literal code block."""
    st.markdown(f'<div class="glass" style="padding:20px 22px; height:100%;">', unsafe_allow_html=True)
    header_right = '<span class="view-all-link">View All</span>' if view_all else ""
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">'
        f'<div style="font-size:15px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\';">{icon} &nbsp;{title}</div>'
        f'{header_right}</div>',
        unsafe_allow_html=True,
    )
    if rows_html:
        st.markdown(rows_html, unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="color:{MIST}; font-size:12.5px; padding:10px 0;">{empty_text}</div>', unsafe_allow_html=True)
    if footer_label:
        st.markdown(f'<div class="card-footer-link">{footer_label} &nbsp;&rarr;</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def quote_card(text):
    """Small italic quote card that sits beside the welcome banner on
    the candidate Overview page."""
    st.markdown(
        f'<div class="glass quote-card"><div class="quote-card-text">&#8220;{text}&#8221;</div></div>',
        unsafe_allow_html=True,
    )


def skill_demand_bars(skills, color=None):
    """skills: list of (skill_name, count) tuples, already sorted
    highest-demand first (e.g. from database.top_skills())."""
    color = color or SIGNAL
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:16px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\'; margin-bottom:16px;">'
        f'🧩 Skill Demand</div>',
        unsafe_allow_html=True,
    )
    if not skills:
        st.markdown(f'<div style="color:{MIST}; font-size:13px;">No skills recorded yet.</div>', unsafe_allow_html=True)
    else:
        base = max((c for _, c in skills), default=0) or 1
        rows = ""
        for name, count in skills:
            pct = max(4, round((count / base) * 100))
            rows += f"""
            <div class="skill-row">
                <div class="skill-label"><span>{name}</span><span>{count}</span></div>
                <div class="skill-track"><div class="skill-fill" style="width:{pct}%; background:{color};"></div></div>
            </div>
            """
        st.markdown(rows, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def recent_candidates_mini(rows):
    """rows: list of dicts with name, job_role, ats_score keys (as
    returned by database.get_candidates())."""
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:16px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\'; margin-bottom:6px;">'
        f'🕒 Recent Candidates</div>',
        unsafe_allow_html=True,
    )
    if not rows:
        st.markdown(f'<div style="color:{MIST}; font-size:13px; padding:8px 0;">No candidates processed yet.</div>', unsafe_allow_html=True)
    else:
        body = ""
        for c in rows:
            score = c.get("ats_score") or 0
            if score >= 85:
                badge_color, badge_text = VERDICT, "Highly Recommended"
            elif score >= 70:
                badge_color, badge_text = SIGNAL, "Recommended"
            elif score >= 50:
                badge_color, badge_text = CAUTION, "Consider"
            else:
                badge_color, badge_text = RISK, "Not Recommended"
            body += f"""
            <div class="mini-row">
                <div>
                    <div class="mini-name">{c.get('name','—')}</div>
                    <div class="mini-sub">{c.get('job_role','—')}</div>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="font-family:'Space Grotesk'; font-weight:800; color:{INK}; font-size:14px;">{score}%</div>
                    <div class="mini-badge" style="background:{badge_color}18; color:{badge_color}; border:1px solid {badge_color}40;">{badge_text}</div>
                </div>
            </div>
            """
        st.markdown(body, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def insight_list(items):
    """items: list of (icon, text, color) tuples — short, real,
    data-derived observations (not fabricated AI copy)."""
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:16px; font-weight:800; color:{INK}; font-family:\'Space Grotesk\'; margin-bottom:12px;">'
        f'✨ Recent Insights</div>',
        unsafe_allow_html=True,
    )
    if not items:
        st.markdown(f'<div style="color:{MIST}; font-size:13px;">Nothing to report yet.</div>', unsafe_allow_html=True)
    else:
        rows = ""
        for icon, text, color in items:
            rows += f"""
            <div class="insight-row">
                <div style="font-size:15px;">{icon}</div>
                <div style="color:{INK_SOFT};">{text}</div>
            </div>
            """
        st.markdown(rows, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def copilot_panel():
    """Decorative panel matching the reference layout's 'AI Copilot' box.
    Not wired to a live assistant — purely a visual placeholder, labeled
    honestly so it doesn't imply a working chat feature."""
    st.markdown(f"""
        <div class="glass copilot-card">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div style="font-size:16px; font-weight:800; color:{INK}; font-family:'Space Grotesk';">🧠 AI Copilot</div>
                <div style="font-size:10.5px; color:{MIST}; font-family:'IBM Plex Mono';">PREVIEW</div>
            </div>
            <div style="font-size:12.5px; color:{MIST}; margin-top:8px; line-height:1.5;">
                Ask anything about candidates, ATS scoring, or hiring trends.
            </div>
            <div class="copilot-input-mock">
                <span>Ask AI Copilot…</span>
                <span>➤</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def profile_field(label, value, icon="•"):
    display_value = value if value else "—"
    st.markdown(f"""
        <div class="profile-field">
            <div class="profile-field-label">{icon} &nbsp;{label}</div>
            <div class="profile-field-value">{display_value}</div>
        </div>
        """, unsafe_allow_html=True)


def chip_list(items, color=None):
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


def section_header(icon, title, subtitle=None):
    """Lightweight inline section header, lighter than page_title's hero card."""
    sub = f'<div style="color:{MIST}; font-size:12.5px; margin-top:2px;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin: 4px 0 14px 0;">
            <div style="width:38px; height:38px; border-radius:11px; background:{SIGNAL}16;
                display:flex; align-items:center; justify-content:center; font-size:17px;">{icon}</div>
            <div>
                <div style="font-size:16px; font-weight:800; color:{INK}; font-family:'Space Grotesk';">{title}</div>
                {sub}
            </div>
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
    <div style="margin-top: 44px; padding: 18px; text-align: center; border-top: 1px solid {LINE};
        color: {MIST}; font-size: 11px; font-family: 'IBM Plex Mono';">
        &#11049; TALENTOPS AI &nbsp;•&nbsp; POLISHED MINT EDITION &nbsp;•&nbsp; ENTERPRISE INTELLIGENCE NETWORK ENGINE
    </div>
    """, unsafe_allow_html=True)
