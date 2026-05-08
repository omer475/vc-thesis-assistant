"""Partners tab — allowlist of partners whose decks get analyzed.

Layout:
  - Header with H1 "Partners" + subtitle + "+ Add partner" button (right).
  - Click "+ Add partner" → inline form with name + email + Save / Cancel.
  - data_table of current partners with delete control.
"""

from __future__ import annotations

import re

import streamlit as st

from src import cache, db
from src.components import esc_html, data_table, format_relative_time
from src.styles import (
    BG_CARD,
    BORDER_DEFAULT,
    RADIUS_MD,
    TEXT_SECONDARY,
)
from src.views._helpers import page_header

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _render_add_partner_section(firm: dict) -> bool:
    """Render the add-partner inline form. Returns True if a partner was added."""
    st.html(
        f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
        f'border-radius: {RADIUS_MD}; padding: 18px 20px; margin-bottom: 16px;">'
        f'<div class="vc-section-label" style="margin-bottom: 12px;">Add partner</div>'
        f"</div>"
    )

    name = st.text_input("Name", key="_partners_add_name", placeholder="Jane Doe")
    email = st.text_input("Email", key="_partners_add_email", placeholder="jane@firm.com")

    save_col, cancel_col, _ = st.columns([1, 1, 4])
    with save_col:
        save_clicked = st.button("Save", type="primary", key="_partners_save")
    with cancel_col:
        if st.button("Cancel", type="secondary", key="_partners_cancel"):
            st.session_state["_partners_add_open"] = False
            st.rerun()

    if save_clicked:
        if not email or not _EMAIL_RE.match(email):
            st.error("Enter a valid email address.")
            return False
        row = db.insert_partner(firm["id"], name or None, email.strip())
        if row is None:
            st.warning(f"{email} is already on the partner list.")
            return False
        cache.invalidate_all()
        st.success(f"Added {email}.")
        st.session_state["_partners_add_open"] = False
        return True

    return False


def render_partners_tab(firm: dict) -> None:
    page_header(
        title="Partners",
        subtitle="Allowlist of partners whose forwarded decks will be analyzed.",
    )

    # Header row: + Add partner button (right)
    head_col, btn_col = st.columns([4, 1])
    with btn_col:
        if st.button("+ Add partner", type="primary", key="_partners_open"):
            st.session_state["_partners_add_open"] = True
            st.rerun()

    if st.session_state.get("_partners_add_open"):
        added = _render_add_partner_section(firm)
        if added:
            st.rerun()

    # Table
    partners = cache.list_partners(firm["id"])
    if not partners:
        st.html(
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 28px; text-align: center; "
            f'font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.6;">'
            f"No partners yet. Click <b>+ Add partner</b> above to start the allowlist."
            f"</div>"
        )
        return

    rows = []
    for p in partners:
        rows.append(
            [
                esc_html(p.get("name") or "—"),
                esc_html(p.get("email") or ""),
                f'<span style="color: {TEXT_SECONDARY};">'
                f'{format_relative_time(p.get("created_at"))}</span>',
            ]
        )
    st.html(data_table(["Name", "Email", "Joined"], rows))

    # Delete control
    with st.expander("Remove a partner", expanded=False):
        options = ["(pick one)"] + [
            f"{p.get('name') or '—'} · {p['email']}" for p in partners
        ]
        sel = st.selectbox("Partner", options, key="_partners_delete_select")
        if sel != "(pick one)":
            idx = options.index(sel) - 1
            target = partners[idx]
            if st.button(
                f"Remove {target['email']}",
                type="secondary",
                key="_partners_delete_btn",
            ):
                db.delete_partner(target["id"])
                cache.invalidate_all()
                st.success(f"Removed {target['email']}.")
                st.rerun()
