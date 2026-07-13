"""
MCU Institutional Research Office — Executive Dashboard
Supabase-wired Streamlit edition.

To run locally:    streamlit run app.py
To deploy:         push repo to GitHub, connect at share.streamlit.io,
                   add SUPABASE_URL + SUPABASE_KEY in app secrets.

Set up your Supabase project once:
  1. Create a project at supabase.com (free tier)
  2. Run schema.sql in the Supabase SQL Editor
  3. Copy your project URL and anon/public API key from Settings → API
  4. Put them in .streamlit/secrets.toml (local) or Streamlit Cloud secrets (deployed)
"""
from __future__ import annotations  # makes type hints work on Python 3.9
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from supabase import create_client, Client
import extra_streamlit_components as stx
from streamlit_calendar import calendar
from streamlit_option_menu import option_menu

# ============================================================
# PAGE CONFIG + BRAND COLORS
# ============================================================
def _resolve_favicon():
    """Pick the MCU Purple Owls head first, then any other available mark."""
    from pathlib import Path as _P
    here = _P(__file__).parent / "assets"
    for name in ("mcu_owl_head.png",
                 "mcu_owl.png", "mcu_owl.jpg", "mcu_owl.jpeg", "mcu_owl.svg",
                 "iroms_logo.png", "iroms_logo.svg",
                 "mcu_logo.png"):
        candidate = here / name
        if candidate.exists():
            return str(candidate)
    return "🎓"

st.set_page_config(
    page_title="MCU IROMS",
    page_icon=_resolve_favicon(),
    layout="wide",
    initial_sidebar_state="collapsed",
)

PURPLE = "#5b21b6"
NAVY = "#0b2545"
GOLD = "#c9a227"
GREEN = "#16a34a"
RED = "#dc2626"

# =============================================================
# UNIFIED BRAND PALETTE
# =============================================================
# All KPI tiles, lifecycle badges, and Plotly chart colours throughout
# the dashboard pull from these constants so the visual language stays
# consistent across pages.

BRAND = {
    "navy":       "#0a1628",   # primary heading / dark text
    "slate":      "#3b82f6",   # bright cornflower blue (primary KPI)
    "tan":        "#f97316",   # vivid orange (warm accent)
    "sage":       "#10b981",   # emerald green (positive / growth)
    "plum":       "#8b5cf6",   # violet (supplementary)
    "brick":      "#ef4444",   # warm red (secondary accent)
    "terracotta": "#fb7185",   # bright coral (VP / top-tier emphasis)
    "amber":      "#fbbf24",   # bright gold (AVP / second-tier emphasis)
    "moss":       "#84cc16",   # lime green (mid-tier committees)
    "leaf":       "#bef264",   # bright leaf (support roles)
    "teal":       "#14b8a6",   # bright teal accent
    "orange":     "#ff7a00",   # italic emphasis
}

# Ordered list for Plotly chart sequences. Picked to differentiate well
# without clashing.
BRAND_CHART_COLORS = [
    BRAND["slate"], BRAND["tan"], BRAND["sage"], BRAND["plum"],
    BRAND["brick"], BRAND["terracotta"], BRAND["amber"],
    BRAND["moss"], BRAND["teal"], BRAND["leaf"],
]

# ----- Domain-specific palettes that stay vivid (status meaning matters) -----
# Quartile colors: stoplight ramp, easy to differentiate at a glance
QUARTILE_COLORS = {
    "Q1": "#059669",   # deep emerald
    "Q2": "#0ea5e9",   # sky blue
    "Q3": "#f59e0b",   # amber
    "Q4": "#ef4444",   # coral red
    "NA": "#94a3b8",   # slate grey
}
# Categorical palette for colleges / programs (no implied ordering) — now
# uses the brand chart sequence so college breakdowns match the rest of
# the dashboard.
CATEGORICAL_COLORS = BRAND_CHART_COLORS

