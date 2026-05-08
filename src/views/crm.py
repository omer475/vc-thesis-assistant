"""CRM tab — Affinity connection + sync UI + manual paste fallback.

Three sections, top to bottom:
  - Affinity status card (Not connected → Connect form, or Connected → Sync now)
  - Manual paste-and-import (works without any CRM)
  - Recent pass reasons table

Functional sync logic lives in `src/affinity.py`. Manual upload is a parser
in this file — accepts free-form text where blank lines separate entries
and a "Company —" or "Company:" heading prefix is best-effort extracted.
"""

from __future__ import annotations

import re

import streamlit as st

from src import cache, db
from src.affinity import AffinityError, AffinityNotConfigured, sync_pass_reasons
from src.components import (
    esc_html,
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


# Regex helpers for the manual paste parser.
_COMPANY_HEADING_RE = re.compile(
    r"^(?P<co>[A-Z][\w &.\-/]{1,50}?)\s*[—\-:](?:\s|$)"
)
_PASSED_ON_RE = re.compile(
    r"^[Pp]assed (?:on |)(?P<co>[A-Z][\w]{1,40})", re.MULTILINE
)


def parse_pasted_pass_reasons(text: str) -> list[dict]:
    """Best-effort parse of free-form pasted text into pass-reason rows.

    Conventions accepted:
      - Blank lines separate entries.
      - First line of each entry is treated as a possible heading; if it
        starts with `Company —` / `Company:` / `Company -`, the company
        is extracted from before the separator.
      - Otherwise, the parser scans for "Passed on COMPANY" anywhere in
        the entry and uses that.
      - If nothing matches, the entry is still ingested with company=None.
    """
    text = (text or "").strip()
    if not text:
        return []
    chunks = re.split(r"\n\s*\n", text)
    out: list[dict] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        company: str | None = None
        first_line = chunk.split("\n", 1)[0]
        m = _COMPANY_HEADING_RE.match(first_line)
        if m:
            company = m.group("co").strip()
        else:
            m = _PASSED_ON_RE.search(chunk)
            if m:
                company = m.group("co").strip()
        out.append({"company_name": company, "reason_text": chunk})
    return out


def _render_manual_upload(firm: dict) -> None:
    st.html('<div style="height: 28px;"></div>')
    st.html(section_label("Or paste pass reasons manually"))
    st.html(
        f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; '
        f'line-height: 1.5; margin-bottom: 12px;">'
        f"Useful if you don't use Affinity, or for backfilling notes that aren't "
        f"in your CRM. Paste your pass reasons below — separate each entry with a "
        f"blank line. The parser will best-effort extract a company name from a "
        f"<code>Company —</code> or <code>Company:</code> heading, but you can "
        f"paste plain text and it still works."
        f"</div>"
    )

    pasted = st.text_area(
        "Paste below",
        height=180,
        key="_crm_manual_paste",
        placeholder=(
            "Stripe — passed 2010\n"
            "We thought it was two college kids with a toy. Lesson: don't pattern-match\n"
            "founder age to market signal.\n"
            "\n"
            "Notion — passed 2018\n"
            "We said wikis are dead. Lesson: dead categories get reset by new primitives.\n"
        ),
        label_visibility="collapsed",
    )

    save_col, _ = st.columns([1, 4])
    with save_col:
        save_clicked = st.button(
            "Import",
            type="primary",
            key="_crm_manual_import",
            disabled=not pasted.strip(),
        )

    if save_clicked:
        entries = parse_pasted_pass_reasons(pasted)
        if not entries:
            st.warning("Nothing to import — paste at least one entry.")
            return
        counts = {"inserted": 0, "updated": 0, "skipped": 0}
        for entry in entries:
            try:
                result = db.upsert_pass_reason(
                    firm_id=firm["id"],
                    source="manual",
                    reason_text=entry["reason_text"],
                    company_name=entry["company_name"],
                )
                action = result.get("action", "skipped")
                counts[action] = counts.get(action, 0) + 1
            except Exception as e:
                st.error(f"Failed on '{entry['company_name'] or '(unnamed)'}': {e}")
                counts["skipped"] += 1
        cache.invalidate_all()
        st.success(
            f"Imported {len(entries)} entries. Inserted: {counts['inserted']}  ·  "
            f"Updated: {counts['updated']}  ·  Skipped: {counts['skipped']}"
        )
        st.rerun()


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
        cache.invalidate_all()
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
    firm = cache.get_firm(firm["id"]) or firm
    is_connected = bool(
        firm.get("affinity_api_key") and firm.get("affinity_passed_status_id")
    )
    pass_reasons = cache.list_pass_reasons(firm["id"])

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
                cache.invalidate_all()
                st.success("Disconnected.")
                st.rerun()

        if sync_clicked:
            try:
                with st.spinner("Syncing from Affinity..."):
                    counts = sync_pass_reasons(firm["id"])
                cache.invalidate_all()
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

    # Manual upload — always visible
    _render_manual_upload(firm)

    # Recent pass reasons table — re-fetch in case the manual upload added rows
    pass_reasons = cache.list_pass_reasons(firm["id"])
    if pass_reasons:
        st.html('<div style="height: 24px;"></div>')
        st.html(section_label("Recent pass reasons"))
        rows = []
        for p in pass_reasons[:50]:
            rows.append(
                [
                    esc_html(p.get("company_name") or "—"),
                    esc_html(_truncate(p.get("reason_text"), 80)),
                    esc_html(p.get("deal_date") or "—"),
                    f'<span style="color: {TEXT_SECONDARY};">{esc_html(p.get("source") or "")}</span>',
                ]
            )
        st.html(data_table(["Company", "Reason snippet", "Date", "Source"], rows))
