"""Partners tab — list of partners at the firm.

Layout:
  - Header with H1 "Partners" + subtitle + "Add partner" button (right).
  - Click "Add partner" → modal dialog with name, email, position, notes.
  - data_table of current partners with delete control.

When Supabase is unavailable, partners are kept in session_state so the
UI can still be exercised end-to-end for testing.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import streamlit as st

from src import cache, db
from src.components import esc_html, data_table, format_relative_time
from src.styles import (
    BG_CARD,
    BG_ELEVATED,
    BORDER_DEFAULT,
    FONT_SERIF,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from src.views._helpers import page_header

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_FALLBACK_KEY = "_partners_local_store"


def _local_partners(firm_id: str) -> list[dict]:
    store = st.session_state.setdefault(_FALLBACK_KEY, {})
    return store.setdefault(firm_id, [])


def _all_partners(firm: dict) -> list[dict]:
    """Combine DB partners with any session-state fallbacks."""
    try:
        db_rows = cache.list_partners(firm["id"]) or []
    except Exception:
        db_rows = []
    local = _local_partners(firm["id"])
    # Merge — DB rows first, then any local-only rows
    seen_emails = {r.get("email") for r in db_rows}
    return db_rows + [r for r in local if r.get("email") not in seen_emails]


def _add_partner(firm: dict, name: str, email: str, position: str, notes: str) -> tuple[bool, str]:
    """Try DB insert; fall back to session state. Returns (ok, message)."""
    full_name = name.strip()
    if position.strip():
        full_name = f"{full_name} · {position.strip()}" if full_name else position.strip()

    try:
        row = db.insert_partner(firm["id"], full_name or None, email.strip())
        if row is None:
            return False, f"{email} is already on the partner list."
        cache.invalidate_all()
        return True, f"Added {email}."
    except Exception:
        local = _local_partners(firm["id"])
        if any(p.get("email") == email.strip() for p in local):
            return False, f"{email} is already on the partner list."
        local.append({
            "id": str(uuid.uuid4()),
            "firm_id": firm["id"],
            "name": full_name or None,
            "email": email.strip(),
            "position": position.strip() or None,
            "notes": notes.strip() or None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return True, f"Added {email} (local session only — Supabase unavailable)."


def _remove_partner(firm: dict, partner_id: str, email: str) -> None:
    try:
        db.delete_partner(partner_id)
        cache.invalidate_all()
    except Exception:
        pass
    local = _local_partners(firm["id"])
    st.session_state[_FALLBACK_KEY][firm["id"]] = [
        p for p in local if p.get("id") != partner_id and p.get("email") != email
    ]


@st.dialog("Add partner")
def _add_partner_dialog(firm: dict) -> None:
    st.html(
        f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; '
        f'margin-bottom: 18px; line-height: 1.6;">'
        f"Add a partner at your firm. They can receive deal analyses and "
        f"appear in analytics."
        f"</div>"
    )

    name = st.text_input(
        "Full name",
        key="_partners_dialog_name",
        placeholder="Jane Doe",
    )
    email = st.text_input(
        "Email",
        key="_partners_dialog_email",
        placeholder="jane@firm.com",
    )
    position = st.text_input(
        "Position / role",
        key="_partners_dialog_position",
        placeholder="General Partner",
    )
    notes = st.text_area(
        "Notes (optional)",
        key="_partners_dialog_notes",
        placeholder="Sub-thesis focus, sector preferences, etc.",
        height=80,
    )

    st.html('<div style="height: 8px;"></div>')

    col_save, col_cancel = st.columns([1, 1])
    with col_save:
        save_clicked = st.button("Save partner", type="primary", key="_partners_dialog_save", use_container_width=True)
    with col_cancel:
        if st.button("Cancel", type="secondary", key="_partners_dialog_cancel", use_container_width=True):
            st.rerun()

    if save_clicked:
        if not email or not _EMAIL_RE.match(email.strip()):
            st.error("Enter a valid email address.")
            return
        ok, msg = _add_partner(firm, name, email, position, notes)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.warning(msg)


def render_partners_tab(firm: dict) -> None:
    page_header(
        title="Partners",
        subtitle="People at your firm who receive deal analyses.",
    )

    # Header row: Add partner button (right)
    head_col, btn_col = st.columns([4, 1])
    with btn_col:
        if st.button("+ Add partner", type="primary", key="_partners_open_dialog"):
            _add_partner_dialog(firm)

    partners = _all_partners(firm)

    if not partners:
        st.html(
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 40px; text-align: center; "
            f'font-size: 14px; color: {TEXT_SECONDARY}; line-height: 1.7;">'
            f'<div style="font-family: {FONT_SERIF}; font-size: 18px; color: {TEXT_PRIMARY}; '
            f'margin-bottom: 8px;">No partners yet</div>'
            f"Click <span style=\"color: {TEXT_PRIMARY};\">+ Add partner</span> above "
            f"to start building the allowlist."
            f"</div>"
        )
        return

    rows = []
    for p in partners:
        name = p.get("name") or "—"
        # Split name from position if it was concatenated
        position = ""
        if " · " in (name or ""):
            name, position = name.split(" · ", 1)
        elif p.get("position"):
            position = p.get("position")
        rows.append(
            [
                f'<span style="color: {TEXT_PRIMARY}; font-weight: 500;">{esc_html(name)}</span>',
                f'<span style="color: {TEXT_SECONDARY};">{esc_html(position or "—")}</span>',
                esc_html(p.get("email") or ""),
                f'<span style="color: {TEXT_TERTIARY};">'
                f'{format_relative_time(p.get("created_at"))}</span>',
            ]
        )
    st.html(data_table(["Name", "Role", "Email", "Joined"], rows))

    # Remove control
    st.html('<div style="height: 16px;"></div>')
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
                _remove_partner(firm, target["id"], target["email"])
                st.success(f"Removed {target['email']}.")
                st.rerun()