st.markdown(f"""
<style>
    /* ===== PAGE BACKGROUND ===== */
    .stApp {{
        background: #f4f6fa !important;
    }}

    /* ===== Force main content flush-left even when sidebar is collapsed ===== */
    /* Streamlit reserves a sidebar slot even when hidden. Override it. */
    section[data-testid="stSidebar"][aria-expanded="false"] {{
        margin-left: -200px !important;
    }}
    section[data-testid="stSidebar"][aria-expanded="false"] + section {{
        margin-left: 0 !important;
    }}

    /* Remove default Streamlit horizontal padding everywhere */
    .main .block-container,
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    [data-testid="block-container"] {{
        padding-top: 0 !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
        margin-left: 0 !important;
    }}

    /* Push the main content area flush against the left edge */
    section.main, [data-testid="stMain"], .main {{
        padding-left: 0 !important;
        margin-left: 0 !important;
        max-width: 100% !important;
    }}

    /* Streamlit's emotion-cache classes — catch-all for padding */
    div[class*="block-container"] {{
        padding-left: 0.5rem !important;
        max-width: 100% !important;
    }}
    div[class^="st-emotion-cache"] > .main {{
        padding-left: 0 !important;
    }}

    /* Inner element containers */
    .element-container, [data-testid="stVerticalBlock"] {{
        margin-left: 0 !important;
    }}

    /* ===== HEADER — full-bleed, with logo + tagline ===== */
    .mcu-header {{
        background: linear-gradient(135deg, {PURPLE} 0%, #4c1d95 100%);
        color: white;
        padding: 28px 32px 24px 32px;
        border-bottom: 4px solid {GOLD};
        margin: -3rem -0.5rem 20px -0.5rem;
        box-shadow: 0 2px 12px rgba(91, 33, 182, 0.2);
        overflow: visible;
        position: relative;
    }}
    /* Defaults — the inline styles in header_html override per-element */
    .mcu-header h1 {{ color: white; margin: 0; }}
    .mcu-header .subtitle {{ opacity: 0.9; }}

    /* ===== Hide the left sidebar entirely (identity moved to top-right) ===== */
    section[data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}

    /* ===== Log-out icon in the banner's bottom-right corner ===== */
    .banner-logout {{
        position: absolute;
        right: 20px;
        bottom: 14px;
        display: inline-flex;
        align-items: center;
        gap: 7px;
        color: #fff !important;
        opacity: 0.85;
        text-decoration: none !important;
        font-size: 12.5px;
        font-weight: 600;
        line-height: 1;
        transition: opacity 0.15s ease, transform 0.15s ease;
    }}
    .banner-logout:hover {{ opacity: 1; transform: translateX(2px); }}
    .banner-logout svg {{ display: block; }}

    /* ===== "Forgot your password?" link below the sign-in tabs ===== */
    .forgot-row {{ text-align: center; margin: 10px 0 2px 0; }}
    .forgot-link {{
        color: {PURPLE};
        font-size: 13px;
        font-weight: 600;
        text-decoration: none;
    }}
    .forgot-link:hover {{ text-decoration: underline; }}

    /* ===== Download buttons — consistent brand purple everywhere ===== */
    [data-testid="stDownloadButton"] button {{
        background-color: {PURPLE} !important;
        border: 1px solid {PURPLE} !important;
        color: #ffffff !important;
    }}
    [data-testid="stDownloadButton"] button p,
    [data-testid="stDownloadButton"] button div {{
        color: #ffffff !important;
    }}
    [data-testid="stDownloadButton"] button:hover,
    [data-testid="stDownloadButton"] button:active,
    [data-testid="stDownloadButton"] button:focus {{
        background-color: #4c1d95 !important;
        border-color: #4c1d95 !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }}

    /* ===== KPI / SECTION CARDS — wrap Streamlit columns in card-style frames ===== */
    /* Apply card styling to columns rows that look like KPI tiles */
    [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {{
        /* leave default — too aggressive otherwise */
    }}

    /* Style metric containers as cards */
    [data-testid="stMetric"] {{
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    [data-testid="stMetricLabel"] {{
        white-space: normal !important;
        overflow: visible !important;
        line-height: 1.3 !important;
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 11px !important;
        color: #6b7280 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-weight: 600 !important;
        white-space: normal !important;
        overflow-wrap: break-word !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {NAVY} !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        line-height: 1.15 !important;
    }}

    /* KPI labels & values when used outside st.metric */
    .kpi-label {{
        font-size: 11px; color: #6b7280; text-transform: uppercase;
        letter-spacing: 0.5px; font-weight: 600; margin-bottom: 4px;
    }}
    .kpi-value {{ font-size: 24px; font-weight: 700; color: {NAVY}; margin: 4px 0; line-height: 1.15; }}
    .delta-up {{ color: {GREEN}; font-size: 12px; font-weight: 500; }}
    .delta-down {{ color: {RED}; font-size: 12px; font-weight: 500; }}

    /* ===== SECTION HEADING ===== */
    .section-heading {{
        font-size: 15px;
        color: {NAVY};
        font-weight: 700;
        border-left: 4px solid {GOLD};
        padding-left: 12px;
        margin: 22px 0 14px 0;
        letter-spacing: 0.4px;
        text-transform: uppercase;
    }}

    /* ===== FORM WIDGET LABELS (text_input, selectbox, date_input, etc.) ===== */
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] *,
    label[data-testid="stWidgetLabel"],
    [data-baseweb="form-control-label"],
    .stTextInput > label,
    .stSelectbox > label,
    .stDateInput > label,
    .stTextArea > label,
    .stNumberInput > label,
    .stMultiSelect > label,
    .stRadio > label,
    .stCheckbox > label,
    .stFileUploader > label,
    .stColorPicker > label,
    .stSlider > label,
    .stTimeInput > label,
    .stToggle > label {{
        font-size: 12.5px !important;
        line-height: 1.5 !important;
        margin-bottom: 8px !important;
        padding-bottom: 0 !important;
        font-weight: 600 !important;
        color: #374151 !important;
        white-space: normal !important;
        overflow-wrap: break-word !important;
        word-wrap: break-word !important;
        display: block !important;
    }}

    /* Force the actual form widget container to claim its full vertical
       space so the label can't sit on top of the input below. */
    [data-testid="stTextInput"],
    [data-testid="stNumberInput"],
    [data-testid="stTextArea"],
    [data-testid="stSelectbox"],
    [data-testid="stDateInput"],
    [data-testid="stTimeInput"],
    [data-testid="stMultiSelect"],
    [data-testid="stFileUploader"],
    [data-testid="stRadio"],
    [data-testid="stCheckbox"],
    [data-testid="stSlider"] {{
        margin-bottom: 12px !important;
    }}

    /* Stacked form widgets get an extra gap so labels never bleed up */
    [data-testid="stForm"] [data-testid="stElementContainer"],
    [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {{
        margin-bottom: 6px !important;
    }}

    /* ===== HORIZONTAL RADIO (submit / edit toggle) ===== */
    [data-testid="stRadio"] [role="radiogroup"] {{
        gap: 18px !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        padding: 4px 0 !important;
    }}
    [data-testid="stRadio"] [role="radiogroup"] label,
    [data-testid="stRadio"] [role="radiogroup"] label p,
    [data-testid="stRadio"] [role="radiogroup"] label span {{
        padding: 6px 4px !important;
        line-height: 1.5 !important;
        font-size: 13px !important;
        white-space: normal !important;
    }}

    /* Selectbox + date_input + text_input inner text comfort */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] div[role="combobox"],
    [data-testid="stSelectbox"] div[data-baseweb="select"],
    [data-testid="stDateInput"] input,
    [data-testid="stMultiSelect"] div[role="combobox"] {{
        font-size: 13.5px !important;
        line-height: 1.5 !important;
        min-height: 38px !important;
    }}

    /* Textarea needs taller height */
    [data-testid="stTextArea"] textarea {{
        min-height: 80px !important;
    }}

    /* Captions (st.caption) — used to describe sections */
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    .stCaption, [data-testid="stCaption"] {{
        font-size: 12.5px !important;
        line-height: 1.5 !important;
        color: #6b7280 !important;
        margin-bottom: 10px !important;
    }}

    /* Buttons — make sure submit buttons don't overlap inputs above them */
    [data-testid="stFormSubmitButton"],
    [data-testid="stButton"] {{
        margin-top: 6px !important;
        margin-bottom: 4px !important;
    }}
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stButton"] button {{
        line-height: 1.4 !important;
        white-space: normal !important;
    }}

    /* Expander headers — they were cramped too */
    [data-testid="stExpander"] summary,
    .streamlit-expanderHeader {{
        font-size: 14px !important;
        line-height: 1.5 !important;
        padding: 10px 12px !important;
    }}

    /* ===== DATAFRAMES — clean white card look ===== */
    [data-testid="stDataFrame"] {{
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}

    /* ===== PLOTLY CHARTS — card-wrap ===== */
    [data-testid="stPlotlyChart"] {{
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 8px 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}

    /* Tighten bold markdown subheading look */
    .stMarkdown p strong:first-child {{
        color: {NAVY};
    }}

    /* ===== INFO/SUCCESS/WARNING/ERROR boxes ===== */
    [data-testid="stAlert"] {{
        border-radius: 8px;
        border-left-width: 4px;
    }}

    /* ===== BUTTONS ===== */
    [data-testid="stBaseButton-primary"] {{
        background: {PURPLE} !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }}
    [data-testid="stBaseButton-primary"]:hover {{
        background: #4c1d95 !important;
    }}

    /* ===== EXPANDER ===== */
    [data-testid="stExpander"] {{
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}

    /* ===== TOP NAV DROPDOWN — make it look prominent ===== */
    [data-testid="stSelectbox"] [data-baseweb="select"] {{
        background: white;
        border: 2px solid {PURPLE};
        border-radius: 6px;
        font-weight: 600;
    }}

    /* ===== HIDE STREAMLIT BRANDING ===== */
    [data-testid="stHeader"] {{ display: none; }}
    #MainMenu, footer, .stDeployButton {{ display: none !important; }}

    /* ===== DIVIDER ===== */
    hr {{ border-color: #e5e7eb !important; margin: 16px 0 !important; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SUPABASE CONNECTION
# ============================================================
@st.cache_resource
def get_supabase() -> Optional[Client]:
    """Initialise Supabase client from secrets. Returns None if not configured."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except (KeyError, FileNotFoundError):
        return None


sb = get_supabase()


# ============================================================
# AUTHENTICATION (Phase 1: allowlist + role gating + cookie session)
# ============================================================
def get_cookie_manager():
    """Returns the cookie manager. Uses session_state so the same instance is
    reused across reruns (can't use @st.cache_resource because the widget
    needs to interact with session state)."""
    if "_cookie_manager" not in st.session_state:
        st.session_state["_cookie_manager"] = stx.CookieManager(key="mcu_iro_cookies")
    return st.session_state["_cookie_manager"]


SESSION_COOKIE_NAME = "mcu_iro_session"
SESSION_DAYS = 7    # keep user logged in for 7 days


def load_session_from_cookie() -> Optional[Dict]:
    """Read the persisted session cookie. Returns user dict or None."""
    try:
        cm = get_cookie_manager()
        raw = cm.get(SESSION_COOKIE_NAME)
        if raw:
            data = raw if isinstance(raw, dict) else json.loads(raw)
            # Re-verify against allowlist (in case role was changed / user disabled)
            allowed = get_allowed_user(data.get("email", ""))
            if allowed:
                return {
                    "email": allowed["email"],
                    "name": allowed["full_name"],
                    "role": allowed["role"],
                }
    except Exception:
        pass
    return None


def save_session_to_cookie(user: Dict):
    """Persist the user session to a cookie that lives 7 days."""
    try:
        cm = get_cookie_manager()
        cm.set(
            SESSION_COOKIE_NAME,
            json.dumps(user),
            expires_at=datetime.now() + timedelta(days=SESSION_DAYS),
        )
    except Exception:
        pass


def clear_session_cookie():
    try:
        cm = get_cookie_manager()
        cm.delete(SESSION_COOKIE_NAME)
    except Exception:
        pass


def get_allowed_user(email: str) -> Optional[Dict]:
    """Look up the email in the allowlist. Returns user record if found and active."""
    if sb is None or not email:
        return None
    try:
        res = sb.table("allowed_users").select("*")\
                .eq("email", email.lower().strip())\
                .eq("active", True).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


# ============================================================
# SHARED BRAND BANNER (used on the login screen AND the dashboard
# so both show the identical header)
# ============================================================
import base64 as _b64
from pathlib import Path as _Path


def _load_mcu_logo_data_uri() -> str:
    """Embed the local MCU logo as a base64 data URI so the HTML <img>
    tag works without a public URL or static-serving route."""
    try:
        logo_path = _Path(__file__).parent / "assets" / "mcu_logo.png"
        if logo_path.exists():
            encoded = _b64.b64encode(logo_path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    except Exception:
        pass
    # Fallback to the public web logo if the local file isn't available
    return "https://mcu.edu.ph/wp-content/uploads/2024/01/MCU-logo@2x.png"


MCU_LOGO_URL = _load_mcu_logo_data_uri()

HEADER_TITLE_STACK = (
    '"Addington CF", "Addington", "AddingtonCF",'
    '"Montserrat", -apple-system, BlinkMacSystemFont, "Segoe UI",'
    'Roboto, sans-serif'
)


DEFAULT_BANNER_SUBTITLE = (
    "MCU · IROMS &mdash; Centralising research administration, "
    "analytics and scholarly activity"
)


def render_mcu_banner(subtitle: str = DEFAULT_BANNER_SUBTITLE, logout: bool = False):
    """Render the shared MCU IROMS brand banner (logo + title + subtitle).

    When ``logout`` is True, a log-out icon (door + right-pointing arrow) is
    placed in the banner's bottom-right corner; clicking it loads ``?logout=1``,
    which the main flow handles by ending the session.
    """
    logout_html = ""
    if logout:
        logout_html = (
            '<a class="banner-logout" href="?logout=1" target="_self" '
            'title="Log out">'
            '<span>Log out</span>'
            '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
            '<polyline points="16 17 21 12 16 7"/>'
            '<line x1="21" y1="12" x2="9" y2="12"/>'
            '</svg></a>'
        )
    # Load Montserrat (used only inside the header title — scoped via inline
    # font-family so no other text on the page is affected).
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    header_html = (
        '<div class="mcu-header">'
        # align-items:center lets the logo and text block share a vertical center.
        '<div style="display:flex;align-items:center;gap:22px;">'
        f'<img src="{MCU_LOGO_URL}" alt="MCU Logo" '
        'style="height:68px;width:auto;flex-shrink:0;display:block;'
        'filter:drop-shadow(0 2px 4px rgba(0,0,0,0.25));">'
        # Text block: no extra padding — flex handles vertical alignment.
        '<div style="display:flex;flex-direction:column;'
        'justify-content:center;line-height:1.25;">'
        # "Manila Central University" eyebrow — sits snug against the title
        '<div style="font-size:14px;letter-spacing:2.5px;text-transform:uppercase;'
        'opacity:0.9;font-weight:700;margin:0;line-height:1;">'
        'Manila Central University</div>'
        # Main title — Addington (with Montserrat Regular fallback, scoped here)
        '<h1 style="margin:2px 0 0 0;font-size:28px;font-weight:400;'
        'letter-spacing:-0.005em;line-height:1.18;'
        f'font-family:{HEADER_TITLE_STACK};">'
        'Institutional Research Office Management System</h1>'
        # Subtitle — tight against title (tagline by default; the dashboard
        # passes the logged-in user's details here instead).
        '<div class="subtitle" style="margin:4px 0 0 0;font-size:15px;'
        'opacity:0.9;line-height:1.35;">'
        f'{subtitle}'
        '</div>'
        '</div>'
        '</div>'
        f'{logout_html}'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def show_password_reset_screen(access_token: str, refresh_token: str):
    """Set-new-password screen reached via a Supabase recovery email link."""
    render_mcu_banner()

    st.caption(
        "You arrived here from a password-reset email. Pick a new password "
        "below and you'll be able to log in with it immediately."
    )

    with st.form("set_new_password_form"):
        new_pwd = st.text_input("New Password (min 8 characters) *",
                                type="password", key="rp_newpwd")
        new_pwd_confirm = st.text_input("Confirm New Password *",
                                        type="password", key="rp_confirm")
        submitted = st.form_submit_button("Set New Password", type="primary")

        if submitted:
            if not new_pwd or new_pwd != new_pwd_confirm:
                st.error("❌ Passwords don't match.")
            elif len(new_pwd) < 8:
                st.error("❌ Password must be at least 8 characters.")
            else:
                try:
                    sb.auth.set_session(access_token, refresh_token)
                    sb.auth.update_user({"password": new_pwd})
                    try:
                        sb.auth.sign_out()
                    except Exception:
                        pass
                    st.success(
                        "✅ Password updated. Use the **Return to Login** "
                        "button below to sign in with your new password.")
                except Exception as e:
                    msg = str(e)
                    if "expired" in msg.lower() or "invalid" in msg.lower():
                        st.error(
                            "❌ This reset link has expired or has already "
                            "been used. Go back to the login page and request "
                            "a fresh **Forgot Password** link.")
                    else:
                        st.error(f"❌ Failed to set new password: {msg}")

    if st.button("← Return to Login"):
        st.session_state.pop("recovery_tokens", None)
        st.query_params.clear()
        st.rerun()


def show_login_screen():
    """Renders the login / signup UI and stops the app until the user authenticates."""
    # ---- Recovery-link handling ----
    # Supabase password-reset emails are configured (Dashboard → Authentication
    # → Email Templates → Reset Password) to link back here as:
    #     {{ .SiteURL }}?token_hash={{ .TokenHash }}&type=recovery
    # The token_hash arrives as an ordinary query param Streamlit can read
    # server-side, so we verify it directly. (The previous approach relied on
    # the token in the URL *fragment* and a JS snippet to promote it to a query
    # param, but that snippet runs in Streamlit's sandboxed iframe, which is not
    # allowed to navigate the top window — so the reset form never appeared.)
    qp = st.query_params

    # If we already verified the link earlier in this session, keep showing the
    # set-new-password form. Reruns (e.g. the form submit) must not try to
    # verify the now-consumed single-use token again.
    if st.session_state.get("recovery_tokens"):
        at, rt = st.session_state["recovery_tokens"]
        show_password_reset_screen(at, rt)
        st.stop()

    if qp.get("type") == "recovery" and qp.get("token_hash") and sb is not None:
        try:
            res = sb.auth.verify_otp(
                {"token_hash": qp.get("token_hash"), "type": "recovery"}
            )
            session = getattr(res, "session", None)
            if session is None:
                raise RuntimeError("verify_otp returned no session")
            # Cache the freshly minted session so later reruns don't re-verify
            # the already-used token.
            st.session_state["recovery_tokens"] = (
                session.access_token, session.refresh_token
            )
            # Strip the token from the URL so it can't be reused or seen.
            st.query_params.clear()
            show_password_reset_screen(
                session.access_token, session.refresh_token
            )
            st.stop()
        except Exception:
            st.error(
                "❌ This password-reset link is invalid or has expired. "
                "Request a fresh one from the **Forgot your password?** link below."
            )

    render_mcu_banner()
    st.caption("🔒 Login required — access is limited to allowlisted MCU IRO users.")

    if sb is None:
        st.error("Database not configured. Cannot log in.")
        st.stop()

    tab_login, tab_signup = st.tabs(
        ["🔑 Log In", "🆕 First-Time Sign Up"]
    )

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("MCU Email *", placeholder="name@mcu.edu.ph")
            password = st.text_input("Password *", type="password")
            submit = st.form_submit_button("Log In", type="primary")

            if submit:
                allowed = get_allowed_user(email)
                if not allowed:
                    st.error("❌ Your email is not on the IRO allowlist. "
                             "Contact the IRO Director to be added.")
                    st.stop()
                try:
                    sb.auth.sign_in_with_password(
                        {"email": email.lower().strip(), "password": password}
                    )
                    # Record the successful login (best-effort) while the
                    # session is still authenticated, then sign out.
                    try:
                        sb.table("access_log").insert({
                            "email": allowed["email"],
                            "full_name": allowed["full_name"],
                            "role": allowed["role"],
                        }).execute()
                    except Exception:
                        pass
                    # Immediately sign out the auth session — we manage identity
                    # via our own cookie. Keeping the client signed in means it
                    # uses a short-lived JWT for queries (expires after 1 hour).
                    try:
                        sb.auth.sign_out()
                    except Exception:
                        pass
                    user_dict = {
                        "email": allowed["email"],
                        "name": allowed["full_name"],
                        "role": allowed["role"],
                    }
                    st.session_state.user = user_dict
                    save_session_to_cookie(user_dict)
                    st.rerun()
                except Exception as e:
                    msg = str(e)
                    if "Invalid login" in msg or "invalid_credentials" in msg.lower():
                        st.error("❌ Incorrect password.")
                    else:
                        st.error(f"❌ Login failed: {msg}")

        # ------ Forgot password — link shown ONLY on the Log In tab ------
        # The link loads ?reset=1, which reveals the reset form in place.
        if st.query_params.get("reset") != "1":
            st.markdown(
                '<div class="forgot-row">'
                '<a class="forgot-link" href="?reset=1" target="_self">'
                'Forgot your password?</a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="forgot-row"><strong>🔓 Reset your password</strong></div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Enter your MCU email below. We'll send a secure reset link from "
                "Supabase to your inbox — click it to set a new password, then "
                "return here to log in."
            )
            with st.form("reset_form"):
                reset_email = st.text_input(
                    "MCU Email *", placeholder="name@mcu.edu.ph", key="rp_email")
                submit_reset = st.form_submit_button("Send Reset Link",
                                                     type="primary")

                if submit_reset:
                    if not reset_email or "@" not in reset_email:
                        st.error("❌ Enter a valid email address.")
                    else:
                        allowed = get_allowed_user(reset_email)
                        if not allowed:
                            st.error(
                                "❌ This email isn't on the IRO allowlist. "
                                "Contact the IRO Director to be added first.")
                        else:
                            try:
                                sb.auth.reset_password_email(
                                    reset_email.lower().strip())
                                st.success(
                                    f"✅ A password-reset link has been sent to "
                                    f"**{reset_email}**. Check your inbox (and "
                                    f"the spam folder). The link is valid for "
                                    f"about an hour.")
                            except Exception as e:
                                st.error(
                                    f"❌ Could not send reset email: {e}")
            st.markdown(
                '<div class="forgot-row">'
                '<a class="forgot-link" href="?" target="_self">'
                '← Back to login</a></div>',
                unsafe_allow_html=True,
            )

    with tab_signup:
        st.caption(
            "Sign-up is only available to emails the IRO Director has pre-approved. "
            "If your email isn't on the list, ask to be added first."
        )
        with st.form("signup_form"):
            email = st.text_input("MCU Email *", placeholder="name@mcu.edu.ph",
                                  key="su_email")
            password = st.text_input("Set a Password (min 8 characters) *",
                                     type="password", key="su_pwd")
            password2 = st.text_input("Confirm Password *", type="password", key="su_pwd2")
            submit = st.form_submit_button("Create Account", type="primary")

            if submit:
                if password != password2:
                    st.error("❌ Passwords do not match.")
                    st.stop()
                if len(password) < 8:
                    st.error("❌ Password must be at least 8 characters.")
                    st.stop()
                allowed = get_allowed_user(email)
                if not allowed:
                    st.error("❌ Your email is not on the IRO allowlist. "
                             "Contact the IRO Director to be added.")
                    st.stop()
                try:
                    sb.auth.sign_up(
                        {"email": email.lower().strip(), "password": password}
                    )
                    st.success(
                        f"✅ Account created for **{allowed['full_name']}**. "
                        "Switch to the **Log In** tab to sign in."
                    )
                except Exception as e:
                    st.error(f"❌ Sign-up failed: {e}")

    st.divider()
    st.caption(
        "Need access? Contact the MCU IRO Director to be added to the user allowlist."
    )
    st.stop()


def current_user() -> Optional[Dict]:
    """Returns the currently authenticated user dict, or None."""
    # First check session state
    user = st.session_state.get("user")
    if user:
        return user
    # Fallback: try to restore from cookie
    cookie_user = load_session_from_cookie()
    if cookie_user:
        st.session_state.user = cookie_user
        return cookie_user
    return None


def require_auth():
    """Show login screen and stop app if user is not authenticated."""
    if not current_user():
        show_login_screen()


# Access roles, ordered from most to least privileged:
#   admin    — every page
#   standard — every page except User Management
#   crc      — Dashboard, Data, E-Library and Submit pages only
ROLES = ["admin", "standard", "crc"]

# Human-friendly labels for the access roles. The stored value stays
# "standard" (so existing accounts keep working); it just displays as
# "IRO Member" everywhere users see it.
ROLE_LABELS = {"admin": "Admin", "standard": "IRO Member", "crc": "CRC"}


def role_label(role) -> str:
    """Display label for a stored role value."""
    return ROLE_LABELS.get((role or "").strip().lower(), (role or "?"))


def require_admin(page_label: str):
    """Show error and stop if current user is not an admin."""
    u = current_user()
    if not u or u.get("role") != "admin":
        st.error(f"🔒 The **{page_label}** page requires Admin role. "
                 "Contact the IRO Director if you need elevated access.")
        st.stop()


def require_roles(page_label: str, allowed_roles):
    """Show error and stop if the current user's role isn't in allowed_roles."""
    u = current_user()
    if not u or u.get("role") not in allowed_roles:
        st.error(f"🔒 The **{page_label}** page isn't available for your role. "
                 "Contact the IRO Director if you need elevated access.")
        st.stop()


# Gate the entire app
require_auth()
_USER = current_user()
_IS_ADMIN = _USER.get("role") == "admin"


def _refresh_sb_on_jwt_expired(exc) -> bool:
    """If the error is a JWT-expired error, sign out the cached client so it
    falls back to using the anon key. Returns True if we recovered."""
    msg = str(exc).lower()
    if "jwt expired" in msg or "pgrst303" in msg:
        try:
            sb.auth.sign_out()
        except Exception:
            pass
        return True
    return False


def _is_transient_conn_error(exc) -> bool:
    """True for transient socket/connection errors that a retry can fix —
    e.g. EAGAIN 'Resource temporarily unavailable', resets, disconnects,
    timeouts. These happen when the cached client's connection goes stale."""
    msg = str(exc).lower()
    return any(s in msg for s in (
        "temporarily unavailable", "errno 35", "errno 11",
        "connection reset", "connection aborted", "broken pipe",
        "server disconnected", "remoteprotocol", "connecterror",
        "read timeout", "timed out", "connection error",
    ))


def _reset_supabase_client():
    """Rebuild the cached Supabase client to recover a stale connection."""
    global sb
    try:
        get_supabase.clear()
    except Exception:
        pass
    sb = get_supabase()


def _recover(exc) -> bool:
    """Try to recover from a recoverable DB error before retrying once:
    an expired JWT, or a transient connection drop (rebuild the client).
    Returns True if a retry is worth attempting."""
    if _refresh_sb_on_jwt_expired(exc):
        return True
    if _is_transient_conn_error(exc):
        _reset_supabase_client()
        return True
    return False


def db_select(table: str, order_col: str = "submitted_at", desc: bool = True) -> List[Dict]:
    """SELECT * FROM table ORDER BY col DESC."""
    if sb is None:
        return []
    try:
        res = sb.table(table).select("*").order(order_col, desc=desc).execute()
        return res.data or []
    except Exception as e:
        if _recover(e):
            # Retry once after recovering (fresh session / reconnect)
            try:
                res = sb.table(table).select("*").order(order_col, desc=desc).execute()
                return res.data or []
            except Exception as e2:
                st.error(f"Database read error on `{table}`: {e2}")
                return []
        st.error(f"Database read error on `{table}`: {e}")
        return []


def db_insert(table: str, row: dict) -> bool:
    """INSERT one row into table."""
    if sb is None:
        st.error("Database not configured. Add SUPABASE_URL and SUPABASE_KEY in app secrets.")
        return False
    try:
        sb.table(table).insert(row).execute()
        return True
    except Exception as e:
        if _recover(e):
            try:
                sb.table(table).insert(row).execute()
                return True
            except Exception as e2:
                st.error(f"Database insert error on `{table}`: {e2}")
                return False
        st.error(f"Database insert error on `{table}`: {e}")
        return False


def db_update(table: str, row_id, updates: dict) -> bool:
    """UPDATE one row by id."""
    if sb is None:
        st.error("Database not configured.")
        return False
    try:
        sb.table(table).update(updates).eq("id", row_id).execute()
        return True
    except Exception as e:
        if _recover(e):
            try:
                sb.table(table).update(updates).eq("id", row_id).execute()
                return True
            except Exception as e2:
                st.error(f"Database update error on `{table}`: {e2}")
                return False
        st.error(f"Database update error on `{table}`: {e}")
        return False


def diff_dict(old: dict, new: dict, fields: list) -> dict:
    """Return {field: {'old': ..., 'new': ...}} for fields that changed."""
    diff = {}
    for f in fields:
        old_v = old.get(f)
        new_v = new.get(f)
        if old_v != new_v:
            diff[f] = {"old": old_v, "new": new_v}
    return diff


def db_count(table: str) -> int:
    """SELECT COUNT(*) FROM table."""
    if sb is None:
        return 0
    try:
        res = sb.table(table).select("id", count="exact").execute()
        return res.count or 0
    except Exception as e:
        if _recover(e):
            try:
                res = sb.table(table).select("id", count="exact").execute()
                return res.count or 0
            except Exception:
                return 0
        return 0


# ============================================================
# HEADER + TOP-RIGHT USER IDENTITY
# ============================================================
# Log-out via the banner icon (bottom-right) — it loads ?logout=1.
if st.query_params.get("logout") == "1":
    try:
        if sb is not None:
            sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    clear_session_cookie()
    st.query_params.clear()
    st.rerun()

render_mcu_banner(logout=True)

# ============================================================
# TOP-OF-PAGE NAVIGATION (always visible — no sidebar needed)
# ============================================================
ALL_PAGES_BY_ROLE = {
    # ----- Dashboard group — admin, standard, CRC -----
    "📊 Overview": ["admin", "standard", "crc"],
    "📋 CRC Reports": ["admin", "standard", "crc"],
    "🌐 Research Ecosystem": ["admin", "standard", "crc"],
    "📅 Calendar of Events": ["admin", "standard", "crc"],
    # ----- Data group — admin, standard, CRC -----
    "📚 Scopus Publications (view)": ["admin", "standard", "crc"],
    "💰 In-House Grants (view)": ["admin", "standard", "crc"],
    "🎓 Capacity-Building Workshops": ["admin", "standard", "crc"],
    "🎤 Scholarly Engagements": ["admin", "standard", "crc"],
    # ----- E-Library group — admin, standard, CRC -----
    "📰 In-House Journal Publications": ["admin", "standard", "crc"],
    "📜 IRO Policies": ["admin", "standard", "crc"],
    # ----- Submit group — admin, standard, CRC -----
    "📋 Submit CRC Monthly Report": ["admin", "standard", "crc"],
    "🧾 In-house grants": ["admin", "standard", "crc"],
    "➕ External Grant Submission": ["admin", "standard", "crc"],
    "➕ Submit Scholarly Engagement": ["admin", "standard", "crc"],
    # ----- Admin group — admin + standard (NOT CRC) -----
    "📁 IRO Presentations & Reports": ["admin", "standard"],
    "📚 Manage Scopus Publications": ["admin", "standard"],
    "💰 Budget Utilisation": ["admin", "standard"],
    "📝 IRO Meetings": ["admin", "standard"],
    "🎓 Manage Workshops": ["admin", "standard"],
    # User Management stays admin-only
    "👥 User Management": ["admin"],
}

# Group pages into categories for the 2-level menu
PAGE_GROUPS = {
    "Dashboard": ["📊 Overview", "🌐 Research Ecosystem", "📋 CRC Reports", "📅 Calendar of Events"],
    "Data": [
        "📚 Scopus Publications (view)",
        "💰 In-House Grants (view)",
        "🎓 Capacity-Building Workshops",
        "🎤 Scholarly Engagements",
    ],
    "E-Library": [
        "📰 In-House Journal Publications",
        "📜 IRO Policies",
    ],
    "Submit": [
        "📋 Submit CRC Monthly Report",
        "🧾 In-house grants",
        "➕ External Grant Submission",
        "➕ Submit Scholarly Engagement",
    ],
    "Admin": [
        "📚 Manage Scopus Publications",
        "🎓 Manage Workshops",
        "💰 Budget Utilisation",
        "📝 IRO Meetings",
        "📁 IRO Presentations & Reports",
        "👥 User Management",
    ],
}
GROUP_ICONS = {
    "Dashboard": "speedometer2",
    "Data":      "bar-chart-fill",
    "E-Library": "journal-bookmark-fill",
    "Submit":    "plus-square-fill",
    "Admin":     "shield-lock-fill",
}

# Filter pages by current user's role
ALL_PAGES = [p for p, roles in ALL_PAGES_BY_ROLE.items()
             if _USER.get("role") in roles]
# Filter groups + their pages by role
PAGE_GROUPS_FOR_USER = {}
for group, pages in PAGE_GROUPS.items():
    allowed = [p for p in pages if p in ALL_PAGES]
    if allowed:
        PAGE_GROUPS_FOR_USER[group] = allowed

# ====== 2-level navigation menu (grouped pills) ======
group_labels = list(PAGE_GROUPS_FOR_USER.keys())
group_icons = [GROUP_ICONS.get(g, "circle") for g in group_labels]

selected_group = option_menu(
    menu_title=None,
    options=group_labels,
    icons=group_icons,
    orientation="horizontal",
    default_index=0,
    key="group_nav",
    styles={
        "container": {
            "padding": "6px",
            "background-color": "white",
            "border": "1px solid #e5e7eb",
            "border-radius": "10px",
            "margin-bottom": "10px",
            "box-shadow": "0 1px 3px rgba(15,23,42,0.05)",
        },
        "icon": {"color": "#9ca3af", "font-size": "18px"},
        "nav-link": {
            "font-size": "14px",
            "font-weight": "600",
            "color": "#6b7280",
            "text-align": "center",
            "margin": "0 4px",
            "padding": "10px 18px",
            "border-radius": "8px",
            "background-color": "transparent",
            "border": "2px solid transparent",
            "--hover-color": "#f4f6fa",
            "letter-spacing": "0.2px",
            "white-space": "nowrap",
            "transition": "all 0.15s ease",
        },
        "nav-link-selected": {
            "background-color": NAVY,
            "color": "white",
            "font-weight": "700",
            "border": f"2px solid {GOLD}",
            "box-shadow": f"0 2px 6px rgba(11,37,69,0.25)",
        },
    },
)

# Sub-menu for the selected group
pages_in_group = PAGE_GROUPS_FOR_USER.get(selected_group, [])
if len(pages_in_group) > 1:
    selected_page = option_menu(
        menu_title=None,
        options=pages_in_group,
        orientation="horizontal",
        default_index=0,
        key=f"sub_{selected_group}",
        styles={
            "container": {
                "padding": "5px",
                "background-color": "#f4f6fa",
                "border": "1px solid #e5e7eb",
                "border-radius": "8px",
                "margin-bottom": "16px",
                "box-shadow": "inset 0 1px 2px rgba(15,23,42,0.04)",
            },
            "icon": {"font-size": "0px"},   # hide icons in sub-menu
            "nav-link": {
                "font-size": "13px",
                "font-weight": "600",
                "color": "#6b7280",
                "text-align": "center",
                "margin": "0 3px",
                "padding": "8px 14px",
                "border-radius": "6px",
                "background-color": "transparent",
                "border-bottom": "2px solid transparent",
                "--hover-color": "white",
                "letter-spacing": "0.15px",
                "white-space": "nowrap",
                "transition": "all 0.15s ease",
            },
            "nav-link-selected": {
                "background-color": "white",
                "color": NAVY,
                "font-weight": "700",
                "border-bottom": f"2px solid {GOLD}",
                "box-shadow": "0 1px 3px rgba(15,23,42,0.08)",
            },
        },
    )
else:
    selected_page = pages_in_group[0] if pages_in_group else "📊 Overview"

page = selected_page.split(" ", 1)[1]   # strip the emoji prefix

# Connection status (compact, only if disconnected)
if sb is None:
    st.error("⚠️ Database not connected.")

# ============================================================
# (Left sidebar removed — user identity / logout now live in the
#  top-right of the page; see the HEADER section above.)
# ============================================================


# ============================================================
# HELPER — donut chart
# ============================================================
def donut(values, labels, colors, total_label, total_value):
    fig = go.Figure(data=[go.Pie(
        values=values, labels=labels, hole=0.65,
        marker=dict(colors=colors),
        textinfo='none', sort=False, direction='clockwise',
    )])
    fig.update_layout(
        annotations=[dict(
            text=f"<b>{total_value}</b><br><span style='font-size:9px;color:#6b7280'>{total_label}</span>",
            x=0.5, y=0.5, font_size=18, showarrow=False, font_color=NAVY)],
        height=180, margin=dict(t=4, b=4, l=4, r=4),
        showlegend=False, paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


# ============================================================
# PAGE: OVERVIEW
# ============================================================
if page == "Overview":
    # ===== HERO HEADER =====
    today = date.today()
    if today.month >= 6:
        ay_label = f"AY {today.year}–{today.year + 1}"
    else:
        ay_label = f"AY {today.year - 1}–{today.year}"
    refreshed_at = datetime.now().strftime("%d %b %Y, %H:%M")
    user_name = (_USER.get("name") or "") if _USER else ""
    HONORIFICS = {"dr", "dr.", "prof", "prof.", "professor", "mr", "mr.",
                  "ms", "ms.", "mrs", "mrs.", "engr", "engr."}
    first_name = ""
    for tok in user_name.replace(",", " ").split():
        if tok.lower().strip(".") not in HONORIFICS:
            first_name = tok
            break
    hero_greeting = (f"Welcome back, {first_name}" if first_name
                     else (f"Welcome back, {user_name}" if user_name
                           else "Welcome"))

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{NAVY} 0%,{PURPLE} 100%);'
        f'color:white;border-radius:10px;padding:18px 24px;margin-bottom:14px;'
        f'box-shadow:0 2px 6px rgba(11,37,69,0.15);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'flex-wrap:wrap;gap:8px;">'
        f'<div>'
        f'<div style="font-size:18px;font-weight:700;letter-spacing:0.2px;'
        f'line-height:1.2;">'
        f'Institutional Research Office Management System</div>'
        f'<div style="font-size:13px;opacity:0.9;margin-top:4px;">'
        f'{hero_greeting} · {ay_label} · Live data as of {refreshed_at}</div>'
        f'</div>'
        f'<div style="font-size:12px;font-weight:700;background:rgba(255,255,255,0.18);'
        f'padding:6px 14px;border-radius:14px;letter-spacing:0.6px;'
        f'text-transform:uppercase;">MCU · IROMS</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Pull live counts from database
    scopus_live = db_count("scopus_publications")
    grant_live = db_count("grant_projects")
    report_live = db_count("grant_reports")
    budget_live = db_count("budget_entries")

    # Workshops completed — all-time count
    workshops_fy26 = 0
    workshops_list = []
    if sb is not None:
        try:
            res = sb.table("capacity_workshops").select("id", count="exact")\
                    .eq("status", "Completed").execute()
            workshops_fy26 = res.count or 0
            workshops_list = db_select("capacity_workshops",
                                       order_col="start_date", desc=True)
        except Exception:
            workshops_fy26 = 0

    # Scholarly engagements — total events + presenter participations
    engagements_total = 0
    engagement_presenters = 0
    engagement_awards = 0
    if sb is not None:
        try:
            ev_res = sb.table("research_events_attended")\
                       .select("id", count="exact").execute()
            engagements_total = ev_res.count or 0
        except Exception:
            engagements_total = 0
        try:
            att_rows = sb.table("research_event_attendees")\
                         .select("role,award").execute().data or []
            PRES_ROLES = {"presenter", "keynote", "keynote speaker",
                          "panelist", "chair", "moderator"}
            engagement_presenters = sum(
                1 for a in att_rows
                if (a.get("role") or "").strip().lower() in PRES_ROLES
            )
            engagement_awards = sum(
                1 for a in att_rows if (a.get("award") or "").strip()
            )
        except Exception:
            pass

    # External grants for KPI tile
    ext_grants_kpi = []
    if sb is not None:
        try:
            ext_grants_kpi = sb.table("external_grants").select("*").execute().data or []
        except Exception:
            ext_grants_kpi = []
    ext_total_kpi = sum(float(g.get("amount") or 0) for g in ext_grants_kpi)
    ext_awarded_amt = sum(float(g.get("amount") or 0) for g in ext_grants_kpi
                          if (g.get("status") or "").strip().lower()
                          in ("awarded", "active", "completed"))
    ext_pipeline_amt = sum(float(g.get("amount") or 0) for g in ext_grants_kpi
                           if (g.get("status") or "").strip().lower()
                           == "in review")
    ext_status_counts = {}
    for g in ext_grants_kpi:
        s = (g.get("status") or "Other").strip() or "Other"
        ext_status_counts[s] = ext_status_counts.get(s, 0) + 1

    # Aggregate amount + count by PI for the donut & legend
    ext_by_pi_amt = {}
    ext_by_pi_cnt = {}
    for g in ext_grants_kpi:
        pi = (g.get("pi") or "Unassigned").strip() or "Unassigned"
        ext_by_pi_amt[pi] = ext_by_pi_amt.get(pi, 0) + float(g.get("amount") or 0)
        ext_by_pi_cnt[pi] = ext_by_pi_cnt.get(pi, 0) + 1

    # ----- Pull data first for KPI tiles -----
    scopus_data = db_select("scopus_publications") if sb else []
    total_pubs = len(scopus_data)
    years_sorted = sorted({p.get("year") for p in scopus_data if p.get("year")})
    last_yr = years_sorted[-1] if years_sorted else None
    latest_year_count = sum(1 for p in scopus_data if p.get("year") == last_yr)
    prev_year_count = sum(1 for p in scopus_data
                          if last_yr and p.get("year") == last_yr - 1)
    scopus_yoy = ((latest_year_count - prev_year_count) / prev_year_count * 100) if prev_year_count else 0

    q_counts = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "NA": 0}
    for p in scopus_data:
        q = p.get("quartile") or "NA"
        if q in q_counts:
            q_counts[q] += 1

    grants_db = db_select("grant_projects", order_col="budget") if sb else []
    grants_total = sum(float(g.get("budget") or 0) for g in grants_db)
    by_col_amt = {}
    by_col_cnt = {}
    for g in grants_db:
        c = g.get("college") or "Others"
        by_col_amt[c] = by_col_amt.get(c, 0) + float(g.get("budget") or 0)
        by_col_cnt[c] = by_col_cnt.get(c, 0) + 1

    # ----- KPI Row — HTML-style cards (label + big number + delta + mini bars) -----
    def make_kpi_html(label, value, delta_text=None, delta_color=GREEN,
                      bars_html=""):
        delta_html = ""
        if delta_text:
            delta_html = (f'<div style="font-size:12px;color:{delta_color};'
                          f'font-weight:500;margin-top:2px;">{delta_text}</div>')
        return (
            '<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
            'padding:16px 18px;height:100%;box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
            f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
            f'letter-spacing:0.5px;font-weight:600;">{label}</div>'
            f'<div style="font-size:28px;font-weight:700;color:{NAVY};margin-top:6px;'
            f'line-height:1.1;">{value}</div>'
            f'{delta_html}'
            f'{bars_html}'
            '</div>'
        )

    def mini_bars(items):
        """items = list of (label, count, color) — render as 4-5 mini stacked bars."""
        if not items:
            return ""
        max_v = max(c for _, c, _ in items) or 1
        bars = ""
        for lbl, cnt, color in items:
            pct = round(cnt / max_v * 100) if max_v else 0
            bars += (
                f'<div style="display:flex;align-items:center;margin:4px 0;font-size:12px;">'
                f'<div style="width:30px;color:#374151;font-weight:700;">{lbl}</div>'
                f'<div style="flex:1;background:#f3f4f6;height:8px;border-radius:3px;margin:0 8px;">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:3px;"></div>'
                f'</div>'
                f'<div style="width:34px;text-align:right;color:#6b7280;font-weight:600;">{cnt}</div>'
                f'</div>'
            )
        return f'<div style="margin-top:12px;">{bars}</div>'

    # ===== Modern accent palette =====
    C_EMERALD = "#10b981"   # workshop completed
    C_INDIGO  = "#6366f1"   # workshop planned
    C_TEAL    = "#0d9488"   # grant awarded
    C_AMBER   = "#f59e0b"   # accent gold
    C_ROSE    = "#f43f5e"   # citation impact accent
    C_SKY     = "#0ea5e9"   # neutral accent
    C_TRACK   = "#eef2f7"   # donut track (lighter, more elegant)

    # ===== Inline SVG donut (compact, embeds into KPI tile) =====
    def svg_donut(segments, center_top, center_bot="",
                  size=84, stroke=11, track=C_TRACK):
        """segments = list of (value, color) tuples."""
        import math
        total = sum(v for v, _ in segments) or 1
        radius = (size - stroke) / 2
        circ = 2 * math.pi * radius
        ring_parts = (
            f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" '
            f'fill="none" stroke="{track}" stroke-width="{stroke}"/>'
        )
        offset = 0.0
        for value, color in segments:
            if value <= 0:
                continue
            length = circ * (value / total)
            ring_parts += (
                f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" '
                f'fill="none" stroke="{color}" stroke-width="{stroke}" '
                f'stroke-linecap="round" '
                f'stroke-dasharray="{length:.2f} {circ - length:.2f}" '
                f'stroke-dashoffset="{-offset:.2f}" '
                f'transform="rotate(-90 {size/2} {size/2})"/>'
            )
            offset += length
        return (
            f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
            f'style="flex-shrink:0;">'
            f'{ring_parts}'
            f'<text x="{size/2}" y="{size/2 - 3}" text-anchor="middle" '
            f'dominant-baseline="central" '
            f'style="font-size:14px;font-weight:700;fill:{NAVY};">'
            f'{center_top}</text>'
            f'<text x="{size/2}" y="{size/2 + 14}" text-anchor="middle" '
            f'dominant-baseline="central" '
            f'style="font-size:9px;fill:#6b7280;letter-spacing:0.3px;">'
            f'{center_bot}</text>'
            f'</svg>'
        )

    # ===== Helper: compact KPI tile (header strip + value + sub + optional right slot) =====
    def kpi_tile(icon, label, value, sub=None, sub_color="#6b7280",
                 accent=C_INDIGO, bars_html="", right_html=""):
        sub_html = (
            f'<div style="font-size:13px;color:{sub_color};font-weight:500;'
            f'margin-top:4px;">{sub}</div>' if sub else ""
        )
        if right_html:
            body = (
                f'<div style="display:flex;align-items:center;'
                f'justify-content:space-between;gap:10px;margin-top:8px;">'
                f'<div style="min-width:0;">'
                f'<div style="font-size:24px;font-weight:700;color:{NAVY};'
                f'line-height:1.1;">{value}</div>{sub_html}</div>'
                f'{right_html}</div>'
            )
        else:
            body = (
                f'<div style="font-size:26px;font-weight:700;color:{NAVY};'
                f'margin-top:8px;line-height:1.1;">{value}</div>{sub_html}'
            )
        return (
            f'<div style="background:white;border:1px solid #e5e7eb;'
            f'border-radius:10px;padding:16px 18px;height:100%;'
            f'box-shadow:0 2px 4px rgba(15,23,42,0.04);'
            f'border-top:3px solid {accent};">'
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'font-size:12px;color:#6b7280;text-transform:uppercase;'
            f'letter-spacing:0.5px;font-weight:700;">'
            f'<span style="font-size:15px;">{icon}</span><span>{label}</span></div>'
            f'{body}{bars_html}'
            f'</div>'
        )

    # ===== Compute additional metrics for KPI strip =====
    cit_total = sum(int(p.get("citation_count") or 0) for p in scopus_data)
    cits_sorted = sorted(
        [int(p.get("citation_count") or 0) for p in scopus_data],
        reverse=True,
    )
    h_idx = 0
    for i, c in enumerate(cits_sorted, start=1):
        if c >= i:
            h_idx = i
        else:
            break

    # Workshop average feedback
    avg_feedback = 0.0
    if workshops_list:
        scores = [float(w.get("feedback_score") or 0)
                  for w in workshops_list
                  if w.get("feedback_score") not in (None, 0, "0", "")]
        avg_feedback = sum(scores) / len(scores) if scores else 0.0

    # ===== 5-tile KPI strip =====
    k1, k2, k3, k4, k5 = st.columns(5)
    yoy_arrow = "▲" if scopus_yoy >= 0 else "▼"
    yoy_color = GREEN if scopus_yoy >= 0 else RED
    q_bars = mini_bars([
        ("Q1", q_counts["Q1"], QUARTILE_COLORS["Q1"]),
        ("Q2", q_counts["Q2"], QUARTILE_COLORS["Q2"]),
        ("Q3", q_counts["Q3"], QUARTILE_COLORS["Q3"]),
        ("Q4", q_counts["Q4"], QUARTILE_COLORS["Q4"]),
    ]) if total_pubs else ""

    # Scopus impact extras (consolidated into the Scopus tile)
    oa_count_kpi = sum(1 for p in scopus_data if p.get("open_access"))
    oa_pct_kpi = round(oa_count_kpi / total_pubs * 100) if total_pubs else 0
    n_years = len(years_sorted)
    year_range_label = (f"{years_sorted[0]}–{years_sorted[-1]}"
                        if n_years > 1
                        else (str(years_sorted[0]) if n_years == 1 else "—"))
    yoy_line = (f"{yoy_arrow} {abs(scopus_yoy):.1f}% YoY ({last_yr})"
                if last_yr else "—")
    impact_line = (
        f'<div style="font-size:13px;color:#374151;margin-top:8px;'
        f'padding-top:8px;border-top:1px solid #f3f4f6;display:flex;'
        f'gap:12px;flex-wrap:wrap;">'
        f'<span><strong style="color:{NAVY};">{n_years}</strong>'
        f'<span style="color:#6b7280;"> yr ({year_range_label})</span></span>'
        f'<span><strong style="color:{NAVY};">h={h_idx}</strong></span>'
        f'<span><strong style="color:{NAVY};">{cit_total:,}</strong>'
        f'<span style="color:#6b7280;"> cites</span></span>'
        f'<span><strong style="color:{NAVY};">{oa_pct_kpi}%</strong>'
        f'<span style="color:#6b7280;"> OA</span></span>'
        f'</div>'
    )

    # Workshop progress totals (used by donut in tile k3)
    WS_TARGET = 18
    ws_done_kpi = sum(1 for w in (workshops_list or [])
                      if (w.get("status") or "").strip() == "Completed")
    ws_plan_kpi = sum(1 for w in (workshops_list or [])
                      if (w.get("status") or "").strip()
                      in ("Upcoming", "Planning"))
    ws_left_kpi = max(0, WS_TARGET - ws_done_kpi - ws_plan_kpi)

    # Grant budget totals (used by donut in tile k2)
    GRANT_BUDGET = 2_000_000
    grant_awarded_kpi = float(grants_total or 0)
    grant_left_kpi = max(0.0, GRANT_BUDGET - grant_awarded_kpi)
    grant_pct = (grant_awarded_kpi / GRANT_BUDGET * 100) if GRANT_BUDGET else 0

    with k1:
        st.markdown(kpi_tile(
            "📚", "Scopus Publications",
            f"{total_pubs}",
            sub=yoy_line,
            sub_color=yoy_color, accent=C_INDIGO,
            bars_html=q_bars + impact_line,
        ), unsafe_allow_html=True)

    with k2:
        n_grants = len(grants_db) if grants_db else 0
        val_text = (f"₱{grant_awarded_kpi/1_000_000:.2f}M"
                    if grant_awarded_kpi >= 1_000_000
                    else (f"₱{grant_awarded_kpi/1_000:.0f}K"
                          if grant_awarded_kpi >= 1_000
                          else f"₱{grant_awarded_kpi:,.0f}"))
        # Per-college segments (largest first) + remaining budget slice
        sorted_colleges_amt = sorted(by_col_amt.items(),
                                     key=lambda x: -x[1])
        college_segments = [
            (amt, CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)])
            for i, (_c, amt) in enumerate(sorted_colleges_amt)
            if amt > 0
        ]
        grant_svg = svg_donut(
            college_segments + [(grant_left_kpi, C_TRACK)],
            center_top=f"{grant_pct:.0f}%",
            center_bot="used",
        )
        # Full college legend — all colleges, wraps onto multiple lines
        legend_items = ""
        for i, (c, amt) in enumerate(sorted_colleges_amt):
            color = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            legend_items += (
                f'<span style="display:inline-flex;align-items:center;'
                f'gap:5px;margin:3px 10px 3px 0;font-size:12px;color:#374151;'
                f'white-space:nowrap;">'
                f'<span style="width:10px;height:10px;background:{color};'
                f'border-radius:50%;display:inline-block;flex-shrink:0;"></span>'
                f'{c}</span>'
            )
        legend_html = (
            f'<div style="margin-top:10px;padding-top:10px;'
            f'border-top:1px solid #f3f4f6;line-height:1.8;'
            f'display:flex;flex-wrap:wrap;">{legend_items}</div>'
            if legend_items else ""
        )
        st.markdown(kpi_tile(
            "💰", "In-House Grants",
            val_text,
            sub=(f"{n_grants} project{'s' if n_grants != 1 else ''} · "
                 f"of ₱2.00M") + legend_html,
            accent=C_TEAL, right_html=grant_svg,
        ), unsafe_allow_html=True)

    with k3:
        sub = (f"⭐ Avg. feedback {avg_feedback:.2f}/5"
               if avg_feedback else f"Target {WS_TARGET}")
        ws_svg = svg_donut(
            [(ws_done_kpi, C_EMERALD),
             (ws_plan_kpi, C_INDIGO),
             (ws_left_kpi, C_TRACK)],
            center_top=f"{ws_done_kpi}/{WS_TARGET}",
            center_bot="done",
        )
        ws_legend_items = [
            (C_EMERALD, "Completed", ws_done_kpi),
            (C_INDIGO, "Planned / Upcoming", ws_plan_kpi),
            (C_TRACK, "Remaining", ws_left_kpi),
        ]
        ws_legend = ""
        for color, label, val in ws_legend_items:
            border = (f"border:1px dashed #9ca3af;"
                      if color == C_TRACK else "")
            ws_legend += (
                f'<div style="display:flex;align-items:center;'
                f'justify-content:space-between;font-size:12px;'
                f'color:#374151;margin:3px 0;">'
                f'<div style="display:flex;align-items:center;gap:7px;">'
                f'<span style="width:10px;height:10px;background:{color};'
                f'border-radius:3px;display:inline-block;{border}'
                f'flex-shrink:0;"></span>{label}</div>'
                f'<strong style="color:{NAVY};font-size:13px;">{val}</strong>'
                f'</div>'
            )
        ws_legend_html = (
            f'<div style="margin-top:10px;padding-top:10px;'
            f'border-top:1px solid #f3f4f6;">{ws_legend}</div>'
        )
        st.markdown(kpi_tile(
            "🎓", "Workshops Completed",
            f"{ws_done_kpi}",
            sub=sub, accent=C_EMERALD,
            right_html=ws_svg, bars_html=ws_legend_html,
        ), unsafe_allow_html=True)

    with k4:
        sub_parts = []
        if engagement_presenters:
            sub_parts.append(f"{engagement_presenters} presenters")
        if engagement_awards:
            sub_parts.append(f"🏆 {engagement_awards}")
        st.markdown(kpi_tile(
            "🎤", "Scholarly Engagements",
            f"{engagements_total}",
            sub=" · ".join(sub_parts) if sub_parts else "—",
            accent=C_SKY,
        ), unsafe_allow_html=True)

    with k5:
        n_ext = len(ext_grants_kpi)
        ext_val_text = (
            f"₱{ext_total_kpi/1_000_000:.2f}M" if ext_total_kpi >= 1_000_000
            else (f"₱{ext_total_kpi/1_000:.0f}K" if ext_total_kpi >= 1_000
                  else f"₱{ext_total_kpi:,.0f}" if ext_total_kpi
                  else "—")
        )
        # Donut segments: one per PI (sorted by amount desc) + remaining track
        sorted_pis = sorted(ext_by_pi_amt.items(), key=lambda x: -x[1])
        pi_segments = [
            (amt, CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)])
            for i, (_pi, amt) in enumerate(sorted_pis) if amt > 0
        ]
        ext_svg = svg_donut(
            pi_segments if pi_segments else [(1, C_TRACK)],
            center_top=f"{n_ext}",
            center_bot="PIs" if not pi_segments
                       else ("PI" if len(sorted_pis) == 1 else "PIs"),
        )

        # Status pill row (sits in the sub-line, color-coded by status)
        STATUS_PILL = {
            "In Review": ("#fef3c7", "#92400e"),
            "Awarded":   ("#d1fae5", "#065f46"),
            "Active":    ("#ccfbf1", "#115e59"),
            "Completed": ("#dbeafe", "#1e40af"),
            "Cancelled": ("#f3f4f6", "#6b7280"),
        }
        status_pills_html = ""
        for s in ["In Review", "Awarded", "Active", "Completed", "Cancelled"]:
            cnt = ext_status_counts.get(s, 0)
            if cnt == 0:
                continue
            bg, fg = STATUS_PILL[s]
            status_pills_html += (
                f'<span style="display:inline-flex;align-items:center;gap:4px;'
                f'background:{bg};color:{fg};padding:2px 8px;border-radius:10px;'
                f'font-size:11px;font-weight:700;margin:2px 4px 2px 0;'
                f'white-space:nowrap;">{s} '
                f'<strong style="font-size:12px;">{cnt}</strong></span>'
            )
        if not status_pills_html:
            status_pills_html = (
                f'<span style="color:#9ca3af;font-size:12px;">No grants yet</span>'
            )
        status_sub = (
            f'<div style="margin-top:6px;display:flex;flex-wrap:wrap;'
            f'align-items:center;">{status_pills_html}</div>'
        )

        # PI legend below
        pi_legend = ""
        for i, (pi, amt) in enumerate(sorted_pis):
            color = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            cnt = ext_by_pi_cnt[pi]
            amt_label = (f"₱{amt/1_000_000:.2f}M" if amt >= 1_000_000
                         else (f"₱{amt/1_000:.0f}K" if amt >= 1_000
                               else f"₱{amt:,.0f}"))
            pi_legend += (
                f'<div style="display:flex;align-items:center;'
                f'justify-content:space-between;font-size:12px;'
                f'color:#374151;margin:3px 0;gap:8px;">'
                f'<div style="display:flex;align-items:center;gap:7px;'
                f'min-width:0;flex:1;">'
                f'<span style="width:10px;height:10px;background:{color};'
                f'border-radius:50%;display:inline-block;flex-shrink:0;"></span>'
                f'<span style="overflow:hidden;text-overflow:ellipsis;'
                f'white-space:nowrap;">{pi}</span></div>'
                f'<strong style="color:{NAVY};font-size:12px;flex-shrink:0;">'
                f'{amt_label}<span style="color:#6b7280;font-weight:500;">'
                f' · {cnt}</span></strong></div>'
            )
        pi_legend_html = (
            f'<div style="margin-top:10px;padding-top:10px;'
            f'border-top:1px solid #f3f4f6;">'
            f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;'
            f'letter-spacing:0.5px;font-weight:700;margin-bottom:6px;">'
            f'By PI</div>{pi_legend}</div>'
            if pi_legend else ""
        )
        st.markdown(kpi_tile(
            "🌐", "External Grants",
            ext_val_text,
            sub=status_sub,
            accent=C_EMERALD,
            right_html=ext_svg, bars_html=pi_legend_html,
        ), unsafe_allow_html=True)

    # Long-label wrap CSS (kept for any st.metric used elsewhere)
    st.markdown(
        '<style>[data-testid="stMetricLabel"]{white-space:normal!important;'
        'overflow:visible!important;line-height:1.25!important;}'
        '[data-testid="stMetricLabel"] p{white-space:normal!important;'
        'overflow-wrap:break-word!important;font-size:13px!important;}</style>',
        unsafe_allow_html=True,
    )

    # ===== Two-column row: Upcoming Events (left) + Award Spotlight (right) =====
    # Merge upcoming items from 3 sources: iro_events, capacity_workshops,
    # and research_events_attended (scholarly engagements).
    upcoming = []
    if sb is not None:
        iso_today = today.isoformat()
        iso_horizon = (today + timedelta(days=30)).isoformat()

        # 1) Calendar events
        try:
            res = sb.table("iro_events").select("*")\
                    .gte("event_date", iso_today)\
                    .lte("event_date", iso_horizon)\
                    .order("event_date", desc=False).execute()
            for ev in (res.data or []):
                upcoming.append({
                    "date": ev.get("event_date"),
                    "title": ev.get("title"),
                    "type": ev.get("event_type") or "Event",
                    "location": ev.get("location"),
                    "source": "calendar",
                })
        except Exception:
            pass

        # 2) Workshops with status Planning / Upcoming
        try:
            res = sb.table("capacity_workshops").select("*")\
                    .gte("start_date", iso_today)\
                    .lte("start_date", iso_horizon)\
                    .in_("status", ["Planning", "Upcoming"])\
                    .order("start_date", desc=False).execute()
            for w in (res.data or []):
                upcoming.append({
                    "date": w.get("start_date"),
                    "title": w.get("title"),
                    "type": "Workshop",
                    "location": w.get("workshop_type"),
                    "source": "workshop",
                })
        except Exception:
            pass

        # 3) Scholarly engagements (research_events_attended)
        try:
            res = sb.table("research_events_attended").select("*")\
                    .gte("start_date", iso_today)\
                    .lte("start_date", iso_horizon)\
                    .order("start_date", desc=False).execute()
            for e in (res.data or []):
                upcoming.append({
                    "date": e.get("start_date"),
                    "title": e.get("event_title"),
                    "type": e.get("event_type") or "Scholarly Engagement",
                    "location": e.get("location"),
                    "source": "engagement",
                })
        except Exception:
            pass

        # Sort by date, keep only items that have a date
        upcoming = sorted(
            [u for u in upcoming if u.get("date")],
            key=lambda u: str(u["date"]),
        )[:10]

    # Award spotlight: recent attendees with non-null award
    award_winners = []
    if sb is not None:
        try:
            res = sb.table("research_event_attendees").select("*")\
                    .neq("award", "").order("id", desc=True).limit(4).execute()
            award_winners = [a for a in (res.data or [])
                             if (a.get("award") or "").strip()][:4]
            if award_winners:
                ev_ids = [a["event_id"] for a in award_winners
                          if a.get("event_id")]
                if ev_ids:
                    ev_lookup = sb.table("research_events_attended")\
                                  .select("id,event_title,start_date")\
                                  .in_("id", ev_ids).execute().data or []
                    ev_map = {e["id"]: e for e in ev_lookup}
                    for a in award_winners:
                        e = ev_map.get(a.get("event_id"), {})
                        a["_event_title"] = e.get("event_title") or "—"
                        a["_event_date"] = e.get("start_date") or ""
        except Exception:
            award_winners = []

    left, right = st.columns([5, 4])

    with left:
        st.markdown(
            '<div class="section-heading">📅 Upcoming · Next 30 days</div>',
            unsafe_allow_html=True,
        )
        if upcoming:
            item_html = ""
            type_color = {
                "Workshop": C_EMERALD,
                "Grant Deadline": "#dc2626",
                "Congress / Symposium": GOLD,
                "Congress": GOLD,
                "Conference": C_AMBER,
                "Meeting": "#16a34a",
                "Training": "#8b5cf6",
                "Holiday": "#94a3b8",
                "Symposium": GOLD,
                "Seminar": C_SKY,
                "Webinar": C_SKY,
                "Scholarly Engagement": C_SKY,
            }
            source_badge = {
                "calendar": ("📅", "#6b7280"),
                "workshop": ("🎓", C_EMERALD),
                "engagement": ("🎤", C_SKY),
            }
            for ev in upcoming:
                ev_date = ev.get("date") or ""
                days_to = ""
                try:
                    d = datetime.fromisoformat(str(ev_date)).date()
                    diff = (d - today).days
                    days_to = (f"<span style=\"color:#dc2626;font-weight:700;\">"
                               f"in {diff}d</span>" if diff <= 7
                               else f"in {diff}d")
                except Exception:
                    pass
                etype = ev.get("type") or "Other"
                ecolor = type_color.get(etype, "#6b7280")
                icon, _ = source_badge.get(ev.get("source"), ("•", "#6b7280"))
                title_text = ev.get("title") or "—"
                loc_text = ev.get("location") or ""
                item_html += (
                    f'<div style="display:flex;align-items:center;gap:12px;'
                    f'padding:10px 4px;border-bottom:1px solid #f3f4f6;">'
                    f'<div style="width:7px;height:42px;background:{ecolor};'
                    f'border-radius:3px;flex-shrink:0;"></div>'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:15px;font-weight:600;color:{NAVY};'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
                    f'{icon} {title_text}</div>'
                    f'<div style="font-size:13px;color:#6b7280;margin-top:3px;">'
                    f'{ev_date} · {etype}'
                    + (f' · {loc_text}' if loc_text else "")
                    + f'</div></div>'
                    f'<div style="font-size:13px;color:#6b7280;flex-shrink:0;'
                    f'font-weight:600;">{days_to}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:white;border:1px solid #e5e7eb;'
                f'border-radius:8px;padding:6px 14px;'
                f'box-shadow:0 1px 2px rgba(0,0,0,0.03);">{item_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:white;border:1px solid #e5e7eb;'
                'border-radius:8px;padding:18px;text-align:center;'
                'color:#9ca3af;font-size:14px;">No events in the next 30 days.</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown(
            '<div class="section-heading">🏆 Award Spotlight</div>',
            unsafe_allow_html=True,
        )
        if award_winners:
            item_html = ""
            for a in award_winners:
                item_html += (
                    f'<div style="padding:12px 4px;border-bottom:1px solid #f3f4f6;">'
                    f'<div style="display:inline-block;padding:3px 10px;'
                    f'background:#fde68a;border:1px solid #f59e0b;'
                    f'border-radius:12px;font-size:12px;font-weight:700;'
                    f'color:#78350f;text-transform:uppercase;'
                    f'letter-spacing:0.4px;">🏆 {(a.get("award") or "").strip()}</div>'
                    f'<div style="font-size:15px;font-weight:600;color:{NAVY};'
                    f'margin-top:6px;">{a.get("attendee_name") or "—"}'
                    + (f' <span style="font-weight:400;color:#6b7280;">'
                       f'· {a.get("attendee_college")}</span>'
                       if a.get("attendee_college") else "")
                    + f'</div>'
                    f'<div style="font-size:13px;color:#6b7280;margin-top:3px;'
                    f'font-style:italic;">{a.get("_event_title") or "—"}'
                    + (f' ({a.get("_event_date")})' if a.get("_event_date") else "")
                    + f'</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:white;border:1px solid #e5e7eb;'
                f'border-radius:8px;padding:6px 14px;'
                f'box-shadow:0 1px 2px rgba(0,0,0,0.03);">{item_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:white;border:1px solid #e5e7eb;'
                'border-radius:8px;padding:18px;text-align:center;'
                'color:#9ca3af;font-size:12px;">No awards logged yet.</div>',
                unsafe_allow_html=True,
            )

    # ----- Research Productivity (mirrors HTML template panel exactly) -----
    st.markdown('<div class="section-heading">Research Productivity</div>',
                unsafe_allow_html=True)

    if scopus_data:
        # Aggregate metrics
        year_counts = {}
        q_counts = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "NA": 0}
        oa_count = 0
        cit_total = 0
        citations_per_paper = []
        for p in scopus_data:
            y = p.get("year")
            if y:
                year_counts[y] = year_counts.get(y, 0) + 1
            q = p.get("quartile") or "NA"
            if q in q_counts:
                q_counts[q] += 1
            if p.get("open_access"):
                oa_count += 1
            c = int(p.get("citation_count") or 0)
            cit_total += c
            citations_per_paper.append(c)

        # h-index = largest n such that n papers have ≥n citations
        citations_per_paper.sort(reverse=True)
        h_index = 0
        for i, c in enumerate(citations_per_paper, start=1):
            if c >= i:
                h_index = i
            else:
                break

        total_pubs_all = len(scopus_data)
        years_sorted = sorted(year_counts.keys())
        last_year = max(years_sorted) if years_sorted else None
        latest_count = year_counts.get(last_year, 0)
        prev_count = year_counts.get(last_year - 1, 0) if last_year else 0
        yoy = ((latest_count - prev_count) / prev_count * 100) if prev_count else 0
        oa_pct = round(oa_count / total_pubs_all * 100) if total_pubs_all else 0
        year_range = (f"{years_sorted[0]}–{years_sorted[-1]}"
                      if len(years_sorted) > 1 else str(years_sorted[0]))

        # ===== PANEL HEADER =====
        header_html = (
            f'<div style="background:white;border:1px solid #e5e7eb;border-radius:8px 8px 0 0;padding:20px 24px 16px 24px;box-shadow:0 1px 2px rgba(0,0,0,0.03);border-bottom:none;">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
            f'<h3 style="margin:0;font-size:18px;color:{NAVY};font-weight:700;letter-spacing:0.2px;">Scopus-Indexed Publications</h3>'
            f'<span style="font-size:12px;font-weight:700;background:#f4f6fa;color:#374151;padding:5px 12px;border-radius:12px;text-transform:uppercase;letter-spacing:0.4px;">{year_range}</span>'
            f'</div>'
            f'<div style="font-size:14px;color:#4b5563;margin-top:6px;">Annual output, quartile mix, and citation impact.</div>'
            f'</div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)

        # ===== TWO COLUMNS — chart left, stats right =====
        chart_col, stats_col = st.columns([5, 4])

        # LEFT — vertical bar chart by year
        with chart_col:
            year_df = pd.DataFrame({
                "Year": years_sorted,
                "Publications": [year_counts[y] for y in years_sorted],
            })
            max_y = max(year_df["Publications"]) if len(year_df) else 1
            fig = px.bar(
                year_df, x="Year", y="Publications",
                color_discrete_sequence=[NAVY],
                text="Publications", height=260,
            )
            fig.update_traces(
                textposition='outside',
                textfont=dict(size=14, color=NAVY, family='Inter, Arial'),
                marker=dict(line=dict(width=0)),
                cliponaxis=False,
                width=0.6,
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(t=24, b=12, l=12, r=12),
                xaxis=dict(title=None, tickmode='linear', showgrid=False,
                           tickfont=dict(size=14, color='#6b7280'),
                           showline=False, zeroline=False),
                yaxis=dict(visible=False, range=[0, max_y * 1.22]),
                plot_bgcolor='white',
                uniformtext=dict(minsize=12, mode='show'),
                bargap=0.35,
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

        # RIGHT — Total + YoY, Quartile Mix, then 3 impact stats inline (matches HTML)
        with stats_col:
            yoy_color = GREEN if yoy >= 0 else RED
            yoy_arrow = "▲" if yoy >= 0 else "▼"

            # IMPORTANT: HTML must NOT be indented (Streamlit's markdown parser
            # otherwise treats it as a code block). Keep one line each.
            quartile_bars = ""
            for q in ["Q1", "Q2", "Q3", "Q4", "NA"]:
                n = q_counts[q]
                pct = round(n / total_pubs_all * 100) if total_pubs_all else 0
                c = QUARTILE_COLORS[q]
                quartile_bars += (
                    f'<div style="display:flex;align-items:center;margin:6px 0;font-size:13px;">'
                    f'<div style="width:34px;color:#374151;font-weight:700;">{q}</div>'
                    f'<div style="flex:1;background:#f3f4f6;height:13px;border-radius:4px;margin:0 10px;">'
                    f'<div style="width:{pct}%;height:100%;background:{c};border-radius:4px;"></div>'
                    f'</div>'
                    f'<div style="width:72px;text-align:right;color:#6b7280;">'
                    f'<strong style="color:{NAVY};">{n}</strong> · {pct}%'
                    f'</div>'
                    f'</div>'
                )

            panel_html = (
                f'<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:18px 22px;font-size:14px;">'
                f'<div style="margin-bottom:16px;">'
                f'<div style="color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:0.4px;font-weight:700;">Total ({last_year})</div>'
                f'<div style="font-size:26px;font-weight:700;color:{NAVY};margin-top:4px;line-height:1;">{latest_count}</div>'
                f'<div style="font-size:13px;color:{yoy_color};font-weight:600;margin-top:6px;">{yoy_arrow} {abs(yoy):.1f}% YoY</div>'
                f'</div>'
                f'<div style="color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:0.4px;font-weight:700;margin-bottom:8px;">Quartile Mix</div>'
                f'{quartile_bars}'
                f'<div style="margin-top:14px;display:flex;gap:22px;padding-top:12px;border-top:1px solid #e5e7eb;flex-wrap:wrap;">'
                f'<div><span style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.3px;font-weight:700;">h-index</span><br>'
                f'<strong style="color:{NAVY};font-size:17px;">{h_index}</strong></div>'
                f'<div><span style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.3px;font-weight:700;">Citations</span><br>'
                f'<strong style="color:{NAVY};font-size:17px;">{cit_total:,}</strong></div>'
                f'<div><span style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.3px;font-weight:700;">Open Access</span><br>'
                f'<strong style="color:{NAVY};font-size:17px;">{oa_pct}%</strong></div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(panel_html, unsafe_allow_html=True)

    else:
        st.info("No publication data yet.")

    # ----- In-House Grants per College (heading first, then utilisation) -----
    st.markdown(
        '<div class="section-heading">In-House Grants per College</div>',
        unsafe_allow_html=True,
    )

    GRANT_BUDGET = 2_000_000  # ₱2M allocation for AY 2025-2026
    awarded = float(grants_total or 0)
    remaining = max(0.0, GRANT_BUDGET - awarded)
    awarded_pct = (awarded / GRANT_BUDGET * 100) if GRANT_BUDGET else 0
    awarded_w = min(100.0, awarded_pct)
    remaining_w = max(0.0, 100.0 - awarded_w)

    def _peso(v):
        if v >= 1_000_000:
            return f"₱{v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"₱{v/1_000:.0f}K"
        return f"₱{v:,.0f}"

    n_grants = len(grants_db) if grants_db else 0
    progress_html = (
        f'<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
        f'padding:18px 20px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'margin-bottom:12px;flex-wrap:wrap;gap:6px;">'
        f'<div style="font-size:14px;font-weight:700;color:{NAVY};'
        f'text-transform:uppercase;letter-spacing:0.5px;">'
        f'💰 Budget Utilisation · AY 2025–2026 (Allocation {_peso(GRANT_BUDGET)})</div>'
        f'<div style="font-size:13px;color:#6b7280;">'
        f'<strong style="color:{NAVY};font-size:16px;">{_peso(awarded)}</strong> awarded '
        f'<span style="color:{GOLD};font-weight:700;">({awarded_pct:.0f}%)</span></div>'
        f'</div>'
        f'<div style="display:flex;height:16px;border-radius:8px;overflow:hidden;'
        f'background:#f3f4f6;border:1px solid #e5e7eb;">'
        f'<div title="Awarded: {_peso(awarded)}" style="width:{awarded_w}%;'
        f'background:{GOLD};"></div>'
        f'<div title="Remaining: {_peso(remaining)}" style="width:{remaining_w}%;'
        f'background:transparent;"></div>'
        f'</div>'
        f'<div style="display:flex;gap:22px;margin-top:12px;font-size:13px;'
        f'color:#374151;flex-wrap:wrap;">'
        f'<div><span style="display:inline-block;width:12px;height:12px;'
        f'background:{GOLD};border-radius:3px;margin-right:6px;'
        f'vertical-align:middle;"></span>'
        f'<strong>{_peso(awarded)}</strong> Awarded · {n_grants} project'
        f'{"s" if n_grants != 1 else ""}</div>'
        f'<div><span style="display:inline-block;width:12px;height:12px;'
        f'background:#e5e7eb;border:1px dashed #9ca3af;border-radius:3px;'
        f'margin-right:6px;vertical-align:middle;"></span>'
        f'<strong>{_peso(remaining)}</strong> Remaining</div>'
        f'<div style="margin-left:auto;color:#6b7280;">'
        f'Avg. grant size: <strong style="color:{NAVY};">'
        f'{_peso(awarded / n_grants) if n_grants else "—"}</strong></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(progress_html, unsafe_allow_html=True)

    if grants_db:
        # Sort colleges by amount descending, build clean HTML bar-rows
        sorted_cols = sorted(by_col_amt.items(), key=lambda x: -x[1])
        max_amt = max(amt for _, amt in sorted_cols) or 1
        bar_rows_html = ""
        for i, (c, amt) in enumerate(sorted_cols):
            color = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            pct = amt / max_amt * 100
            n = by_col_cnt[c]
            bar_rows_html += (
                f'<div style="display:flex;align-items:center;margin:10px 0;'
                f'font-size:14px;">'
                f'<div style="width:170px;color:#374151;font-weight:600;'
                f'flex-shrink:0;padding-right:12px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap;">{c}</div>'
                f'<div style="flex:1;background:#f3f4f6;height:20px;'
                f'border-radius:4px;position:relative;overflow:hidden;">'
                f'<div style="width:{pct}%;height:100%;background:{color};'
                f'border-radius:4px;"></div></div>'
                f'<div style="width:160px;text-align:right;color:#6b7280;'
                f'padding-left:12px;flex-shrink:0;">'
                f'<strong style="color:{NAVY};">₱{amt:,.0f}</strong>'
                f' · {n} grant{"s" if n != 1 else ""}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:white;border:1px solid #e5e7eb;'
            f'border-radius:8px;padding:18px 22px;'
            f'box-shadow:0 1px 2px rgba(0,0,0,0.03);">{bar_rows_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No in-house grants in the database yet.")

    # ----- External Grants -----
    st.markdown(
        '<div class="section-heading">External Grants</div>',
        unsafe_allow_html=True,
    )
    ext_grants = []
    ext_missing = False
    if sb is not None:
        try:
            res = sb.table("external_grants").select("*")\
                    .order("date_submitted", desc=True).execute()
            ext_grants = res.data or []
        except Exception as ex:
            if "PGRST205" in str(ex) or "schema cache" in str(ex).lower():
                ext_missing = True

    if ext_missing:
        st.warning(
            "⚠️ The `external_grants` table doesn't exist yet. "
            "Run **`add_external_grants.sql`** in the Supabase SQL Editor, "
            "then refresh this page."
        )
    elif not ext_grants:
        st.info("No external grants logged yet.")
    else:
        # KPI summary
        ext_total = sum(float(g.get("amount") or 0) for g in ext_grants)
        def _norm(s): return (s or "").strip().lower()
        ext_review = sum(1 for g in ext_grants
                         if _norm(g.get("status")) == "in review")
        ext_awarded = sum(1 for g in ext_grants
                          if _norm(g.get("status")) in ("awarded", "active"))
        ext_completed = sum(1 for g in ext_grants
                            if _norm(g.get("status")) == "completed")

        def _peso2(v):
            if v >= 1_000_000:
                return f"₱{v/1_000_000:.2f}M"
            if v >= 1_000:
                return f"₱{v/1_000:.0f}K"
            return f"₱{v:,.0f}"

        em1, em2, em3, em4, em5 = st.columns(5)
        em1.metric("Total Grants", len(ext_grants))
        em2.metric("Total Value", _peso2(ext_total))
        em3.metric("In Review", ext_review)
        em4.metric("Awarded / Active", ext_awarded)
        em5.metric("Completed", ext_completed)

        # Aggregate by funding source
        by_src_amt = {}
        by_src_cnt = {}
        for g in ext_grants:
            src = g.get("funding_source") or "Other"
            by_src_amt[src] = by_src_amt.get(src, 0) + float(g.get("amount") or 0)
            by_src_cnt[src] = by_src_cnt.get(src, 0) + 1

        sorted_src = sorted(by_src_amt.items(), key=lambda x: -x[1])
        max_ext = max(amt for _, amt in sorted_src) or 1
        ext_rows = ""
        for i, (src, amt) in enumerate(sorted_src):
            color = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            pct = amt / max_ext * 100
            n = by_src_cnt[src]
            ext_rows += (
                f'<div style="display:flex;align-items:center;margin:10px 0;'
                f'font-size:14px;">'
                f'<div style="width:170px;color:#374151;font-weight:600;'
                f'flex-shrink:0;padding-right:12px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap;">{src}</div>'
                f'<div style="flex:1;background:#f3f4f6;height:20px;'
                f'border-radius:4px;position:relative;overflow:hidden;">'
                f'<div style="width:{pct}%;height:100%;background:{color};'
                f'border-radius:4px;"></div></div>'
                f'<div style="width:170px;text-align:right;color:#6b7280;'
                f'padding-left:12px;flex-shrink:0;">'
                f'<strong style="color:{NAVY};">{_peso2(amt)}</strong>'
                f' · {n} grant{"s" if n != 1 else ""}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:white;border:1px solid #e5e7eb;'
            f'border-radius:8px;padding:18px 22px;'
            f'box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
            f'<div style="font-size:12px;font-weight:700;color:#6b7280;'
            f'text-transform:uppercase;letter-spacing:0.5px;'
            f'margin-bottom:8px;">By funding source</div>'
            f'{ext_rows}</div>',
            unsafe_allow_html=True,
        )

        # ----- Application status pipeline -----
        STATUS_BADGE = {
            "In Review":  ("#fef3c7", "#92400e", "#f59e0b"),  # bg, fg, border
            "Awarded":    ("#d1fae5", "#065f46", "#10b981"),
            "Active":     ("#ccfbf1", "#115e59", "#0d9488"),
            "Completed":  ("#dbeafe", "#1e40af", "#3b82f6"),
            "Cancelled":  ("#f3f4f6", "#6b7280", "#9ca3af"),
        }
        STATUS_PIPELINE_ORDER = ["In Review", "Awarded", "Active",
                                  "Completed", "Cancelled"]

        # Group grants by status, preserving the lifecycle order
        by_status = {s: [] for s in STATUS_PIPELINE_ORDER}
        for g in ext_grants:
            s = (g.get("status") or "").strip()
            if s in by_status:
                by_status[s].append(g)
            else:
                by_status.setdefault("In Review", []).append(g)

        def _safe(v):
            if v is None:
                return ""
            return str(v).replace("<", "&lt;").replace(">", "&gt;")

        pipeline_cols_html = ""
        for s in STATUS_PIPELINE_ORDER:
            bag = by_status.get(s, [])
            bg, fg, border = STATUS_BADGE.get(s, ("#f3f4f6", "#374151", "#9ca3af"))
            items_html = ""
            for g in bag[:8]:
                title = _safe((g.get("title") or "")[:60])
                pi = _safe(g.get("pi") or "—")
                amt = float(g.get("amount") or 0)
                amt_label = _peso2(amt) if amt else "—"
                src = _safe(g.get("funding_source") or "")
                items_html += (
                    f'<div style="padding:8px 10px;background:white;'
                    f'border:1px solid #e5e7eb;border-radius:6px;'
                    f'margin-bottom:6px;font-size:12px;">'
                    f'<div style="font-weight:600;color:{NAVY};line-height:1.3;'
                    f'overflow:hidden;text-overflow:ellipsis;'
                    f'white-space:nowrap;">{title or "—"}</div>'
                    f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">'
                    f'{pi} · {src}</div>'
                    f'<div style="font-size:11px;margin-top:3px;">'
                    f'<strong style="color:{NAVY};">{amt_label}</strong></div>'
                    f'</div>'
                )
            if len(bag) > 8:
                items_html += (
                    f'<div style="text-align:center;font-size:11px;'
                    f'color:#6b7280;padding:4px;">+ {len(bag) - 8} more</div>'
                )
            if not items_html:
                items_html = (
                    f'<div style="text-align:center;color:#9ca3af;'
                    f'font-size:11px;padding:8px;font-style:italic;">empty</div>'
                )
            pipeline_cols_html += (
                f'<div style="flex:1;min-width:0;background:#fafafa;'
                f'border:1px solid #e5e7eb;border-radius:8px;padding:10px;">'
                f'<div style="display:flex;align-items:center;'
                f'justify-content:space-between;margin-bottom:8px;">'
                f'<span style="display:inline-block;padding:3px 10px;'
                f'background:{bg};color:{fg};border:1px solid {border};'
                f'border-radius:12px;font-size:11px;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:0.4px;">{s}</span>'
                f'<strong style="color:{NAVY};font-size:14px;">'
                f'{len(bag)}</strong></div>'
                f'{items_html}</div>'
            )

        st.markdown(
            f'<div style="background:white;border:1px solid #e5e7eb;'
            f'border-radius:8px;padding:18px 22px;margin-top:14px;'
            f'box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
            f'<div style="font-size:12px;font-weight:700;color:#6b7280;'
            f'text-transform:uppercase;letter-spacing:0.5px;'
            f'margin-bottom:10px;">Application status pipeline</div>'
            f'<div style="display:flex;gap:10px;flex-wrap:wrap;">'
            f'{pipeline_cols_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ----- Capacity-Building Workshops summary table -----
    st.markdown('<div class="section-heading">Capacity-Building Workshops</div>',
                unsafe_allow_html=True)

    # ----- Workshop target progress (AY 2025-2027 target = 18) -----
    WS_TARGET = 18
    WS_PLAN_LABEL = "AY 2025–2027 plan"
    ws_completed = sum(1 for w in (workshops_list or [])
                       if (w.get("status") or "").strip() == "Completed")
    ws_planned = sum(1 for w in (workshops_list or [])
                     if (w.get("status") or "").strip()
                     in ("Upcoming", "Planning"))
    ws_remaining = max(0, WS_TARGET - ws_completed - ws_planned)
    achieved_pct = (ws_completed / WS_TARGET * 100) if WS_TARGET else 0
    pipeline_pct = ((ws_completed + ws_planned) / WS_TARGET * 100) if WS_TARGET else 0

    comp_w = (ws_completed / WS_TARGET * 100) if WS_TARGET else 0
    plan_w = (ws_planned / WS_TARGET * 100) if WS_TARGET else 0
    rem_w = max(0, 100 - comp_w - plan_w)

    progress_html = (
        f'<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
        f'padding:18px 20px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'margin-bottom:12px;flex-wrap:wrap;gap:6px;">'
        f'<div style="font-size:14px;font-weight:700;color:{NAVY};'
        f'text-transform:uppercase;letter-spacing:0.5px;">'
        f'🎯 Target vs Actual · {WS_PLAN_LABEL}</div>'
        f'<div style="font-size:13px;color:#6b7280;">'
        f'<strong style="color:{NAVY};font-size:16px;">{ws_completed}</strong> / '
        f'{WS_TARGET} completed '
        f'<span style="color:{GOLD};font-weight:700;">'
        f'({achieved_pct:.0f}%)</span></div>'
        f'</div>'
        f'<div style="display:flex;height:16px;border-radius:8px;overflow:hidden;'
        f'background:#f3f4f6;border:1px solid #e5e7eb;">'
        f'<div title="Completed: {ws_completed}" style="width:{comp_w}%;'
        f'background:{GOLD};"></div>'
        f'<div title="Planned: {ws_planned}" style="width:{plan_w}%;'
        f'background:{PURPLE};"></div>'
        f'<div title="Remaining: {ws_remaining}" style="width:{rem_w}%;'
        f'background:transparent;"></div>'
        f'</div>'
        f'<div style="display:flex;gap:22px;margin-top:12px;font-size:13px;'
        f'color:#374151;flex-wrap:wrap;">'
        f'<div><span style="display:inline-block;width:12px;height:12px;'
        f'background:{GOLD};border-radius:3px;margin-right:6px;'
        f'vertical-align:middle;"></span>'
        f'<strong>{ws_completed}</strong> Completed</div>'
        f'<div><span style="display:inline-block;width:12px;height:12px;'
        f'background:{PURPLE};border-radius:3px;margin-right:6px;'
        f'vertical-align:middle;"></span>'
        f'<strong>{ws_planned}</strong> Planned / Upcoming</div>'
        f'<div><span style="display:inline-block;width:12px;height:12px;'
        f'background:#e5e7eb;border:1px dashed #9ca3af;border-radius:3px;'
        f'margin-right:6px;vertical-align:middle;"></span>'
        f'<strong>{ws_remaining}</strong> Remaining to target</div>'
        f'<div style="margin-left:auto;color:#6b7280;">'
        f'Pipeline coverage: <strong style="color:{NAVY};">'
        f'{pipeline_pct:.0f}%</strong></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(progress_html, unsafe_allow_html=True)

    if workshops_list:
        ws_df = pd.DataFrame(workshops_list)

        # Combine start–end date into a readable "Date" column
        def date_label(row):
            s = str(row.get("start_date") or "")
            e = str(row.get("end_date") or "")
            if e and e != s and e != "None":
                return f"{s} – {e}"
            return s
        ws_df["Date"] = ws_df.apply(date_label, axis=1)

        display_cols = ["title", "Date", "speakers"]
        rename_map = {"title": "Workshop Title", "speakers": "Speaker(s)"}
        st.dataframe(
            ws_df[display_cols].rename(columns=rename_map),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Workshop Title": st.column_config.TextColumn("Workshop Title",
                                                              width="large"),
                "Date": st.column_config.TextColumn("Date", width="small"),
                "Speaker(s)": st.column_config.TextColumn("Speaker(s)",
                                                          width="medium"),
            },
        )
    else:
        st.info("No workshops in the database yet.")

# ============================================================
# PAGE: SCOPUS PUBLICATIONS (VIEW)
# ============================================================
# ============================================================
# PAGE: RESEARCH ECOSYSTEM
# ============================================================
elif page == "Research Ecosystem":
    st.markdown('<div class="section-heading">Research Ecosystem</div>',
                unsafe_allow_html=True)
    st.caption(
        "Organisational structure of the MCU research ecosystem — from the "
        "Office of the VP for Academic Affairs down to the Institutional "
        "Research Office and its supporting roles."
    )

    org_chart_svg_raw = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="-260 0 1960 720" style="font-family:Inter,-apple-system,system-ui,sans-serif;">
<defs>
<filter id="boxShadow" x="-10%" y="-10%" width="120%" height="140%">
<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0a1628" flood-opacity="0.18"/>
</filter>
<marker id="arrowHead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
<path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/>
</marker>
</defs>
<g filter="url(#boxShadow)"><rect x="560" y="20" width="280" height="70" rx="10" fill="#7c3aed"/></g>
<text x="700" y="50" text-anchor="middle" fill="#ffffff" font-size="22" font-weight="700">Vice President</text>
<text x="700" y="72" text-anchor="middle" fill="#ffffff" font-size="20">for Academic Affairs</text>
<g filter="url(#boxShadow)"><rect x="560" y="110" width="280" height="70" rx="10" fill="#a78bfa"/></g>
<text x="700" y="140" text-anchor="middle" fill="#ffffff" font-size="22" font-weight="700">Assistant Vice President</text>
<text x="700" y="162" text-anchor="middle" fill="#ffffff" font-size="20">for Academic Affairs</text>
<line x1="700" y1="90" x2="700" y2="110" stroke="#475569" stroke-width="2"/>
<line x1="700" y1="180" x2="700" y2="210" stroke="#475569" stroke-width="2"/>
<line x1="190" y1="210" x2="1210" y2="210" stroke="#475569" stroke-width="2"/>
<line x1="190" y1="210" x2="190" y2="240" stroke="#475569" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="530" y1="210" x2="530" y2="240" stroke="#475569" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="870" y1="210" x2="870" y2="240" stroke="#475569" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="1210" y1="210" x2="1210" y2="240" stroke="#475569" stroke-width="2" marker-end="url(#arrowHead)"/>
<g filter="url(#boxShadow)">
<rect x="50" y="240" width="280" height="90" rx="10" fill="#ca8a04"/>
<rect x="390" y="240" width="280" height="90" rx="10" fill="#ca8a04"/>
<rect x="730" y="240" width="280" height="90" rx="10" fill="#ca8a04"/>
<rect x="1070" y="240" width="280" height="90" rx="10" fill="#ca8a04"/>
</g>
<text x="190" y="272" text-anchor="middle" fill="#ffffff" font-size="19" font-weight="700">INSTITUTE OF ANIMAL CARE</text>
<text x="190" y="290" text-anchor="middle" fill="#ffffff" font-size="19" font-weight="700">AND USE COMMITTEE</text>
<text x="190" y="312" text-anchor="middle" fill="#ffffff" font-size="16" font-style="italic">(Chairperson)</text>
<text x="530" y="290" text-anchor="middle" fill="#ffffff" font-size="20" font-weight="700">BIOSAFETY OFFICER</text>
<text x="870" y="272" text-anchor="middle" fill="#ffffff" font-size="19" font-weight="700">INSTITUTIONAL RESEARCH</text>
<text x="870" y="290" text-anchor="middle" fill="#ffffff" font-size="19" font-weight="700">OFFICE</text>
<text x="870" y="312" text-anchor="middle" fill="#ffffff" font-size="16" font-style="italic">(Head)</text>
<text x="1210" y="280" text-anchor="middle" fill="#ffffff" font-size="19" font-weight="700">ETHICS REVIEW BOARD</text>
<text x="1210" y="304" text-anchor="middle" fill="#ffffff" font-size="16" font-style="italic">(Chairperson)</text>
<line x1="330" y1="285" x2="390" y2="285" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 4"/>
<line x1="670" y1="285" x2="730" y2="285" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 4"/>
<line x1="1010" y1="285" x2="1070" y2="285" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 4"/>
<!-- IACUC chain: 2 support roles flipped LEFT, gold family -->
<line x1="190" y1="330" x2="190" y2="475" stroke="#78350f" stroke-width="2"/>
<line x1="190" y1="405" x2="40" y2="405" stroke="#78350f" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="190" y1="475" x2="40" y2="475" stroke="#78350f" stroke-width="2" marker-end="url(#arrowHead)"/>
<g filter="url(#boxShadow)">
<rect x="-240" y="380" width="280" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
<rect x="-240" y="450" width="280" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
</g>
<text x="-100" y="412" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">MCU Veterinarian</text>
<text x="-100" y="482" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">IACUC Faculty Reviewer</text>
<!-- IRO chain: flipped LEFT, green family -->
<line x1="870" y1="330" x2="870" y2="545" stroke="#78350f" stroke-width="2"/>
<line x1="870" y1="385" x2="720" y2="385" stroke="#78350f" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="870" y1="465" x2="720" y2="465" stroke="#78350f" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="870" y1="545" x2="720" y2="545" stroke="#78350f" stroke-width="2" marker-end="url(#arrowHead)"/>
<g filter="url(#boxShadow)">
<rect x="440" y="360" width="280" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
<rect x="440" y="430" width="280" height="70" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
<rect x="440" y="520" width="280" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
</g>
<text x="580" y="392" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">College Research Chair<tspan fill="#c0392b" font-weight="800">*</tspan></text>
<text x="580" y="458" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">Research Statistician<tspan fill="#c0392b" font-weight="800">*</tspan> /</text>
<text x="580" y="482" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">Research Officer</text>
<text x="580" y="552" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">Research Assistant</text>
<!-- ERB chain: branching RIGHT, teal family, all roles report to chairperson -->
<line x1="1210" y1="330" x2="1210" y2="635" stroke="#7c2d12" stroke-width="2"/>
<line x1="1210" y1="405" x2="1360" y2="405" stroke="#7c2d12" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="1210" y1="495" x2="1360" y2="495" stroke="#7c2d12" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="1210" y1="565" x2="1360" y2="565" stroke="#7c2d12" stroke-width="2" marker-end="url(#arrowHead)"/>
<line x1="1210" y1="635" x2="1360" y2="635" stroke="#7c2d12" stroke-width="2" marker-end="url(#arrowHead)"/>
<g filter="url(#boxShadow)">
<rect x="1360" y="360" width="290" height="90" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
<rect x="1360" y="470" width="290" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
<rect x="1360" y="540" width="290" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
<rect x="1360" y="610" width="290" height="50" rx="8" fill="#fde68a" stroke="#f59e0b" stroke-width="2"/>
</g>
<text x="1505" y="388" text-anchor="middle" fill="#78350f" font-size="20" font-weight="700">Vice Chair</text>
<text x="1505" y="409" text-anchor="middle" fill="#78350f" font-size="20" font-weight="700">Member-Secretary</text>
<text x="1505" y="430" text-anchor="middle" fill="#78350f" font-size="20" font-weight="700">Regular Members</text>
<text x="1505" y="500" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">Alternate Members</text>
<text x="1505" y="570" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">Independent Consultants</text>
<text x="1505" y="640" text-anchor="middle" fill="#78350f" font-size="21" font-weight="700">MCU ERB Staff</text>
</svg>"""
    # Base64-encode and embed as <img> so Streamlit's HTML sanitiser doesn't
    # strip the SVG <text> elements.
    import base64 as _b64_org
    _b64_svg = _b64_org.b64encode(
        org_chart_svg_raw.encode("utf-8")).decode("ascii")
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;'
        f'border-radius:12px;padding:24px 16px;margin-top:8px;">'
        f'<img src="data:image/svg+xml;base64,{_b64_svg}" '
        f'style="width:100%;height:auto;max-width:1400px;display:block;'
        f'margin:0 auto;" alt="MCU Research Ecosystem Org Chart"/>'
        f'<p style="font-size:12px;color:#5b6878;margin:14px 0 0 0;'
        f'text-align:center;font-style:italic;">'
        f'<span style="color:#c0392b;font-weight:700;">*</span> '
        f'Joint appointment / advisory role shared with the College.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE: CALENDAR OF EVENTS
# ============================================================
elif page == "Calendar of Events":
    st.markdown('<div class="section-heading">Calendar of Events</div>',
                unsafe_allow_html=True)
    st.caption(
        "IRO calendar showing workshops, grant deadlines, congresses, "
        "and other research events."
    )

    # Color map per event type — muted brand palette for consistency
    EVENT_COLORS = {
        "Workshop":             BRAND["plum"],
        "Grant Deadline":       BRAND["terracotta"],
        "Congress / Symposium": BRAND["amber"],
        "Meeting":              BRAND["sage"],
        "Training":             BRAND["tan"],
        "Conference":           BRAND["brick"],
        "Holiday":              "#94a3b8",
        "Other":                BRAND["slate"],
    }

    events = db_select("iro_events", order_col="event_date", desc=False) if sb else []
    # Also pull workshops as events
    workshops_for_cal = db_select("capacity_workshops", order_col="start_date") if sb else []

    # Convert workshops to event format
    workshop_events = []
    for w in workshops_for_cal:
        workshop_events.append({
            "title": f"🎓 {w.get('title', 'Workshop')[:60]}",
            "start": str(w.get("start_date")),
            "end": (str(w.get("end_date")) if w.get("end_date") and w.get("end_date") != w.get("start_date")
                    else str(w.get("start_date"))),
            "color": PURPLE,
            "allDay": True,
        })

    # Convert iro_events to calendar format
    cal_events = []
    for e in events:
        c = e.get("color") or EVENT_COLORS.get(e.get("event_type"), "#6b7280")
        cal_events.append({
            "id": f"event-{e['id']}",   # so we can map back when dragged
            "title": e.get("title", "Event"),
            "start": str(e.get("event_date")),
            "end": (str(e.get("end_date")) if e.get("end_date") else str(e.get("event_date"))),
            "color": c,
            "allDay": True,
            "editable": True if _IS_ADMIN else False,
            "extendedProps": {
                "type": e.get("event_type"),
                "location": e.get("location") or "",
                "organizer": e.get("organizer") or "",
            },
        })

    # Workshop events get an id too (so they're distinguishable)
    for w_evt in workshop_events:
        w_evt["editable"] = False   # workshops are managed elsewhere

    combined = cal_events + workshop_events

    # Calendar options — drag-and-drop reschedule for admins
    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listMonth",
        },
        "initialView": "dayGridMonth",
        "selectable": True,
        "navLinks": True,
        "editable": True if _IS_ADMIN else False,
        "eventStartEditable": True if _IS_ADMIN else False,
        "eventDurationEditable": True if _IS_ADMIN else False,
        "dayMaxEvents": True,
        "height": 680,
    }

    custom_css = """
        .fc-event-title { font-weight: 600 !important; }
        .fc-button-primary {
            background-color: """ + PURPLE + """ !important;
            border-color: """ + PURPLE + """ !important;
        }
        .fc-button-primary:hover { background-color: #4c1d95 !important; }
        .fc-day-today { background-color: #fef3c7 !important; }
        .fc-toolbar-title { color: """ + NAVY + """ !important; font-size: 18px !important; }
    """

    cal_state = calendar(events=combined, options=calendar_options,
                         custom_css=custom_css, key="iro_calendar")

    # Handle drag-and-drop reschedule (admin only)
    if _IS_ADMIN and isinstance(cal_state, dict):
        callback_name = cal_state.get("callback")
        cb_data = cal_state.get(callback_name) if callback_name else None
        if callback_name in ("eventChange", "eventDrop", "eventResize") and cb_data:
            ev = cb_data.get("event") or {}
            event_id_str = ev.get("id", "")
            # Only handle iro_events (their id starts with "event-")
            if event_id_str.startswith("event-"):
                event_id = int(event_id_str.replace("event-", ""))
                new_start = (ev.get("start") or "")[:10]   # 'YYYY-MM-DD'
                new_end = (ev.get("end") or "")[:10]
                # FullCalendar's "end" for all-day events is exclusive (next day)
                if new_end and new_end > new_start:
                    # Subtract one day to make inclusive
                    from datetime import timedelta as _td
                    try:
                        new_end_d = datetime.fromisoformat(new_end).date() - _td(days=1)
                        new_end = new_end_d.isoformat()
                    except Exception:
                        pass
                # Build update payload
                updates = {"event_date": new_start}
                if new_end and new_end != new_start:
                    updates["end_date"] = new_end
                else:
                    updates["end_date"] = None
                if db_update("iro_events", event_id, updates):
                    st.success(
                        f"✅ Event rescheduled to **{new_start}**" +
                        (f" – {new_end}" if new_end and new_end != new_start else "")
                    )
                    # Brief delay then rerun so the UI catches up
                    st.rerun()

    # ----- Upcoming events list -----
    st.markdown('<div class="section-heading">Upcoming Events</div>',
                unsafe_allow_html=True)

    today_str = datetime.now().date().isoformat()
    upcoming = [e for e in (events + workshop_events)
                if str(e.get("start") or e.get("event_date") or "") >= today_str]
    # Workshop_events have "start"; iro_events have "event_date"
    upcoming_unified = []
    for e in events:
        if str(e.get("event_date") or "") >= today_str:
            upcoming_unified.append({
                "date": str(e.get("event_date")),
                "title": e.get("title"),
                "type": e.get("event_type"),
                "location": e.get("location") or "",
                "organizer": e.get("organizer") or "",
                "color": e.get("color") or EVENT_COLORS.get(e.get("event_type"), "#6b7280"),
            })
    for w in workshops_for_cal:
        if str(w.get("start_date") or "") >= today_str:
            upcoming_unified.append({
                "date": str(w.get("start_date")),
                "title": f"🎓 {w.get('title')}",
                "type": "Workshop",
                "location": "",
                "organizer": w.get("speakers") or "",
                "color": PURPLE,
            })
    upcoming_unified.sort(key=lambda x: x["date"])

    if not upcoming_unified:
        st.info("No upcoming events scheduled.")
    else:
        cards_html = ""
        for ev in upcoming_unified[:10]:
            cards_html += (
                f'<div style="background:white;border-left:4px solid {ev["color"]};'
                f'border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;'
                f'margin-bottom:8px;display:flex;align-items:center;gap:16px;">'
                f'<div style="min-width:110px;">'
                f'<div style="font-size:10px;color:#6b7280;text-transform:uppercase;'
                f'font-weight:600;letter-spacing:0.5px;">{ev["type"]}</div>'
                f'<div style="font-size:14px;font-weight:700;color:{NAVY};">{ev["date"]}</div>'
                f'</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:14px;font-weight:600;color:{NAVY};">{ev["title"]}</div>'
                + (f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">'
                   f'📍 {ev["location"]}</div>' if ev["location"] else '')
                + (f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">'
                   f'👤 {ev["organizer"]}</div>' if ev["organizer"] else '')
                + '</div>'
                '</div>'
            )
        st.markdown(cards_html, unsafe_allow_html=True)

    # ----- Edit / delete existing event (admin only) -----
    if _IS_ADMIN and events:
        with st.expander("✏️ Edit or Delete an Existing Event (Admin)"):
            event_labels = [
                f"[{e.get('event_date')}] {e.get('title')[:60]} ({e.get('event_type')})"
                for e in events
            ]
            ev_picked = st.selectbox("Select event to edit",
                                      [""] + event_labels, key="edit_event_pick")

            if ev_picked:
                ev_idx = event_labels.index(ev_picked)
                e = events[ev_idx]
                eid = e["id"]

                # When the picked event changes, clear any stale widget state
                # from the previous one so the form re-initialises from `value=`.
                if st.session_state.get("edit_event_loaded_id") != eid:
                    stale_prefixes = (
                        "edit_ev_title_", "edit_ev_date_", "edit_ev_end_",
                        "edit_ev_type_", "edit_ev_loc_", "edit_ev_org_",
                        "edit_ev_desc_", "edit_ev_link_", "edit_ev_status_",
                    )
                    for k in list(st.session_state.keys()):
                        if any(k.startswith(p) for p in stale_prefixes):
                            del st.session_state[k]
                    st.session_state["edit_event_loaded_id"] = eid

                # Scope the form to the event id so Streamlit fully resets
                # the widget tree whenever the user picks a different event.
                with st.form(f"edit_event_form_{eid}"):
                    title2 = st.text_input(
                        "Event Title *",
                        value=e.get("title") or "",
                        max_chars=200,
                        key=f"edit_ev_title_{eid}",
                    )
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        event_date2 = st.date_input(
                            "Event Date *",
                            value=datetime.fromisoformat(
                                str(e.get("event_date"))).date()
                            if e.get("event_date") else date.today(),
                            key=f"edit_ev_date_{eid}",
                        )
                    with c2:
                        end_default = (
                            datetime.fromisoformat(
                                str(e.get("end_date"))).date()
                            if e.get("end_date") else event_date2
                        )
                        end_date2 = st.date_input(
                            "End Date (multi-day)",
                            value=end_default,
                            key=f"edit_ev_end_{eid}",
                        )
                    with c3:
                        type_opts = [
                            "Workshop", "Grant Deadline",
                            "Congress / Symposium", "Meeting", "Training",
                            "Conference", "Holiday", "Other",
                        ]
                        current_type = e.get("event_type") or "Other"
                        event_type2 = st.selectbox(
                            "Type *", type_opts,
                            index=type_opts.index(current_type)
                            if current_type in type_opts else 0,
                            key=f"edit_ev_type_{eid}",
                        )

                    c4, c5 = st.columns(2)
                    with c4:
                        location2 = st.text_input(
                            "Location",
                            value=e.get("location") or "",
                            key=f"edit_ev_loc_{eid}",
                        )
                    with c5:
                        organizer2 = st.text_input(
                            "Organizer / Owner",
                            value=e.get("organizer") or "",
                            key=f"edit_ev_org_{eid}",
                        )

                    description2 = st.text_area(
                        "Description",
                        value=e.get("description") or "",
                        max_chars=500, height=80,
                        key=f"edit_ev_desc_{eid}",
                    )
                    link2 = st.text_input(
                        "Link / URL",
                        value=e.get("link") or "",
                        key=f"edit_ev_link_{eid}",
                    )

                    status_opts = ["Scheduled", "Cancelled", "Postponed"]
                    cur_status = e.get("status") or "Scheduled"
                    status2 = st.selectbox(
                        "Status", status_opts,
                        index=status_opts.index(cur_status)
                        if cur_status in status_opts else 0,
                        key=f"edit_ev_status_{eid}",
                    )

                    bc1, bc2 = st.columns([1, 1])
                    with bc1:
                        save_btn = st.form_submit_button(
                            "💾 Save Changes", type="primary",
                            use_container_width=True,
                        )
                    with bc2:
                        delete_btn = st.form_submit_button(
                            "🗑️ Delete Event",
                            use_container_width=True,
                        )

                    if save_btn:
                        if not (title2 and event_type2):
                            st.error("Title and Type are required.")
                        else:
                            updates = {
                                "title": title2,
                                "event_date": str(event_date2),
                                "end_date": (str(end_date2)
                                             if end_date2 and end_date2 != event_date2
                                             else None),
                                "event_type": event_type2,
                                "location": location2 or None,
                                "organizer": organizer2 or None,
                                "description": description2 or None,
                                "link": link2 or None,
                                "color": EVENT_COLORS.get(event_type2, "#6b7280"),
                                "status": status2,
                            }
                            if db_update("iro_events", e["id"], updates):
                                st.success(f"✅ Updated event: {title2}")
                                st.rerun()

                    if delete_btn:
                        try:
                            sb.table("iro_events").delete().eq(
                                "id", e["id"]).execute()
                            st.success(f"🗑️ Deleted: {e.get('title')}")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ Failed to delete: {ex}")

    # ----- Add new event (admin only) -----
    if _IS_ADMIN:
        with st.expander("➕ Add a New Event (Admin)"):
            with st.form("add_event_form", clear_on_submit=True):
                title = st.text_input("Event Title *", max_chars=200)
                c1, c2, c3 = st.columns(3)
                with c1:
                    event_date = st.date_input("Event Date *", value=date.today())
                with c2:
                    end_date = st.date_input("End Date (multi-day)", value=date.today())
                with c3:
                    event_type = st.selectbox(
                        "Type *",
                        ["", "Workshop", "Grant Deadline",
                         "Congress / Symposium", "Meeting", "Training",
                         "Conference", "Holiday", "Other"],
                    )

                c4, c5 = st.columns(2)
                with c4:
                    location = st.text_input("Location")
                with c5:
                    organizer = st.text_input("Organizer / Owner")

                description = st.text_area("Description", max_chars=500, height=80)
                link = st.text_input("Link / URL", placeholder="https://...")

                submitted = st.form_submit_button("Add Event", type="primary")

                if submitted:
                    if not (title and event_type):
                        st.error("Title and Type are required.")
                    else:
                        row = {
                            "title": title,
                            "event_date": str(event_date),
                            "end_date": (str(end_date)
                                         if end_date and end_date != event_date else None),
                            "event_type": event_type,
                            "location": location or None,
                            "organizer": organizer or None,
                            "description": description or None,
                            "link": link or None,
                            "color": EVENT_COLORS.get(event_type, "#6b7280"),
                            "created_by": _USER.get("email"),
                        }
                        try:
                            sb.table("iro_events").insert(row).execute()
                            st.success(f"✅ Added event: {title}")
                        except Exception as e:
                            st.error(f"❌ Failed: {e}")


elif page == "Scopus Publications (view)":
    st.markdown('<div class="section-heading">Scopus Publications Log</div>', unsafe_allow_html=True)

    pubs = db_select("scopus_publications", order_col="year", desc=True)
    if pubs:
        df = pd.DataFrame(pubs)

        # Last updated timestamp (most recent edit, falling back to insert)
        timestamps = []
        for col in ("updated_at", "created_at"):
            if col in df.columns:
                timestamps.extend(
                    pd.to_datetime(df[col], errors="coerce")
                    .dropna().tolist()
                )
        if timestamps:
            last_ts = max(timestamps)
            st.caption(
                f"🕒 Last updated: {last_ts.strftime('%d %b %Y, %H:%M')}"
            )

        # ----- H-index calculation -----
        h_index = 0
        if "citation_count" in df.columns:
            citations = (df["citation_count"].fillna(0).astype(int)
                         .sort_values(ascending=False).tolist())
            for i, c in enumerate(citations):
                if c >= i + 1:
                    h_index = i + 1
                else:
                    break

        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Publications", len(df))
        col2.metric("Q1 Articles",
                    int((df["quartile"] == "Q1").sum()) if "quartile" in df else 0)
        col3.metric("Open Access",
                    int(df["open_access"].sum()) if "open_access" in df else 0)
        col4.metric("Total Citations",
                    int(df["citation_count"].sum()) if "citation_count" in df else 0)
        col5.metric("H-index", h_index)

        # ---------- Shared chart styling ----------
        def _style(fig, *, title=None, show_legend=True):
            fig.update_layout(
                template="plotly_white",
                title=dict(text=title, font=dict(size=15, color="#000000"),
                           x=0.0, xanchor="left") if title else None,
                font=dict(family="Inter, -apple-system, system-ui, sans-serif",
                          color="#000000"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=46 if title else 12, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1.0,
                            font=dict(size=11, color="#000000"),
                            bgcolor="rgba(0,0,0,0)") if show_legend else None,
                xaxis=dict(showgrid=False, zeroline=False,
                           linecolor="#cbd5e1",
                           tickfont=dict(size=11, color="#000000")),
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                           linecolor="#cbd5e1",
                           tickfont=dict(size=11, color="#000000")),
            )
            return fig

        # ---------- 1. Publications by Year and Quartile ----------
        if "year" in df.columns and "quartile" in df.columns:
            chart_df = df.groupby(["year", "quartile"]).size().reset_index(name="count")
            fig = px.bar(chart_df, x="year", y="count", color="quartile",
                         color_discrete_map=QUARTILE_COLORS,
                         category_orders={"quartile": ["Q1", "Q2", "Q3", "Q4", "NA"]},
                         barmode="stack", height=340)
            _style(fig, title="📈 Publications by Year and Quartile")
            fig.update_layout(bargap=0.55)
            st.plotly_chart(fig, use_container_width=True)

        # ---------- 2. Publications by College — Year on Year ----------
        if "college" in df.columns and "year" in df.columns:
            college_year_df = (df.assign(
                                   college=df["college"].fillna("Unassigned").replace("", "Unassigned"))
                               .groupby(["year", "college"]).size()
                               .reset_index(name="count"))
            # Order colleges by overall total so the busiest lead the legend.
            college_order = (college_year_df.groupby("college")["count"].sum()
                             .sort_values(ascending=False).index.tolist())
            college_year_df = college_year_df.sort_values("year")
            fig_c = px.bar(
                college_year_df, x="year", y="count", color="college",
                color_discrete_sequence=CATEGORICAL_COLORS,
                category_orders={"college": college_order},
                barmode="group", height=380,
            )
            _style(fig_c, title="🏛️ Publications by College — Year on Year")
            fig_c.update_layout(bargap=0.3, bargroupgap=0.06,
                                xaxis_title=None, yaxis_title="Publications")
            fig_c.update_xaxes(type="category")  # years as discrete categories
            st.plotly_chart(fig_c, use_container_width=True)

        # ---------- 3. Citation Impact Over Years (line + markers) ----------
        if {"year", "citation_count"}.issubset(df.columns):
            cite_df = (df.assign(citation_count=df["citation_count"].fillna(0))
                       .groupby("year").agg(
                           citations=("citation_count", "sum"),
                           pubs=("citation_count", "count")).reset_index())
            cite_df["avg_per_paper"] = (cite_df["citations"] /
                                        cite_df["pubs"]).round(1)
            cite_df = cite_df.sort_values("year")

            cite_col, type_col = st.columns(2)

            with cite_col:
                fig_cite = px.line(cite_df, x="year", y="citations",
                                   markers=True, height=320,
                                   line_shape="spline")
                fig_cite.update_traces(line=dict(color=BRAND["plum"], width=3),
                                       marker=dict(size=10, color=BRAND["plum"],
                                                   line=dict(color="white",
                                                             width=2)),
                                       hovertemplate=(
                                           "<b>%{x}</b><br>"
                                           "Citations: %{y}<br>"
                                           "Pubs: %{customdata[0]}<br>"
                                           "Avg/paper: %{customdata[1]}"
                                           "<extra></extra>"),
                                       customdata=cite_df[["pubs",
                                                           "avg_per_paper"]])
                _style(fig_cite, title="📊 Citation Impact by Year",
                       show_legend=False)
                fig_cite.update_layout(yaxis_title="Total citations")
                st.plotly_chart(fig_cite, use_container_width=True)

            # ---------- 4. Publication Type donut ----------
            with type_col:
                if "publication_type" in df.columns:
                    type_df = (df.assign(
                                   publication_type=df["publication_type"]
                                       .fillna("Unspecified")
                                       .replace("", "Unspecified"))
                               .groupby("publication_type").size()
                               .reset_index(name="count")
                               .sort_values("count", ascending=False))
                    fig_pt = px.pie(type_df, names="publication_type",
                                    values="count", hole=0.55, height=320,
                                    color_discrete_sequence=BRAND_CHART_COLORS)
                    fig_pt.update_traces(textinfo="percent+label",
                                         textposition="outside",
                                         marker=dict(line=dict(color="white",
                                                               width=2)))
                    _style(fig_pt, title="📚 Publication Type Mix",
                           show_legend=False)
                    fig_pt.update_layout(
                        annotations=[dict(text=f"<b>{len(df)}</b><br>"
                                          "<span style='font-size:11px;color:#6b7280;'>"
                                          "publications</span>",
                                          x=0.5, y=0.5, showarrow=False,
                                          font=dict(size=24, color=NAVY))])
                    st.plotly_chart(fig_pt, use_container_width=True)

        # ---------- 5. Top Journals + Open Access split ----------
        if "journal" in df.columns:
            top_col, oa_col = st.columns([2, 1])

            with top_col:
                jr_df = (df.assign(journal=df["journal"].fillna("Unknown")
                                   .replace("", "Unknown"))
                         .groupby("journal").size().reset_index(name="count")
                         .nlargest(10, "count")
                         .sort_values("count", ascending=True))
                if not jr_df.empty:
                    fig_jr = px.bar(jr_df, x="count", y="journal",
                                    orientation="h", height=380,
                                    color_discrete_sequence=[BRAND["slate"]])
                    fig_jr.update_traces(marker=dict(line=dict(color="white",
                                                               width=0.5)))
                    _style(fig_jr, title="🏅 Top 10 Journals",
                           show_legend=False)
                    fig_jr.update_layout(bargap=0.4,
                                          xaxis_title="Publications",
                                          yaxis_title=None)
                    st.plotly_chart(fig_jr, use_container_width=True)

            with oa_col:
                if "open_access" in df.columns:
                    oa_count = int(df["open_access"].fillna(False).astype(bool).sum())
                    closed = len(df) - oa_count
                    fig_oa = px.pie(
                        names=["Open Access", "Subscription"],
                        values=[oa_count, closed],
                        hole=0.7, height=380,
                        color_discrete_sequence=[BRAND["sage"], BRAND["slate"]])
                    fig_oa.update_traces(textinfo="percent",
                                         textposition="outside",
                                         marker=dict(line=dict(color="white",
                                                               width=2)))
                    _style(fig_oa, title="🔓 Open Access Share",
                           show_legend=True)
                    pct = (oa_count / len(df) * 100) if len(df) else 0
                    fig_oa.update_layout(
                        annotations=[dict(
                            text=f"<b>{pct:.0f}%</b><br>"
                                 "<span style='font-size:11px;color:#6b7280;'>"
                                 "open</span>",
                            x=0.5, y=0.5, showarrow=False,
                            font=dict(size=26, color=NAVY))])
                    st.plotly_chart(fig_oa, use_container_width=True)

        # Filter controls
        st.markdown("**Filters**")
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            year_filter = st.multiselect("Year",
                                         sorted(df["year"].unique().tolist(), reverse=True) if "year" in df else [],
                                         default=[])
        with fcol2:
            college_filter = st.multiselect("College",
                                            sorted(df["college"].unique().tolist()) if "college" in df else [],
                                            default=[])
        with fcol3:
            quartile_filter = st.multiselect("Quartile",
                                             ["Q1", "Q2", "Q3", "Q4"],
                                             default=[])

        # Apply filters
        filtered = df.copy()
        if year_filter:
            filtered = filtered[filtered["year"].isin(year_filter)]
        if college_filter:
            filtered = filtered[filtered["college"].isin(college_filter)]
        if quartile_filter:
            filtered = filtered[filtered["quartile"].isin(quartile_filter)]

        st.markdown(f"**Showing {len(filtered)} of {len(df)} publications**")
        display_cols = [c for c in
                        ["year", "title", "lead_author", "authors", "journal",
                         "quartile", "publication_type", "college", "doi",
                         "open_access", "citation_count", "updated_by",
                         "updated_at"]
                        if c in filtered.columns]

        # Admins get a temporary inline-edit option: type directly in the
        # table and click Save to write the changes back to the database.
        inline_edit = _IS_ADMIN and st.toggle(
            "✏️ Edit inline (admin) — type directly in the table, then Save",
            value=False, key="scopus_inline_edit",
        )

        if inline_edit:
            edit_cols = [c for c in (["id"] + display_cols)
                         if c in filtered.columns
                         and c not in ("updated_by", "updated_at")]
            editable = filtered[edit_cols].copy()
            edited = st.data_editor(
                editable,
                hide_index=True, use_container_width=True,
                num_rows="fixed", disabled=["id"],
                column_config={
                    "id": st.column_config.NumberColumn(
                        "ID", help="Row id (read-only)"),
                    "year": st.column_config.NumberColumn("Year", format="%d"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "lead_author": st.column_config.TextColumn("Lead Author"),
                    "authors": st.column_config.TextColumn(
                        "Co-Authors", width="large"),
                    "journal": st.column_config.TextColumn(
                        "Journal", width="medium"),
                    "quartile": st.column_config.SelectboxColumn(
                        "Quartile", options=["Q1", "Q2", "Q3", "Q4", "NA"]),
                    "open_access": st.column_config.CheckboxColumn("Open Access"),
                    "citation_count": st.column_config.NumberColumn(
                        "Citations", format="%d"),
                },
                key="scopus_editor",
            )
            st.caption(
                "Editing the rows currently shown. Adding/removing rows is done "
                "on the **Manage Scopus Publications** page."
            )
            if st.button("💾 Save changes", type="primary",
                         key="scopus_save_inline"):
                orig = editable.set_index("id")
                new = edited.set_index("id")
                changed = 0
                for rid in new.index:
                    if rid not in orig.index:
                        continue
                    updates = {}
                    for c in new.columns:
                        ov, nv = orig.at[rid, c], new.at[rid, c]
                        if pd.isna(ov) and pd.isna(nv):
                            continue
                        if ov != nv:
                            updates[c] = (None if pd.isna(nv)
                                          else (nv.item() if hasattr(nv, "item")
                                                else nv))
                    if updates:
                        updates["updated_by"] = _USER.get("email", "admin")
                        updates["updated_at"] = datetime.now().isoformat()
                        if db_update("scopus_publications", int(rid), updates):
                            changed += 1
                if changed:
                    st.success(f"✅ Updated {changed} publication(s).")
                    st.rerun()
                else:
                    st.info("No changes detected.")
        else:
            st.dataframe(
                filtered[display_cols] if display_cols else filtered,
                hide_index=True, use_container_width=True,
                column_config={
                    "lead_author": st.column_config.TextColumn("Lead Author"),
                    "authors":     st.column_config.TextColumn(
                        "Co-Authors",
                        help="Full author list as recorded on the paper",
                        width="large"),
                    "title":       st.column_config.TextColumn(
                        "Title", width="large"),
                    "journal":     st.column_config.TextColumn(
                        "Journal", width="medium"),
                },
            )
    else:
        st.info("No publications logged yet. Use the **Submit Scopus Data** page to add some.")


# ============================================================
# PAGE: SUBMIT SCOPUS DATA
# ============================================================
elif page == "Manage Scopus Publications":
    require_roles("Manage Scopus Publications", ["admin", "standard"])
    st.markdown('<div class="section-heading">Manage Scopus Publications</div>',
                unsafe_allow_html=True)
    scopus_action = st.radio(
        "Action",
        ["➕ Add New Publication", "✏️ Edit Existing Publication"],
        horizontal=True, label_visibility="collapsed",
    )
    if scopus_action == "➕ Add New Publication":
        st.caption(
            "Use this form to log a newly published Scopus-indexed article. "
            "Faculty and students can submit; the Research Office will verify each entry."
        )

        with st.form("scopus_form", clear_on_submit=True):
            title = st.text_input("Article Title *", max_chars=300,
                                  placeholder="e.g., Temporal trends in antimicrobial susceptibility...")

            c1, c2 = st.columns(2)
            with c1:
                lead_author = st.text_input("Lead Author (Surname A.B.) *",
                                            placeholder="Ng C.M.M.")
                college = st.selectbox("College / Department *",
                                       ["", "Medicine", "Nursing", "Med Tech", "Pharmacy",
                                        "Dentistry", "Optometry", "Physical Therapy",
                                        "Arts & Sciences", "Education",
                                        "Business and Management", "Others"])
                year = st.number_input("Year of Publication *",
                                       min_value=2015, max_value=2030, value=2025)
                pub_type = st.selectbox("Publication Type *",
                                        ["", "Article", "Review", "Conference Paper",
                                         "Book Chapter", "Editorial", "Letter", "Note",
                                         "Short Survey", "Case Report"])
            with c2:
                authors = st.text_area("Full Author List *",
                                       placeholder="Surname A.B., Surname C.D., Surname E.F.",
                                       max_chars=1000, height=80)
                journal = st.text_input("Journal Name *",
                                        placeholder="e.g., Pathogens")
                quartile = st.selectbox("Scopus Quartile *",
                                        ["", "Q1", "Q2", "Q3", "Q4"])
                open_access = st.checkbox("Open Access publication")

            c3, c4, c5 = st.columns(3)
            with c3:
                volume = st.text_input("Volume", placeholder="e.g., 12")
            with c4:
                issue = st.text_input("Issue", placeholder="e.g., 3")
            with c5:
                pages = st.text_input("Pages", placeholder="e.g., 245–258")

            doi = st.text_input("DOI",
                                placeholder="e.g., 10.3390/pathogens12030245")
            scopus_link = st.text_input("Scopus Link (optional)",
                                        placeholder="https://www.scopus.com/record/display.uri?eid=...")

            citation_count = st.number_input("Current Citation Count (optional)",
                                             min_value=0, value=0)

            c6, c7 = st.columns(2)
            with c6:
                funding = st.text_input("Funding Source",
                                        placeholder="e.g., DOST-PCHRD, MCU In-house grant")
            with c7:
                acknowledgment = st.text_input("MCU Acknowledged?",
                                               placeholder="e.g., Yes, in funding statement")

            submitted = st.form_submit_button("Submit Publication", type="primary")

            if submitted:
                if not all([title, lead_author, authors, journal, college,
                            quartile, pub_type, year]):
                    st.error("Please fill in all required fields (marked with *).")
                else:
                    row = {
                        "title": title,
                        "authors": authors,
                        "lead_author": lead_author,
                        "year": int(year),
                        "journal": journal,
                        "volume": volume or None,
                        "issue": issue or None,
                        "pages": pages or None,
                        "doi": doi or None,
                        "scopus_link": scopus_link or None,
                        "quartile": quartile,
                        "publication_type": pub_type,
                        "college": college,
                        "open_access": open_access,
                        "citation_count": int(citation_count),
                        "funding_source": funding or None,
                        "acknowledgment": acknowledgment or None,
                    }
                    if db_insert("scopus_publications", row):
                        st.success(f"✅ Publication **\"{title[:60]}...\"** logged successfully.")
                        st.balloons()


    if scopus_action == "✏️ Edit Existing Publication":
        st.caption(
            "Search for an existing publication, update its fields, and the change is "
            "recorded with your name + timestamp + a full audit log entry."
        )

        pubs = db_select("scopus_publications", order_col="year", desc=True)
        if not pubs:
            st.info("No publications in the database yet. Use **Submit Scopus Data** to add one first.")
        else:
            # Search/select publication
            st.markdown("**Step 1 — Pick the publication to edit**")
            search = st.text_input("Search by title or lead author",
                                   placeholder="Type a few words to filter…")
            filtered_pubs = pubs
            if search:
                s = search.lower()
                filtered_pubs = [p for p in pubs
                                 if s in (p.get("title") or "").lower()
                                 or s in (p.get("lead_author") or "").lower()]

            if not filtered_pubs:
                st.warning("No publications match your search.")
            else:
                options = {
                    f"[{p.get('year')}] {p.get('lead_author', '?')} — "
                    f"{(p.get('title') or '')[:80]}": p
                    for p in filtered_pubs
                }
                pick = st.selectbox("Publication", list(options.keys()))
                current = options[pick]

                # Show audit info (if any)
                if current.get("updated_at"):
                    st.info(
                        f"📝 Last updated by **{current.get('updated_by', 'unknown')}** on "
                        f"**{current.get('updated_at')[:19].replace('T', ' ')}**"
                        + (f" — _\"{current.get('update_note')}\"_"
                           if current.get("update_note") else "")
                    )
                else:
                    st.caption(f"First created on {current.get('submitted_at', '?')[:19].replace('T', ' ')}. No edits yet.")

                # Show audit log
                audit_log = []
                try:
                    if sb is not None:
                        audit_res = sb.table("scopus_audit_log").select("*") \
                                      .eq("publication_id", current["id"]) \
                                      .order("changed_at", desc=True).execute()
                        audit_log = audit_res.data or []
                except Exception:
                    pass

                if audit_log:
                    with st.expander(f"📜 Full edit history ({len(audit_log)} previous edits)"):
                        for entry in audit_log:
                            st.markdown(f"**{entry['changed_at'][:19].replace('T', ' ')}** "
                                        f"by *{entry['changed_by']}*")
                            if entry.get("change_note"):
                                st.caption(f"_Note:_ {entry['change_note']}")
                            if entry.get("changed_fields"):
                                for field, change in entry["changed_fields"].items():
                                    st.text(f"  • {field}: {change.get('old')} → {change.get('new')}")
                            st.divider()

                # Edit form
                st.markdown("**Step 2 — Edit the fields**")
                with st.form("edit_form", clear_on_submit=False):
                    title = st.text_input("Article Title *", value=current.get("title") or "",
                                          max_chars=300)
                    c1, c2 = st.columns(2)
                    with c1:
                        lead_author = st.text_input("Lead Author *",
                                                    value=current.get("lead_author") or "")
                        college_opts = ["Medicine", "Nursing", "Med Tech", "Pharmacy",
                                        "Dentistry", "Optometry", "Physical Therapy",
                                        "Arts & Sciences", "Education",
                                        "Business and Management", "Others"]
                        current_col = current.get("college") or "Medicine"
                        college = st.selectbox("College / Department *", college_opts,
                                               index=college_opts.index(current_col)
                                               if current_col in college_opts else 0)
                        year = st.number_input("Year *", min_value=2015, max_value=2030,
                                               value=int(current.get("year") or 2025))
                        pt_opts = ["Article", "Review", "Conference Paper", "Book Chapter",
                                   "Editorial", "Letter", "Note", "Short Survey", "Case Report"]
                        current_pt = current.get("publication_type") or "Article"
                        pub_type = st.selectbox("Publication Type *", pt_opts,
                                                index=pt_opts.index(current_pt)
                                                if current_pt in pt_opts else 0)
                    with c2:
                        authors = st.text_area("Full Author List *",
                                               value=current.get("authors") or "",
                                               max_chars=1000, height=80)
                        journal = st.text_input("Journal *", value=current.get("journal") or "")
                        q_opts = ["Q1", "Q2", "Q3", "Q4"]
                        current_q = current.get("quartile") or "Q1"
                        quartile = st.selectbox("Quartile *", q_opts,
                                                index=q_opts.index(current_q)
                                                if current_q in q_opts else 0)
                        open_access = st.checkbox("Open Access",
                                                  value=bool(current.get("open_access")))

                    c3, c4, c5 = st.columns(3)
                    with c3:
                        volume = st.text_input("Volume", value=current.get("volume") or "")
                    with c4:
                        issue = st.text_input("Issue", value=current.get("issue") or "")
                    with c5:
                        pages = st.text_input("Pages", value=current.get("pages") or "")

                    doi = st.text_input("DOI", value=current.get("doi") or "")
                    scopus_link = st.text_input("Scopus Link",
                                                value=current.get("scopus_link") or "")
                    citation_count = st.number_input("Citation Count", min_value=0,
                                                     value=int(current.get("citation_count") or 0))

                    c6, c7 = st.columns(2)
                    with c6:
                        funding = st.text_input("Funding Source",
                                                value=current.get("funding_source") or "")
                    with c7:
                        acknowledgment = st.text_input("MCU Acknowledged?",
                                                       value=current.get("acknowledgment") or "")

                    st.markdown("---")
                    st.markdown("**Step 3 — Identify yourself + describe the change**")
                    ac1, ac2 = st.columns([1, 2])
                    with ac1:
                        updated_by = st.text_input("Your Name *",
                                                   placeholder="e.g., Dr. Charmaine Ng")
                    with ac2:
                        update_note = st.text_input("What changed and why? *",
                                                    placeholder="e.g., Quartile updated to Q1 after Scopus reclassification")

                    save = st.form_submit_button("💾 Save Changes", type="primary")

                    if save:
                        if not updated_by.strip() or not update_note.strip():
                            st.error("Please fill in your name AND a brief description of the change.")
                        elif not all([title, lead_author, authors, journal, college,
                                      quartile, pub_type, year]):
                            st.error("All starred fields are required.")
                        else:
                            # Build proposed update
                            new_values = {
                                "title": title, "lead_author": lead_author,
                                "authors": authors, "year": int(year),
                                "journal": journal, "volume": volume or None,
                                "issue": issue or None, "pages": pages or None,
                                "doi": doi or None, "scopus_link": scopus_link or None,
                                "quartile": quartile, "publication_type": pub_type,
                                "college": college, "open_access": open_access,
                                "citation_count": int(citation_count),
                                "funding_source": funding or None,
                                "acknowledgment": acknowledgment or None,
                            }
                            tracked_fields = list(new_values.keys())
                            diff = diff_dict(current, new_values, tracked_fields)

                            if not diff:
                                st.warning("No fields actually changed. Nothing to save.")
                            else:
                                # Add audit fields
                                new_values["updated_by"] = updated_by.strip()
                                new_values["updated_at"] = datetime.now().isoformat()
                                new_values["update_note"] = update_note.strip()

                                # 1. Update the main row
                                ok = db_update("scopus_publications", current["id"], new_values)
                                # 2. Insert audit log entry
                                if ok:
                                    try:
                                        sb.table("scopus_audit_log").insert({
                                            "publication_id": current["id"],
                                            "changed_by": updated_by.strip(),
                                            "change_note": update_note.strip(),
                                            "changed_fields": diff,
                                        }).execute()
                                    except Exception as e:
                                        st.warning(f"Update saved, but audit log failed: {e}")

                                    st.success(
                                        f"✅ Updated {len(diff)} field(s) — recorded as "
                                        f"changed by **{updated_by}** at "
                                        f"**{datetime.now().strftime('%b %d, %Y · %H:%M')}**."
                                    )
                                    with st.expander("View what changed"):
                                        for f, c in diff.items():
                                            st.text(f"• {f}: {c['old']} → {c['new']}")

                # ----- Remove (delete) this publication -----
                st.divider()
                with st.expander("🗑️ Remove this publication"):
                    st.warning(
                        "This permanently deletes the article and its edit "
                        "history. It cannot be undone.")
                    st.caption(
                        f"**[{current.get('year')}] "
                        f"{current.get('lead_author', '?')} — "
                        f"{(current.get('title') or '')[:80]}**")
                    confirm_del = st.checkbox(
                        "Yes, permanently delete this publication",
                        key=f"scopus_del_confirm_{current['id']}")
                    if st.button("🗑️ Delete publication", type="primary",
                                 disabled=not confirm_del,
                                 key=f"scopus_del_btn_{current['id']}"):
                        try:
                            if sb is not None:
                                # Remove audit rows first (in case the FK isn't
                                # set to cascade), then the publication itself.
                                try:
                                    sb.table("scopus_audit_log").delete() \
                                        .eq("publication_id", current["id"]).execute()
                                except Exception:
                                    pass
                                sb.table("scopus_publications").delete() \
                                    .eq("id", current["id"]).execute()
                            st.success("✅ Publication deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Could not delete: {e}")


# ============================================================
# PAGE: IN-HOUSE GRANTS (VIEW)
# ============================================================
elif page == "In-House Grants (view)":
    st.markdown('<div class="section-heading">In-House Grants Awarded AY2026</div>', unsafe_allow_html=True)

    grants_all = db_select("grant_projects", order_col="budget")
    n = len(grants_all)
    total = sum(float(g.get("budget") or 0) for g in grants_all)
    avg = total / n if n else 0
    avg_duration = (sum(int(g.get("duration") or 0) for g in grants_all) / n) if n else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Grants Awarded", n)
    col2.metric("Total Budget", f"₱{total:,.0f}")
    col3.metric("Avg per Grant", f"₱{avg:,.0f}")
    col4.metric("Avg Duration", f"{avg_duration:.1f} mo")

    # ----- Lifecycle status panel -----
    st.markdown("**Lifecycle Status**")

    # Pull DB counts where applicable; the rest are placeholders for now
    db_status = {}
    for g in grants_all:
        s = g.get("status") or "Unknown"
        db_status[s] = db_status.get(s, 0) + 1

    # Boxes to display (in lifecycle order) — muted brand palette
    status_boxes = [
        ("Submitted",          db_status.get("Submitted", 0),          BRAND["slate"]),
        ("Approved",           6,                                       BRAND["moss"]),
        ("In Progress",        6,                                       BRAND["amber"]),
        ("Mid Project Report", db_status.get("Mid Project Report", 0), BRAND["tan"]),
        ("Final Report",       db_status.get("Final Report", 0),       BRAND["plum"]),
        ("Completed",          db_status.get("Completed", 0),          BRAND["sage"]),
    ]
    cols = st.columns(len(status_boxes))
    for col, (label, count, color) in zip(cols, status_boxes):
        col.markdown(
            f'<div style="background:{color};color:white;padding:14px;border-radius:8px;'
            f'text-align:center;min-height:90px;">'
            f'<div style="font-size:26px;font-weight:700;">{count}</div>'
            f'<div style="font-size:11px;opacity:0.95;margin-top:4px;">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("")

    st.markdown("**Recent Project Submissions**")
    projects = db_select("grant_projects")
    if projects:
        df = pd.DataFrame(projects)
        display_cols = [c for c in
                        ["project_id", "title", "pi", "college", "track",
                         "budget", "duration", "submitted_at", "status"] if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df,
                     hide_index=True, use_container_width=True)
    else:
        st.info("No grant projects submitted yet.")

    st.markdown("**Recent Budget Entries**")
    entries = db_select("budget_entries", order_col="date")
    if entries:
        df = pd.DataFrame(entries)
        display_cols = [c for c in
                        ["grant_id", "date", "category", "amount",
                         "payee", "voucher"] if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df,
                     hide_index=True, use_container_width=True)
    else:
        st.info("No budget entries logged yet.")


# ============================================================
# PAGE: CAPACITY-BUILDING WORKSHOPS (VIEW)
# ============================================================
elif page == "Capacity-Building Workshops":
    st.markdown('<div class="section-heading">Capacity-Building Workshops</div>',
                unsafe_allow_html=True)

    workshops = db_select("capacity_workshops", order_col="start_date", desc=True)

    if not workshops:
        st.info("No workshops in the database yet. Run `python3 import_workshops.py` "
                "or use the **➕ Log Workshop** page.")
    else:
        # Summary metrics
        total = len(workshops)
        completed = sum(1 for w in workshops if w.get("status") == "Completed")
        upcoming = sum(1 for w in workshops if w.get("status") == "Upcoming")
        attendees = sum(int(w.get("attendees") or 0) for w in workshops)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Workshops", total)
        c2.metric("Completed", completed)
        c3.metric("Upcoming", upcoming)
        c4.metric("Total Attendees", attendees or "TBD")

        # Workshop log
        df = pd.DataFrame(workshops)

        # Compute Academic Year column (Philippine AY: June–May cycle)
        def to_ay(date_str):
            try:
                y, m, _d = str(date_str).split("-")
                y, m = int(y), int(m)
                # June onwards → next AY starts (e.g., June 2025 → AY 2025–2026 → "AY2026")
                if m >= 6:
                    return f"AY{y + 1}"
                else:
                    return f"AY{y}"
            except Exception:
                return ""
        if "start_date" in df.columns:
            df.insert(0, "AY", df["start_date"].apply(to_ay))

        st.markdown("**Workshop Log**")

        # Build a custom HTML table so text wraps to multiple lines cleanly
        def safe(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            return str(v).replace("<", "&lt;").replace(">", "&gt;")

        def date_label(s, e):
            s = safe(s); e = safe(e)
            if e and e != s and e != "None":
                return f"{s} – {e}"
            return s

        def feedback_cell(materials):
            """A 'View' link to the uploaded feedback document, or ''."""
            if materials is None or (isinstance(materials, float)
                                     and pd.isna(materials)):
                return ""
            path = str(materials).strip()
            if not path:
                return ""
            url = ""
            if path.startswith("http"):
                url = path
            elif sb is not None:
                try:
                    res = sb.storage.from_("grant-reports").create_signed_url(
                        path, 3600)
                    url = res.get("signedURL") or res.get("signed_url") or ""
                except Exception:
                    url = ""
            if not url:
                return ""
            return (f'<a href="{url}" target="_blank" '
                    f'style="color:{PURPLE};text-decoration:none;'
                    f'font-weight:600;">📄 View</a>')

        # Column widths (percent of table width)
        col_widths = [
            ("AY", 5),
            ("Date", 10),
            ("Title", 22),
            ("Speakers", 20),
            ("Type", 11),
            ("Status", 8),
            ("Attendance", 7),
            ("Feedback /5", 7),
            ("Feedback Doc", 10),
        ]

        thead = "".join(
            f'<th style="width:{w}%;text-align:left;padding:8px 10px;font-size:10px;'
            f'color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;'
            f'font-weight:600;border-bottom:1px solid #e5e7eb;background:#f9fafb;">'
            f'{h}</th>'
            for h, w in col_widths
        )

        body_rows = ""
        for _, r in df.iterrows():
            body_rows += (
                '<tr>'
                f'<td style="padding:10px;font-size:11px;color:#374151;border-bottom:1px solid #f3f4f6;vertical-align:top;white-space:nowrap;font-weight:600;">{safe(r.get("AY"))}</td>'
                f'<td style="padding:10px;font-size:11px;color:#374151;border-bottom:1px solid #f3f4f6;vertical-align:top;white-space:nowrap;">{date_label(r.get("start_date"), r.get("end_date"))}</td>'
                f'<td style="padding:10px;font-size:12px;color:{NAVY};border-bottom:1px solid #f3f4f6;vertical-align:top;line-height:1.35;font-weight:500;word-break:break-word;">{safe(r.get("title"))}</td>'
                f'<td style="padding:10px;font-size:11px;color:#374151;border-bottom:1px solid #f3f4f6;vertical-align:top;line-height:1.35;word-break:break-word;">{safe(r.get("speakers"))}</td>'
                f'<td style="padding:10px;font-size:11px;color:#6b7280;border-bottom:1px solid #f3f4f6;vertical-align:top;line-height:1.35;word-break:break-word;">{safe(r.get("workshop_type"))}</td>'
                f'<td style="padding:10px;font-size:11px;color:#6b7280;border-bottom:1px solid #f3f4f6;vertical-align:top;white-space:nowrap;">{safe(r.get("status"))}</td>'
                f'<td style="padding:10px;font-size:11px;color:#374151;border-bottom:1px solid #f3f4f6;vertical-align:top;text-align:right;">{safe(r.get("attendees"))}</td>'
                f'<td style="padding:10px;font-size:11px;color:#374151;border-bottom:1px solid #f3f4f6;vertical-align:top;text-align:right;">{safe(r.get("feedback_score"))}</td>'
                f'<td style="padding:10px;font-size:11px;border-bottom:1px solid #f3f4f6;vertical-align:top;text-align:center;">{feedback_cell(r.get("materials"))}</td>'
                '</tr>'
            )

        table_html = (
            '<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
            'box-shadow:0 1px 2px rgba(0,0,0,0.03);overflow:hidden;">'
            '<table style="width:100%;border-collapse:collapse;table-layout:fixed;">'
            f'<thead><tr>{thead}</tr></thead>'
            f'<tbody>{body_rows}</tbody>'
            '</table></div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)


# ============================================================
# PAGE: SCHOLARLY ENGAGEMENTS (view)
# ============================================================
elif page == "Scholarly Engagements":
    st.markdown('<div class="section-heading">Scholarly Engagements</div>',
                unsafe_allow_html=True)
    st.caption(
        "External conferences, congresses, workshops and webinars that MCU "
        "faculty &amp; staff have attended or presented at."
    )

    refresh_c, _ = st.columns([1, 8])
    with refresh_c:
        if st.button("🔄 Refresh", key="rea_view_refresh"):
            st.rerun()

    # Quiet fetch — if either table is missing, don't spam red errors.
    def _quiet_select(table: str, order_col: str, desc: bool = True):
        if sb is None:
            return []
        try:
            res = sb.table(table).select("*").order(order_col, desc=desc).execute()
            return res.data or []
        except Exception:
            return []

    events = _quiet_select("research_events_attended",
                           order_col="start_date", desc=True)
    all_attendees = _quiet_select("research_event_attendees",
                                  order_col="id")

    if not events:
        st.info("No scholarly engagements logged yet. Use the "
                "**➕ Submit Scholarly Engagement** page to add one.")
    else:
        df = pd.DataFrame(events)
        att_df = pd.DataFrame(all_attendees) if all_attendees else pd.DataFrame(
            columns=["event_id", "attendee_name", "attendee_college",
                     "role", "presentation_title"]
        )

        # Last updated stamp
        timestamps = []
        for col in ("updated_at", "created_at"):
            if col in df.columns:
                timestamps.extend(
                    pd.to_datetime(df[col], errors="coerce")
                    .dropna().tolist()
                )
        if timestamps:
            last_ts = max(timestamps)
            st.caption(
                f"🕒 Last updated: {last_ts.strftime('%d %b %Y, %H:%M')}"
            )

        # Summary metrics
        total = len(df)
        total_people = len(att_df)
        presenters = int(
            att_df["role"].fillna("").str.lower().isin(
                ["presenter", "keynote speaker", "keynote",
                 "panelist", "chair", "moderator"]
            ).sum()
        ) if "role" in att_df.columns else 0
        unique_people = (
            int(att_df["attendee_name"].dropna().nunique())
            if "attendee_name" in att_df.columns else 0
        )
        awards_count = (
            int(att_df["award"].fillna("").astype(str).str.strip().ne("").sum())
            if "award" in att_df.columns else 0
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Events", total)
        c2.metric("Participations", total_people)
        c3.metric("Presenters", presenters)
        c4.metric("Unique People", unique_people)
        c5.metric("🏆 Awards", awards_count)

        ev_filtered = df.copy()
        st.markdown(f"**Showing {len(ev_filtered)} events**")

        # ----- Build a styled HTML table (mirrors Workshops page) -----
        def safe(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            return str(v).replace("<", "&lt;").replace(">", "&gt;")

        def date_label(s, e):
            s = safe(s); e = safe(e)
            if e and e != s and e != "None":
                return f"{s} – {e}"
            return s

        # Per-event attendee HTML (name + role badge if presenting)
        PRESENTER_ROLES = {"presenter", "keynote", "keynote speaker",
                           "panelist", "chair", "moderator"}

        def fmt_attendees_html(eid):
            if "event_id" not in att_df.columns:
                return ""
            rows = att_df[att_df["event_id"] == eid]
            chunks = []
            for _, r in rows.iterrows():
                name = safe((r.get("attendee_name") or "").strip())
                if not name:
                    continue
                role = (r.get("role") or "").strip()
                pres = safe((r.get("presentation_title") or "").strip())
                award = safe((r.get("award") or "").strip())
                is_presenter = role.lower() in PRESENTER_ROLES
                role_badge = (
                    f'<span style="display:inline-block;padding:2px 7px;'
                    f'font-size:9px;font-weight:700;color:white;'
                    f'background:{PURPLE};border-radius:8px;'
                    f'margin:1px 0 1px 4px;line-height:1.3;'
                    f'text-transform:uppercase;letter-spacing:0.4px;'
                    f'vertical-align:middle;white-space:nowrap;">'
                    f'{safe(role)}</span>'
                    if is_presenter else ""
                )
                award_badge = (
                    f'<span style="display:inline-block;padding:2px 7px;'
                    f'font-size:9px;font-weight:700;color:#78350f;'
                    f'background:#fde68a;border:1px solid #f59e0b;'
                    f'border-radius:8px;margin:1px 0 1px 4px;'
                    f'line-height:1.3;vertical-align:middle;white-space:nowrap;'
                    f'text-transform:uppercase;letter-spacing:0.4px;">'
                    f'🏆 {award}</span>'
                    if award else ""
                )
                pres_html = (
                    f'<div style="font-size:10px;color:#6b7280;'
                    f'margin-top:3px;line-height:1.4;font-style:italic;'
                    f'word-break:break-word;">{pres}</div>'
                    if pres else ""
                )
                if is_presenter or award:
                    chunks.append(
                        f'<div style="margin-bottom:6px;line-height:1.6;'
                        f'word-break:break-word;">'
                        f'<span style="font-weight:600;color:{NAVY};'
                        f'vertical-align:middle;">{name}</span>'
                        f'{role_badge}{award_badge}{pres_html}</div>'
                    )
                else:
                    chunks.append(
                        f'<div style="margin-bottom:4px;color:#374151;'
                        f'line-height:1.45;word-break:break-word;">'
                        f'{name}</div>'
                    )
            return "".join(chunks) or '<span style="color:#9ca3af;">—</span>'

        def att_count(eid):
            if "event_id" not in att_df.columns:
                return 0
            return int((att_df["event_id"] == eid).sum())

        def fmt_awards_html(eid):
            if "event_id" not in att_df.columns or "award" not in att_df.columns:
                return '<span style="color:#9ca3af;">—</span>'
            rows = att_df[att_df["event_id"] == eid]
            chunks = []
            for _, r in rows.iterrows():
                award = safe((r.get("award") or "").strip())
                if not award:
                    continue
                name = safe((r.get("attendee_name") or "").strip())
                chunks.append(
                    f'<div style="margin-bottom:6px;line-height:1.5;">'
                    f'<span style="display:inline-block;padding:2px 8px;'
                    f'font-size:10px;font-weight:700;color:#78350f;'
                    f'background:#fde68a;border:1px solid #f59e0b;'
                    f'border-radius:8px;white-space:nowrap;'
                    f'line-height:1.4;">🏆 {award}</span>'
                    f'<div style="font-size:10px;color:#6b7280;'
                    f'margin-top:3px;line-height:1.4;word-break:break-word;">'
                    f'{name}</div></div>'
                )
            return "".join(chunks) or '<span style="color:#9ca3af;">—</span>'

        # Column widths
        col_widths = [
            ("Date", 10),
            ("Event Title", 20),
            ("Type", 9),
            ("Location", 11),
            ("Organizer", 11),
            ("#", 5),
            ("Attendees / Presenters", 22),
            ("🏆 Awards", 12),
        ]
        thead = "".join(
            f'<th style="width:{w}%;text-align:left;padding:10px;'
            f'font-size:10px;color:#6b7280;text-transform:uppercase;'
            f'letter-spacing:0.5px;font-weight:700;line-height:1.4;'
            f'border-bottom:1px solid #e5e7eb;background:#f9fafb;">{h}</th>'
            for h, w in col_widths
        )

        body_rows = ""
        for _, r in ev_filtered.iterrows():
            eid = r.get("id")
            n = att_count(eid)
            body_rows += (
                '<tr>'
                f'<td style="padding:12px 10px;font-size:11px;color:#374151;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.45;white-space:nowrap;">'
                f'{date_label(r.get("start_date"), r.get("end_date"))}</td>'
                f'<td style="padding:12px 10px;font-size:12px;color:{NAVY};'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.45;font-weight:600;word-break:break-word;">'
                f'{safe(r.get("event_title"))}</td>'
                f'<td style="padding:12px 10px;font-size:11px;color:#6b7280;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.45;word-break:break-word;">'
                f'{safe(r.get("event_type"))}</td>'
                f'<td style="padding:12px 10px;font-size:11px;color:#374151;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.45;word-break:break-word;">'
                f'{safe(r.get("location"))}</td>'
                f'<td style="padding:12px 10px;font-size:11px;color:#374151;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.45;word-break:break-word;">'
                f'{safe(r.get("organizer"))}</td>'
                f'<td style="padding:12px 10px;font-size:12px;color:#374151;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'text-align:right;font-weight:700;line-height:1.45;">{n}</td>'
                f'<td style="padding:12px 10px;font-size:11px;color:#374151;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.5;">{fmt_attendees_html(eid)}</td>'
                f'<td style="padding:12px 10px;font-size:11px;color:#374151;'
                f'border-bottom:1px solid #f3f4f6;vertical-align:top;'
                f'line-height:1.5;">{fmt_awards_html(eid)}</td>'
                '</tr>'
            )

        table_html = (
            '<div style="background:white;border:1px solid #e5e7eb;'
            'border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,0.03);'
            'overflow:hidden;">'
            '<table style="width:100%;border-collapse:collapse;'
            'table-layout:fixed;">'
            f'<thead><tr>{thead}</tr></thead>'
            f'<tbody>{body_rows}</tbody>'
            '</table></div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

        # Per-person breakdown
        with st.expander("👥 Per-person attendee list", expanded=False):
            if att_df.empty:
                st.info("No attendees logged yet.")
            else:
                merged = att_df.merge(
                    df[[c for c in ["id", "event_title", "start_date",
                                    "event_type"] if c in df.columns]],
                    left_on="event_id", right_on="id", how="left",
                    suffixes=("", "_event"),
                )
                show_cols = [c for c in
                             ["start_date", "event_title", "event_type",
                              "attendee_name", "attendee_college", "role",
                              "presentation_title", "award"]
                             if c in merged.columns]
                st.dataframe(merged[show_cols] if show_cols else merged,
                             hide_index=True, use_container_width=True)


# ============================================================
# PAGE: UPLOAD WORKSHOP FEEDBACK (ADMIN ONLY)
# ============================================================
elif page == "Manage Workshops":
    require_roles("Manage Workshops", ["admin", "standard"])
    st.markdown('<div class="section-heading">Manage Workshops</div>',
                unsafe_allow_html=True)
    workshop_action = st.radio(
        "Action",
        ["➕ Log New Workshop", "✏️ Edit Existing Workshop",
         "📥 Upload Feedback Form"],
        horizontal=True, label_visibility="collapsed",
    )
    if workshop_action == "📥 Upload Feedback Form":
        st.caption(
            "Drag and drop a feedback file for any workshop. "
            "Accepted formats: PDF, Word, Excel, CSV, image."
        )

        workshops_for_fb = db_select("capacity_workshops",
                                      order_col="start_date") if sb else []

        if not workshops_for_fb:
            st.info("No workshops in the database yet. Log a workshop first.")
        else:
            with st.form("workshop_feedback_form", clear_on_submit=True):
                ws_options = [""] + [
                    f"[{w.get('start_date')}] {w.get('title')[:80]}"
                    for w in workshops_for_fb
                ]
                picked = st.selectbox("Select workshop *", ws_options)

                uploader_name = st.text_input("Your Name *",
                                              placeholder="e.g., Dr. Charmaine Ng",
                                              value=_USER.get("name") or "")

                feedback_file = st.file_uploader(
                    "Drag & drop the feedback form here *",
                    type=["pdf", "docx", "doc", "xlsx", "xls", "csv", "png", "jpg", "jpeg"],
                    help="Single file, max 200 MB",
                )

                fcol1, fcol2 = st.columns(2)
                with fcol1:
                    avg_score = st.number_input(
                        "Average Feedback Score (out of 5, optional)",
                        min_value=0.0, max_value=5.0, value=0.0, step=0.05,
                    )
                with fcol2:
                    n_attendees = st.number_input(
                        "Number of Attendees (optional)",
                        min_value=0, value=0,
                    )

                cover_note = st.text_area(
                    "Cover Note (optional)",
                    placeholder="Any context — completion rate, key themes from comments, etc.",
                    max_chars=500, height=70,
                )

                submitted_fb = st.form_submit_button("📤 Upload Feedback", type="primary")

                if submitted_fb:
                    if not picked or not uploader_name or feedback_file is None:
                        st.error("Please select a workshop, enter your name, "
                                 "and attach a feedback file.")
                    else:
                        ws_start = picked[1:11]
                        matched = [w for w in workshops_for_fb
                                   if str(w.get("start_date")) == ws_start]
                        if not matched:
                            st.error("Couldn't locate that workshop in the database.")
                        else:
                            ws = matched[0]
                            fname = feedback_file.name
                            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                            storage_path = f"workshop-feedback/{ws['id']}/{ts}_{fname}"
                            file_bytes = feedback_file.getvalue()

                            upload_ok = False
                            if sb is not None:
                                try:
                                    sb.storage.from_("grant-reports").upload(
                                        storage_path, file_bytes,
                                        {"content-type": feedback_file.type
                                         or "application/octet-stream"},
                                    )
                                    upload_ok = True
                                except Exception as e:
                                    st.warning(
                                        f"Binary upload failed: {e}. Metadata still saved."
                                    )

                                updates = {
                                    "materials": storage_path,
                                    "updated_by": uploader_name,
                                    "updated_at": datetime.now().isoformat(),
                                }
                                if avg_score > 0:
                                    updates["feedback_score"] = float(avg_score)
                                if n_attendees > 0:
                                    updates["attendees"] = int(n_attendees)
                                if cover_note:
                                    updates["notes"] = cover_note

                                db_update("capacity_workshops", ws["id"], updates)

                            if upload_ok:
                                st.success(
                                    f"✅ Feedback uploaded for **{ws.get('title')[:60]}**."
                                )
                                st.balloons()
                            else:
                                st.info(
                                    f"📋 Feedback metadata logged for "
                                    f"**{ws.get('title')[:60]}**. "
                                    "Set up the `grant-reports` Storage bucket "
                                    "to enable file persistence."
                                )


    if workshop_action == "➕ Log New Workshop":
        st.caption("Log a new capacity-building workshop.")

        with st.form("workshop_form", clear_on_submit=True):
            title = st.text_input("Workshop Title *", max_chars=200)
            c1, c2 = st.columns(2)
            with c1:
                start = st.date_input("Start Date *", value=date.today())
                workshop_type = st.selectbox("Workshop Type *",
                                             ["", "Research Methods", "Publication",
                                              "Research Ethics", "Statistics",
                                              "IP & Commercialization", "Academic Writing",
                                              "Research Monitoring", "Congress / Symposium",
                                              "Other"])
                target = st.selectbox("Target Audience",
                                      ["", "Faculty", "Students", "Both"])
            with c2:
                end = st.date_input("End Date (if multi-day)", value=date.today())
                status = st.selectbox("Status",
                                      ["Planning", "Upcoming", "Completed", "Cancelled"])
                attendees = st.number_input("Number of Attendees", min_value=0, value=0)

            speakers = st.text_area("Speakers / Facilitators *",
                                    placeholder="Dr. Speaker Name (Affiliation); Dr. Another (Affiliation)",
                                    max_chars=500, height=70)

            c3, c4 = st.columns(2)
            with c3:
                materials = st.text_input("Materials (filename or link)")
            with c4:
                feedback = st.number_input("Feedback Score (out of 5)",
                                           min_value=0.0, max_value=5.0,
                                           value=0.0, step=0.05)

            notes = st.text_area("Notes (optional)", max_chars=500, height=70)

            submitted = st.form_submit_button("Log Workshop", type="primary")

            if submitted:
                if not (title and speakers and workshop_type):
                    st.error("Please fill in title, speakers, and workshop type.")
                else:
                    row = {
                        "title": title,
                        "start_date": str(start),
                        "end_date": str(end) if end != start else None,
                        "speakers": speakers,
                        "workshop_type": workshop_type,
                        "target_audience": target or None,
                        "attendees": int(attendees) if attendees else None,
                        "materials": materials or None,
                        "feedback_score": float(feedback) if feedback else None,
                        "status": status,
                        "notes": notes or None,
                    }
                    if db_insert("capacity_workshops", row):
                        st.success(f"✅ Workshop '{title}' logged.")
                        st.balloons()

    if workshop_action == "✏️ Edit Existing Workshop":
        st.caption(
            "Pick a workshop, update its fields, and the change is saved with "
            "your name + timestamp."
        )

        workshops_for_edit = db_select("capacity_workshops",
                                       order_col="start_date") if sb else []
        if not workshops_for_edit:
            st.info("No workshops in the database yet. Log one first.")
        else:
            ws_labels = [
                f"[{w.get('start_date')}] {(w.get('title') or '')[:70]} "
                f"· #{w.get('id')}"
                for w in workshops_for_edit
            ]
            pick_idx = st.selectbox(
                "Select workshop to edit",
                options=[-1] + list(range(len(workshops_for_edit))),
                format_func=lambda i: "" if i < 0 else ws_labels[i],
            )

            if pick_idx >= 0:
                w = workshops_for_edit[pick_idx]
                wid = w["id"]

                with st.form(f"edit_workshop_form_{wid}"):
                    title2 = st.text_input("Workshop Title *",
                                            value=w.get("title") or "",
                                            max_chars=200)
                    e1, e2 = st.columns(2)
                    with e1:
                        start2 = st.date_input(
                            "Start Date *",
                            value=(datetime.fromisoformat(str(w.get("start_date"))).date()
                                   if w.get("start_date") else date.today()),
                        )
                        type_opts = ["", "Research Methods", "Publication",
                                     "Research Ethics", "Statistics",
                                     "IP & Commercialization", "Academic Writing",
                                     "Research Monitoring",
                                     "Congress / Symposium", "Other"]
                        cur_type = w.get("workshop_type") or ""
                        workshop_type2 = st.selectbox(
                            "Workshop Type *", type_opts,
                            index=type_opts.index(cur_type)
                            if cur_type in type_opts else 0,
                        )
                        target_opts = ["", "Faculty", "Students", "Both"]
                        cur_target = w.get("target_audience") or ""
                        target2 = st.selectbox(
                            "Target Audience", target_opts,
                            index=target_opts.index(cur_target)
                            if cur_target in target_opts else 0,
                        )
                    with e2:
                        end2 = st.date_input(
                            "End Date (if multi-day)",
                            value=(datetime.fromisoformat(str(w.get("end_date"))).date()
                                   if w.get("end_date") else start2),
                        )
                        st_opts = ["Planning", "Upcoming", "Completed", "Cancelled"]
                        cur_status = w.get("status") or "Upcoming"
                        status2 = st.selectbox(
                            "Status", st_opts,
                            index=st_opts.index(cur_status)
                            if cur_status in st_opts else 0,
                        )
                        attendees2 = st.number_input(
                            "Number of Attendees", min_value=0,
                            value=int(w.get("attendees") or 0),
                        )

                    speakers2 = st.text_area(
                        "Speakers / Facilitators *",
                        value=w.get("speakers") or "",
                        max_chars=500, height=70,
                    )

                    e3, e4 = st.columns(2)
                    with e3:
                        materials2 = st.text_input(
                            "Materials (filename or link)",
                            value=w.get("materials") or "",
                        )
                    with e4:
                        feedback2 = st.number_input(
                            "Feedback Score (out of 5)",
                            min_value=0.0, max_value=5.0, step=0.05,
                            value=float(w.get("feedback_score") or 0),
                        )

                    notes2 = st.text_area("Notes (optional)",
                                          value=w.get("notes") or "",
                                          max_chars=500, height=70)

                    your_name = st.text_input(
                        "Your Name (for audit log) *",
                        value=_USER.get("name") or "",
                    )

                    bc1, bc2 = st.columns([1, 1])
                    with bc1:
                        save_w = st.form_submit_button(
                            "💾 Save Changes", type="primary",
                            use_container_width=True,
                        )
                    with bc2:
                        delete_w = st.form_submit_button(
                            "🗑️ Delete Workshop", use_container_width=True,
                        )

                    if save_w:
                        if not (title2 and speakers2 and workshop_type2
                                and your_name):
                            st.error("Title, speakers, type, and your name "
                                     "are required.")
                        else:
                            updates = {
                                "title": title2,
                                "start_date": str(start2),
                                "end_date": (str(end2)
                                             if end2 != start2 else None),
                                "speakers": speakers2,
                                "workshop_type": workshop_type2,
                                "target_audience": target2 or None,
                                "attendees": int(attendees2) if attendees2 else None,
                                "materials": materials2 or None,
                                "feedback_score": (float(feedback2)
                                                   if feedback2 else None),
                                "status": status2,
                                "notes": notes2 or None,
                                "updated_by": your_name,
                                "updated_at": datetime.now().isoformat(),
                            }
                            if db_update("capacity_workshops", w["id"], updates):
                                st.success(
                                    f"✅ Updated '{title2}' "
                                    f"(saved by {your_name})."
                                )

                    if delete_w:
                        try:
                            sb.table("capacity_workshops").delete()\
                              .eq("id", w["id"]).execute()
                            st.success(f"🗑️ Deleted: {w.get('title')}")
                        except Exception as ex:
                            st.error(f"❌ Failed to delete: {ex}")


# ============================================================
# PAGE: MCU RESEARCH JOURNAL
# ============================================================
elif page == "In-House Journal Publications":
    st.markdown('<div class="section-heading">In-House Journal Publications</div>',
                unsafe_allow_html=True)
    st.caption(
        "Peer-reviewed journals managed within MCU — the flagship MCU "
        "Research Journal and college-level faculty-led journals."
    )

    journal_tab = st.radio(
        "Category",
        ["📘 MCU Journal", "📗 Faculty-Led Journals"],
        horizontal=True, label_visibility="collapsed",
    )

    # Helper: build a signed URL to view/download a journal PDF stored in
    # the grant-reports Supabase Storage bucket.
    def _journal_pdf_url(path: str, ttl_seconds: int = 3600) -> str:
        if not (path and sb is not None):
            return ""
        try:
            res = sb.storage.from_("grant-reports") \
                            .create_signed_url(path, ttl_seconds)
            return (res.get("signedURL") or res.get("signed_url") or "")
        except Exception:
            return ""

    if journal_tab == "📗 Faculty-Led Journals":
        st.caption(
            "College / department-level journals where MCU faculty serve "
            "as editors or editorial-board members."
        )

        fl_issues = []
        fl_table_missing = False
        if sb is not None:
            try:
                res = sb.table("faculty_led_journal_issues").select("*")\
                        .order("publication_year", desc=True).execute()
                fl_issues = res.data or []
            except Exception as ex:
                if "PGRST205" in str(ex) or "schema cache" in str(ex).lower():
                    fl_table_missing = True
                else:
                    st.error(f"Read error: {ex}")

        if fl_table_missing:
            st.warning(
                "⚠️ The `faculty_led_journal_issues` table doesn't exist yet. "
                "Run **`add_faculty_led_journals.sql`** in the Supabase SQL "
                "Editor, then refresh this page. The form below is shown "
                "for preview — submissions will fail until the SQL is applied."
            )

        # Top metrics
        fl_n = len(fl_issues)
        fl_pub = sum(1 for i in fl_issues if i.get("status") == "Published")
        fm1, _ = st.columns([1, 3])
        fm1.metric("Published Journals", fl_pub)

        # ----- Issue list (moved up: right after the count) -----
        st.markdown("### 📚 All Issues")
        if not fl_issues:
            st.info(
                "No faculty-led journal issues yet. " +
                ("Use the form below to add the first one." if _IS_ADMIN
                 else "Contact the IRO Director to add an issue.")
            )
        else:
            fl_df = pd.DataFrame(fl_issues)
            fl_df["Issue Label"] = fl_df.apply(
                lambda r: f"Vol. {r.get('volume')}, No. {r.get('issue')} "
                          f"({int(r.get('publication_year'))})",
                axis=1,
            )
            fl_df["View PDF"] = fl_df.get("pdf_storage_path", "") \
                .apply(_journal_pdf_url) if "pdf_storage_path" in fl_df.columns \
                else ""
            fl_cols = [c for c in
                       ["journal_name", "Issue Label", "college",
                        "faculty_lead", "theme", "editor", "isbn_or_issn",
                        "status", "publication_month", "View PDF"]
                       if c in fl_df.columns]
            st.dataframe(
                fl_df[fl_cols] if fl_cols else fl_df,
                hide_index=True, use_container_width=True,
                column_config={
                    "journal_name": st.column_config.TextColumn(
                        "Journal", width="medium"),
                    "Issue Label": st.column_config.TextColumn("Issue"),
                    "college": st.column_config.TextColumn("College"),
                    "faculty_lead": st.column_config.TextColumn("Lead"),
                    "theme": st.column_config.TextColumn("Theme"),
                    "editor": st.column_config.TextColumn("Editor"),
                    "isbn_or_issn": st.column_config.TextColumn("ISSN"),
                    "status": st.column_config.TextColumn("Status"),
                    "publication_month": st.column_config.NumberColumn(
                        "Month", format="%d"),
                    "View PDF": st.column_config.LinkColumn(
                        "View PDF",
                        help="Open or download the issue PDF",
                        display_text="📥 Open / Download",
                        disabled=True),
                },
            )

        st.divider()

        # ----- Add new issue (admin only) -----
        if _IS_ADMIN:
            with st.expander("➕ Add a New Issue (Admin)", expanded=False):
                with st.form("add_fl_issue_form", clear_on_submit=True):
                    fl_journal_name = st.text_input(
                        "Journal Name *",
                        placeholder="e.g., MCU Journal of Medical Education",
                    )
                    FL_COLLEGES = [
                        "", "Medicine", "Nursing", "Med Tech", "Pharmacy",
                        "Dentistry", "Optometry", "Physical Therapy",
                        "Arts & Sciences", "Education",
                        "Business and Management",
                    ]
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        fl_college = st.selectbox(
                            "College / Department",
                            FL_COLLEGES, index=0,
                        )
                    with fc2:
                        fl_lead = st.text_input(
                            "Faculty Lead (Editor-in-Chief)",
                            placeholder="Dr. ...",
                        )

                    fc3, fc4, fc5 = st.columns(3)
                    with fc3:
                        fl_vol = st.text_input("Volume *",
                                               placeholder="e.g., 1")
                    with fc4:
                        fl_iss = st.text_input("Issue (No.) *",
                                               placeholder="e.g., 1")
                    with fc5:
                        fl_year = st.number_input(
                            "Publication Year *",
                            min_value=2000, max_value=2030, value=2026,
                        )

                    fc6, fc7 = st.columns(2)
                    with fc6:
                        fl_month = st.selectbox(
                            "Publication Month",
                            [None, 1, 2, 3, 4, 5, 6, 7, 8,
                             9, 10, 11, 12],
                            format_func=lambda m: "" if m is None
                            else ["", "Jan", "Feb", "Mar", "Apr", "May",
                                  "Jun", "Jul", "Aug", "Sep", "Oct",
                                  "Nov", "Dec"][m],
                        )
                    with fc7:
                        fl_status = st.selectbox(
                            "Status *",
                            ["Published", "Under Review", "Draft"],
                        )

                    fc8, fc9 = st.columns(2)
                    with fc8:
                        fl_editor = st.text_input("Editor")
                    with fc9:
                        fl_coed = st.text_input("Co-Editor")

                    fl_theme = st.text_input(
                        "Theme / Special Issue Title (optional)",
                    )
                    fl_issn = st.text_input("ISSN / ISBN")
                    fl_notes = st.text_area("Notes",
                                            max_chars=500, height=80)

                    fl_upload_pdf = st.file_uploader(
                        "Upload Issue PDF (optional)", type=["pdf"],
                    )

                    fl_submit = st.form_submit_button(
                        "➕ Add Issue", type="primary",
                    )

                    if fl_submit:
                        if not (fl_journal_name and fl_vol and fl_iss
                                and fl_year):
                            st.error("Journal Name, Volume, Issue, and "
                                     "Year are required.")
                        else:
                            fl_pdf_path = None
                            fl_pdf_name = None
                            fl_ok = True
                            if fl_upload_pdf is not None:
                                fl_pdf_name = fl_upload_pdf.name
                                ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                                slug = "".join(c if c.isalnum() else "-"
                                               for c in fl_journal_name)[:32]
                                fl_pdf_path = (
                                    f"faculty-led/{slug}/"
                                    f"vol{fl_vol}-iss{fl_iss}/"
                                    f"{ts}_{fl_pdf_name}"
                                )
                                try:
                                    sb.storage.from_("grant-reports").upload(
                                        fl_pdf_path, fl_upload_pdf.getvalue(),
                                        {"content-type": "application/pdf"},
                                    )
                                except Exception as e:
                                    fl_ok = False
                                    st.warning(
                                        f"Binary upload failed: {e}. "
                                        "Metadata still saved."
                                    )

                            row = {
                                "journal_name": fl_journal_name,
                                "college": fl_college or None,
                                "faculty_lead": fl_lead or None,
                                "volume": fl_vol,
                                "issue": fl_iss,
                                "publication_year": int(fl_year),
                                "publication_month": (int(fl_month)
                                                      if fl_month else None),
                                "editor": fl_editor or None,
                                "co_editor": fl_coed or None,
                                "theme": fl_theme or None,
                                "isbn_or_issn": fl_issn or None,
                                "pdf_filename": fl_pdf_name,
                                "pdf_storage_path": fl_pdf_path,
                                "status": fl_status,
                                "notes": fl_notes or None,
                                "updated_by": _USER.get("email") if _USER else None,
                                "updated_at": datetime.now().isoformat(),
                            }
                            try:
                                sb.table("faculty_led_journal_issues")\
                                  .insert(row).execute()
                                st.success(
                                    f"✅ Added {fl_journal_name} "
                                    f"Vol. {fl_vol}, No. {fl_iss} "
                                    f"({fl_year})."
                                )
                                if fl_ok and fl_upload_pdf:
                                    st.balloons()
                            except Exception as e:
                                if "duplicate" in str(e).lower():
                                    st.error(
                                        f"❌ {fl_journal_name} Vol. {fl_vol}, "
                                        f"No. {fl_iss} already exists."
                                    )
                                else:
                                    st.error(f"❌ Failed: {e}")

        # ----- Edit existing Faculty-Led issue (admin only) -----
        if _IS_ADMIN and fl_issues:
            with st.expander("✏️ Edit an Existing Issue (Admin)",
                             expanded=False):
                fl_edit_labels = [
                    f"{i.get('journal_name')} — Vol. {i.get('volume')}, "
                    f"No. {i.get('issue')} ({int(i.get('publication_year'))})"
                    for i in fl_issues
                ]
                fl_pick_idx = st.selectbox(
                    "Select issue to edit", range(len(fl_edit_labels)),
                    format_func=lambda i: fl_edit_labels[i],
                    key="fl_edit_pick",
                )
                fei = fl_issues[fl_pick_idx]

                with st.form("edit_fl_issue_form"):
                    fe_journal = st.text_input(
                        "Journal Name *",
                        value=fei.get("journal_name") or "",
                    )
                    FL_COLLEGES_E = [
                        "", "Medicine", "Nursing", "Med Tech", "Pharmacy",
                        "Dentistry", "Optometry", "Physical Therapy",
                        "Arts & Sciences", "Education",
                        "Business and Management",
                    ]
                    cur_fl_col = fei.get("college") or ""
                    fec1, fec2 = st.columns(2)
                    with fec1:
                        fe_college = st.selectbox(
                            "College / Department",
                            FL_COLLEGES_E,
                            index=(FL_COLLEGES_E.index(cur_fl_col)
                                   if cur_fl_col in FL_COLLEGES_E else 0),
                        )
                    with fec2:
                        fe_lead = st.text_input(
                            "Faculty Lead (Editor-in-Chief)",
                            value=fei.get("faculty_lead") or "",
                        )

                    fec3, fec4, fec5 = st.columns(3)
                    with fec3:
                        fe_vol = st.text_input(
                            "Volume *", value=fei.get("volume") or "",
                        )
                    with fec4:
                        fe_iss = st.text_input(
                            "Issue (No.) *", value=fei.get("issue") or "",
                        )
                    with fec5:
                        fe_year = st.number_input(
                            "Publication Year *", min_value=2000,
                            max_value=2030,
                            value=int(fei.get("publication_year") or 2026),
                        )

                    fec6, fec7 = st.columns(2)
                    with fec6:
                        cur_month = fei.get("publication_month")
                        fe_month = st.selectbox(
                            "Publication Month",
                            [None, 1, 2, 3, 4, 5, 6, 7, 8,
                             9, 10, 11, 12],
                            index=([None, 1, 2, 3, 4, 5, 6, 7, 8,
                                    9, 10, 11, 12].index(cur_month)
                                    if cur_month in
                                    [None, 1, 2, 3, 4, 5, 6, 7, 8,
                                     9, 10, 11, 12] else 0),
                            format_func=lambda m: "" if m is None
                            else ["", "Jan", "Feb", "Mar", "Apr", "May",
                                  "Jun", "Jul", "Aug", "Sep", "Oct",
                                  "Nov", "Dec"][m],
                        )
                    with fec7:
                        cur_status = fei.get("status") or "Draft"
                        status_opts = ["Published", "Under Review", "Draft"]
                        fe_status = st.selectbox(
                            "Status *", status_opts,
                            index=status_opts.index(cur_status)
                            if cur_status in status_opts else 2,
                        )

                    fec8, fec9 = st.columns(2)
                    with fec8:
                        fe_editor = st.text_input(
                            "Editor", value=fei.get("editor") or "",
                        )
                    with fec9:
                        fe_coed = st.text_input(
                            "Co-Editor", value=fei.get("co_editor") or "",
                        )

                    fe_theme = st.text_input(
                        "Theme / Special Issue Title",
                        value=fei.get("theme") or "",
                    )
                    fe_issn = st.text_input(
                        "ISSN / ISBN",
                        value=fei.get("isbn_or_issn") or "",
                    )
                    fe_notes = st.text_area(
                        "Notes", value=fei.get("notes") or "",
                        max_chars=500, height=80,
                    )

                    fe_pdf = st.file_uploader(
                        "Replace Issue PDF (optional)", type=["pdf"],
                        key="fl_edit_pdf",
                    )

                    fe_audit = st.text_input(
                        "Your Name (for audit log) *",
                        key="fl_edit_audit",
                    )

                    fesave, fedel = st.columns(2)
                    with fesave:
                        fl_save_btn = st.form_submit_button(
                            "💾 Save Changes", type="primary",
                        )
                    with fedel:
                        fl_del_btn = st.form_submit_button(
                            "🗑️ Delete Issue",
                        )

                    if fl_save_btn:
                        if not (fe_journal and fe_vol and fe_iss
                                and fe_year and fe_audit):
                            st.error(
                                "Journal Name, Volume, Issue, Year, "
                                "and your name are required."
                            )
                        else:
                            new_path = fei.get("pdf_storage_path")
                            new_name = fei.get("pdf_filename")
                            if fe_pdf is not None:
                                new_name = fe_pdf.name
                                ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                                slug = "".join(c if c.isalnum() else "-"
                                               for c in fe_journal)[:32]
                                new_path = (
                                    f"faculty-led/{slug}/"
                                    f"vol{fe_vol}-iss{fe_iss}/"
                                    f"{ts}_{new_name}"
                                )
                                try:
                                    sb.storage.from_("grant-reports").upload(
                                        new_path, fe_pdf.getvalue(),
                                        {"content-type": "application/pdf"},
                                    )
                                except Exception as ex:
                                    st.warning(
                                        f"Binary upload failed: {ex}. "
                                        "Metadata still saved."
                                    )

                            updates = {
                                "journal_name": fe_journal,
                                "college": fe_college or None,
                                "faculty_lead": fe_lead or None,
                                "volume": fe_vol,
                                "issue": fe_iss,
                                "publication_year": int(fe_year),
                                "publication_month": (int(fe_month)
                                                      if fe_month else None),
                                "editor": fe_editor or None,
                                "co_editor": fe_coed or None,
                                "theme": fe_theme or None,
                                "isbn_or_issn": fe_issn or None,
                                "pdf_filename": new_name,
                                "pdf_storage_path": new_path,
                                "status": fe_status,
                                "notes": fe_notes or None,
                                "updated_by": fe_audit,
                                "updated_at": datetime.now().isoformat(),
                            }
                            if db_update("faculty_led_journal_issues",
                                         fei["id"], updates):
                                st.success(
                                    f"✅ Updated {fe_journal} "
                                    f"Vol. {fe_vol}, No. {fe_iss} "
                                    f"(saved by {fe_audit})."
                                )

                    if fl_del_btn:
                        try:
                            sb.table("faculty_led_journal_issues").delete()\
                              .eq("id", fei["id"]).execute()
                            st.success(
                                f"🗑️ Deleted {fei.get('journal_name')} "
                                f"Vol. {fei.get('volume')}, "
                                f"No. {fei.get('issue')}."
                            )
                        except Exception as ex:
                            st.error(f"❌ Failed to delete: {ex}")

        # ----- Drill-down: pick an issue, view details -----
        if fl_issues:
            st.markdown("### 🔍 Issue Detail")
            fl_labels = [
                f"{i.get('journal_name')} — Vol. {i.get('volume')}, "
                f"No. {i.get('issue')} ({int(i.get('publication_year'))})"
                for i in fl_issues
            ]
            fl_pick = st.selectbox("Choose an issue", fl_labels,
                                   key="fl_pick")
            fl_chosen = fl_issues[fl_labels.index(fl_pick)]

            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown(f"**Journal:** {fl_chosen.get('journal_name')}")
                st.markdown(f"**College:** {fl_chosen.get('college') or '—'}")
                st.markdown(f"**Volume:** {fl_chosen.get('volume')}")
                st.markdown(f"**Issue No.:** {fl_chosen.get('issue')}")
                st.markdown(f"**Year:** {fl_chosen.get('publication_year')}")
                st.markdown(f"**Status:** {fl_chosen.get('status')}")
            with dc2:
                st.markdown(f"**Faculty Lead:** "
                            f"{fl_chosen.get('faculty_lead') or '—'}")
                st.markdown(f"**Editor:** {fl_chosen.get('editor') or '—'}")
                st.markdown(f"**Co-Editor:** "
                            f"{fl_chosen.get('co_editor') or '—'}")
                st.markdown(f"**ISSN:** "
                            f"{fl_chosen.get('isbn_or_issn') or '—'}")
                if fl_chosen.get("doi"):
                    st.markdown(f"**DOI:** {fl_chosen.get('doi')}")
            if fl_chosen.get("theme"):
                st.markdown(f"**Theme:** _{fl_chosen.get('theme')}_")
            if fl_chosen.get("notes"):
                st.info(fl_chosen.get("notes"))
            if fl_chosen.get("pdf_filename"):
                st.markdown(f"**PDF:** 📄 {fl_chosen.get('pdf_filename')}")

        st.stop()

    # ===== MCU Journal sub-category =====
    st.caption(
        "Manila Central University Research Journal — semi-annual, "
        "ISSN 2012-3884 (print). Published by the Institutional Research Office."
    )

    issues = db_select("mcu_journal_issues", order_col="publication_year", desc=True)

    # Top metric — only Published count is surfaced.
    n_published = sum(1 for i in issues if i.get("status") == "Published")
    mc1, _ = st.columns([1, 3])
    mc1.metric("Published Journals", n_published)

    # ----- Issue list (moved up: right after the count) -----
    st.markdown("### 📚 All Issues")
    if not issues:
        st.info(
            "No journal issues yet. " +
            ("Use the form below to add the first one." if _IS_ADMIN
             else "Contact the IRO Director to add an issue.")
        )
    else:
        df = pd.DataFrame(issues)
        df["Issue Label"] = df.apply(
            lambda r: f"Vol. {r.get('volume')}, No. {r.get('issue')} "
                      f"({int(r.get('publication_year'))})",
            axis=1,
        )
        df["View PDF"] = df.get("pdf_storage_path", "") \
            .apply(_journal_pdf_url) if "pdf_storage_path" in df.columns \
            else ""
        display_cols = [c for c in
                        ["Issue Label", "theme", "editor", "co_editor",
                         "isbn_or_issn", "status", "publication_month",
                         "View PDF"]
                        if c in df.columns]
        st.dataframe(
            df[display_cols] if display_cols else df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Issue Label": st.column_config.TextColumn("Issue",
                                                            width="medium"),
                "theme": st.column_config.TextColumn("Theme"),
                "editor": st.column_config.TextColumn("Editor"),
                "co_editor": st.column_config.TextColumn("Co-Editor"),
                "isbn_or_issn": st.column_config.TextColumn("ISSN"),
                "status": st.column_config.TextColumn("Status"),
                "publication_month": st.column_config.NumberColumn(
                    "Month", format="%d"),
                "View PDF": st.column_config.LinkColumn(
                    "View PDF",
                    help="Open or download the issue PDF",
                    display_text="📥 Open / Download",
                    disabled=True),
            },
        )

    st.divider()

    # ----- Add new issue (admin only) -----
    if _IS_ADMIN:
        with st.expander("➕ Add a New Issue (Admin)", expanded=False):
            with st.form("add_issue_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    volume = st.text_input("Volume *", placeholder="e.g., 12")
                with c2:
                    issue = st.text_input("Issue (No.) *", placeholder="e.g., 1")
                with c3:
                    pub_year = st.number_input("Publication Year *",
                                                min_value=2000, max_value=2030,
                                                value=2026)
                c4, c5 = st.columns(2)
                with c4:
                    pub_month = st.selectbox("Publication Month",
                                              [None, 1, 2, 3, 4, 5, 6, 7, 8,
                                               9, 10, 11, 12],
                                              format_func=lambda m: "" if m is None
                                              else ["", "Jan", "Feb", "Mar", "Apr",
                                                    "May", "Jun", "Jul", "Aug",
                                                    "Sep", "Oct", "Nov", "Dec"][m])
                with c5:
                    status = st.selectbox("Status *",
                                          ["Published", "Under Review", "Draft"])

                c6, c7 = st.columns(2)
                with c6:
                    editor = st.text_input("Editor", placeholder="Dr. ... LPT, ...")
                with c7:
                    co_editor = st.text_input("Co-Editor")

                theme = st.text_input("Theme / Special Issue Title (optional)")
                isbn_or_issn = st.text_input("ISSN / ISBN",
                                              value="ISSN 2012-3884 (print)")
                notes = st.text_area("Notes", max_chars=500, height=80)

                upload_pdf = st.file_uploader("Upload Issue PDF (optional)",
                                               type=["pdf"])

                submit_issue = st.form_submit_button("➕ Add Issue", type="primary")

                if submit_issue:
                    if not (volume and issue and pub_year):
                        st.error("Volume, Issue, and Year are required.")
                    else:
                        pdf_storage_path = None
                        pdf_filename = None
                        upload_ok = True

                        if upload_pdf is not None:
                            pdf_filename = upload_pdf.name
                            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                            pdf_storage_path = (
                                f"mcu-journal/vol{volume}-iss{issue}/{ts}_{pdf_filename}"
                            )
                            try:
                                sb.storage.from_("grant-reports").upload(
                                    pdf_storage_path, upload_pdf.getvalue(),
                                    {"content-type": "application/pdf"},
                                )
                            except Exception as e:
                                upload_ok = False
                                st.warning(
                                    f"Binary upload failed: {e}. "
                                    "Metadata still saved."
                                )

                        row = {
                            "volume": volume,
                            "issue": issue,
                            "publication_year": int(pub_year),
                            "publication_month": int(pub_month) if pub_month else None,
                            "editor": editor or None,
                            "co_editor": co_editor or None,
                            "theme": theme or None,
                            "isbn_or_issn": isbn_or_issn or None,
                            "pdf_filename": pdf_filename,
                            "pdf_storage_path": pdf_storage_path,
                            "status": status,
                            "notes": notes or None,
                            "updated_by": _USER.get("email"),
                            "updated_at": datetime.now().isoformat(),
                        }
                        try:
                            sb.table("mcu_journal_issues").insert(row).execute()
                            st.success(
                                f"✅ Added Vol. {volume}, No. {issue} ({pub_year})."
                            )
                            if upload_ok and upload_pdf:
                                st.balloons()
                        except Exception as e:
                            if "duplicate" in str(e).lower():
                                st.error(
                                    f"❌ Vol. {volume}, No. {issue} already exists."
                                )
                            else:
                                st.error(f"❌ Failed: {e}")

        # ----- Edit existing MCU Journal issue (admin only) -----
        if issues:
            with st.expander("✏️ Edit an Existing Issue (Admin)",
                             expanded=False):
                issue_labels = [
                    f"Vol. {i.get('volume')}, No. {i.get('issue')} "
                    f"({int(i.get('publication_year'))})"
                    for i in issues
                ]
                pick_idx = st.selectbox(
                    "Select issue to edit", range(len(issue_labels)),
                    format_func=lambda i: issue_labels[i],
                    key="mcu_edit_pick",
                )
                ei = issues[pick_idx]

                with st.form("edit_mcu_issue_form"):
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        e_vol = st.text_input(
                            "Volume *", value=ei.get("volume") or "",
                        )
                    with ec2:
                        e_iss = st.text_input(
                            "Issue (No.) *", value=ei.get("issue") or "",
                        )
                    with ec3:
                        e_year = st.number_input(
                            "Publication Year *", min_value=2000,
                            max_value=2030,
                            value=int(ei.get("publication_year") or 2026),
                        )

                    ec4, ec5 = st.columns(2)
                    with ec4:
                        cur_month = ei.get("publication_month")
                        e_month = st.selectbox(
                            "Publication Month",
                            [None, 1, 2, 3, 4, 5, 6, 7, 8,
                             9, 10, 11, 12],
                            index=([None, 1, 2, 3, 4, 5, 6, 7, 8,
                                    9, 10, 11, 12].index(cur_month)
                                    if cur_month in
                                    [None, 1, 2, 3, 4, 5, 6, 7, 8,
                                     9, 10, 11, 12] else 0),
                            format_func=lambda m: "" if m is None
                            else ["", "Jan", "Feb", "Mar", "Apr", "May",
                                  "Jun", "Jul", "Aug", "Sep", "Oct",
                                  "Nov", "Dec"][m],
                        )
                    with ec5:
                        cur_status = ei.get("status") or "Draft"
                        status_opts = ["Published", "Under Review", "Draft"]
                        e_status = st.selectbox(
                            "Status *", status_opts,
                            index=status_opts.index(cur_status)
                            if cur_status in status_opts else 2,
                        )

                    ec6, ec7 = st.columns(2)
                    with ec6:
                        e_editor = st.text_input(
                            "Editor", value=ei.get("editor") or "",
                        )
                    with ec7:
                        e_coed = st.text_input(
                            "Co-Editor", value=ei.get("co_editor") or "",
                        )

                    e_theme = st.text_input(
                        "Theme / Special Issue Title",
                        value=ei.get("theme") or "",
                    )
                    e_issn = st.text_input(
                        "ISSN / ISBN",
                        value=ei.get("isbn_or_issn") or "",
                    )
                    e_notes = st.text_area(
                        "Notes", value=ei.get("notes") or "",
                        max_chars=500, height=80,
                    )

                    e_pdf = st.file_uploader(
                        "Replace Issue PDF (optional)", type=["pdf"],
                        key="mcu_edit_pdf",
                    )

                    e_audit = st.text_input(
                        "Your Name (for audit log) *",
                        key="mcu_edit_audit",
                    )

                    esave_col, edel_col = st.columns(2)
                    with esave_col:
                        save_btn = st.form_submit_button(
                            "💾 Save Changes", type="primary",
                        )
                    with edel_col:
                        del_btn = st.form_submit_button(
                            "🗑️ Delete Issue",
                        )

                    if save_btn:
                        if not (e_vol and e_iss and e_year and e_audit):
                            st.error("Volume, Issue, Year, and your name "
                                     "are required.")
                        else:
                            new_pdf_path = ei.get("pdf_storage_path")
                            new_pdf_name = ei.get("pdf_filename")
                            if e_pdf is not None:
                                new_pdf_name = e_pdf.name
                                ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                                new_pdf_path = (
                                    f"mcu-journal/vol{e_vol}-iss{e_iss}/"
                                    f"{ts}_{new_pdf_name}"
                                )
                                try:
                                    sb.storage.from_("grant-reports").upload(
                                        new_pdf_path, e_pdf.getvalue(),
                                        {"content-type": "application/pdf"},
                                    )
                                except Exception as ex:
                                    st.warning(
                                        f"Binary upload failed: {ex}. "
                                        "Metadata still saved."
                                    )

                            updates = {
                                "volume": e_vol,
                                "issue": e_iss,
                                "publication_year": int(e_year),
                                "publication_month": (int(e_month)
                                                      if e_month else None),
                                "editor": e_editor or None,
                                "co_editor": e_coed or None,
                                "theme": e_theme or None,
                                "isbn_or_issn": e_issn or None,
                                "pdf_filename": new_pdf_name,
                                "pdf_storage_path": new_pdf_path,
                                "status": e_status,
                                "notes": e_notes or None,
                                "updated_by": e_audit,
                                "updated_at": datetime.now().isoformat(),
                            }
                            if db_update("mcu_journal_issues",
                                         ei["id"], updates):
                                st.success(
                                    f"✅ Updated Vol. {e_vol}, "
                                    f"No. {e_iss} (saved by {e_audit})."
                                )

                    if del_btn:
                        try:
                            sb.table("mcu_journal_issues").delete()\
                              .eq("id", ei["id"]).execute()
                            st.success(
                                f"🗑️ Deleted Vol. {ei.get('volume')}, "
                                f"No. {ei.get('issue')}."
                            )
                        except Exception as ex:
                            st.error(f"❌ Failed to delete: {ex}")

    # ----- Drill-down: pick an issue, view articles, link to PDF -----
    if issues:
        st.markdown("### 🔍 Issue Detail")
        labels = [f"Vol. {i.get('volume')}, No. {i.get('issue')} "
                  f"({int(i.get('publication_year'))}) · #{i.get('id')}"
                  for i in issues]
        pick_idx = st.selectbox(
            "Choose an issue", options=range(len(issues)),
            format_func=lambda i: labels[i],
        )
        chosen = issues[pick_idx]

        dc1, dc2 = st.columns(2)
        with dc1:
            st.markdown(f"**Volume:** {chosen.get('volume')}")
            st.markdown(f"**Issue No.:** {chosen.get('issue')}")
            st.markdown(f"**Year:** {chosen.get('publication_year')}")
            st.markdown(f"**Status:** {chosen.get('status')}")
        with dc2:
            st.markdown(f"**Editor:** {chosen.get('editor') or '—'}")
            st.markdown(f"**Co-Editor:** {chosen.get('co_editor') or '—'}")
            st.markdown(f"**ISSN:** {chosen.get('isbn_or_issn') or '—'}")
            if chosen.get("doi"):
                st.markdown(f"**DOI:** {chosen.get('doi')}")
        if chosen.get("theme"):
            st.markdown(f"**Theme:** _{chosen.get('theme')}_")
        if chosen.get("notes"):
            st.info(chosen.get("notes"))
        if chosen.get("pdf_filename"):
            st.markdown(f"**PDF:** 📄 {chosen.get('pdf_filename')}")

        # Articles in this issue
        try:
            arts_res = sb.table("mcu_journal_articles").select("*")\
                         .eq("issue_id", chosen["id"]).execute()
            articles = arts_res.data or []
        except Exception:
            articles = []

        if articles:
            st.markdown(f"**📝 Articles in this issue ({len(articles)}):**")
            adf = pd.DataFrame(articles)
            acols = [c for c in
                     ["title", "authors", "college", "page_start", "page_end",
                      "keywords", "doi"] if c in adf.columns]
            st.dataframe(adf[acols] if acols else adf,
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No article-level metadata logged for this issue yet.")



# ============================================================
# PAGE: IRO POLICIES (E-Library)
# ============================================================
elif page == "IRO Policies":
    st.markdown(
        '<div class="section-heading">IRO Policies</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Institutional Research Office policies. Submit a new policy "
        "(drag-and-drop the file) or browse the existing library below."
    )

    # Preflight: warn if the table is missing
    pol_table_ok = True
    if sb is not None:
        try:
            sb.table("iro_policies").select("id").limit(1).execute()
        except Exception as ex:
            if "PGRST205" in str(ex) or "schema cache" in str(ex).lower():
                pol_table_ok = False

    if not pol_table_ok:
        st.warning(
            "⚠️ The `iro_policies` table doesn't exist yet. Run "
            "**`add_iro_policies.sql`** in the Supabase SQL Editor, then "
            "refresh. The form is shown for preview — submissions will "
            "fail until the SQL is applied."
        )

    # ----- Submit a new policy -----
    with st.expander("➕ Submit a New Policy", expanded=False):
        with st.form("submit_policy_form", clear_on_submit=True):
            p_title = st.text_input(
                "Policy Title *", max_chars=200,
                placeholder="e.g., Authorship & Acknowledgement Policy",
            )
            pc1, pc2 = st.columns(2)
            with pc1:
                p_type = st.text_input(
                    "Policy Type *",
                    placeholder="e.g., Research Ethics, Authorship, Data "
                                "Management, Intellectual Property",
                )
                p_person = st.text_input(
                    "Person Updating *",
                    value=(_USER.get("name") or "") if _USER else "",
                    placeholder="Full name",
                )
            with pc2:
                p_date = st.date_input("Date Updated *", value=date.today())
                p_notes = st.text_input(
                    "Notes (optional)",
                    placeholder="e.g., revised section 4 on co-authorship",
                )

            p_file = st.file_uploader(
                "Drag & drop the policy file (PDF / DOCX / DOC) *",
                type=["pdf", "docx", "doc"],
                accept_multiple_files=False,
                help="Drag a file from your desktop here, or click to browse.",
            )

            p_submitted = st.form_submit_button(
                "📤 Submit Policy", type="primary",
            )

            if p_submitted:
                if not (p_title and p_type and p_person and p_date and p_file):
                    st.error(
                        "Title, Policy Type, Person Updating, Date Updated, "
                        "and a file are all required."
                    )
                else:
                    file_storage_path = None
                    upload_ok = True
                    p_filename = p_file.name
                    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                    slug = "".join(c if c.isalnum() else "-"
                                   for c in p_type)[:32].strip("-")
                    file_storage_path = (
                        f"iro-policies/{slug}/{ts}_{p_filename}"
                    )
                    try:
                        sb.storage.from_("grant-reports").upload(
                            file_storage_path, p_file.getvalue(),
                            {"content-type": p_file.type or
                             "application/octet-stream"},
                        )
                    except Exception as e:
                        upload_ok = False
                        st.warning(
                            f"Binary upload failed: {e}. "
                            "Metadata still saved."
                        )

                    row = {
                        "policy_title": p_title,
                        "policy_type": p_type,
                        "updated_by_person": p_person,
                        "date_updated": str(p_date),
                        "file_filename": p_filename,
                        "file_storage_path": file_storage_path,
                        "notes": p_notes or None,
                        "uploaded_by": (_USER.get("email")
                                        if _USER else None),
                    }
                    if db_insert("iro_policies", row):
                        st.success(
                            f"✅ Policy '{p_title}' submitted "
                            f"({p_type} · updated {p_date})."
                        )
                        if upload_ok:
                            st.balloons()

    # ----- Existing policies -----
    policies = db_select("iro_policies",
                         order_col="date_updated", desc=True) if sb else []

    # ----- Edit / delete an existing policy -----
    if policies:
        with st.expander("✏️ Edit an Existing Policy", expanded=False):
            pol_labels = [
                f"[{p.get('date_updated')}] {(p.get('policy_title') or '')[:60]} "
                f"· {p.get('policy_type') or ''} · #{p.get('id')}"
                for p in policies
            ]
            pol_pick_idx = st.selectbox(
                "Select policy to edit",
                options=range(len(policies)),
                format_func=lambda i: pol_labels[i],
                key="pol_edit_pick",
            )
            ep = policies[pol_pick_idx]
            epid = ep["id"]

            # Reset stale widget keys when switching to a different policy
            if st.session_state.get("pol_edit_loaded_id") != epid:
                for k in list(st.session_state.keys()):
                    if k.startswith("pol_edit_field_"):
                        del st.session_state[k]
                st.session_state["pol_edit_loaded_id"] = epid

            with st.form(f"edit_policy_form_{epid}"):
                ep_title = st.text_input(
                    "Policy Title *", max_chars=200,
                    value=ep.get("policy_title") or "",
                    key=f"pol_edit_field_title_{epid}",
                )
                epc1, epc2 = st.columns(2)
                with epc1:
                    ep_type = st.text_input(
                        "Policy Type *",
                        value=ep.get("policy_type") or "",
                        key=f"pol_edit_field_type_{epid}",
                    )
                    ep_person = st.text_input(
                        "Person Updating *",
                        value=ep.get("updated_by_person") or "",
                        key=f"pol_edit_field_person_{epid}",
                    )
                with epc2:
                    ep_date = st.date_input(
                        "Date Updated *",
                        value=(datetime.fromisoformat(
                            str(ep.get("date_updated"))).date()
                            if ep.get("date_updated") else date.today()),
                        key=f"pol_edit_field_date_{epid}",
                    )
                    ep_notes = st.text_input(
                        "Notes",
                        value=ep.get("notes") or "",
                        key=f"pol_edit_field_notes_{epid}",
                    )

                cur_file = ep.get("file_filename") or "—"
                st.caption(f"📄 Current file: **{cur_file}**")
                ep_replace_file = st.file_uploader(
                    "Replace file (optional — leave empty to keep current)",
                    type=["pdf", "docx", "doc"],
                    accept_multiple_files=False,
                    key=f"pol_edit_field_file_{epid}",
                )

                ebs, ebd = st.columns(2)
                with ebs:
                    pol_save_btn = st.form_submit_button(
                        "💾 Save Changes", type="primary",
                        use_container_width=True,
                    )
                with ebd:
                    pol_del_btn = st.form_submit_button(
                        "🗑️ Delete Policy",
                        use_container_width=True,
                    )

                if pol_save_btn:
                    if not (ep_title and ep_type and ep_person and ep_date):
                        st.error(
                            "Title, Policy Type, Person Updating and "
                            "Date Updated are all required."
                        )
                    else:
                        new_path = ep.get("file_storage_path")
                        new_name = ep.get("file_filename")
                        upload_ok = True
                        if ep_replace_file is not None:
                            new_name = ep_replace_file.name
                            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                            slug = "".join(c if c.isalnum() else "-"
                                           for c in ep_type)[:32].strip("-")
                            new_path = (
                                f"iro-policies/{slug}/{ts}_{new_name}"
                            )
                            try:
                                sb.storage.from_("grant-reports").upload(
                                    new_path, ep_replace_file.getvalue(),
                                    {"content-type":
                                     ep_replace_file.type or
                                     "application/octet-stream"},
                                )
                            except Exception as ex:
                                upload_ok = False
                                st.warning(
                                    f"Binary upload failed: {ex}. "
                                    "Metadata still updated."
                                )

                        updates = {
                            "policy_title": ep_title,
                            "policy_type": ep_type,
                            "updated_by_person": ep_person,
                            "date_updated": str(ep_date),
                            "file_filename": new_name,
                            "file_storage_path": new_path,
                            "notes": ep_notes or None,
                        }
                        if db_update("iro_policies", epid, updates):
                            st.success(
                                f"✅ Updated policy '{ep_title}' "
                                f"(saved by {ep_person})."
                            )
                            if upload_ok and ep_replace_file:
                                st.balloons()

                if pol_del_btn:
                    try:
                        sb.table("iro_policies").delete()\
                          .eq("id", epid).execute()
                        st.success(
                            f"🗑️ Deleted policy: {ep.get('policy_title')}"
                        )
                    except Exception as ex:
                        st.error(f"❌ Failed to delete: {ex}")

    st.markdown(
        f'<div style="margin-top:14px;font-size:18px;font-weight:700;'
        f'color:{NAVY};">📚 Policy Library ({len(policies)})</div>',
        unsafe_allow_html=True,
    )

    if not policies:
        st.info("No policies in the library yet. Use the form above to add one.")
    else:
        @st.cache_data(ttl=300, show_spinner=False)
        def _fetch_policy_bytes(path: str):
            if sb is None:
                return None, "Database not configured"
            if not path:
                return None, "No storage path"
            try:
                data = sb.storage.from_("grant-reports").download(path)
                if not data:
                    return None, "Empty file"
                return data, None
            except Exception as ex:
                msg = str(ex)
                if "not found" in msg.lower() or "404" in msg:
                    return None, "Not in storage"
                return None, msg[:60]

        @st.cache_data(ttl=600, show_spinner=False)
        def _fetch_policy_url(path: str):
            """Return a 10-min signed URL so the user can open the PDF in
            a new browser tab. Falls back to None on any failure."""
            if sb is None or not path:
                return None
            try:
                res = sb.storage.from_("grant-reports").create_signed_url(
                    path, 600
                )
                return res.get("signedURL") or res.get("signed_url")
            except Exception:
                return None

        # ----- Toolbar: search + filter -----
        tb1, tb2, tb3 = st.columns([4, 3, 2])
        with tb1:
            q = st.text_input(
                "Search title / filename / notes",
                placeholder="Type to filter…",
                label_visibility="collapsed",
                key="pol_search",
            )
        with tb2:
            type_opts = sorted({(p.get("policy_type") or "Other")
                                for p in policies})
            t_filter = st.multiselect(
                "Filter by type", type_opts,
                placeholder="All types",
                label_visibility="collapsed",
                key="pol_type_filter",
            )
        with tb3:
            sort_key = st.selectbox(
                "Sort by",
                ["Date (newest)", "Date (oldest)", "Title", "Type"],
                label_visibility="collapsed",
                key="pol_sort",
            )

        # Apply filter + sort
        filtered = policies
        if q:
            ql = q.lower()
            filtered = [
                p for p in filtered
                if ql in (p.get("policy_title") or "").lower()
                or ql in (p.get("file_filename") or "").lower()
                or ql in (p.get("notes") or "").lower()
                or ql in (p.get("policy_type") or "").lower()
            ]
        if t_filter:
            filtered = [p for p in filtered
                        if (p.get("policy_type") or "Other") in t_filter]

        if sort_key == "Date (newest)":
            filtered = sorted(filtered,
                              key=lambda p: str(p.get("date_updated") or ""),
                              reverse=True)
        elif sort_key == "Date (oldest)":
            filtered = sorted(filtered,
                              key=lambda p: str(p.get("date_updated") or ""))
        elif sort_key == "Title":
            filtered = sorted(filtered,
                              key=lambda p: (p.get("policy_title") or "").lower())
        elif sort_key == "Type":
            filtered = sorted(filtered,
                              key=lambda p: ((p.get("policy_type") or "").lower(),
                                              str(p.get("date_updated") or "")),
                              reverse=False)

        st.caption(f"Showing **{len(filtered)}** of {len(policies)} policies")

        # ----- Table header -----
        COL_WIDTHS = [3, 2, 2, 1.4, 3]
        header_labels = ["Policy Title", "Type", "Person Updating",
                         "Date Updated", "File"]
        hcols = st.columns(COL_WIDTHS)
        for hc, lbl in zip(hcols, header_labels):
            hc.markdown(
                f'<div style="font-size:13px;font-weight:700;color:#6b7280;'
                f'text-transform:uppercase;letter-spacing:0.5px;'
                f'padding:10px 0 8px 0;border-bottom:2px solid #e5e7eb;">'
                f'{lbl}</div>',
                unsafe_allow_html=True,
            )

        # ----- Table rows -----
        if not filtered:
            st.markdown(
                '<div style="padding:24px;text-align:center;color:#9ca3af;'
                'font-size:15px;">No policies match the current filter.</div>',
                unsafe_allow_html=True,
            )
        for p in filtered:
            fname = p.get("file_filename") or "—"
            path = p.get("file_storage_path")
            title = p.get("policy_title") or "—"
            ptype = p.get("policy_type") or "—"
            person = p.get("updated_by_person") or "—"
            dt = p.get("date_updated") or "—"
            notes = p.get("notes") or ""

            cols = st.columns(COL_WIDTHS)
            # Title (+ notes underneath, muted)
            cols[0].markdown(
                f'<div style="padding:12px 8px 12px 0;font-size:16px;'
                f'color:{NAVY};font-weight:600;line-height:1.4;'
                f'word-break:break-word;">{title}'
                + (f'<div style="font-size:13px;color:#9ca3af;'
                   f'font-style:italic;margin-top:4px;line-height:1.4;">'
                   f'{notes}</div>'
                   if notes else "")
                + '</div>',
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                f'<div style="padding:14px 8px 12px 0;font-size:14px;'
                f'color:#374151;line-height:1.4;">{ptype}</div>',
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                f'<div style="padding:14px 8px 12px 0;font-size:14px;'
                f'color:#374151;line-height:1.4;">{person}</div>',
                unsafe_allow_html=True,
            )
            cols[3].markdown(
                f'<div style="padding:14px 8px 12px 0;font-size:14px;'
                f'color:#374151;white-space:nowrap;">{dt}</div>',
                unsafe_allow_html=True,
            )
            with cols[4]:
                # Filename label (with truncation)
                st.markdown(
                    f'<div style="padding:10px 8px 6px 0;font-size:14px;'
                    f'color:#374151;font-weight:500;overflow:hidden;'
                    f'text-overflow:ellipsis;white-space:nowrap;" '
                    f'title="{fname}">📄 {fname}</div>',
                    unsafe_allow_html=True,
                )
                # Two compact action icons side-by-side
                if path:
                    data, err = _fetch_policy_bytes(path)
                    signed_url = _fetch_policy_url(path) if data else None
                    if data:
                        low = fname.lower()
                        if low.endswith(".pdf"):
                            mime = "application/pdf"
                        elif low.endswith(".docx"):
                            mime = ("application/vnd.openxmlformats-"
                                    "officedocument.wordprocessingml.document")
                        elif low.endswith(".doc"):
                            mime = "application/msword"
                        else:
                            mime = "application/octet-stream"

                        dl_col, vw_col = st.columns(2)
                        with dl_col:
                            st.download_button(
                                "📥 Download", data=data,
                                file_name=fname, mime=mime,
                                key=f"pol_dl_{p.get('id')}",
                                use_container_width=True,
                                help=f"Download {fname}",
                            )
                        with vw_col:
                            if signed_url:
                                st.link_button(
                                    "👁️ View", url=signed_url,
                                    use_container_width=True,
                                    help="Open in a new browser tab",
                                )
                            else:
                                st.button(
                                    "👁️ View", disabled=True,
                                    use_container_width=True,
                                    key=f"pol_vw_disabled_{p.get('id')}",
                                    help="Preview link unavailable",
                                )
                    else:
                        st.markdown(
                            f'<div style="padding:8px 0;font-size:13px;'
                            f'color:#dc2626;">⚠️ {err or "Missing"}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<div style="padding:8px 0;font-size:13px;'
                        'color:#9ca3af;">No file attached</div>',
                        unsafe_allow_html=True,
                    )

            # Thin row separator
            st.markdown(
                '<div style="border-bottom:1px solid #f3f4f6;'
                'margin:0 0 2px 0;"></div>',
                unsafe_allow_html=True,
            )


# ============================================================
# PAGE: IRO PRESENTATIONS & REPORTS LIBRARY
# ============================================================
elif page == "IRO Presentations & Reports":
    require_roles("IRO Presentations & Reports", ["admin", "standard"])
    st.markdown('<div class="section-heading">IRO Presentations &amp; Reports Library</div>',
                unsafe_allow_html=True)
    st.caption(
        "Central repository for Institutional Research Office presentations, "
        "annual reports, quarterly updates, board memos, and policy documents."
    )

    docs = db_select("iro_documents", order_col="uploaded_at") if sb else []

    # --- Top metrics ---
    presentations = [d for d in docs if (d.get("doc_type") or "").lower().endswith("presentation")
                     or "presentation" in (d.get("doc_type") or "").lower()]
    reports = [d for d in docs if "report" in (d.get("doc_type") or "").lower()]

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total Documents", len(docs))
    mc2.metric("Presentations", len(presentations))
    mc3.metric("Reports", len(reports))
    mc4.metric("Other", len(docs) - len(presentations) - len(reports))

    st.divider()

    # ---------- DRAG-AND-DROP UPLOAD ----------
    st.markdown("### 📤 Upload New Document")
    st.caption("Drag & drop a presentation or report to add it to the library.")

    with st.form("iro_doc_upload", clear_on_submit=True):
        title = st.text_input("Document Title *", max_chars=200,
                              placeholder="e.g., IRO 2026 Mid-Year Report")
        c1, c2 = st.columns(2)
        with c1:
            doc_type = st.selectbox(
                "Document Type *",
                ["", "Presentation", "Annual Report", "Quarterly Report",
                 "Board Memo", "Policy Document", "Strategic Plan",
                 "Research Agenda", "Audit Report", "External Submission",
                 "Workshop Material", "Other"],
            )
            doc_date = st.date_input("Document Date", value=date.today())
        with c2:
            presenter = st.text_input("Author / Presenter / Owner",
                                      placeholder="e.g., Dr. Charmaine Ng (Research Strategist)")
            uploaded_by = st.text_input("Your Name *",
                                        placeholder="e.g., Dr. Charmaine Ng")

        description = st.text_area("Description / Abstract",
                                   placeholder="Brief context for the document...",
                                   max_chars=500, height=80)
        tags = st.text_input("Tags (comma-separated)",
                             placeholder="e.g., research-agenda, AY2026, board")

        uploaded_file = st.file_uploader(
            "Drag &amp; drop the file here *",
            type=["pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls",
                  "png", "jpg", "jpeg", "mp4"],
            help="Single file, max 200 MB",
        )

        submitted = st.form_submit_button("📤 Upload to Library", type="primary")

        if submitted:
            if not all([title, doc_type, uploaded_by, uploaded_file]):
                st.error("Please fill required fields and attach a file.")
            else:
                fname = uploaded_file.name
                ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                safe_type = doc_type.lower().replace(" ", "-")
                storage_path = f"iro-library/{safe_type}/{ts}_{fname}"
                file_bytes = uploaded_file.getvalue()

                upload_ok = False
                if sb is not None:
                    try:
                        sb.storage.from_("grant-reports").upload(
                            storage_path, file_bytes,
                            {"content-type": uploaded_file.type
                             or "application/octet-stream"},
                        )
                        upload_ok = True
                    except Exception as e:
                        st.warning(
                            f"Binary upload failed: {e}. Metadata still saved."
                        )

                    db_insert("iro_documents", {
                        "title": title,
                        "doc_type": doc_type,
                        "doc_date": str(doc_date),
                        "presenter": presenter or None,
                        "description": description or None,
                        "tags": tags or None,
                        "filename": fname,
                        "storage_path": storage_path,
                        "uploaded_by": uploaded_by,
                    })

                if upload_ok:
                    st.success(f"✅ '{title}' added to the IRO library.")
                    st.balloons()
                else:
                    st.info(f"📋 Metadata logged for '{title}'.")

    st.divider()

    # ---------- LIBRARY VIEW ----------
    st.markdown("### 📚 Library")

    if not docs:
        st.info("No documents in the library yet. Upload one above to get started.")
    else:
        df = pd.DataFrame(docs)

        # Filters
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            type_filter = st.multiselect(
                "Filter by Type",
                sorted(df["doc_type"].dropna().unique().tolist()) if "doc_type" in df else [],
                default=[],
            )
        with fcol2:
            search_q = st.text_input("Search title / description",
                                     placeholder="Type to filter…")
        with fcol3:
            year_filter = st.multiselect(
                "Filter by Year",
                sorted({d.get("doc_date", "")[:4] for d in docs if d.get("doc_date")},
                       reverse=True),
                default=[],
            )

        filtered = df.copy()
        if type_filter:
            filtered = filtered[filtered["doc_type"].isin(type_filter)]
        if year_filter and "doc_date" in filtered:
            filtered = filtered[
                filtered["doc_date"].astype(str).str[:4].isin(year_filter)
            ]
        if search_q:
            q = search_q.lower()
            filtered = filtered[
                filtered["title"].str.lower().str.contains(q, na=False)
                | filtered.get("description", pd.Series([""] * len(filtered)))
                    .fillna("").str.lower().str.contains(q, na=False)
            ]

        st.markdown(f"**Showing {len(filtered)} of {len(df)} documents**")

        display_cols = [c for c in
                        ["doc_date", "doc_type", "title", "presenter",
                         "description", "tags", "filename", "uploaded_by",
                         "uploaded_at"] if c in filtered.columns]
        st.dataframe(
            filtered[display_cols] if display_cols else filtered,
            hide_index=True,
            use_container_width=True,
            column_config={
                "doc_date": st.column_config.DateColumn("Date"),
                "doc_type": st.column_config.TextColumn("Type"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "presenter": st.column_config.TextColumn("Author / Presenter"),
                "description": st.column_config.TextColumn("Description", width="medium"),
                "tags": st.column_config.TextColumn("Tags"),
                "filename": st.column_config.TextColumn("File"),
                "uploaded_by": st.column_config.TextColumn("Uploaded By"),
                "uploaded_at": st.column_config.DatetimeColumn("Uploaded",
                                                                format="YYYY-MM-DD HH:mm"),
            },
        )


# ============================================================
# PAGE: BUDGET UTILISATION (ADMIN ONLY)
# ============================================================
elif page == "Budget Utilisation":
    require_roles("Budget Utilisation", ["admin", "standard"])
    st.markdown('<div class="section-heading">Budget Utilisation</div>',
                unsafe_allow_html=True)
    st.caption(
        "Institutional Research Office annual operating budget — line-item "
        "tracking of allocation, utilisation, and outstanding balance."
    )

    # Preflight: warn if iro_budget_items missing
    schema_ok = True
    schema_msg = ""
    if sb is None:
        schema_ok = False
        schema_msg = "Database not configured."
    else:
        try:
            sb.table("iro_budget_items").select("id").limit(1).execute()
        except Exception as ex:
            schema_ok = False
            schema_msg = f"`iro_budget_items` table is missing ({ex})."

    if not schema_ok:
        st.warning(
            f"⚠️ {schema_msg}\n\n"
            f"Run **`add_iro_budget_items.sql`** in the Supabase SQL Editor "
            f"to create the table and seed the FY2025 line items, then refresh."
        )
        st.stop()

    # Canonical activity names keyed by the last 6 digits of the budget ref no.
    # Used so the detail table / breakdown always show the current names even
    # when the database still has older spellings.
    _CANONICAL_ACTIVITY_BY_SUFFIX = {
        "000048": "Faculty Publication, Patents, Presentation (Fee Registration)",
        "000049": "Faculty Awards Incentives (Publication, Presentation, Patents, Product)",
        "000050": "In house Research Grants for Institution",
        "000051": "MCU Research Journal (Publication of 2 Issues/yr, printing, honorarium for reviewers)",
        "000052": "Membership Accreditation, Research Collaboration with Industry, University, Government (Fees, Transportation, Registration)",
        "000053": "Monthly Coordination Meeting",
        "000054": "Research Capacity Building",
        "000055": "Research Colloqium (Institutional and all programs)",
        "000056": "Research Presentation",
        "000057": "Student Journal",
        "000058": "Token Representation",
    }

    def _canon_activity(ref_no: str, fallback: str) -> str:
        """Return the canonical activity name for a budget ref."""
        if not ref_no:
            return fallback or ""
        return _CANONICAL_ACTIVITY_BY_SUFFIX.get(ref_no[-6:], fallback or "")

    items = db_select("iro_budget_items", order_col="budget_ref_no") or []

    # Academic-year helpers — store as int (2025 = AY 2025-2026), display as label.
    def _ay_label(y):
        return f"AY{int(y)}-{int(y) + 1}"
    def _year_from_ay(label):
        # Accepts "AY2025-2026" → returns 2025
        try:
            return int(label.replace("AY", "").split("-", 1)[0])
        except Exception:
            return date.today().year

    AY_OPTIONS = ["AY2025-2026", "AY2026-2027"]

    # Academic-year selector — always include AY_OPTIONS, plus any others
    # represented in the data.
    data_years = {int(it.get("fiscal_year")) for it in items
                  if it.get("fiscal_year")}
    ay_filter_options = list(AY_OPTIONS)
    for y in sorted(data_years, reverse=True):
        label = _ay_label(y)
        if label not in ay_filter_options:
            ay_filter_options.append(label)

    fy_col, _ = st.columns([1, 4])
    with fy_col:
        ay_picked = st.selectbox("Academic Year", ay_filter_options)
    fy = _year_from_ay(ay_picked)

    rows = [it for it in items if int(it.get("fiscal_year") or 0) == fy]

    def _f(v):
        return float(v or 0)
    def _peso(n):
        return f"₱{n:,.2f}"

    # ---- KPI strip ----
    tot_alloc    = sum(_f(r.get("total_budget_allocation")) for r in rows)
    tot_explan   = sum(_f(r.get("explan_budget")) for r in rows)
    tot_adjusted = sum(_f(r.get("adjusted_budget")) for r in rows)
    tot_util     = sum(_f(r.get("utilized_budget")) for r in rows)
    tot_out      = tot_alloc - tot_util
    pct_util     = (tot_util / tot_alloc * 100) if tot_alloc > 0 else 0

    kpi_boxes = [
        ("Total Budget",   _peso(tot_alloc),       BRAND["slate"]),
        ("Utilised",       _peso(tot_util),        BRAND["tan"]),
        ("Outstanding",    _peso(tot_out),         BRAND["sage"]),
        ("% Utilisation",  f"{pct_util:.2f}%",     BRAND["plum"]),
    ]
    kpi_cols = st.columns(len(kpi_boxes))
    for col, (label, value, color) in zip(kpi_cols, kpi_boxes):
        col.markdown(
            f'<div style="background:{color};color:white;padding:14px;border-radius:8px;'
            f'text-align:center;min-height:90px;">'
            f'<div style="font-size:22px;font-weight:700;">{value}</div>'
            f'<div style="font-size:11px;opacity:0.95;margin-top:4px;">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("")

    st.divider()

    # ---- Line-item table ----
    if not rows:
        st.info(f"No budget items recorded for {_ay_label(fy)} yet. "
                f"Use **➕ Log a New Transaction** below.")
    else:
        st.markdown(f"**Institutional Research Office — {_ay_label(fy)} "
                    f"(detail by line item)**")

        body_rows = []
        for r in rows:
            total       = _f(r.get("total_budget_allocation"))
            util        = _f(r.get("utilized_budget"))
            outstanding = total - util
            pct         = (util / total * 100) if total > 0 else 0
            body_rows.append({
                "Budget Ref. No.":           r.get("budget_ref_no") or "",
                "Activity Name":             _canon_activity(
                    r.get("budget_ref_no"), r.get("activity_name")),
                "Total Budget Allocation":   _peso(total),
                "Explan Budget":             _peso(_f(r.get("explan_budget"))),
                "Adjusted Budget":           _peso(_f(r.get("adjusted_budget"))),
                "Utilized Budget":           _peso(util),
                "Outstanding Budget":        _peso(outstanding),
                "% Utilization":             round(pct, 2),
            })

        df_b = pd.DataFrame(body_rows)
        st.dataframe(
            df_b,
            hide_index=True, use_container_width=True,
            column_config={
                "% Utilization": st.column_config.ProgressColumn(
                    "% Utilization",
                    format="%.2f%%",
                    min_value=0, max_value=100,
                ),
            },
        )

    # ---- Transaction breakdown ----
    st.markdown(f"**Transaction Breakdown — {_ay_label(fy)}**")
    txn_table_ok = True
    txns = []
    if sb is not None:
        try:
            txn_res = sb.table("iro_budget_transactions").select("*") \
                       .eq("fiscal_year", int(fy)) \
                       .order("transaction_date", desc=True).execute()
            txns = txn_res.data or []
        except Exception as ex:
            txn_table_ok = False
            st.warning(
                f"⚠️ `iro_budget_transactions` table is missing ({ex}). "
                f"Run **`add_iro_budget_transactions.sql`** in the Supabase "
                f"SQL Editor to enable the per-transaction breakdown.")

    if txn_table_ok:
        # Activity filter — derive from line items via canonical-name lookup,
        # so options always match the names shown on transactions even if the
        # database still has older spellings.
        all_activities = sorted({
            _canon_activity(r.get("budget_ref_no"),
                            r.get("activity_name") or "")
            for r in rows if r.get("budget_ref_no") or r.get("activity_name")
        })
        filter_options = ["All activities"] + all_activities
        fcol, _ = st.columns([2, 3])
        with fcol:
            txn_filter = st.selectbox("Filter by Activity",
                                      filter_options, index=0,
                                      key="txn_filter")

        # Resolve every transaction's display name through the same canonical
        # lookup so old- and new-name rows alike match the filter selection.
        def _txn_canon(t):
            return _canon_activity(t.get("budget_ref_no"),
                                   t.get("activity_name") or "")

        shown = (txns if txn_filter == "All activities"
                 else [t for t in txns if _txn_canon(t) == txn_filter])

        if not shown:
            st.info("No transactions logged yet. "
                    "Use **➕ Log a New Transaction** below to add one.")
        else:
            shown_df = pd.DataFrame([{
                "Date":         t.get("transaction_date") or "",
                "Ref":          t.get("budget_ref_no") or "",
                "Activity":     _txn_canon(t),
                "Payee":        t.get("payee") or "",
                "Requested By": t.get("requested_by") or "",
                "RFAA No.":     t.get("rfaa_no") or "",
                "RFP No.":      t.get("rfp_no") or "",
                "College":      t.get("college") or "",
                "Amount":       _peso(_f(t.get("amount"))),
                "Notes":        t.get("notes") or "",
            } for t in shown])
            st.dataframe(
                shown_df, hide_index=True, use_container_width=True,
                column_config={
                    "Activity": st.column_config.TextColumn(
                        "Activity", width="large"),
                    "Notes":    st.column_config.TextColumn(
                        "Notes", width="medium"),
                },
            )
            sub_total = sum(_f(t.get("amount")) for t in shown)
            st.caption(f"**Subtotal of shown transactions:** {_peso(sub_total)} "
                       f"({len(shown)} transaction(s))")

        # ---- Expenditure by College × Activity (stacked) ----
        if txns:
            st.markdown(f"**Expenditure by College & Activity — {_ay_label(fy)}**")

            # Build a long-form dataframe: one row per (college, activity)
            # with total expenditure summed.
            ca_totals = {}
            for t in txns:
                col   = (t.get("college") or "Uncategorised").strip()
                act   = (_txn_canon(t) or "Uncategorised").strip()
                key   = (col, act)
                ca_totals[key] = ca_totals.get(key, 0) + _f(t.get("amount"))

            ca_df = pd.DataFrame([
                {"College": c, "Activity": a, "Expenditure": v}
                for (c, a), v in ca_totals.items()
            ])
            # Sort colleges by total expenditure (largest on top of the chart).
            col_totals = (ca_df.groupby("College")["Expenditure"].sum()
                          .sort_values(ascending=True))
            ca_df["College"] = pd.Categorical(
                ca_df["College"], categories=col_totals.index, ordered=True)
            ca_df = ca_df.sort_values(["College", "Activity"])

            fig_ca = px.bar(
                ca_df, x="Expenditure", y="College", color="Activity",
                orientation="h", height=420,
                hover_data={"Expenditure": ":,.2f"},
                color_discrete_sequence=BRAND_CHART_COLORS,
            )
            fig_ca.update_layout(
                barmode="stack",
                margin=dict(t=10, b=10, l=10, r=10),
                yaxis_title=None, xaxis_title="Expenditure (₱)",
                legend=dict(orientation="h", y=-0.15,
                            font=dict(size=10)),
            )
            st.plotly_chart(fig_ca, use_container_width=True)

    st.divider()

    # ---- Add new budget item ----
    BUDGET_COLLEGES = [
        "Institutional Research Office",
        "Medicine", "Nursing", "Med Tech", "Pharmacy",
        "Dentistry", "Optometry", "Physical Therapy",
        "Arts & Sciences", "Education", "Business and Management",
    ]
    _ACTIVITY_TEMPLATE = [
        ("000048", "Faculty Publication, Patents, Presentation (Fee Registration)"),
        ("000049", "Faculty Awards Incentives (Publication, Presentation, Patents, Product)"),
        ("000050", "In house Research Grants for Institution"),
        ("000051", "MCU Research Journal (Publication of 2 Issues/yr, printing, honorarium for reviewers)"),
        ("000052", "Membership Accreditation, Research Collaboration with Industry, University, Government (Fees, Transportation, Registration)"),
        ("000053", "Monthly Coordination Meeting"),
        ("000054", "Research Capacity Building"),
        ("000055", "Research Colloqium (Institutional and all programs)"),
        ("000056", "Research Presentation"),
        ("000057", "Student Journal"),
        ("000058", "Token Representation"),
    ]
    # Build refs for both AY2025-2026 (2025-prefix) and AY2026-2027 (2026-prefix).
    BUDGET_ACTIVITY_MAP = {
        f"{ay_prefix}{suffix}": name
        for ay_prefix in ("2025", "2026")
        for suffix, name in _ACTIVITY_TEMPLATE
    }
    BUDGET_ACTIVITIES = [f"{ref} — {name}"
                         for ref, name in BUDGET_ACTIVITY_MAP.items()] \
                        + ["Other (specify below)"]

    def _activity_name_from_pick(pick: str) -> str:
        """Strip the 'REF — ' prefix from a dropdown label."""
        if pick == "Other (specify below)":
            return ""
        return pick.split(" — ", 1)[1] if " — " in pick else pick

    def _label_for_activity(name: str) -> str:
        """Find the 'REF — NAME' label for a stored activity name."""
        for ref, n in BUDGET_ACTIVITY_MAP.items():
            if n == name:
                return f"{ref} — {n}"
        return "Other (specify below)"
    with st.expander("➕ Log a New Transaction", expanded=False):
        with st.form("add_iro_budget_form", clear_on_submit=True):
            ab1, ab2 = st.columns(2)
            with ab1:
                _default_ay = _ay_label(fy) if _ay_label(fy) in AY_OPTIONS \
                              else AY_OPTIONS[0]
                add_ay = st.selectbox("Academic Year *", AY_OPTIONS,
                                      index=AY_OPTIONS.index(_default_ay))
                add_fy = _year_from_ay(add_ay)
                add_payee = st.text_input("Payee",
                                          placeholder="Name of vendor / recipient")
                add_rfaa = st.text_input("RFAA No.",
                                         placeholder="Request for Allotment Advice No.")
            with ab2:
                add_college = st.selectbox("College *", BUDGET_COLLEGES,
                                           index=0)
                add_requester = st.text_input(
                    "Requested By",
                    placeholder="Name of faculty / staff requesting")
                add_rfp = st.text_input("RFP No.",
                                        placeholder="Request for Payment No.")
            ab3, _ = st.columns([1, 1])
            with ab3:
                add_txn_date = st.date_input("Transaction Date",
                                             value=date.today(),
                                             format="MM/DD/YYYY")
            add_activity_pick = st.selectbox("Activity Name *",
                                             BUDGET_ACTIVITIES, index=0)
            add_activity_custom = ""
            add_ref_custom = ""
            if add_activity_pick == "Other (specify below)":
                aoc1, aoc2 = st.columns([2, 1])
                with aoc1:
                    add_activity_custom = st.text_input(
                        "Custom Activity Name *", max_chars=300,
                        placeholder="Enter a new activity name")
                with aoc2:
                    add_ref_custom = st.text_input(
                        "Custom Budget Ref. No. *",
                        placeholder="e.g., 2025000059")
            add_activity = (add_activity_custom
                            if add_activity_pick == "Other (specify below)"
                            else _activity_name_from_pick(add_activity_pick))
            # Derive budget_ref_no: from the picked dropdown, or from custom field.
            if add_activity_pick == "Other (specify below)":
                add_ref = add_ref_custom
            else:
                add_ref = add_activity_pick.split(" — ", 1)[0]
            an4, _ = st.columns([1, 1])
            with an4:
                add_amount = st.number_input(
                    "Transaction Amount (₱) *",
                    min_value=0.0, value=0.0, step=100.0,
                    help="The amount being disbursed for this transaction. "
                         "Adds to the activity's running Utilised total.")
            add_notes = st.text_area("Notes", max_chars=500, height=70)
            save_bi = st.form_submit_button("💾 Save Transaction",
                                            type="primary")
            if save_bi:
                if not (add_ref and add_activity and add_amount > 0):
                    st.error("Activity Name and a Transaction Amount are required. "
                             "If you picked 'Other', also enter a custom Budget Ref. No.")
                else:
                    # Find the parent line item to link the transaction.
                    parent = next(
                        (it for it in items
                         if it.get("budget_ref_no") == add_ref
                         and int(it.get("fiscal_year") or 0) == int(add_fy)),
                        None)
                    if parent is None:
                        st.error(
                            f"No line item exists for {add_ref} in "
                            f"{_ay_label(add_fy)}. Add the line-item allocation "
                            f"first via Edit, or pick an existing activity.")
                    else:
                        txn = {
                            "budget_item_id":   parent.get("id"),
                            "fiscal_year":      int(add_fy),
                            "budget_ref_no":    add_ref,
                            "activity_name":    add_activity,
                            "transaction_date": str(add_txn_date) if add_txn_date else None,
                            "rfaa_no":          add_rfaa or None,
                            "rfp_no":           add_rfp or None,
                            "payee":            add_payee or None,
                            "requested_by":     add_requester or None,
                            "college":          add_college,
                            "amount":           float(add_amount),
                            "notes":            add_notes or None,
                            "created_by":       _USER.get("name") or None,
                        }
                        if db_insert("iro_budget_transactions", txn):
                            # Increment the parent line item's running utilised total.
                            new_util = _f(parent.get("utilized_budget")) + float(add_amount)
                            db_update("iro_budget_items", parent["id"],
                                      {"utilized_budget": new_util,
                                       "updated_at": datetime.now().isoformat()})
                            st.success(
                                f"✅ Logged ₱{add_amount:,.2f} against "
                                f"**{add_ref} — {add_activity}**. "
                                f"Running utilised total updated.")

    # ---- Edit existing transaction ----
    with st.expander("✏️ Edit Transaction", expanded=False):
        if not txn_table_ok:
            st.info("The transactions table doesn't exist yet — run "
                    "`add_iro_budget_transactions.sql` first.")
        elif not txns:
            st.info("No transactions for this academic year yet. "
                    "Log one via **➕ Log a New Transaction** below.")
        else:
            # Step 1 — pick the activity.
            act_options = sorted({t.get("activity_name") for t in txns
                                  if t.get("activity_name")})
            picked_activity = st.selectbox(
                "Step 1 — Pick an activity",
                [""] + act_options,
                key="edit_txn_activity_pick")

            t_ed = None
            if picked_activity:
                # Step 2 — pick a transaction in that activity.
                def _txn_label(t):
                    d = t.get("transaction_date") or "—"
                    ref = t.get("budget_ref_no") or "—"
                    payee = (t.get("payee") or "")[:30]
                    amt = _f(t.get("amount"))
                    return f"{d} · {ref} · {payee or '(no payee)'} · ₱{amt:,.2f}"

                act_txns = [t for t in txns
                            if t.get("activity_name") == picked_activity]
                if not act_txns:
                    st.info("No transactions logged for this activity yet.")
                else:
                    txn_picker = {_txn_label(t): i for i, t in enumerate(act_txns)}
                    pick = st.selectbox(
                        "Step 2 — Pick a transaction",
                        [""] + list(txn_picker.keys()),
                        key="edit_txn_txn_pick")
                    if pick:
                        t_ed = act_txns[txn_picker[pick]]

            if t_ed:
                old_amount = _f(t_ed.get("amount"))
                old_ref    = t_ed.get("budget_ref_no")
                old_item_id = t_ed.get("budget_item_id")
                # Filter the activity dropdown to options for the transaction's
                # AY only — avoids showing each activity twice (2025 + 2026).
                _ay_prefix = str(int(t_ed.get("fiscal_year") or fy))
                EDIT_ACTIVITY_OPTIONS = [
                    opt for opt in BUDGET_ACTIVITIES
                    if opt == "Other (specify below)"
                    or opt.startswith(_ay_prefix)
                ]
                with st.form(f"edit_iro_txn_form_{t_ed['id']}"):
                    st.caption(
                        f"Editing transaction currently under "
                        f"**{old_ref} — {t_ed.get('activity_name')}**.")
                    cur_activity_name = t_ed.get("activity_name") or ""
                    cur_label = _label_for_activity(cur_activity_name)
                    if cur_label not in EDIT_ACTIVITY_OPTIONS:
                        cur_label = "Other (specify below)"
                    _act_idx = EDIT_ACTIVITY_OPTIONS.index(cur_label)
                    e_activity_pick = st.selectbox(
                        "Activity *", EDIT_ACTIVITY_OPTIONS, index=_act_idx,
                        help="Change to re-link this transaction to a different "
                             "line item. The running utilised totals on both "
                             "the old and new activity will be adjusted.")
                    e_activity_custom = ""
                    e_ref_custom = ""
                    if e_activity_pick == "Other (specify below)":
                        eoc1, eoc2 = st.columns([2, 1])
                        with eoc1:
                            e_activity_custom = st.text_input(
                                "Custom Activity Name *",
                                value=(cur_activity_name
                                       if cur_label == "Other (specify below)"
                                       else ""),
                                max_chars=300)
                        with eoc2:
                            e_ref_custom = st.text_input(
                                "Custom Budget Ref. No. *",
                                value=(old_ref
                                       if cur_label == "Other (specify below)"
                                       else ""))
                        new_activity = e_activity_custom
                        new_ref = e_ref_custom
                    else:
                        new_activity = _activity_name_from_pick(e_activity_pick)
                        new_ref = e_activity_pick.split(" — ", 1)[0]
                    tec1, tec2 = st.columns(2)
                    cur_college = (t_ed.get("college")
                                   or "Institutional Research Office")
                    with tec1:
                        e_college = st.selectbox(
                            "College *", BUDGET_COLLEGES,
                            index=(BUDGET_COLLEGES.index(cur_college)
                                   if cur_college in BUDGET_COLLEGES else 0))
                        e_payee = st.text_input(
                            "Payee",
                            value=t_ed.get("payee") or "",
                            placeholder="Name of vendor / recipient")
                        e_rfaa = st.text_input(
                            "RFAA No.",
                            value=t_ed.get("rfaa_no") or "",
                            placeholder="Request for Allotment Advice No.")
                    with tec2:
                        _cur_td = t_ed.get("transaction_date")
                        try:
                            _td_val = (datetime.fromisoformat(str(_cur_td)).date()
                                       if _cur_td else date.today())
                        except Exception:
                            _td_val = date.today()
                        e_txn_date = st.date_input("Transaction Date",
                                                   value=_td_val,
                                                   format="MM/DD/YYYY")
                        e_requester = st.text_input(
                            "Requested By",
                            value=t_ed.get("requested_by") or "",
                            placeholder="Name of faculty / staff requesting")
                        e_rfp = st.text_input(
                            "RFP No.",
                            value=t_ed.get("rfp_no") or "",
                            placeholder="Request for Payment No.")
                    eta, _ = st.columns([1, 1])
                    with eta:
                        e_amount = st.number_input(
                            "Transaction Amount (₱) *",
                            min_value=0.0, step=100.0,
                            value=old_amount)
                    e_notes = st.text_area("Notes", max_chars=500, height=70,
                                           value=t_ed.get("notes") or "")
                    e_who = st.text_input("Your Name (for audit log) *",
                                          value=_USER.get("name") or "")
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        save_e = st.form_submit_button(
                            "💾 Save Changes", type="primary",
                            use_container_width=True)
                    with cb2:
                        del_e = st.form_submit_button(
                            "🗑️ Delete Transaction",
                            use_container_width=True)

                    old_parent = next(
                        (it for it in items if it.get("id") == old_item_id),
                        None)

                    if save_e:
                        if not (e_amount > 0 and e_who and new_activity and new_ref):
                            st.error("Transaction amount, activity, ref, and "
                                     "your name are all required.")
                        else:
                            activity_changed = (new_ref != old_ref)
                            new_parent = old_parent
                            if activity_changed:
                                new_parent = next(
                                    (it for it in items
                                     if it.get("budget_ref_no") == new_ref
                                     and int(it.get("fiscal_year") or 0) == int(fy)),
                                    None)
                                if new_parent is None:
                                    st.error(
                                        f"No line item exists for {new_ref} "
                                        f"in {_ay_label(fy)}. Set up the "
                                        f"allocation first before moving a "
                                        f"transaction here.")
                                    st.stop()

                            updates = {
                                "activity_name":    new_activity,
                                "budget_ref_no":    new_ref,
                                "budget_item_id":   new_parent.get("id")
                                                    if new_parent else None,
                                "college":          e_college,
                                "payee":            e_payee or None,
                                "rfaa_no":          e_rfaa or None,
                                "rfp_no":           e_rfp or None,
                                "transaction_date": str(e_txn_date) if e_txn_date else None,
                                "requested_by":     e_requester or None,
                                "amount":           float(e_amount),
                                "notes":            e_notes or None,
                            }
                            if db_update("iro_budget_transactions",
                                         t_ed["id"], updates):
                                if activity_changed:
                                    # Move the amount from old parent to new.
                                    if old_parent is not None:
                                        old_new_util = max(
                                            0.0,
                                            _f(old_parent.get("utilized_budget")) - old_amount)
                                        db_update("iro_budget_items",
                                                  old_parent["id"],
                                                  {"utilized_budget": old_new_util,
                                                   "updated_at": datetime.now().isoformat()})
                                    if new_parent is not None:
                                        new_new_util = (
                                            _f(new_parent.get("utilized_budget"))
                                            + float(e_amount))
                                        db_update("iro_budget_items",
                                                  new_parent["id"],
                                                  {"utilized_budget": new_new_util,
                                                   "updated_at": datetime.now().isoformat()})
                                    st.success(
                                        f"✅ Transaction moved to **{new_ref} — "
                                        f"{new_activity}** and saved. "
                                        f"Utilised totals on both activities updated.")
                                else:
                                    # Same parent — adjust by amount delta only.
                                    if old_parent is not None:
                                        delta = float(e_amount) - old_amount
                                        if delta != 0:
                                            new_util = max(
                                                0.0,
                                                _f(old_parent.get("utilized_budget")) + delta)
                                            db_update("iro_budget_items",
                                                      old_parent["id"],
                                                      {"utilized_budget": new_util,
                                                       "updated_at": datetime.now().isoformat()})
                                    st.success(
                                        f"✅ Transaction updated. Running utilised "
                                        f"total adjusted by "
                                        f"₱{(float(e_amount) - old_amount):,.2f}.")

                    if del_e:
                        try:
                            sb.table("iro_budget_transactions").delete() \
                              .eq("id", t_ed["id"]).execute()
                            # Decrement parent's utilised total by the deleted amount.
                            if old_parent is not None and old_amount > 0:
                                new_util = max(
                                    0.0,
                                    _f(old_parent.get("utilized_budget")) - old_amount)
                                db_update("iro_budget_items", old_parent["id"],
                                          {"utilized_budget": new_util,
                                           "updated_at": datetime.now().isoformat()})
                            st.success(
                                f"🗑️ Deleted transaction "
                                f"(₱{old_amount:,.2f}). Running utilised total "
                                f"reduced.")
                        except Exception as ex:
                            st.error(f"❌ Failed to delete: {ex}")


# ============================================================
# PAGE: MINUTES OF IRO MEETING (ADMIN ONLY)
# ============================================================
elif page == "IRO Meetings":
    require_roles("IRO Meetings", ["admin", "standard"])
    st.markdown('<div class="section-heading">IRO Meetings</div>',
                unsafe_allow_html=True)
    st.caption(
        "Record and review minutes from Institutional Research Office meetings "
        "— monthly coordination, ad-hoc discussions, executive committee, etc."
    )

    # Preflight
    schema_ok_m = True
    schema_msg_m = ""
    if sb is None:
        schema_ok_m = False
        schema_msg_m = "Database not configured."
    else:
        try:
            sb.table("iro_meeting_minutes").select("id").limit(1).execute()
        except Exception as ex:
            schema_ok_m = False
            schema_msg_m = f"`iro_meeting_minutes` table is missing ({ex})."

    if not schema_ok_m:
        st.warning(
            f"⚠️ {schema_msg_m}\n\n"
            f"Run **`add_iro_meeting_minutes.sql`** in the Supabase SQL Editor "
            f"to create the table, then refresh."
        )
        st.stop()

    minutes_rows = db_select("iro_meeting_minutes",
                             order_col="meeting_date", desc=True) or []

    m1, m2 = st.columns(2)
    m1.metric("Total Meetings Logged", len(minutes_rows))
    if minutes_rows:
        latest_raw = minutes_rows[0].get("meeting_date") or ""
        try:
            latest_str = datetime.fromisoformat(str(latest_raw)).strftime(
                "%m/%d/%Y")
        except Exception:
            latest_str = str(latest_raw)
        m2.metric("Most Recent", latest_str)
    else:
        m2.metric("Most Recent", "—")

    st.divider()

    # ----- Helpers shared by the table and the detail cards -----
    def _signed_doc_url(path: str, ttl_seconds: int = 3600,
                        download_name: str | None = None) -> str:
        """Return a signed URL for the meeting document, or ''.

        - download_name None → view URL (browser may preview or download
          depending on file type & Content-Disposition).
        - download_name given → URL that forces download as that filename.
        """
        if not (path and sb is not None):
            return ""
        try:
            res = sb.storage.from_("grant-reports") \
                            .create_signed_url(path, ttl_seconds)
            url = (res.get("signedURL")
                   or res.get("signed_url")
                   or "")
        except Exception:
            return ""
        if not url:
            return ""
        if download_name:
            from urllib.parse import quote
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}download={quote(download_name)}"
        return url

    def _view_url(path: str, filename: str = "") -> str:
        """URL that opens the document *in the browser*.

        PDFs / images / text render inline directly. Office files (Word,
        Excel, PowerPoint) can't be shown natively by a browser, so they
        are routed through the Microsoft Office web viewer, which renders
        them in-browser from the signed URL.
        """
        url = _signed_doc_url(path)
        if not url:
            return ""
        ext = (filename or path or "").lower().rsplit(".", 1)[-1]
        if ext in ("doc", "docx", "ppt", "pptx", "xls", "xlsx"):
            from urllib.parse import quote
            return ("https://view.officeapps.live.com/op/view.aspx?src="
                    + quote(url, safe=""))
        return url

    def _split_attendees(raw: str) -> list[str]:
        """Break the attendance text into individual names."""
        if not raw:
            return []
        parts = []
        for line in raw.splitlines():
            for piece in line.split(","):
                p = piece.strip().lstrip("•-*").strip()
                if p:
                    parts.append(p)
        return parts

    # ----- Past IRO Meetings (inline-editable table at the top) -----
    st.markdown("**Past IRO Meetings**")
    st.caption("Edit Date, Title, or Attendance directly in the table, then "
               "click **💾 Save table changes** below. "
               "Use **📥 Download** to save the uploaded document, or "
               "**👁 View** to open it within the browser.")

    if not minutes_rows:
        st.info("No meeting minutes logged yet. Use **➕ Log a Meeting** below.")
    else:
        table_rows = []
        for mr in minutes_rows:
            attendees_list = _split_attendees(mr.get("attendees") or "")
            attendees_full = "\n".join(attendees_list)
            path = mr.get("doc_path") or ""
            _dl_name = ((mr.get("doc_filenames") or [None])[0]
                        or (path.split("/")[-1] if path else None))
            download_url = (_signed_doc_url(path, download_name=_dl_name)
                            if path else "")
            view_url = _view_url(path, _dl_name) if path else ""

            try:
                date_val = (datetime.fromisoformat(str(mr.get("meeting_date"))).date()
                            if mr.get("meeting_date") else date.today())
            except Exception:
                date_val = date.today()

            table_rows.append({
                "Date":                  date_val,
                "Title":                 mr.get("meeting_title") or "",
                "No.":                   len(attendees_list),
                "Attendance":            attendees_full,
                "Download":              download_url,
                "View":                  view_url,
                "Logged By":             mr.get("submitted_by") or "",
            })

        df_orig = pd.DataFrame(table_rows)
        max_attendees = max((r["No."] for r in table_rows), default=1)
        row_h = min(20 + max_attendees * 22, 320)

        edited_df = st.data_editor(
            df_orig,
            hide_index=True, use_container_width=True,
            row_height=row_h,
            num_rows="fixed",
            key="past_iro_meetings_editor",
            column_config={
                "Date":       st.column_config.DateColumn(
                    "Date", format="MM/DD/YYYY"),
                "Title":      st.column_config.TextColumn(
                    "Title", width="medium"),
                "No.":        st.column_config.NumberColumn(
                    "No.", help="Attendee count", width="small",
                    disabled=True),
                "Attendance": st.column_config.TextColumn(
                    "Attendance", width="large",
                    help="Names of attendees, one per line"),
                "Download": st.column_config.LinkColumn(
                    "Download",
                    help="Download the uploaded meeting document",
                    display_text="📥 Download",
                    disabled=True),
                "View": st.column_config.LinkColumn(
                    "View",
                    help="View the document within the browser",
                    display_text="👁 View",
                    disabled=True),
                "Logged By":             st.column_config.TextColumn(
                    "Logged By", disabled=True),
            },
        )

        # Save edits explicitly — read the edits straight from the editor's
        # own state (the reliable source of truth), not a df comparison.
        if st.button("💾 Save table changes", type="primary",
                     key="save_iro_meetings"):
            editor_state = st.session_state.get("past_iro_meetings_editor", {})
            edited_rows = (editor_state.get("edited_rows", {})
                           if isinstance(editor_state, dict) else {})
            field_for = {"Date": "meeting_date", "Title": "meeting_title",
                         "Attendance": "attendees"}
            saved = failed = 0
            for row_pos, changed_cols in edited_rows.items():
                try:
                    mr = minutes_rows[int(row_pos)]
                except (IndexError, ValueError, TypeError):
                    continue
                changes = {}
                for col, field in field_for.items():
                    if col in changed_cols:
                        val = changed_cols[col]
                        if col == "Date":
                            val = str(val)
                        elif field == "meeting_title":
                            val = val or None
                        changes[field] = val
                if changes:
                    changes["updated_at"] = datetime.now().isoformat()
                    changes["updated_by"] = _USER.get("name") or "inline-edit"
                    if db_update("iro_meeting_minutes", mr["id"], changes):
                        saved += 1
                    else:
                        failed += 1   # db_update already shows the error
            if failed:
                st.error(f"❌ {failed} change(s) could not be saved "
                         "(see the error message above).")
            if saved:
                st.toast(f"✅ Saved {saved} change(s).")
                st.rerun()
            elif not failed:
                st.warning("No edits detected. Type in a cell, press **Enter** "
                           "(or click another cell) to commit it, then click "
                           "**Save table changes**.")

    st.divider()

    with st.form("add_iro_minutes_form", clear_on_submit=True):
        mc1, mc2 = st.columns([1, 2])
        with mc1:
            m_date = st.date_input("Meeting Date *",
                                   value=date.today(),
                                   format="MM/DD/YYYY")
        with mc2:
            m_title = st.text_input(
                "Meeting Title",
                placeholder="e.g., Monthly Coordination Meeting")

        m_attendees = st.text_area(
            "Attendance *", max_chars=2000, height=120,
            placeholder="One name per line, or comma-separated. "
                        "e.g., Dr. Charmaine Ng (Chair), Dr. Cruz, "
                        "Mr. De Leon …")

        st.markdown("**Meeting Document**")
        st.caption("Drag and drop a meeting minutes file below, **or** "
                   "paste the minutes text into the field underneath. "
                   "Either (or both) is fine.")

        m_doc = st.file_uploader(
            "Drop a file here (PDF, Word, image, etc.)",
            type=["pdf", "docx", "doc", "txt", "rtf", "md",
                  "xlsx", "xls", "csv",
                  "png", "jpg", "jpeg"],
            accept_multiple_files=False,
            help="Single file, max 200 MB",
        )

        m_minutes = st.text_area(
            "…or paste meeting minutes here",
            max_chars=20000, height=240,
            placeholder="Paste the meeting minutes / discussion notes "
                        "directly here.")

        m_submitted = st.form_submit_button("💾 Save Meeting",
                                            type="primary")
        if m_submitted:
            if not m_attendees:
                st.error("Attendance is required.")
            elif not (m_doc or m_minutes):
                st.error("Attach a document or paste the minutes "
                         "before saving.")
            else:
                # Upload the file to Supabase Storage (best-effort).
                doc_path = None
                if m_doc is not None and sb is not None:
                    try:
                        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                        doc_path = f"meeting-minutes/{m_date}_{ts}_{m_doc.name}"
                        # Guess content-type from filename if Streamlit
                        # didn't supply one — important so PDFs/images
                        # render inline when "Open" is clicked.
                        import mimetypes as _mt
                        ctype = m_doc.type or _mt.guess_type(
                            m_doc.name)[0] or "application/octet-stream"
                        sb.storage.from_("grant-reports").upload(
                            doc_path, m_doc.getvalue(),
                            {"content-type":        ctype,
                             "content-disposition": "inline"})
                    except Exception as e:
                        st.warning(
                            f"Binary upload failed: {e}. "
                            f"Metadata still saved.")

                row = {
                    "meeting_date":  str(m_date),
                    "meeting_title": m_title or None,
                    "attendees":     m_attendees,
                    "minutes":       m_minutes or None,
                    "doc_filenames": [m_doc.name] if m_doc else [],
                    "doc_path":      doc_path,
                    "submitted_by":  _USER.get("name") or None,
                }
                if db_insert("iro_meeting_minutes", row):
                    st.success(f"✅ Meeting logged for {m_date}.")


# ============================================================
# PAGE: USER MANAGEMENT (ADMIN ONLY)
# ============================================================
elif page == "User Management":
    require_admin("User Management")
    st.markdown('<div class="section-heading">User Management</div>',
                unsafe_allow_html=True)
    st.caption(
        "Manage the allowlist of users who can log into the IRO Dashboard. "
        "Only admins see this page."
    )

    # List current users
    users = db_select("allowed_users", order_col="added_at")
    if users:
        st.markdown(f"**{len(users)} users on the allowlist**")
        df = pd.DataFrame(users)
        if "role" in df.columns:
            df["role"] = df["role"].map(role_label)
        display_cols = [c for c in
                        ["email", "full_name", "role", "active",
                         "added_by", "added_at"] if c in df.columns]
        st.dataframe(
            df[display_cols] if display_cols else df,
            hide_index=True, use_container_width=True,
            column_config={
                "email": st.column_config.TextColumn("Email"),
                "full_name": st.column_config.TextColumn("Full Name", width="medium"),
                "role": st.column_config.TextColumn("Role"),
                "active": st.column_config.CheckboxColumn("Active"),
                "added_by": st.column_config.TextColumn("Added By"),
                "added_at": st.column_config.DatetimeColumn("Added",
                                                             format="YYYY-MM-DD HH:mm"),
            },
        )
    else:
        st.info("No users in the allowlist yet.")

    st.divider()

    # ----- Add new user -----
    st.markdown("### ➕ Add a New User to the Allowlist")
    with st.form("add_user_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_email = st.text_input("Email *", placeholder="name@mcu.edu.ph")
        with c2:
            new_name = st.text_input("Full Name *", placeholder="Dr. Juan Dela Cruz")
        new_role = st.selectbox("Role *", ["standard", "crc", "admin"], format_func=role_label)
        submit = st.form_submit_button("Add User", type="primary")

        if submit:
            if not (new_email and new_name):
                st.error("Email and full name are required.")
            else:
                row = {
                    "email": new_email.lower().strip(),
                    "full_name": new_name.strip(),
                    "role": new_role,
                    "added_by": _USER.get("email", "unknown"),
                }
                try:
                    sb.table("allowed_users").insert(row).execute()
                    st.success(f"✅ Added {new_name} ({new_email}) as {new_role}.")
                    st.caption(
                        f"They can now sign up at the login screen using **{new_email}** "
                        "to create their password."
                    )
                except Exception as e:
                    if "duplicate" in str(e).lower():
                        st.error(f"❌ {new_email} is already in the allowlist.")
                    else:
                        st.error(f"❌ Failed: {e}")

    st.divider()

    # ----- Toggle active / change role -----
    st.markdown("### ⚙️ Modify a User")
    if users:
        with st.form("modify_user_form"):
            target_emails = [u.get("email") for u in users]
            target = st.selectbox("Select user", target_emails)
            cc1, cc2 = st.columns(2)
            with cc1:
                new_role2 = st.selectbox("New Role",
                                         ["standard", "crc", "admin"],
                                         format_func=role_label,
                                         key="modify_role")
            with cc2:
                new_active = st.selectbox("Status",
                                          [True, False],
                                          format_func=lambda x: "Active" if x else "Disabled",
                                          key="modify_active")
            modify = st.form_submit_button("Update User", type="primary")

            if modify:
                target_user = next((u for u in users if u["email"] == target), None)
                if target_user:
                    try:
                        sb.table("allowed_users").update({
                            "role": new_role2,
                            "active": new_active,
                        }).eq("id", target_user["id"]).execute()
                        st.success(f"✅ Updated {target}.")
                    except Exception as e:
                        st.error(f"❌ Failed: {e}")

    # ----- Recent sign-ins — visible ONLY to the owner account -----
    LOGIN_LOG_VIEWER = "cmng@mcu.edu.ph"
    if (current_user() or {}).get("email", "").strip().lower() == LOGIN_LOG_VIEWER:
        st.divider()
        st.markdown("### 🕘 Recent Sign-Ins")
        st.caption("The most recent successful logins to the dashboard.")
        _logins = None
        try:
            _log_res = (sb.table("access_log").select("*")
                        .order("logged_in_at", desc=True).limit(100).execute())
            _logins = _log_res.data or []
        except Exception:
            st.info(
                "Sign-in logging isn't set up yet — run `add_access_log.sql` in the "
                "Supabase SQL Editor to create the `access_log` table."
            )
        if _logins is not None:
            if _logins:
                _ldf = pd.DataFrame(_logins)
                if "role" in _ldf.columns:
                    _ldf["role"] = _ldf["role"].map(role_label)
                _lcols = [c for c in ["logged_in_at", "full_name", "email", "role"]
                          if c in _ldf.columns]
                st.markdown(f"**{len(_logins)} most recent sign-ins**")
                st.dataframe(
                    _ldf[_lcols] if _lcols else _ldf,
                    hide_index=True, use_container_width=True,
                    column_config={
                        "logged_in_at": st.column_config.DatetimeColumn(
                            "Signed In", format="YYYY-MM-DD HH:mm"),
                        "full_name": st.column_config.TextColumn(
                            "Full Name", width="medium"),
                        "email": st.column_config.TextColumn("Email"),
                        "role": st.column_config.TextColumn("Role"),
                    },
                )
            else:
                st.info("No sign-ins recorded yet.")


# ============================================================
# PAGE: CRC REPORTS — submission tracker
# ============================================================
elif page == "CRC Reports":
    require_roles("CRC Reports", ["admin", "standard", "crc"])
    st.markdown('<div class="section-heading">CRC Reports — Submission Tracker</div>',
                unsafe_allow_html=True)
    st.caption("Monthly reports submitted by College Research Coordinators — "
               "who submitted, when, and whether a completed form was uploaded.")

    _crc_rows = db_select("crc_monthly_reports", order_col="submitted_at",
                          desc=True) or []
    if not _crc_rows:
        st.info("No CRC reports submitted yet.")
    else:
        cdf = pd.DataFrame(_crc_rows)
        _MONTHS_AB = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                      "Aug", "Sep", "Oct", "Nov", "Dec"]
        if "reporting_month" in cdf and "reporting_year" in cdf:
            cdf["reporting_month"] = pd.to_numeric(
                cdf["reporting_month"], errors="coerce").fillna(0).astype(int)
            cdf["reporting_year"] = pd.to_numeric(
                cdf["reporting_year"], errors="coerce").fillna(0).astype(int)
            cdf["Period"] = cdf.apply(
                lambda r: f"{_MONTHS_AB[r['reporting_month']] if 1 <= r['reporting_month'] <= 12 else '?'} "
                          f"{r['reporting_year']}", axis=1)
            cdf["period_key"] = cdf["reporting_year"] * 100 + cdf["reporting_month"]
        if "submitted_at" in cdf.columns:
            cdf["submitted_at"] = pd.to_datetime(cdf["submitted_at"], errors="coerce")
        cdf["Form"] = (cdf["doc_path"].notna() if "doc_path" in cdf.columns else False)

        # ----- Filters -----
        _fc1, _fc2 = st.columns(2)
        with _fc1:
            _years = (sorted(cdf["reporting_year"].unique().tolist(), reverse=True)
                      if "reporting_year" in cdf else [])
            _year_sel = st.multiselect("Year", _years, default=[])
        with _fc2:
            _colleges = (sorted(cdf["college"].dropna().unique().tolist())
                         if "college" in cdf else [])
            _college_sel = st.multiselect("College", _colleges, default=[])
        fdf = cdf.copy()
        if _year_sel:
            fdf = fdf[fdf["reporting_year"].isin(_year_sel)]
        if _college_sel:
            fdf = fdf[fdf["college"].isin(_college_sel)]

        # ----- KPIs -----
        import datetime as _dt2
        _this_year = _dt2.date.today().year
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Reports submitted", len(fdf))
        k2.metric("Colleges reporting",
                  int(fdf["college"].nunique()) if "college" in fdf else 0)
        k3.metric(f"This year ({_this_year})",
                  int((fdf["reporting_year"] == _this_year).sum())
                  if "reporting_year" in fdf else 0)
        k4.metric("With uploaded form", int(fdf["Form"].sum()))

        st.divider()

        _ca, _cb = st.columns(2)
        with _ca:
            if len(fdf) and "college" in fdf.columns:
                _bc = (fdf.groupby("college").size()
                       .reset_index(name="Reports").sort_values("Reports"))
                _figc = px.bar(_bc, x="Reports", y="college", orientation="h",
                               height=320, color_discrete_sequence=[BRAND["slate"]],
                               title="Reports submitted by college")
                _figc.update_layout(xaxis_title="Reports", yaxis_title=None,
                                    template="plotly_white",
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(_figc, use_container_width=True)
        with _cb:
            if len(fdf) and "period_key" in fdf.columns:
                _bm = (fdf.groupby(["period_key", "Period"]).size()
                       .reset_index(name="Reports").sort_values("period_key"))
                _figm = px.bar(_bm, x="Period", y="Reports", height=320,
                               color_discrete_sequence=[BRAND["tan"]],
                               title="Reports submitted by month")
                _figm.update_layout(xaxis_title=None, yaxis_title="Reports",
                                    template="plotly_white",
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)")
                _figm.update_xaxes(type="category")
                st.plotly_chart(_figm, use_container_width=True)

        st.divider()
        st.markdown("**Submissions**")
        _show = [c for c in ["Period", "college", "crc_name", "crc_email",
                             "Form", "submitted_at"] if c in fdf.columns]
        _tbl = (fdf.sort_values("period_key", ascending=False)
                if "period_key" in fdf.columns else fdf)
        st.dataframe(
            _tbl[_show] if _show else _tbl,
            hide_index=True, use_container_width=True,
            column_config={
                "college": st.column_config.TextColumn("College"),
                "crc_name": st.column_config.TextColumn("CRC"),
                "crc_email": st.column_config.TextColumn("Email"),
                "Form": st.column_config.CheckboxColumn("Form uploaded"),
                "submitted_at": st.column_config.DatetimeColumn(
                    "Submitted", format="YYYY-MM-DD HH:mm"),
            },
        )


# ============================================================
# PAGE: IN-HOUSE GRANT SUBMISSION
# ============================================================
elif page == "Submit CRC Monthly Report":
    st.markdown('<div class="section-heading">CRC Monthly Report — Submission</div>',
                unsafe_allow_html=True)
    st.caption(
        "Use this form to log a College Research Coordinator (CRC) monthly report. "
        "Each entry summarises the research activity for one college in one month."
    )

    # Downloadable blank form template.
    from pathlib import Path as _P
    _crc_form_path = _P(__file__).parent / "templates" / "CRC_Monthly_Report_Form.docx"
    if _crc_form_path.exists():
        st.download_button(
            "⬇️ Download the CRC Monthly Report Form",
            data=_crc_form_path.read_bytes(),
            file_name="CRC Monthly Report Form.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            help="The official blank form to fill out offline.",
        )

    # Preflight: warn if the table is missing but still show the form for preview.
    schema_ok = True
    schema_msg = ""
    has_progress_cols = False
    has_doc_path = False
    if sb is None:
        schema_ok = False
        schema_msg = "Database not configured."
    else:
        try:
            sb.table("crc_monthly_reports").select("id").limit(1).execute()
        except Exception as ex:
            schema_ok = False
            schema_msg = f"`crc_monthly_reports` table is missing ({ex})."
        # Detect the collaboration / Scopus-output columns (added later).
        try:
            sb.table("crc_monthly_reports").select("scopus_faculty").limit(1).execute()
            has_progress_cols = True
        except Exception:
            has_progress_cols = False
        # Detect the doc_path column (stores the uploaded completed form).
        try:
            sb.table("crc_monthly_reports").select("doc_path").limit(1).execute()
            has_doc_path = True
        except Exception:
            has_doc_path = False

    if not schema_ok:
        st.warning(
            f"⚠️ {schema_msg}\n\n"
            f"The form below is shown for preview. Submissions will fail until "
            f"you run **`add_crc_monthly_reports.sql`** in the Supabase SQL Editor."
        )
    elif not has_doc_path:
        st.info(
            "ℹ️ Uploaded forms won't be stored yet — run "
            "**`add_crc_progress_fields.sql`** (adds the `doc_path` column) in the "
            "Supabase SQL Editor. The report still submits."
        )

    import datetime as _dt
    _today = _dt.date.today()
    _months = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

    with st.form("crc_monthly_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_month = st.selectbox("Reporting Month *", _months, index=_today.month)
        with c2:
            r_year = st.number_input("Reporting Year *", min_value=2024,
                                     max_value=2035, value=_today.year, step=1)
        with c3:
            college = st.selectbox("College *",
                                   ["", "Medicine", "Nursing", "Med Tech", "Pharmacy",
                                    "Dentistry", "Optometry", "Physical Therapy",
                                    "Business and Management", "Others"])
        c4, c5 = st.columns(2)
        with c4:
            crc_name = st.text_input("CRC Name *", placeholder="Submitting coordinator")
        with c5:
            crc_email = st.text_input("CRC Email *")

        st.markdown("**📤 Upload completed form ***")
        completed_form = st.file_uploader(
            "Attach your filled-out CRC Monthly Report Form",
            type=["docx", "doc", "pdf"], accept_multiple_files=False,
            help="Download the form above, fill it out, then upload it here.")

        submitted = st.form_submit_button("Submit Report", type="primary")
        if submitted:
            if (not all([r_month, college, crc_name, crc_email])
                    or completed_form is None):
                st.error("Complete the period / college / name and attach your "
                         "completed form.")
            else:
                # Store the completed form in Supabase Storage (best-effort).
                crc_doc_path = None
                if sb is not None:
                    try:
                        import mimetypes as _mt
                        _ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                        crc_doc_path = (f"crc-reports/{int(r_year)}-"
                                        f"{_months.index(r_month):02d}_{college}_"
                                        f"{_ts}_{completed_form.name}")
                        _ctype = (completed_form.type
                                  or _mt.guess_type(completed_form.name)[0]
                                  or "application/octet-stream")
                        sb.storage.from_("grant-reports").upload(
                            crc_doc_path, completed_form.getvalue(),
                            {"content-type": _ctype,
                             "content-disposition": "inline"})
                    except Exception as e:
                        crc_doc_path = None
                        st.warning(f"Form upload failed: {e}. Submission still recorded.")

                row = {
                    "reporting_month": _months.index(r_month),
                    "reporting_year": int(r_year),
                    "college": college,
                    "crc_name": crc_name,
                    "crc_email": crc_email,
                    "activities_summary": "See uploaded completed form.",
                    "doc_filenames": [completed_form.name],
                    "status": "Submitted",
                }
                if has_doc_path and crc_doc_path:
                    row["doc_path"] = crc_doc_path
                if db_insert("crc_monthly_reports", row):
                    st.success(
                        f"✅ Report for **{college} — {r_month} {int(r_year)}** "
                        f"submitted.")

    # ----- Summary of submitted reports & achievements -----
    st.divider()
    st.markdown("### 📋 Summary of submitted reports & achievements")
    st.caption("Submitted CRC reports — most recent first. Open one to download "
               "the completed form.")
    _MONTHS_FULL = ["", "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]
    _reports = db_select("crc_monthly_reports", order_col="submitted_at",
                         desc=True) or []
    if not _reports:
        st.info("No reports submitted yet.")
    else:
        _scols = sorted({r.get("college") for r in _reports if r.get("college")})
        _sfilter = st.multiselect("Filter by college", _scols, default=[],
                                  key="crc_summary_college")
        _shown = 0
        for _rep in _reports:
            if _sfilter and _rep.get("college") not in _sfilter:
                continue
            _shown += 1
            try:
                _mn = int(_rep.get("reporting_month") or 0)
                _per = (f"{_MONTHS_FULL[_mn] if 1 <= _mn <= 12 else '?'} "
                        f"{int(_rep.get('reporting_year') or 0)}")
            except Exception:
                _per = "?"
            with st.expander(f"📅 {_per} — {_rep.get('college', '?')} · "
                             f"{_rep.get('crc_name', '?')}"):
                _dp = _rep.get("doc_path")
                _url = ""
                if _dp and sb is not None:
                    try:
                        _r = sb.storage.from_("grant-reports").create_signed_url(_dp, 3600)
                        _url = _r.get("signedURL") or _r.get("signed_url") or ""
                    except Exception:
                        _url = ""
                if _url:
                    st.link_button("📥 Download completed form", _url)
                else:
                    _fn = _rep.get("doc_filenames") or []
                    st.caption(f"Attached: {', '.join(_fn)}" if _fn
                               else "No form attached.")
                st.caption("Submitted "
                           + str(_rep.get("submitted_at", ""))[:19].replace("T", " ")
                           + (f" · {_rep.get('crc_email')}" if _rep.get("crc_email") else ""))
        if _sfilter and _shown == 0:
            st.info("No reports for the selected college(s).")


# ============================================================
# PAGE: IN-HOUSE GRANTS — downloadable forms
# ============================================================
elif page == "In-house grants":
    require_roles("In-house grants", ["admin", "standard", "crc"])
    st.markdown('<div class="section-heading">In-House Research Grants</div>',
                unsafe_allow_html=True)
    st.caption("Download the grant forms, submit completed application forms and "
               "progress reports, and view submissions.")

    from pathlib import Path as _P
    _tdir = _P(__file__).parent / "templates"
    _DOCX_MIME = ("application/vnd.openxmlformats-officedocument."
                  "wordprocessingml.document")
    _IHG_TABLE = "in_house_grant_submissions"
    _IHG_BUCKET = "grant-reports"
    _COLLEGES = ["", "Medicine", "Nursing", "Med Tech", "Pharmacy", "Dentistry",
                 "Optometry", "Physical Therapy", "Business and Management", "Others"]

    _ihg_ok = False
    if sb is not None:
        try:
            sb.table(_IHG_TABLE).select("id").limit(1).execute()
            _ihg_ok = True
        except Exception:
            _ihg_ok = False

    tab_dl, tab_submit, tab_view = st.tabs(
        ["📥 Download Forms", "📤 Submit", "📋 View Submissions"])

    # ---------- Download forms ----------
    with tab_dl:
        _grant_forms = [
            ("In-house Research Grant — Application Form",
             "IH_Grant_Application_Form.docx",
             "In-house Research Grant - Application Form.docx",
             "Apply for an in-house research grant."),
            ("Acceptance, Recommendation & Endorsement",
             "IH_Grant_Acceptance_Recommendation_Endorsement.docx",
             "In-house Research Grant - Acceptance, Recommendation, Endorsement.docx",
             "Acceptance / recommendation / endorsement of the awarded grant."),
            ("Memorandum of Agreement",
             "IH_Grant_Memorandum_of_Agreement.docx",
             "In-house Research Grant - Memorandum of Agreement.docx",
             "MOA between the grantee and MCU-IRO."),
            ("Waiver on the Disbursement of IRO Research Fund",
             "IH_Grant_Waiver_Disbursement.docx",
             "In-house Research Grant - Waiver on Disbursement of MCU-IRO Funds.docx",
             "Waiver on the disbursement and use of MCU-IRO funds."),
            ("In-house Research Grant — Progress Report",
             "IH_Grant_Progress_Report.docx",
             "In-house Research Grant - Progress Report.docx",
             "Periodic progress report for the funded project."),
        ]
        for _i, (_label, _fname, _dlname, _desc) in enumerate(_grant_forms, start=1):
            _fp = _tdir / _fname
            st.markdown(f"**{_i}. 📄 {_label}**")
            st.caption(_desc)
            if _fp.exists():
                st.download_button(
                    "⬇️ Download", data=_fp.read_bytes(),
                    file_name=_dlname, mime=_DOCX_MIME, key=f"dl_ihg_{_i}")
            else:
                st.caption("⚠️ Not yet available")
            st.divider()

    # ---------- Submit ----------
    with tab_submit:
        if not _ihg_ok:
            st.info("ℹ️ Submissions aren't set up yet — run "
                    "**`add_ih_grant_submissions.sql`** in the Supabase SQL "
                    "Editor to enable them.")
        st.caption("Upload a completed **Application Form** or **Progress Report**.")
        with st.form("ihg_submit_form", clear_on_submit=True):
            _stype = st.selectbox("Document type *",
                                  ["Application Form", "Progress Report"])
            _sc1, _sc2 = st.columns(2)
            with _sc1:
                _sname = st.text_input("Your name *")
            with _sc2:
                _semail = st.text_input("Email")
            _sc3, _sc4 = st.columns(2)
            with _sc3:
                _scollege = st.selectbox("College", _COLLEGES)
            with _sc4:
                _sproj_id = st.text_input(
                    "Project ID", placeholder="e.g., MCU-IHG-2026-0001")
            _sproject = st.text_input("Project title")
            _snotes = st.text_area("Notes (optional)", max_chars=500, height=80)
            _sfile = st.file_uploader("Completed form *",
                                      type=["docx", "doc", "pdf"],
                                      accept_multiple_files=False)
            _ssub = st.form_submit_button("📤 Submit", type="primary")
            if _ssub:
                if not _sname or _sfile is None:
                    st.error("Enter your name and attach the completed form.")
                elif not _ihg_ok:
                    st.error("Submissions table isn't set up yet (see note above).")
                else:
                    _doc_path = None
                    try:
                        import mimetypes as _mt
                        _ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                        _doc_path = f"in-house-grants/{_ts}_{_sfile.name}"
                        _ct = (_sfile.type or _mt.guess_type(_sfile.name)[0]
                               or "application/octet-stream")
                        sb.storage.from_(_IHG_BUCKET).upload(
                            _doc_path, _sfile.getvalue(),
                            {"content-type": _ct,
                             "content-disposition": "inline"})
                    except Exception as e:
                        _doc_path = None
                        st.warning(f"File upload failed: {e}. Submission recorded.")
                    _row = {
                        "submission_type": _stype,
                        "applicant_name": _sname,
                        "applicant_email": _semail or None,
                        "college": _scollege or None,
                        "project_id": _sproj_id or None,
                        "project_title": _sproject or None,
                        "notes": _snotes or None,
                        "doc_path": _doc_path,
                        "doc_filename": _sfile.name,
                    }
                    if db_insert(_IHG_TABLE, _row):
                        st.success(f"✅ {_stype} submitted. Thank you, {_sname}.")

    # ---------- View submissions ----------
    with tab_view:
        _subs = (db_select(_IHG_TABLE, order_col="submitted_at", desc=True)
                 if _ihg_ok else [])
        if not _ihg_ok:
            st.info("Submissions aren't set up yet.")
        elif not _subs:
            st.info("No submissions yet.")
        else:
            _vt1, _vt2 = st.columns(2)
            with _vt1:
                _tf = st.multiselect("Type",
                                     ["Application Form", "Progress Report"],
                                     default=[], key="ihg_view_type")
            with _vt2:
                _colls = sorted({s.get("college") for s in _subs if s.get("college")})
                _cf = st.multiselect("College", _colls, default=[],
                                     key="ihg_view_college")
            _shown = 0
            for _s in _subs:
                if _tf and _s.get("submission_type") not in _tf:
                    continue
                if _cf and _s.get("college") not in _cf:
                    continue
                _shown += 1
                _ttl = f"{_s.get('submission_type', '?')} — "
                if _s.get("project_id"):
                    _ttl += f"{_s['project_id']} · "
                _ttl += str(_s.get("applicant_name", "?"))
                if _s.get("project_title"):
                    _ttl += f" · {str(_s['project_title'])[:50]}"
                with st.expander(f"📄 {_ttl}"):
                    st.markdown(
                        f"**Project ID:** {_s.get('project_id') or '—'}  ·  "
                        f"**College:** {_s.get('college') or '—'}  ·  "
                        f"**Email:** {_s.get('applicant_email') or '—'}")
                    if _s.get("notes"):
                        st.caption(_s["notes"])
                    _dp = _s.get("doc_path")
                    if _dp and sb is not None:
                        try:
                            _r = sb.storage.from_(_IHG_BUCKET).create_signed_url(
                                _dp, 3600)
                            _u = _r.get("signedURL") or _r.get("signed_url") or ""
                        except Exception:
                            _u = ""
                        if _u:
                            st.link_button("📥 Download submitted file", _u)
                    st.caption("Submitted " + str(
                        _s.get("submitted_at", ""))[:19].replace("T", " "))
            if (_tf or _cf) and _shown == 0:
                st.info("No submissions match the filters.")


# ============================================================
# PAGE: EXTERNAL GRANT SUBMISSION / EDIT
# ============================================================
elif page == "External Grant Submission":
    st.markdown(
        '<div class="section-heading">External Grant — Submit &amp; Edit</div>',
        unsafe_allow_html=True,
    )

    # Preflight: warn (don't block) if the table is missing
    ext_table_ok = True
    if sb is not None:
        try:
            sb.table("external_grants").select("id").limit(1).execute()
        except Exception as ex:
            if "PGRST205" in str(ex) or "schema cache" in str(ex).lower():
                ext_table_ok = False

    if not ext_table_ok:
        st.warning(
            "⚠️ The `external_grants` table doesn't exist yet. "
            "Run **`add_external_grants.sql`** in the Supabase SQL Editor "
            "and click *Reload schema*. The form below is shown for preview "
            "— submissions will fail until the SQL is applied."
        )

    ext_action = st.radio(
        "Action",
        ["➕ Submit New Grant", "✏️ Edit Existing Grant"],
        horizontal=True, label_visibility="collapsed",
    )

    SOURCES = ["", "DOST-PCHRD", "MMHRDC", "CHED", "DA-BAR", "DOH",
               "Industry", "International", "NGO / Foundation", "Other"]
    COLLEGES = ["", "Medicine", "Nursing", "Med Tech", "Pharmacy",
                "Dentistry", "Optometry", "Physical Therapy",
                "Business and Management", "Others"]
    STATUSES = ["In Review", "Awarded",
                "Active", "Completed", "Cancelled"]

    # ===== Submit New =====
    if ext_action == "➕ Submit New Grant":
        st.caption(
            "Log a research grant received from a funder outside MCU."
        )
        with st.form("submit_external_grant", clear_on_submit=True):
            title = st.text_input("Project Title *", max_chars=250)
            c1, c2 = st.columns(2)
            with c1:
                pi = st.text_input("Principal Investigator *")
                college = st.selectbox("College / Department", COLLEGES)
                funding_source = st.selectbox("Funding Source *", SOURCES)
                funder_name = st.text_input(
                    "Funder Name (specific)",
                    placeholder="e.g., Pfizer Inc., DOST-PCHRD",
                )
            with c2:
                amount = st.number_input("Amount (₱) *", min_value=0.0,
                                         value=0.0, step=1000.0)
                duration = st.number_input("Duration (months)",
                                           min_value=0, max_value=120, value=12)
                date_submitted = st.date_input("Date Submitted",
                                               value=date.today())
                status = st.selectbox("Status *", STATUSES)

            contract_ref = st.text_input(
                "Contract / Award Number",
                placeholder="e.g., DOST-PCHRD-2025-042",
            )

            notes = st.text_area("Notes", max_chars=500, height=80)

            submit_ext = st.form_submit_button("📤 Submit Grant",
                                                type="primary")

            if submit_ext:
                if not (title and pi and funding_source and amount):
                    st.error(
                        "Title, PI, Funding Source, and Amount are required."
                    )
                else:
                    row = {
                        "title": title,
                        "pi": pi,
                        "college": college or None,
                        "funding_source": funding_source,
                        "funder_name": funder_name or None,
                        "amount": float(amount),
                        "currency": "PHP",
                        "duration_months": int(duration) if duration else None,
                        "date_submitted": (str(date_submitted)
                                           if date_submitted else None),
                        "status": status,
                        "contract_ref": contract_ref or None,
                        "notes": notes or None,
                        "submitted_by": (_USER.get("email")
                                         if _USER else None),
                    }
                    if db_insert("external_grants", row):
                        st.success(
                            f"✅ External grant '{title}' submitted."
                        )
                        st.balloons()

    # ===== Edit Existing =====
    if ext_action == "✏️ Edit Existing Grant":
        st.caption(
            "Pick a grant, update its fields, and the change is saved "
            "with your name + timestamp."
        )
        existing = db_select("external_grants",
                             order_col="date_submitted", desc=True) if sb else []
        if not existing:
            st.info("No external grants in the database yet. Submit one first.")
        else:
            labels = [
                f"[{g.get('date_submitted') or '—'}] {(g.get('title') or '')[:60]} · "
                f"{g.get('funding_source') or ''} · #{g.get('id')}"
                for g in existing
            ]
            pick_idx = st.selectbox(
                "Select grant to edit",
                options=range(len(existing)),
                format_func=lambda i: labels[i],
                key="ext_edit_pick",
            )
            g = existing[pick_idx]

            with st.form("edit_external_grant"):
                e_title = st.text_input("Project Title *",
                                        value=g.get("title") or "",
                                        max_chars=250)
                e1, e2 = st.columns(2)
                with e1:
                    e_pi = st.text_input("Principal Investigator *",
                                         value=g.get("pi") or "")
                    cur_col = g.get("college") or ""
                    e_college = st.selectbox(
                        "College / Department", COLLEGES,
                        index=COLLEGES.index(cur_col)
                        if cur_col in COLLEGES else 0,
                    )
                    cur_src = g.get("funding_source") or ""
                    e_src = st.selectbox(
                        "Funding Source *", SOURCES,
                        index=SOURCES.index(cur_src)
                        if cur_src in SOURCES else 0,
                    )
                    e_funder = st.text_input(
                        "Funder Name (specific)",
                        value=g.get("funder_name") or "",
                    )
                with e2:
                    e_amount = st.number_input(
                        "Amount (₱) *", min_value=0.0,
                        value=float(g.get("amount") or 0.0), step=1000.0,
                    )
                    e_duration = st.number_input(
                        "Duration (months)", min_value=0, max_value=120,
                        value=int(g.get("duration_months") or 12),
                    )
                    e_date_sub = st.date_input(
                        "Date Submitted",
                        value=(datetime.fromisoformat(
                            str(g.get("date_submitted"))).date()
                            if g.get("date_submitted") else None),
                    )
                    cur_st = g.get("status") or "In Review"
                    e_status = st.selectbox(
                        "Status *", STATUSES,
                        index=STATUSES.index(cur_st)
                        if cur_st in STATUSES else 0,
                    )

                e_contract = st.text_input(
                    "Contract / Award Number",
                    value=g.get("contract_ref") or "",
                )

                e_notes = st.text_area("Notes",
                                       value=g.get("notes") or "",
                                       max_chars=500, height=80)

                e_audit = st.text_input("Your Name (for audit log) *")

                ec1, ec2 = st.columns(2)
                with ec1:
                    save_btn = st.form_submit_button("💾 Save Changes",
                                                     type="primary")
                with ec2:
                    delete_btn = st.form_submit_button("🗑️ Delete Grant")

                if save_btn:
                    if not (e_title and e_pi and e_src and e_amount
                            and e_audit):
                        st.error(
                            "Title, PI, Funding Source, Amount, and your "
                            "name are required."
                        )
                    else:
                        updates = {
                            "title": e_title,
                            "pi": e_pi,
                            "college": e_college or None,
                            "funding_source": e_src,
                            "funder_name": e_funder or None,
                            "amount": float(e_amount),
                            "duration_months": int(e_duration)
                            if e_duration else None,
                            "date_submitted": (str(e_date_sub)
                                               if e_date_sub else None),
                            "status": e_status,
                            "contract_ref": e_contract or None,
                            "notes": e_notes or None,
                            "updated_by": e_audit,
                            "updated_at": datetime.now().isoformat(),
                        }
                        if db_update("external_grants", g["id"], updates):
                            st.success(
                                f"✅ Updated '{e_title}' "
                                f"(saved by {e_audit})."
                            )

                if delete_btn:
                    try:
                        sb.table("external_grants").delete()\
                          .eq("id", g["id"]).execute()
                        st.success(f"🗑️ Deleted: {g.get('title')}")
                    except Exception as ex:
                        st.error(f"❌ Failed to delete: {ex}")


# ============================================================
# PAGE: SUBMIT SCHOLARLY ENGAGEMENT
# ============================================================
elif page == "Submit Scholarly Engagement":
    st.markdown('<div class="section-heading">'
                'Scholarly Engagement — Submit &amp; Edit</div>',
                unsafe_allow_html=True)

    # Preflight: make sure both tables exist. Show a warning if not,
    # but still render the form so the user can see the layout.
    schema_ok = True
    schema_msg = ""
    if sb is None:
        schema_ok = False
        schema_msg = "Database not configured."
    else:
        try:
            sb.table("research_events_attended").select("id").limit(1).execute()
        except Exception as ex:
            schema_ok = False
            schema_msg = f"`research_events_attended` table is missing ({ex})."
        try:
            sb.table("research_event_attendees").select("id").limit(1).execute()
        except Exception as ex:
            schema_ok = False
            schema_msg = (
                f"`research_event_attendees` child table is missing ({ex})."
            )

    if not schema_ok:
        st.warning(
            f"⚠️ {schema_msg}\n\n"
            f"The form below is shown for preview. Submissions will fail until "
            f"you run **`add_research_events_attended.sql`** in the Supabase "
            f"SQL Editor and click *Reload schema*."
        )

    rea_action = st.radio(
        "Action",
        ["➕ Submit New Event", "✏️ Edit Existing Event"],
        horizontal=True, label_visibility="collapsed",
    )

    EVENT_TYPES = ["", "Conference", "Congress", "Workshop", "Seminar",
                   "Webinar", "Symposium", "Training", "Other"]
    ROLES = ["Attendee", "Presenter", "Keynote Speaker",
             "Panelist", "Chair", "Moderator"]

    def _blank_attendee():
        return {"name": "", "college": "", "role": "Attendee",
                "presentation_title": "", "award": ""}

    def _render_attendee_rows(state_key: str):
        """Render dynamic attendee rows backed by st.session_state[state_key]."""
        rows = st.session_state[state_key]
        for i, att in enumerate(rows):
            cols = st.columns([3, 2, 2, 3, 3, 1])
            att["name"] = cols[0].text_input(
                "Name" if i == 0 else " ",
                value=att.get("name") or "",
                key=f"{state_key}_name_{i}",
                placeholder="Full name",
                label_visibility="visible" if i == 0 else "collapsed",
            )
            att["college"] = cols[1].text_input(
                "College / Dept." if i == 0 else " ",
                value=att.get("college") or "",
                key=f"{state_key}_college_{i}",
                placeholder="e.g., COM",
                label_visibility="visible" if i == 0 else "collapsed",
            )
            cur_role = att.get("role") or "Attendee"
            att["role"] = cols[2].selectbox(
                "Role" if i == 0 else " ",
                ROLES,
                index=ROLES.index(cur_role) if cur_role in ROLES else 0,
                key=f"{state_key}_role_{i}",
                label_visibility="visible" if i == 0 else "collapsed",
            )
            att["presentation_title"] = cols[3].text_input(
                "Presentation Title (if any)" if i == 0 else " ",
                value=att.get("presentation_title") or "",
                key=f"{state_key}_pres_{i}",
                placeholder="Leave blank for attendee-only",
                label_visibility="visible" if i == 0 else "collapsed",
            )
            att["award"] = cols[4].text_input(
                "Award (if any)" if i == 0 else " ",
                value=att.get("award") or "",
                key=f"{state_key}_award_{i}",
                placeholder="e.g., Best Paper, 1st Place",
                label_visibility="visible" if i == 0 else "collapsed",
            )
            with cols[5]:
                if i == 0:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                if len(rows) > 1:
                    if st.button("✖", key=f"{state_key}_del_{i}",
                                 help="Remove this attendee"):
                        rows.pop(i)
                        st.rerun()

    # ===== Submit New =====
    if rea_action == "➕ Submit New Event":
        st.caption(
            "Log a scholarly engagement (conference, congress, workshop, webinar) "
            "that one or more MCU faculty/staff attended or presented at."
        )

        # Confirmation card for the most recent successful submission.
        last = st.session_state.get("rea_last_logged")
        if last:
            att_lines = "".join(
                f'<li style="margin-bottom:2px;">'
                f'<b>{a["name"]}</b> <span style="color:#6b7280;'
                f'font-size:11px;">— {a["role"]}'
                + (f": <i>{a['presentation_title']}</i>"
                   if a.get("presentation_title") else "") + '</span></li>'
                for a in last["attendees"]
            )
            date_str = last["start_date"]
            if last.get("end_date"):
                date_str += f" – {last['end_date']}"
            st.markdown(
                f'<div style="background:#ecfdf5;border:1px solid #10b981;'
                f'border-radius:8px;padding:12px 14px;margin-bottom:8px;">'
                f'<div style="font-weight:700;color:#065f46;font-size:13px;'
                f'margin-bottom:4px;">✅ Just logged</div>'
                f'<div style="font-weight:600;color:{NAVY};font-size:14px;">'
                f'{last["event_title"]}</div>'
                f'<div style="font-size:11px;color:#6b7280;margin-bottom:6px;">'
                f'{date_str} · {last.get("event_type") or "—"} · '
                f'{last.get("location") or "—"} · '
                f'{last.get("organizer") or "—"}</div>'
                f'<ul style="margin:4px 0 0 16px;padding:0;font-size:12px;'
                f'color:#374151;">{att_lines}</ul>'
                f'<div style="margin-top:6px;font-size:11px;color:#065f46;">'
                f'Visit <b>Data → 🎤 Scholarly Engagements</b> to see it '
                f'in the table.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Dismiss", key="rea_dismiss_confirm"):
                st.session_state.pop("rea_last_logged", None)
                st.rerun()

        # ----- Event metadata -----
        event_title = st.text_input(
            "Event Title *", max_chars=250,
            key="rea_new_title",
            placeholder="e.g., 2026 ASEAN Microbiology Congress",
        )
        r1, r2 = st.columns(2)
        with r1:
            start = st.date_input("Start Date *", value=date.today(),
                                  key="rea_new_start")
            event_type = st.selectbox("Event Type *", EVENT_TYPES,
                                      key="rea_new_type")
            location = st.text_input(
                "Location", key="rea_new_location",
                placeholder="e.g., Manila, Philippines / Online",
            )
        with r2:
            end = st.date_input("End Date (if multi-day)",
                                value=date.today(), key="rea_new_end")
            organizer = st.text_input("Organizer / Host",
                                      key="rea_new_organizer")
            certificate = st.text_input(
                "Certificate (filename or link)",
                key="rea_new_cert",
                placeholder="e.g., cert_ASEAN2026.pdf or https://...",
            )

        notes = st.text_area("Notes (optional)", key="rea_new_notes",
                             max_chars=500, height=70)

        # ----- Attendees -----
        st.markdown("**👥 Attendees / Presenters**")
        st.caption(
            "Add one row per MCU attendee. Set Role to *Presenter / Keynote / "
            "Panelist / Chair / Moderator* and fill the presentation title "
            "if they presented."
        )
        if "rea_new_attendees" not in st.session_state:
            st.session_state.rea_new_attendees = [_blank_attendee()]

        _render_attendee_rows("rea_new_attendees")

        add_c, _spacer = st.columns([1, 5])
        with add_c:
            if st.button("➕ Add Attendee", key="rea_new_add"):
                st.session_state.rea_new_attendees.append(_blank_attendee())
                st.rerun()

        st.divider()
        if st.button("📤 Submit Event", type="primary", key="rea_new_submit"):
            attendees_clean = [
                a for a in st.session_state.rea_new_attendees
                if (a.get("name") or "").strip()
            ]
            if not (event_title and event_type):
                st.error("Please fill in event title and event type.")
            elif not attendees_clean:
                st.error("Add at least one attendee with a name.")
            else:
                row = {
                    "event_title": event_title,
                    "event_type": event_type or None,
                    "start_date": str(start),
                    "end_date": str(end) if end != start else None,
                    "location": location or None,
                    "organizer": organizer or None,
                    "certificate": certificate or None,
                    "notes": notes or None,
                    "submitted_by": (_USER.get("email") if _USER else None),
                }
                new_id = None
                try:
                    res = sb.table("research_events_attended")\
                            .insert(row).execute()
                    new_id = res.data[0]["id"]
                    for a in attendees_clean:
                        sb.table("research_event_attendees").insert({
                            "event_id": new_id,
                            "attendee_name": a["name"].strip(),
                            "attendee_college": (a.get("college") or "").strip() or None,
                            "role": a.get("role") or "Attendee",
                            "presentation_title":
                                (a.get("presentation_title") or "").strip() or None,
                            "award": (a.get("award") or "").strip() or None,
                        }).execute()
                    st.success(
                        f"✅ Event '{event_title}' logged with "
                        f"{len(attendees_clean)} attendee(s). "
                        f"View it under **Data → 🎤 Scholarly Engagements**."
                    )
                    st.balloons()
                    # Stash a snapshot of what was just logged so the next rerun
                    # can show a confirmation card.
                    st.session_state["rea_last_logged"] = {
                        "event_title": event_title,
                        "start_date": str(start),
                        "end_date": str(end) if end != start else None,
                        "event_type": event_type,
                        "location": location,
                        "organizer": organizer,
                        "attendees": [
                            {"name": a["name"].strip(),
                             "role": a.get("role") or "Attendee",
                             "presentation_title":
                                 (a.get("presentation_title") or "").strip()}
                            for a in attendees_clean
                        ],
                    }
                    # Reset form
                    st.session_state.rea_new_attendees = [_blank_attendee()]
                    for k in ("rea_new_title", "rea_new_location",
                              "rea_new_organizer", "rea_new_cert",
                              "rea_new_notes"):
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as ex:
                    # Roll back the parent if it was created but children failed.
                    if new_id is not None:
                        try:
                            sb.table("research_events_attended").delete()\
                              .eq("id", new_id).execute()
                        except Exception:
                            pass
                    st.error(f"❌ Failed to submit event: {ex}")

    # ===== Edit Existing =====
    if rea_action == "✏️ Edit Existing Event":
        st.caption(
            "Pick an event, update its fields and attendee list, then save."
        )

        events_for_edit = db_select("research_events_attended",
                                    order_col="start_date",
                                    desc=True) if sb else []
        if not events_for_edit:
            st.info("No events in the database yet. Submit one first.")
        else:
            ev_labels = [
                f"[{e.get('start_date')}] {(e.get('event_title') or '')[:70]} "
                f"· #{e.get('id')}"
                for e in events_for_edit
            ]
            pick_idx = st.selectbox(
                "Select event to edit",
                options=range(len(events_for_edit)),
                format_func=lambda i: ev_labels[i],
                key="rea_edit_pick",
            )
            ev = events_for_edit[pick_idx]

            # Load attendees fresh whenever the picked event changes.
            if st.session_state.get("rea_edit_loaded_id") != ev["id"]:
                attendees_existing = db_select(
                    "research_event_attendees", order_col="id"
                ) or []
                attendees_existing = [
                    a for a in attendees_existing
                    if a.get("event_id") == ev["id"]
                ]
                st.session_state.rea_edit_attendees = [
                    {
                        "id": a.get("id"),
                        "name": a.get("attendee_name") or "",
                        "college": a.get("attendee_college") or "",
                        "role": a.get("role") or "Attendee",
                        "presentation_title": a.get("presentation_title") or "",
                        "award": a.get("award") or "",
                    }
                    for a in attendees_existing
                ] or [_blank_attendee()]
                st.session_state.rea_edit_loaded_id = ev["id"]
                # Clear stale widget keys from previous event
                for k in list(st.session_state.keys()):
                    if k.startswith("rea_edit_attendees_"):
                        del st.session_state[k]

            # ----- Event metadata -----
            title2 = st.text_input(
                "Event Title *", value=ev.get("event_title") or "",
                max_chars=250, key=f"rea_edit_title_{ev['id']}",
            )
            e1, e2 = st.columns(2)
            with e1:
                start2 = st.date_input(
                    "Start Date *",
                    value=(datetime.fromisoformat(
                        str(ev.get("start_date"))).date()
                        if ev.get("start_date") else date.today()),
                    key=f"rea_edit_start_{ev['id']}",
                )
                type_cur = ev.get("event_type") or ""
                type2 = st.selectbox(
                    "Event Type *", EVENT_TYPES,
                    index=EVENT_TYPES.index(type_cur)
                    if type_cur in EVENT_TYPES else 0,
                    key=f"rea_edit_type_{ev['id']}",
                )
                location2 = st.text_input(
                    "Location", value=ev.get("location") or "",
                    key=f"rea_edit_loc_{ev['id']}",
                )
            with e2:
                end2 = st.date_input(
                    "End Date (if multi-day)",
                    value=(datetime.fromisoformat(
                        str(ev.get("end_date"))).date()
                        if ev.get("end_date") else start2),
                    key=f"rea_edit_end_{ev['id']}",
                )
                organizer2 = st.text_input(
                    "Organizer / Host", value=ev.get("organizer") or "",
                    key=f"rea_edit_org_{ev['id']}",
                )
                cert2 = st.text_input(
                    "Certificate (filename or link)",
                    value=ev.get("certificate") or "",
                    key=f"rea_edit_cert_{ev['id']}",
                )

            notes2 = st.text_area(
                "Notes (optional)", value=ev.get("notes") or "",
                max_chars=500, height=70,
                key=f"rea_edit_notes_{ev['id']}",
            )

            # ----- Attendees -----
            st.markdown("**👥 Attendees / Presenters**")
            _render_attendee_rows("rea_edit_attendees")

            add_c, _spacer = st.columns([1, 5])
            with add_c:
                if st.button("➕ Add Attendee", key="rea_edit_add"):
                    st.session_state.rea_edit_attendees.append(_blank_attendee())
                    st.rerun()

            your_name = st.text_input("Your Name (for audit log) *",
                                      key=f"rea_edit_audit_{ev['id']}")

            st.divider()
            save_c, del_c = st.columns(2)
            save_btn = save_c.button("💾 Save Changes", type="primary",
                                     key="rea_edit_save")
            delete_btn = del_c.button("🗑️ Delete Event",
                                      key="rea_edit_delete")

            if save_btn:
                attendees_clean = [
                    a for a in st.session_state.rea_edit_attendees
                    if (a.get("name") or "").strip()
                ]
                if not (title2 and type2 and your_name):
                    st.error("Title, type and your name are required.")
                elif not attendees_clean:
                    st.error("At least one attendee with a name is required.")
                else:
                    updates = {
                        "event_title": title2,
                        "event_type": type2,
                        "start_date": str(start2),
                        "end_date": str(end2) if end2 != start2 else None,
                        "location": location2 or None,
                        "organizer": organizer2 or None,
                        "certificate": cert2 or None,
                        "notes": notes2 or None,
                        "updated_by": your_name,
                        "updated_at": datetime.now().isoformat(),
                    }
                    if db_update("research_events_attended",
                                 ev["id"], updates):
                        try:
                            # Replace attendees: delete-all-then-insert
                            sb.table("research_event_attendees").delete()\
                              .eq("event_id", ev["id"]).execute()
                            for a in attendees_clean:
                                sb.table("research_event_attendees").insert({
                                    "event_id": ev["id"],
                                    "attendee_name": a["name"].strip(),
                                    "attendee_college":
                                        (a.get("college") or "").strip() or None,
                                    "role": a.get("role") or "Attendee",
                                    "presentation_title":
                                        (a.get("presentation_title") or "").strip()
                                        or None,
                                    "award":
                                        (a.get("award") or "").strip() or None,
                                }).execute()
                            st.success(
                                f"✅ Updated '{title2}' with "
                                f"{len(attendees_clean)} attendee(s) "
                                f"(saved by {your_name})."
                            )
                        except Exception as ex:
                            st.error(f"❌ Failed to update attendees: {ex}")

            if delete_btn:
                try:
                    sb.table("research_events_attended").delete()\
                      .eq("id", ev["id"]).execute()
                    st.success(f"🗑️ Deleted: {ev.get('event_title')}")
                    st.session_state.pop("rea_edit_loaded_id", None)
                    st.session_state.pop("rea_edit_attendees", None)
                except Exception as ex:
                    st.error(f"❌ Failed to delete: {ex}")


# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("Manila Central University · Institutional Research Office · Prototype — figures are illustrative")
