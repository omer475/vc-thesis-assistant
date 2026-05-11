"""Design tokens and global CSS injection.

Visual language: minimalist, near-black background with muted sage/teal accents.
Serif headings paired with sans-serif body. Generous spacing throughout.

All visual constants come from this module. Components reference these values
by name; `src/app.py` calls `inject_global_css()` once per route at startup.
"""

from __future__ import annotations

import streamlit as st


# ----- Colors ----------------------------------------------------------------

# Foundation — near-black charcoal with subtle warmth
BG_PAGE = "#1A1D1C"           # outermost page background (deep charcoal)
BG_CARD = "#22272A"           # cards, main content surfaces
BG_SIDEBAR = "#161918"        # sidebar — slightly darker than page
BG_ELEVATED = "#2A2F31"       # elevated surfaces (modals, dropdowns)
BG_TABLE_HEAD = "#1E2322"     # subtle table header tint
BG_INPUT = "#2A2F31"          # input field background

BORDER_DEFAULT = "rgba(255, 255, 255, 0.08)"
BORDER_HOVER = "rgba(255, 255, 255, 0.16)"
BORDER_FOCUS = "rgba(154, 184, 168, 0.45)"

# Text — soft, never pure white
TEXT_PRIMARY = "#E6E4DE"       # warm off-white
TEXT_SECONDARY = "#A8ADAB"     # muted gray
TEXT_TERTIARY = "#6B7270"      # tertiary / labels

# Accent — muted sage / teal
ACCENT = "#9AB8A8"             # sage primary accent
ACCENT_HOVER = "#AECABA"
ACCENT_MUTED = "#3D4844"       # deeper sage for backgrounds
ACCENT_DARK = "#2D3633"

# Verdict ramps — desaturated, muted
TAKE_BG = "#2C3A30"            # muted forest
TAKE_TEXT = "#A8C9B0"
TAKE_BORDER = "#3F5A48"
TAKE_DOT = "#7FA88E"

ASK_BG = "#3A352A"             # muted amber/olive
ASK_TEXT = "#D4B98C"
ASK_BORDER = "#5A4E38"
ASK_DOT = "#B8A074"

PASS_BG = "#3A2C2C"            # muted rose
PASS_TEXT = "#C9A8A8"
PASS_BORDER = "#5A3F3F"
PASS_DOT = "#A88080"


# ----- Typography ------------------------------------------------------------

# Serif for headings — soft, refined
FONT_SERIF = '"Cormorant Garamond", "Playfair Display", Georgia, "Times New Roman", serif'

# Sans-serif for body — clean and quiet
FONT_SANS = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

FONT_STACK = FONT_SANS  # backwards-compat alias


# ----- Spacing & shape -------------------------------------------------------

RADIUS_SM = "8px"
RADIUS_MD = "12px"
RADIUS_LG = "16px"
RADIUS_XL = "20px"

PADDING_CARD = "28px"
PADDING_DEAL = "40px"
PADDING_SIDEBAR = "20px 16px"
PADDING_MAIN = "32px 36px"

GAP_SECTION = "36px"
GAP_ROW = "12px"

# Soft, muted shadows — depth without contrast
SHADOW_SOFT = "0 1px 3px rgba(0, 0, 0, 0.18), 0 1px 2px rgba(0, 0, 0, 0.12)"
SHADOW_MEDIUM = "0 4px 12px rgba(0, 0, 0, 0.22), 0 2px 4px rgba(0, 0, 0, 0.14)"


# ----- CSS blocks ------------------------------------------------------------

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Cormorant+Garamond:wght@400;500;600&"
    "family=Inter:wght@300;400;500;600&"
    "display=swap"
)

_TABLER_ICONS_CSS_URL = (
    "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3/dist/tabler-icons.min.css"
)


def _global_css() -> str:
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{_GOOGLE_FONTS_URL}">
<link rel="stylesheet" href="{_TABLER_ICONS_CSS_URL}">
<style>
/* ---- Hide Streamlit chrome ---- */
#MainMenu,
header[data-testid="stHeader"],
header,
footer,
.stDeployButton,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeader"],
button[kind="header"] {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
}}

/* ---- Page foundation ---- */
html, body, .stApp, [data-testid="stAppViewContainer"] {{
    background: {BG_PAGE} !important;
    font-family: {FONT_SANS} !important;
    color: {TEXT_PRIMARY};
}}
.stApp {{
    background: {BG_PAGE} !important;
}}
.block-container,
[data-testid="block-container"],
.main .block-container {{
    padding-top: 32px !important;
    padding-bottom: 40px !important;
    max-width: 1180px !important;
}}

