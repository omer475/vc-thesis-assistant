"""Settings tab — firm configuration.

Read-only displays for identity + security. Password changes are noted
as live in env var only for v1; the form is shown but disabled. Danger
zone is a placeholder (delete-firm not implemented in v1).
"""

from __future__ import annotations

import os

import streamlit as st

from src import db
from src.components import esc_html, section_label
from src.styles import (
    BG_CARD,
    BORDER_DEFAULT,
    PASS_BG,
    PASS_BORDER,
    PASS_TEXT,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from src.views._helpers import page_header


def _identity_row(label: str, value: str, hint: str = "") -> str:
    hint_html = (
        f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; margin-top: 2px;">'
        f"{esc_html(hint)}</div>"
        if hint
        else ""
    )
    return (
        f'<div style="display: flex; gap: 24px; padding: 14px 0; '
        f'border-bottom: 0.5px solid {BORDER_DEFAULT};">'
        f'<div style="flex: 0 0 180px; font-size: 13px; color: {TEXT_SECONDARY};">'
        f"{esc_html(label)}</div>"
        f'<div style="flex: 1; font-size: 13px; color: {TEXT_PRIMARY};">'
        f"{value}{hint_html}</div>"
        f"</div>"
    )


def render_settings_tab(firm: dict) -> None:
    page_header(title="Settings", subtitle="Firm configuration.")

    # Identity
    st.html(section_label("Identity"))

    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_supabase = bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    has_affinity = bool(firm.get("affinity_api_key"))

    rows_html = (
        _identity_row(
            "Firm name",
            f'<span style="font-weight: 500;">{esc_html(firm.get("name") or "")}</span>',
        )
        + _identity_row(
            "Firm slug",
            f'<code style="background: #F4F3EE; padding: 1px 6px; border-radius: 4px; '
            f'font-size: 12px;">{esc_html(firm.get("slug") or "")}</code>',
        )
        + _identity_row(
            "Email address",
            f'<code style="background: #F4F3EE; padding: 1px 6px; border-radius: 4px; '
            f'font-size: 12px;">deals@{esc_html(firm.get("slug") or "")}.thesis.ai</code>',
            "Live in Phase 2 — email forwarding not yet wired up.",
        )
        + _identity_row(
            "Anthropic API key",
            "✓ Configured" if has_anthropic else "✗ Missing",
        )
        + _identity_row(
            "Supabase",
            "✓ Connected" if has_supabase else "✗ Missing",
        )
        + _identity_row(
            "Affinity",
            "✓ Connected" if has_affinity else "Not connected",
        )
    )
    st.html(
        f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
        f'border-radius: {RADIUS_MD}; padding: 4px 20px;">{rows_html}</div>'
    )

    # Security
    st.html('<div style="height: 28px;"></div>')
    st.html(section_label("Security"))
    st.html(
        f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
        f'border-radius: {RADIUS_MD}; padding: 18px 20px;">'
        f'<div style="font-size: 13px; color: {TEXT_PRIMARY}; line-height: 1.5; '
        f'margin-bottom: 8px;">App password</div>'
        f'<div style="font-size: 12px; color: {TEXT_SECONDARY}; line-height: 1.5;">'
        f"For v1, the admin password is set via the <code>APP_PASSWORD</code> "
        f"environment variable (in <code>.env</code> locally, or Streamlit "
        f"Cloud secrets in production). Change it there and restart the app."
        f"</div>"
        f"</div>"
    )

    # Danger zone
    st.html('<div style="height: 28px;"></div>')
    st.html(section_label("Danger zone"))
    st.html(
        f'<div style="background: {BG_CARD}; border: 0.5px solid {PASS_BORDER}; '
        f'border-radius: {RADIUS_MD}; padding: 18px 20px;">'
        f'<div style="font-size: 13px; color: {TEXT_PRIMARY}; font-weight: 500; '
        f'margin-bottom: 4px;">Delete this firm and all associated data</div>'
        f'<div style="font-size: 12px; color: {TEXT_SECONDARY}; line-height: 1.5; '
        f'margin-bottom: 12px;">'
        f"Removes the firm row, all documents, all decks, all analyses, all "
        f"pass reasons. Cannot be undone. Coming in a later phase."
        f"</div>"
        f"</div>"
    )
    danger_col, _ = st.columns([1, 4])
    with danger_col:
        st.button("Coming soon", type="secondary", disabled=True, key="_settings_delete")
