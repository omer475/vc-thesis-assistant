"""Design tokens and global CSS injection.

All visual constants come from this module. Components in `src/components.py`
reference these values by name; `src/app.py` calls `inject_global_css()`
once per route at startup. The public deal-page route additionally calls
`inject_public_mode_css()` for the centered/no-sidebar override.

Source of truth: DESIGN.md.
"""

from __future__ import annotations

import streamlit as st


# ----- Colors ----------------------------------------------------------------

# Foundation
BG_PAGE = "#FAFAFA"
BG_CARD = "#FFFFFF"
BG_SIDEBAR = "#F4F3EE"
BG_TABLE_HEAD = "#F7F6F1"

BORDER_DEFAULT = "rgba(15, 15, 15, 0.08)"
BORDER_HOVER = "rgba(15, 15, 15, 0.16)"

TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#5F5E5A"
TEXT_TERTIARY = "#9A9A9A"

# Verdict ramps — green / amber / red
TAKE_BG = "#EAF3DE"
TAKE_TEXT = "#27500A"
TAKE_BORDER = "#C0DD97"
TAKE_DOT = "#3B6D11"

ASK_BG = "#FAEEDA"
ASK_TEXT = "#633806"
ASK_BORDER = "#FAC775"
ASK_DOT = "#854F0B"

PASS_BG = "#FCEBEB"
PASS_TEXT = "#791F1F"
PASS_BORDER = "#F7C1C1"
PASS_DOT = "#A32D2D"


# ----- Typography ------------------------------------------------------------

FONT_STACK = '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif'


# ----- Spacing & shape -------------------------------------------------------

RADIUS_SM = "6px"
RADIUS_MD = "8px"
RADIUS_LG = "12px"

PADDING_CARD = "24px"
PADDING_DEAL = "32px"
PADDING_SIDEBAR = "16px 12px"
PADDING_MAIN = "24px 28px"

GAP_SECTION = "28px"
GAP_ROW = "8px"


# ----- CSS blocks ------------------------------------------------------------

# Tabler icons webfont. Pinned to major version 3 to bound surface; loose enough
# to pick up bug-fix releases inside that line.
_TABLER_ICONS_CSS_URL = (
    "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3/dist/tabler-icons.min.css"
)


def _global_css() -> str:
    return f"""
<link rel="stylesheet" href="{_TABLER_ICONS_CSS_URL}">
<style>
/* ---- Hide Streamlit chrome (display: none, not visibility: hidden, so space is reclaimed) ---- */
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
    font-family: {FONT_STACK} !important;
    color: {TEXT_PRIMARY};
}}
.stApp {{
    background: {BG_PAGE} !important;
}}
.block-container,
[data-testid="block-container"],
.main .block-container {{
    padding-top: 24px !important;
    padding-bottom: 24px !important;
    max-width: 1200px !important;
}}

/* ---- Sidebar ---- */
[data-testid="stSidebar"],
section[data-testid="stSidebar"] {{
    background: {BG_SIDEBAR} !important;
    border-right: 0.5px solid {BORDER_DEFAULT};
    width: 220px !important;
    min-width: 220px !important;
}}
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    padding: {PADDING_SIDEBAR} !important;
    background: {BG_SIDEBAR} !important;
}}

/* ---- Buttons (multiple selector variants for cross-version safety) ---- */
.stButton button,
[data-testid="stButton"] button,
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"] {{
    border-radius: {RADIUS_MD} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
    transition: border-color 0.1s ease, background 0.1s ease;
    box-shadow: none !important;
    line-height: 1.4 !important;
    min-height: 0 !important;
}}
.stButton button[kind="primary"],
button[data-testid="baseButton-primary"] {{
    background: {TEXT_PRIMARY} !important;
    color: white !important;
    border: none !important;
}}
.stButton button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {{
    background: #000000 !important;
    color: white !important;
}}
.stButton button[kind="secondary"],
button[data-testid="baseButton-secondary"] {{
    background: {BG_CARD} !important;
    color: {TEXT_PRIMARY} !important;
    border: 0.5px solid {BORDER_HOVER} !important;
}}
.stButton button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover {{
    border-color: rgba(15, 15, 15, 0.32) !important;
    color: {TEXT_PRIMARY} !important;
}}
.stDownloadButton button {{
    border-radius: {RADIUS_MD} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
}}

/* ---- Inputs ---- */
.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div,
.stNumberInput input,
[data-testid="stTextInput"] input {{
    border-radius: {RADIUS_MD} !important;
    border: 0.5px solid {BORDER_HOVER} !important;
    font-size: 13px !important;
    background: {BG_CARD} !important;
}}

/* ---- File uploader ---- */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {{
    border-radius: {RADIUS_MD} !important;
    border: 0.5px dashed {BORDER_HOVER} !important;
    background: {BG_CARD} !important;
}}

/* ---- Tabs (still used until Step 3 replaces with sidebar nav) ---- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    border-bottom: 0.5px solid {BORDER_DEFAULT};
}}
.stTabs [data-baseweb="tab"] {{
    font-size: 13px !important;
    font-weight: 500 !important;
    color: {TEXT_SECONDARY} !important;
    padding: 8px 14px !important;
}}
.stTabs [aria-selected="true"] {{
    color: {TEXT_PRIMARY} !important;
}}

/* ---- Headings ---- */
.stApp h1, .main h1 {{
    font-size: 22px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY} !important;
    line-height: 1.3 !important;
    margin-bottom: 4px !important;
}}
.stApp h2, .main h2 {{
    font-size: 18px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY} !important;
}}
.stApp h3, .main h3 {{
    font-size: 15px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY} !important;
}}

/* ---- Body text ---- */
.stApp, .stMarkdown, .stMarkdown p {{
    font-family: {FONT_STACK} !important;
}}
.stMarkdown p {{
    font-size: 15px;
    line-height: 1.6;
    color: {TEXT_PRIMARY};
}}
.stCaption, [data-testid="stCaptionContainer"] {{
    color: {TEXT_TERTIARY} !important;
    font-size: 12px !important;
}}

/* ---- Markdown utility classes (used by components) ---- */
.vc-section-label {{
    font-size: 11px;
    color: {TEXT_TERTIARY};
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 500;
    margin-bottom: 12px;
}}
.vc-citation {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
</style>
"""


def _public_mode_css() -> str:
    return f"""
<style>
[data-testid="stSidebar"] {{ display: none !important; }}
.block-container {{
    max-width: 800px !important;
    padding-top: 48px;
}}
</style>
"""


# ----- Public API ------------------------------------------------------------


def inject_global_css() -> None:
    """Inject the global stylesheet. Call once after `st.set_page_config`."""
    st.markdown(_global_css(), unsafe_allow_html=True)


def inject_public_mode_css() -> None:
    """Inject the public-route override (hides sidebar, narrows layout)."""
    st.markdown(_public_mode_css(), unsafe_allow_html=True)
