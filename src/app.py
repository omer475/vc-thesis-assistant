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

from src import bootstrap, cache, db
from src.styles import (
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    inject_global_css,
)
from src.views.analytics import render_analytics_tab
from src.views.analyze import render_analyze_tab
from src.views.crm import render_crm_tab
from src.views.firm_setup import render_firm_setup_tab as render_investor_profile_tab
from src.views.onboarding import (
    get_onboarding_data,
    is_onboarding_complete,
    render_onboarding,
)
from src.views.partners import render_partners_tab
from src.views.public_deal import render_public_deal_page

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


# ----- onboarding gate -------------------------------------------------------
# First-run: capture firm name, thesis, CRM choice. Once completed, the
# onboarding data populates the rest of the app.

if not is_onboarding_complete():
    render_onboarding()
    st.stop()


# ----- sidebar ---------------------------------------------------------------


# (label, tabler icon class)
_NAV_ITEMS = [
    ("Analyze", "ti-activity"),
    ("Investor profile", "ti-user"),
    ("Partners", "ti-users"),
    ("CRM", "ti-affiliate"),
    ("Analytics", "ti-chart-line"),
]


def _render_sidebar_nav() -> str:
    """Render the sidebar nav as native Streamlit buttons (no iframe).

    session_state preserves selection across reruns — critical, otherwise
    every click resets onboarding state. Active item uses `type="primary"`
    so CSS can distinguish it; icons render in a thin column on the left.
    """
    selected = st.session_state.setdefault("_nav_selected", "Analyze")

    for label, icon in _NAV_ITEMS:
        is_active = label == selected
        icon_color = "#9AB8A8" if is_active else "#A8ADAB"

        col_icon, col_btn = st.columns([1, 7], gap="small")
        with col_icon:
            st.html(
                f'<div style="display: flex; align-items: center; '
                f'justify-content: center; height: 40px;">'
                f'<i class="ti {icon}" style="font-size: 16px; '
                f'color: {icon_color};"></i>'
                f"</div>"
            )
        with col_btn:
            if st.button(
                label,
                key=f"_nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["_nav_selected"] = label
                st.rerun()

    return selected


def _firm_header_html(firm: dict) -> str:
    return (
        f'<div style="margin: 0 0 18px 8px; padding-bottom: 16px; '
        f'border-bottom: 1px solid rgba(255, 255, 255, 0.06);">'
        f'<div style="font-family: \'Cormorant Garamond\', Georgia, serif; '
        f'font-size: 20px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'line-height: 1.2; letter-spacing: -0.01em;">{firm["name"]}</div>'
        f'<div style="font-size: 10px; color: {TEXT_SECONDARY}; '
        f'margin-top: 4px; letter-spacing: 0.1em; text-transform: uppercase;">'
        f'Thesis assistant</div>'
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
        f'<div style="margin-top: 40px; padding-top: 20px; '
        f'border-top: 1px solid rgba(255, 255, 255, 0.06);">'
        f'<div class="vc-section-label">Status</div>'
        f'<div style="font-size: 12px; color: {TEXT_SECONDARY}; line-height: 2;">'
        f"{n_docs} docs · {chars_label}<br>"
        f"Not connected<br>"
        f"{n_deals_week} deals this week"
        f"</div>"
        f"</div>"
    )


firm = cache.get_firm(FIRM_ID) or {"id": FIRM_ID, "slug": "forge", "name": "Forge Ventures", "profile_md": None}

# Overlay onboarding data so renamed firm propagates everywhere
_onb = get_onboarding_data()
if _onb.get("company_name"):
    firm = {**firm, "name": _onb["company_name"]}
    if _onb.get("investment_thesis") or _onb.get("company_info"):
        # Build a minimal profile from onboarding if none exists
        if not firm.get("profile_md"):
            parts = []
            if _onb.get("company_name"):
                parts.append(f"# {_onb['company_name']}")
            if _onb.get("company_info"):
                parts.append(f"## About\n\n{_onb['company_info']}")
            if _onb.get("investment_thesis"):
                parts.append(f"## Investment thesis\n\n{_onb['investment_thesis']}")
            firm = {**firm, "profile_md": "\n\n".join(parts)}

with st.sidebar:
    st.html(_firm_header_html(firm))

    selected = _render_sidebar_nav()

    st.html(_status_block_html(FIRM_ID))


# ----- dispatch --------------------------------------------------------------

_DISPATCH = {
    "Analyze": render_analyze_tab,
    "Investor profile": render_investor_profile_tab,
    "Partners": render_partners_tab,
    "CRM": render_crm_tab,
    "Analytics": render_analytics_tab,
}

_render_fn = _DISPATCH.get(selected, render_analyze_tab)
_render_fn(firm)
