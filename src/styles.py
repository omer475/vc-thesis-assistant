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
/* ---- Hide Streamlit chrome ---- */
#MainMenu {{ visibility: hidden; }}
header {{ visibility: hidden; height: 0; }}
footer {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}
[data-testid="stToolbar"] {{ display: none; }}
[data-testid="stStatusWidget"] {{ display: none; }}

/* ---- Page foundation ---- */
.stApp {{
    background: {BG_PAGE};
    font-family: {FONT_STACK};
    color: {TEXT_PRIMARY};
}}
.block-container {{
    padding-top: 24px;
    padding-bottom: 24px;
    max-width: 1200px;
}}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {{
    background: {BG_SIDEBAR};
    border-right: 0.5px solid {BORDER_DEFAULT};
    width: 220px !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    padding: {PADDING_SIDEBAR};
}}

/* ---- Buttons ---- */
.stButton button {{
    border-radius: {RADIUS_MD};
    font-size: 13px;
    font-weight: 500;
    padding: 8px 14px;
    transition: border-color 0.1s ease, background 0.1s ease;
    box-shadow: none;
}}
.stButton button[kind="primary"] {{
    background: {TEXT_PRIMARY};
    color: white;
    border: none;
}}
.stButton button[kind="primary"]:hover {{
    background: #000000;
}}
.stButton button[kind="secondary"] {{
    background: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 0.5px solid {BORDER_HOVER};
}}
.stButton button[kind="secondary"]:hover {{
    border-color: rgba(15, 15, 15, 0.32);
}}
.stDownloadButton button {{
    border-radius: {RADIUS_MD};
    font-size: 13px;
    font-weight: 500;
    padding: 8px 14px;
}}

/* ---- Inputs ---- */
.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div,
.stNumberInput input {{
    border-radius: {RADIUS_MD} !important;
    border: 0.5px solid {BORDER_HOVER} !important;
    font-size: 13px !important;
}}

/* ---- File uploader ---- */
[data-testid="stFileUploader"] section {{
    border-radius: {RADIUS_MD};
    border: 0.5px dashed {BORDER_HOVER};
    background: {BG_CARD};
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