/* ---- Sidebar — always open, no collapse control ---- */
[data-testid="stSidebar"],
section[data-testid="stSidebar"] {{
    background: {BG_SIDEBAR} !important;
    border-right: 1px solid {BORDER_DEFAULT};
    width: 248px !important;
    min-width: 248px !important;
    transform: translateX(0) !important;
    visibility: visible !important;
}}
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    padding: 24px 16px !important;
    background: {BG_SIDEBAR} !important;
}}
/* Kill all backgrounds and box borders that streamlit-option-menu adds */
[data-testid="stSidebar"] [class*="st-emotion-cache"],
[data-testid="stSidebar"] .element-container,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"],
[data-testid="stSidebar"] iframe[title*="option_menu"] {{
    background: transparent !important;
}}
/* The streamlit-option-menu renders inside an iframe with its own wrapper —
   target the container chain that gives it the boxed look */
[data-testid="stSidebar"] .nav,
[data-testid="stSidebar"] ul,
[data-testid="stSidebar"] ul.nav,
[data-testid="stSidebar"] nav,
[data-testid="stSidebar"] nav > ul,
[data-testid="stSidebar"] .menu,
[data-testid="stSidebar"] [class*="menu"] {{
    background: transparent !important;
    background-color: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}
/* Tighten any vertical block in the sidebar so items move up */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    gap: 4px !important;
}}
/* Hide the sidebar collapse/expand button so the sidebar is permanently visible */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[kind="headerNoPadding"],
[data-testid="stSidebar"] button[aria-label*="collapse" i],
[data-testid="stSidebar"] button[aria-label*="close" i],
[data-testid="stSidebar"] [data-testid="baseButton-headerNoPadding"] {{
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
}}
/* Make sure the main content doesn't shift when sidebar is "collapsed" */
[data-testid="stSidebar"][aria-expanded="false"] {{
    margin-left: 0 !important;
    transform: translateX(0) !important;
    visibility: visible !important;
}}

/* ---- Buttons — consistent sizing, predictable rhythm ---- */
.stButton button,
[data-testid="stButton"] button,
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"] {{
    height: 40px !important;
    min-height: 40px !important;
    border-radius: {RADIUS_SM} !important;
    font-family: {FONT_SANS} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 0 18px !important;
    transition: background 0.15s ease, border-color 0.15s ease, transform 0.05s ease;
    box-shadow: none !important;
    line-height: 1 !important;
    letter-spacing: 0.01em;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}}
.stButton button[kind="primary"],
button[data-testid="baseButton-primary"] {{
    background: {ACCENT} !important;
    color: {BG_PAGE} !important;
    border: none !important;
}}
.stButton button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {{
    background: {ACCENT_HOVER} !important;
    color: {BG_PAGE} !important;
}}
.stButton button[kind="primary"]:active {{
    transform: translateY(1px);
}}
.stButton button[kind="secondary"],
button[data-testid="baseButton-secondary"] {{
    background: transparent !important;
    color: {TEXT_PRIMARY} !important;
    border: 1px solid {BORDER_HOVER} !important;
}}
.stButton button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover {{
    border-color: {ACCENT} !important;
    color: {TEXT_PRIMARY} !important;
    background: rgba(154, 184, 168, 0.05) !important;
}}
.stButton button[disabled],
.stButton button[disabled]:hover {{
    opacity: 0.4 !important;
    cursor: not-allowed !important;
}}
.stDownloadButton button {{
    height: 40px !important;
    border-radius: {RADIUS_SM} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 0 18px !important;
    background: transparent !important;
    color: {TEXT_PRIMARY} !important;
    border: 1px solid {BORDER_HOVER} !important;
}}

/* ---- Inputs (CRITICAL: ensure text visibility on dark theme) ---- */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {{
    border-radius: {RADIUS_SM} !important;
    border: 1px solid {BORDER_HOVER} !important;
    font-size: 14px !important;
    font-family: {FONT_SANS} !important;
    background: {BG_INPUT} !important;
    color: {TEXT_PRIMARY} !important;
    caret-color: {ACCENT} !important;
    padding: 10px 14px !important;
}}
.stTextInput input:focus,
.stTextArea textarea:focus,
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {{
    border-color: {BORDER_FOCUS} !important;
    box-shadow: 0 0 0 3px rgba(154, 184, 168, 0.12) !important;
    outline: none !important;
}}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
[data-baseweb="input"] input::placeholder {{
    color: {TEXT_TERTIARY} !important;
    opacity: 1 !important;
}}

