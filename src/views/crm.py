"""CRM tab — Affinity connection + sync UI.

Two states:
  - Not connected: status_card with a "Connect Affinity" CTA. Clicking it
    opens an inline form for the API key + Passed status ID.
  - Connected: status_card with sync stats + Sync now / Disconnect actions,
    plus a data_table of synced pass reasons.

Functional sync logic lives in `src/affinity.py`. Without a real Affinity
workspace, use `python -m scripts.seed_synthetic_pass_reasons` to populate
the table for demo purposes.
"""

from __future__ import annotations

import streamlit as st

from src import db
from src.affinity import AffinityError, AffinityNotConfigured, sync_pass_reasons
from src.components import (
    _esc,
    data_table,
    format_relative_time,
    section_label,
    status_card_html,
)
from src.styles import (
    BG_CARD,
    BORDER_DEFAULT,
    RADIUS_MD,
    TEXT_SECONDARY,
)
from src.views._helpers import page_header


def _truncate(text: str | None, n: int) -> str:
    s = (text or "").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _last_sync_label(pass_reasons: list[dict]) -> str:
    affinity_rows = [p for p in pass_reasons if p.get("source") == "affinity"]
    if not affinity_rows:
        return ""
    most_recent = max((p.get("ingested_at") or "") for p in affinity_rows)
    return format_relative_time(most_recent)


def _render_connect_form(firm: dict) -> bool:
    """Inline form for entering Affinity creds. Returns True if saved."""
    st.html(
        f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
        f'border-radius: {RADIUS_MD}; padding: 18px 20px; margin: 12px 0;">'
        f'<div class="vc-section-label" style="margin-bottom: 12px;">'
        f"Connect Affinity</div>"
        f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.5; '
        f'margin-bottom: 8px;">'
        f"Generate an API key in Affinity → Settings → API. Find your "
        f'"Passed" dropdown option ID via the Fields API.'
        f"</div>"
        f"</div>"
    )

    api_key = st.text_input(
        "API key",
        type="password",
        key="_crm_api_key_input",
        placeholder="e.g. ABCDEFG1234567...",
    )
    passed_status_id = st.text_input(
        "Passed status ID",
        key="_crm_passed_id_input",
        placeholder="e.g. 123456 (the dropdown_option_id for 'Passed')",
    )

    save_col, cancel_col, _ = st.columns([1, 1, 4])
    with save_col:
        save_clicked = st.button("Save", type="primary", key="_crm_save")
    with cancel_col:
        if st.button("Cancel", type="secondary", key="_crm_cancel"):
            st.session_state["_crm_connect_open"] = False
            st.rerun()

    if save_clicked:
        if not api_key or not passed_status_id:
            st.error("Both fields are required.")
            return False
        db.update_firm_affinity_config(
            firm["id"], api_key.strip(), passed_status_id.strip()
        )
        st.success("Saved. You can run a sync now.")
        st.session_state["_crm_connect_open"] = False
        return True
    return False


def render_crm_tab(firm: dict) -> None:
    page_header(
        title="CRM",
        subtitle="Sync pass reasons from your CRM into the firm corpus.",
    )

    # Reload firm to get latest config
    firm = db.get_firm(firm["id"]) or firm
    is_connected = bool(
        firm.get("affinity_api_key") and firm.get("affinity_passed_status_id")
    )
    pass_reasons = db.list_pass_reasons(firm["id"])

    if not is_connected:
        st.html(
            status_card_html(
                title="Not connected",
                subtitle="Connect Affinity to pull pass-reason notes from your archive.",
            )
        )
        connect_col, _ = st.columns([1, 4])
        with connect_col:
            if st.button("Connect Affinity", type="primary", key="_crm_connect_btn"):
                st.session_state["_crm_connect_open"] = True
                st.rerun()

        if st.session_state.get("_crm_connect_open"):
            saved = _render_connect_form(firm)
            if saved:
                st.rerun()
    else:
        n_synced = sum(1 for p in pass_reasons if p.get("source") == "affinity")
        last_sync = _last_sync_label(pass_reasons)
        subtitle = (
            f"{n_synced} pass reasons synced"
            + (f" · last synced {last_sync}" if last_sync else " · never synced")
        )
        st.html(status_card_html(title="Connected to Affinity", subtitle=subtitle))

        sync_col, dis_col, _ = st.columns([1, 1, 4])
        with sync_col:
            sync_clicked = st.button("Sync now", type="primary", key="_crm_sync")
        with dis_col:
            if st.button("Disconnect", type="secondary", key="_crm_disconnect"):
                db.update_firm_affinity_config(firm["id"], None, None)
                st.success("Disconnected.")
                st.rerun()

        if sync_clicked:
            try:
                with st.spinner("Syncing from Affinity..."):
                    counts = sync_pass_reasons(firm["id"])
                st.success(
                    f"Sync complete. Inserted: {counts['inserted']}  ·  "
                    f"Updated: {counts['updated']}  ·  Skipped: {counts['skipped']}"
                )
                st.rerun()
            except AffinityNotConfigured as e:
                st.error(f"Affinity not configured: {e}")
            except AffinityError as e:
                st.error(f"Affinity sync failed: {e}")
            except Exception as e:
                st.error(f"Unexpected error during sync: {e}")

    # Recent pass reasons table
    if pass_reasons:
        st.html('<div style="height: 24px;"></div>')
        st.html(section_label("Recent pass reasons"))
        rows = []
        for p in pass_reasons[:50]:
            rows.append(
                [
                    _esc(p.get("company_name") or "—"),
                    _esc(_truncate(p.get("reason_text"), 80)),
                    _esc(p.get("deal_date") or "—"),
                    f'<span style="color: {TEXT_SECONDARY};">{_esc(p.get("source") or "")}</span>',
                ]
            )
        st.html(data_table(["Company", "Reason snippet", "Date", "Source"], rows))
