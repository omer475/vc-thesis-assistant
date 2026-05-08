"""Shared helpers used by every admin tab.

Components live in `src/components.py`; this module is for layout
helpers that compose multiple components into a recurring pattern.
"""

from __future__ import annotations

import streamlit as st

from src.styles import (
    BG_CARD,
    BORDER_DEFAULT,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def page_header(title: str, subtitle: str = "") -> None:
    """Render the standard tab header — H1 + muted subtitle.

    Used at the top of every admin view. Fixed shape, no action button —
    if a view needs a primary action in the header row it should render
    its own using `st.columns` and the title HTML side-by-side.
    """
    sub_html = (
        f'<p style="font-size: 13px; color: {TEXT_SECONDARY}; '
        f'margin: 0; line-height: 1.5;">{subtitle}</p>'
        if subtitle
        else ""
    )
    st.html(
        f'<div style="margin-bottom: 28px;">'
        f'<h1 style="font-size: 22px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'margin: 0 0 4px 0; line-height: 1.3;">{title}</h1>'
        f"{sub_html}"
        f"</div>"
    )


def placeholder_card(message: str) -> None:
    """A subtle card used inside stub views to indicate not-yet-built sections."""
    st.html(
        f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
        f"border-radius: {RADIUS_MD}; padding: 28px; "
        f'font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.6;">'
        f"{message}"
        f"</div>"
    )