/* ---- Selectbox: container, selected value, caret, options ---- */
.stSelectbox > div > div,
.stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {BG_INPUT} !important;
    border-radius: {RADIUS_SM} !important;
    border: 1px solid {BORDER_HOVER} !important;
    min-height: 42px !important;
}}
/* The selected value — needs aggressive selectors because BaseWeb nests deeply */
.stSelectbox [data-baseweb="select"] [data-baseweb="select-input"],
.stSelectbox [data-baseweb="select"] [data-baseweb="select-input"] *,
.stSelectbox [data-baseweb="select"] [class*="ValueContainer"],
.stSelectbox [data-baseweb="select"] [class*="ValueContainer"] *,
.stSelectbox [data-baseweb="select"] [class*="SingleValue"],
.stSelectbox [data-baseweb="select"] [class*="SingleValue"] *,
.stSelectbox [data-baseweb="select"] input,
.stSelectbox [data-baseweb="select"] div[role="combobox"],
.stSelectbox [data-baseweb="select"] div[role="combobox"] *,
.stSelectbox [data-baseweb="select"] span,
.stSelectbox div[data-baseweb="select"] > div > div {{
    color: {TEXT_PRIMARY} !important;
    background: transparent !important;
    font-size: 14px !important;
    font-family: {FONT_SANS} !important;
    -webkit-text-fill-color: {TEXT_PRIMARY} !important;
}}
/* The caret/chevron */
.stSelectbox [data-baseweb="select"] svg {{
    fill: {TEXT_SECONDARY} !important;
    color: {TEXT_SECONDARY} !important;
}}

/* Selectbox dropdown menu (the popover with options) */
[data-baseweb="popover"],
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"],
ul[role="listbox"] {{
    background: {BG_ELEVATED} !important;
    border: 1px solid {BORDER_HOVER} !important;
    border-radius: {RADIUS_SM} !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.32) !important;
}}
[data-baseweb="menu"] li,
[data-baseweb="menu"] li *,
ul[role="listbox"] li,
ul[role="listbox"] li *,
[role="option"],
[role="option"] * {{
    color: {TEXT_PRIMARY} !important;
    background: transparent !important;
    font-size: 14px !important;
    -webkit-text-fill-color: {TEXT_PRIMARY} !important;
}}
[data-baseweb="menu"] li:hover,
ul[role="listbox"] li:hover,
[role="option"]:hover,
[role="option"][aria-selected="true"] {{
    background: {ACCENT_DARK} !important;
}}
/* Labels above inputs */
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stNumberInput label,
.stFileUploader label,
[data-testid="stWidgetLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-family: {FONT_SANS} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}}

/* ---- File uploader ---- */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {{
    border-radius: {RADIUS_MD} !important;
    border: 1px dashed {BORDER_HOVER} !important;
    background: {BG_CARD} !important;
}}
[data-testid="stFileUploader"] section *,
[data-testid="stFileUploaderDropzone"] * {{
    color: {TEXT_SECONDARY} !important;
}}
[data-testid="stFileUploader"] button {{
    background: transparent !important;
    color: {TEXT_PRIMARY} !important;
    border: 1px solid {BORDER_HOVER} !important;
}}

/* ---- Headings — serif ---- */
.stApp h1, .main h1 {{
    font-family: {FONT_SERIF} !important;
    font-size: 36px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY} !important;
    line-height: 1.2 !important;
    margin-bottom: 6px !important;
    letter-spacing: -0.01em;
}}
.stApp h2, .main h2 {{
    font-family: {FONT_SERIF} !important;
    font-size: 26px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY} !important;
    line-height: 1.3 !important;
}}
.stApp h3, .main h3 {{
    font-family: {FONT_SERIF} !important;
    font-size: 20px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY} !important;
}}

/* ---- Body text ---- */
.stApp, .stMarkdown, .stMarkdown p {{
    font-family: {FONT_SANS} !important;
    color: {TEXT_PRIMARY};
}}
.stMarkdown p {{
    font-size: 15px;
    line-height: 1.7;
    color: {TEXT_PRIMARY};
}}
.stMarkdown a {{
    color: {ACCENT} !important;
    text-decoration: none;
}}
.stMarkdown a:hover {{
    color: {ACCENT_HOVER} !important;
}}
.stCaption, [data-testid="stCaptionContainer"] {{
    color: {TEXT_TERTIARY} !important;
    font-size: 13px !important;
    font-family: {FONT_SANS} !important;
}}
/* Code blocks */
code, pre {{
    background: {BG_INPUT} !important;
    color: {ACCENT} !important;
    border-radius: 6px !important;
    font-size: 13px !important;
}}
[data-testid="stCodeBlock"] {{
    background: {BG_INPUT} !important;
    border: 1px solid {BORDER_DEFAULT} !important;
    border-radius: {RADIUS_SM} !important;
}}

