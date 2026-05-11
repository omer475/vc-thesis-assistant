"""First-run onboarding flow.

Captures basic firm info — company name, description, investment thesis, and
CRM preference. Replaces the hardcoded "Forge Ventures" default. The captured
data populates the firm record and an initial firm_profile.md, and the CRM
choice is persisted so the CRM tab renders the right connector.

Stored in session_state under `_onboarding_data`. If Supabase is reachable
the data is also persisted via db.update_firm(), but the UI is fully usable
without a backend.
"""

from __future__ import annotations

import streamlit as st

from src import cache, db
from src.styles import (
    ACCENT,
    BG_CARD,
    BG_PAGE,
    BORDER_DEFAULT,
    FONT_SANS,
    FONT_SERIF,
    RADIUS_LG,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)

ONBOARDING_KEY = "_onboarding_data"
ONBOARDING_DONE_KEY = "_onboarding_complete"


def is_onboarding_complete() -> bool:
    """Returns True if onboarding has already been completed (or skipped)."""
    return bool(st.session_state.get(ONBOARDING_DONE_KEY))


def get_onboarding_data() -> dict:
    """Return the captured onboarding data, or empty defaults."""
    return st.session_state.get(ONBOARDING_KEY, {})


def _build_initial_profile(data: dict) -> str:
    """Convert onboarding answers into a starter firm_profile.md."""
    name = data.get("company_name", "")
    info = data.get("company_info", "")
    thesis = data.get("investment_thesis", "")
    parts = []
    if name:
        parts.append(f"# {name}")
    if info:
        parts.append(f"## About\n\n{info}")
    if thesis:
        parts.append(f"## Investment thesis\n\n{thesis}")
    return "\n\n".join(parts)


def _save_onboarding(data: dict) -> None:
    """Persist onboarding data to session_state and (best-effort) Supabase."""
    st.session_state[ONBOARDING_KEY] = data
    st.session_state[ONBOARDING_DONE_KEY] = True

    # Best-effort DB persist
    try:
        firm = db.get_or_create_default_firm()
        profile_md = _build_initial_profile(data)
        if profile_md:
            db.update_firm_profile(firm["id"], profile_md)
        cache.invalidate_all()
    except Exception:
        pass


def render_onboarding() -> None:
    """Render the centered onboarding card. Called from app.py when needed."""
    st.html(
        f"""
        <style>
        [data-testid="stSidebar"] {{ display: none !important; }}
        .block-container {{ max-width: 720px !important; padding-top: 64px !important; }}
        </style>
        """
    )

    # Hero header
    st.html(
        f'<div style="text-align: center; margin-bottom: 48px;">'
        f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; letter-spacing: 0.16em; '
        f'text-transform: uppercase; margin-bottom: 16px; font-weight: 500;">Welcome</div>'
        f'<h1 style="font-family: {FONT_SERIF}; font-size: 44px; font-weight: 500; '
        f'color: {TEXT_PRIMARY}; margin: 0 0 16px 0; line-height: 1.15; '
        f'letter-spacing: -0.02em;">Let\'s set up your firm</h1>'
        f'<p style="font-size: 16px; color: {TEXT_SECONDARY}; line-height: 1.6; '
        f'margin: 0 auto; max-width: 480px; font-weight: 300;">'
        f"A few details so every analysis is grounded in your thesis and how your firm thinks."
        f"</p>"
        f"</div>"
    )

    # Form fields
    company_name = st.text_input(
        "Firm name",
        value=st.session_state.get("_onb_name", ""),
        placeholder="e.g. Forge Ventures",
        key="_onb_name",
    )

    st.html('<div style="height: 12px;"></div>')

    company_info = st.text_area(
        "About the firm",
        value=st.session_state.get("_onb_info", ""),
        placeholder="Stage, sectors, geography, fund size, anything that defines who you are.",
        height=110,
        key="_onb_info",
    )

    st.html('<div style="height: 12px;"></div>')

    investment_thesis = st.text_area(
        "Investment thesis",
        value=st.session_state.get("_onb_thesis", ""),
        placeholder=(
            "What do you back, what do you pass on, and why? "
            "The sharper this is, the sharper every verdict will be."
        ),
        height=160,
        key="_onb_thesis",
    )

    st.html('<div style="height: 12px;"></div>')

    crm_choice = st.selectbox(
        "Which CRM does your firm use?",
        options=["Affinity", "Spectre", "Neither / skip for now"],
        index=0,
        key="_onb_crm",
    )

    st.html('<div style="height: 28px;"></div>')

    col_continue, col_skip = st.columns([1, 1])
    with col_continue:
        if st.button(
            "Continue",
            type="primary",
            key="_onb_continue",
            use_container_width=True,
            disabled=not (company_name and company_name.strip()),
        ):
            _save_onboarding({
                "company_name": company_name.strip(),
                "company_info": company_info.strip(),
                "investment_thesis": investment_thesis.strip(),
                "crm": crm_choice,
            })
            st.rerun()
    with col_skip:
        if st.button(
            "Skip for now",
            type="secondary",
            key="_onb_skip",
            use_container_width=True,
        ):
            _save_onboarding({
                "company_name": "",
                "company_info": "",
                "investment_thesis": "",
                "crm": "Neither / skip for now",
            })
            st.rerun()

    # Footer hint
    st.html(
        f'<div style="text-align: center; margin-top: 32px; '
        f'font-size: 12px; color: {TEXT_TERTIARY}; letter-spacing: 0.04em;">'
        f"You can change all of this later in the Investor profile tab."
        f"</div>"
    )
