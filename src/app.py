"""Streamlit web UI for the VC Thesis Assistant.

Run with:
    streamlit run src/app.py

Two routes share the same script:
  - **Admin** (default): sidebar + tab dispatch (Analyze, Firm setup,
    Partners, CRM, Analytics, Settings). Password-gated by APP_PASSWORD.
  - **Public deal page** (`?deal=<analysis_id>`): read-only verdict +
    memo for one analysis. No login, no admin chrome.

After Step 2 of Phase 1: all firm/deck/analysis data lives in Supabase.
After design step 3: admin uses a 6-tab sidebar shell with dispatch to
view modules under `src/views/`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `from src...` works when streamlit runs this file.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# Mirror Streamlit Cloud secrets into os.environ so the supabase client,
# anthropic SDK, and password gate all read from the same place regardless
# of host (local .env / Streamlit Cloud secrets / Render env vars).
try:
    for _key in list(st.secrets.keys()):
        _val = st.secrets[_key]
        if isinstance(_val, str):
            os.environ.setdefault(_key, _val)
except Exception:
    pass

from dotenv import load_dotenv
from streamlit_option_menu import option_menu

from src import bootstrap, cache, db
from src.styles import (
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    inject_global_css,
)
from src.views.analytics import render_analytics_tab
from src.views.analyze import render_analyze_tab
from src.views.crm import render_crm_tab
from src.views.firm_setup import render_firm_setup_tab
from src.views.partners import render_partners_tab
from src.views.public_deal import render_public_deal_page
from src.views.settings import render_settings_tab

load_dotenv()

# Bootstrap once per Streamlit session, not on every rerun. The seed and
# default-firm-create operations are idempotent but each makes 2 DB calls,
# so re-running them on every widget interaction adds 200-600ms of latency
# for nothing.
if "_boot_info" not in st.session_state:
    st.session_state["_boot_info"] = bootstrap.run()
_boot_info = st.session_state["_boot_info"]
FIRM_ID: str = _boot_info["firm_id"]


# ----- public deal page detour -----------------------------------------------
# Must run BEFORE set_page_config and the password gate.

_query_deal_id = ""
try:
    _query_deal_id = (st.query_params.get("deal") or "").strip()
except Exception:
    pass

if _query_deal_id:
    render_public_deal_page(_query_deal_id)
    st.stop()


# ----- admin app -------------------------------------------------------------

st.set_page_config(
    page_title="VC Thesis Assistant",
    page_icon="V",
    layout="wide",
)
inject_global_css()


def _require_password() -> None:
    """If APP_PASSWORD is set in the environment, gate the admin app behind it."""
    expected = os.environ.get("APP_PASSWORD", "").strip()
    if not expected:
        return
    if st.session_state.get("_authed"):
        return

    st.title("VC Thesis Assistant")
    st.caption("Enter the access password to continue.")
    pw = st.text_input("Password", type="password", key="_pw_input")
    if pw == "":
        st.stop()
    if pw == expected:
        st.session_state["_authed"] = True
        st.rerun()
    else:
        st.error("Wrong password.")
        st.stop()


_require_password()


# ----- sidebar ---------------------------------------------------------------


def _firm_header_html(firm: dict) -> str:
    return (
        f'<div style="margin-bottom: 16px;">'
        f'<div style="font-size: 14px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'line-height: 1.3;">{firm["name"]}</div>'
        f'<div style="font-size: 11px; color: {TEXT_SECONDARY}; margin-top: 2px;">'
        f'{firm["slug"]}.thesis.ai</div>'
        f"</div>"
    )


def _status_block_html(firm_id: str) -> str:
    n_docs = cache.count_documents(firm_id)
    total_chars = cache.total_corpus_chars(firm_id)
    n_deals_week = cache.count_deals_this_week(firm_id)

    if total_chars >= 1000:
        chars_label = f"{round(total_chars / 1000)}k chars"
    else:
        chars_label = f"{total_chars} chars"

    return (
        f'<div style="margin-top: 32px;">'
        f'<div class="vc-section-label">Status</div>'
        f'<div style="font-size: 11px; color: {TEXT_SECONDARY}; line-height: 1.7;">'
        f"{n_docs} docs · {chars_label}<br>"
        f"Not connected<br>"
        f"{n_deals_week} deals this week"
        f"</div>"
        f"</div>"
    )


firm = cache.get_firm(FIRM_ID) or db.get_or_create_default_firm()

with st.sidebar:
    st.html(_firm_header_html(firm))

    selected = option_menu(
        menu_title=None,
        options=["Analyze", "Firm setup", "Partners", "CRM", "Analytics", "Settings"],
        icons=["bullseye", "file-text", "people", "plug", "bar-chart", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "0", "background": "transparent"},
            "icon": {"font-size": "15px", "color": TEXT_SECONDARY},
            "nav-link": {
                "font-size": "13px",
                "color": TEXT_SECONDARY,
                "padding": "7px 10px",
                "border-radius": "8px",
                "margin": "0 0 2px 0",
                "text-align": "left",
                "--hover-color": "rgba(255, 255, 255, 0.5)",
            },
            "nav-link-selected": {
                "background": "#FFFFFF",
                "color": TEXT_PRIMARY,
                "font-weight": "500",
            },
        },
    )

    st.html(_status_block_html(FIRM_ID))


# ----- dispatch --------------------------------------------------------------

_DISPATCH = {
    "Analyze": render_analyze_tab,
    "Firm setup": render_firm_setup_tab,
    "Partners": render_partners_tab,
    "CRM": render_crm_tab,
    "Analytics": render_analytics_tab,
    "Settings": render_settings_tab,
}

_render_fn = _DISPATCH.get(selected, render_analyze_tab)
_render_fn(firm)