/* ---- Markdown utility classes ---- */
.vc-section-label {{
    font-family: {FONT_SANS};
    font-size: 11px;
    color: {TEXT_TERTIARY};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 500;
    margin-bottom: 16px;
}}
.vc-citation {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    font-family: {FONT_SANS};
}}
.vc-deal-card {{
    transition: background 0.15s ease, border-color 0.15s ease;
}}
.vc-deal-card:hover {{
    border-color: {ACCENT} !important;
    background: {BG_ELEVATED} !important;
    cursor: pointer;
}}
details summary::-webkit-details-marker {{ display: none; }}
details summary {{ outline: none; }}

/* ---- Tables ---- */
table {{
    color: {TEXT_PRIMARY};
}}

/* ---- Spinner / progress ---- */
.stSpinner > div {{
    border-color: {ACCENT} transparent {ACCENT} transparent !important;
}}

/* ---- Sidebar nav buttons — flat nav rows, not card buttons ---- */
[data-testid="stSidebar"] .stButton button,
[data-testid="stSidebar"] button[data-testid="baseButton-primary"],
[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {{
    background: transparent !important;
    color: #A8ADAB !important;
    border: none !important;
    border-left: 2px solid transparent !important;
    border-radius: 6px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 0 12px !important;
    height: 40px !important;
    min-height: 40px !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    letter-spacing: 0.005em !important;
    box-shadow: none !important;
    width: 100% !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{
    background: rgba(255, 255, 255, 0.035) !important;
    color: {TEXT_PRIMARY} !important;
    border-color: transparent !important;
}}
/* Active item (kind="primary") — brighter text + sage accent bar on the left */
[data-testid="stSidebar"] .stButton button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {{
    background: transparent !important;
    color: {TEXT_PRIMARY} !important;
    font-weight: 500 !important;
    border-left: 2px solid {ACCENT} !important;
    border-radius: 0 6px 6px 0 !important;
    padding-left: 10px !important;
}}
[data-testid="stSidebar"] .stButton button[kind="primary"]:hover,
[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover {{
    background: rgba(255, 255, 255, 0.035) !important;
    color: {TEXT_PRIMARY} !important;
}}
/* Tighten the horizontal columns that hold (icon | button) */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
    gap: 4px !important;
    margin-bottom: 2px !important;
}}
[data-testid="stSidebar"] [data-testid="column"] {{
    padding: 0 !important;
}}

/* ---- Streamlit native alerts ---- */
[data-testid="stAlert"] {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER_DEFAULT} !important;
    border-radius: {RADIUS_MD} !important;
    color: {TEXT_PRIMARY} !important;
}}

/* ---- Dividers ---- */
hr {{
    border-color: {BORDER_DEFAULT} !important;
    opacity: 0.5;
}}

/* ---- Expander ---- */
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {{
    background: {BG_CARD} !important;
    color: {TEXT_PRIMARY} !important;
    border: 1px solid {BORDER_DEFAULT} !important;
    border-radius: {RADIUS_SM} !important;
}}

/* ---- Responsive ---- */
@media (max-width: 1024px) {{
    .block-container {{
        padding-left: 24px !important;
        padding-right: 24px !important;
    }}
}}
@media (max-width: 640px) {{
    .block-container {{
        padding-top: 20px !important;
        padding-bottom: 20px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        max-width: 100% !important;
    }}
    [data-testid="column"] {{
        min-width: 100% !important;
        flex: 0 0 100% !important;
    }}
    .stApp h1, .main h1 {{
        font-size: 28px !important;
    }}
}}
</style>
"""


def _public_mode_css() -> str:
    return f"""
<style>
[data-testid="stSidebar"] {{ display: none !important; }}
.block-container {{
    max-width: 820px !important;
    padding-top: 64px !important;
}}
</style>
"""


# ----- Public API ------------------------------------------------------------


def inject_global_css() -> None:
    """Inject the global stylesheet. Call once after `st.set_page_config`."""
    st.html(_global_css())


def inject_public_mode_css() -> None:
    """Inject the public-route override (hides sidebar, narrows layout)."""
    st.html(_public_mode_css())
