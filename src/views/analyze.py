"""Analyze tab — daily deal-triage surface.

Layout:
  - Page header (Analyze + subtitle) with a "+ New analysis" button on the right.
  - Inline new-analysis card (only when toggled): file uploader, optional
    partner select, "Run analysis" button, streaming response, completion
    state with copy-share-link + Done.
  - "Recent deals" section: a list of deal_cards for the last 50 analyses.

The whole card is a clickable link to /?deal=<id>; clicking it opens the
public deal page in the same tab.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import streamlit as st
from pypdf import PdfReader

from src import cache, db
from src.analyze import run_analysis
from src.components import (
    esc_html,
    deal_card,
    format_relative_time,
    section_label,
    share_url_for,
    verdict_pill,
)
from src.ingest import SUPPORTED_EXTENSIONS
from src.styles import (
    BG_CARD,
    BORDER_DEFAULT,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from src.views._helpers import page_header


# ----- helpers ---------------------------------------------------------------


def _extract_uploaded_file(uploaded_file) -> tuple[str, int]:
    """Extract text from a Streamlit UploadedFile in memory."""
    name = uploaded_file.name
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(uploaded_file.getvalue()))
        pages = [(p.extract_text() or "") for p in reader.pages]
        return "\n\n".join(pages).strip(), len(reader.pages)
    if suffix in {".md", ".txt"}:
        text = uploaded_file.getvalue().decode("utf-8", errors="replace").strip()
        return text, max(1, text.count("\n\n") // 5 + 1)
    raise ValueError(f"Unsupported file type: {suffix}")


def _render_completed_triage(result: dict) -> None:
    """Render the structured triage layout after an analysis completes."""
    verdict = result.get("verdict") or "Unknown"
    bullets = result.get("bullets") or []
    questions = result.get("questions")

    pill_html = verdict_pill(verdict, "lg")
    bullets_html = ""
    if bullets:
        items = []
        for i, b in enumerate(bullets, 1):
            text = esc_html(b.get("text"))
            items.append(
                f'<li style="display: flex; gap: 12px; padding: 10px 0; '
                f'list-style: none; border-bottom: 0.5px solid {BORDER_DEFAULT};">'
                f'<div style="flex: 0 0 22px; width: 22px; height: 22px; '
                f"border-radius: 99px; background: #F4F3EE; color: {TEXT_PRIMARY}; "
                f"display: flex; align-items: center; justify-content: center; "
                f'font-size: 12px; font-weight: 500;">{i}</div>'
                f'<div style="font-size: 14px; line-height: 1.55; color: {TEXT_PRIMARY};">'
                f"{text}</div>"
                f"</li>"
            )
        # Strip last bullet's bottom border via re-building the last item
        if items:
            items[-1] = items[-1].replace(
                f"border-bottom: 0.5px solid {BORDER_DEFAULT};", ""
            )
        bullets_html = (
            f'<div style="margin-top: 16px;">'
            f'<div class="vc-section-label" style="margin-bottom: 4px;">Why</div>'
            f'<ol style="list-style: none; padding: 0; margin: 0;">'
            f'{"".join(items)}'
            f"</ol>"
            f"</div>"
        )

    questions_html = ""
    if verdict == "Ask first" and questions:
        from src.styles import ASK_BG, ASK_BORDER, ASK_TEXT

        qs = "".join(
            f'<li style="margin-bottom: 8px; line-height: 1.55;">{esc_html(q)}</li>'
            for q in questions
        )
        questions_html = (
            f'<div style="margin-top: 16px;">'
            f'<div class="vc-section-label" style="margin-bottom: 4px;">Ask first</div>'
            f'<div style="background: {ASK_BG}; border: 0.5px solid {ASK_BORDER}; '
            f"border-radius: {RADIUS_MD}; padding: 14px 18px; color: {ASK_TEXT}; "
            f'font-size: 14px;">'
            f'<ol style="margin: 0; padding-left: 20px;">{qs}</ol>'
            f"</div></div>"
        )

    st.html(
        f'<div style="margin-bottom: 12px;">{pill_html}</div>'
        f"{bullets_html}"
        f"{questions_html}"
    )


# ----- main entry point ------------------------------------------------------


def render_analyze_tab(firm: dict) -> None:
    page_header(
        title="Analyze",
        subtitle="Triage incoming decks against the firm's thesis.",
    )

    state_key_open = "_analyze_new_open"
    state_key_result = "_analyze_last_result"
    state_key_filename = "_analyze_last_filename"

    is_open = st.session_state.get(state_key_open, False)
    last_result = st.session_state.get(state_key_result)
    last_filename = st.session_state.get(state_key_filename, "")

    # Header row: + New analysis on the right
    col_spacer, col_btn = st.columns([4, 1])
    with col_btn:
        if not is_open:
            if st.button("+ New analysis", type="primary", key="_analyze_open"):
                st.session_state[state_key_open] = True
                st.session_state[state_key_result] = None
                st.session_state[state_key_filename] = ""
                st.rerun()

    # Inline "+ New analysis" card
    if is_open:
        st.html(
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 20px; margin-bottom: 24px;\">"
            f'<div class="vc-section-label" style="margin-bottom: 12px;">New analysis</div>'
            f"</div>"
        )

        # Streamlit components for the form must come right after the html() above;
        # they appear visually below the card opener but before the next st.html block.
        deck_file = st.file_uploader(
            "Upload a deck (.pdf, .md, .txt)",
            type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
            accept_multiple_files=False,
            key="_analyze_deck_upload",
            label_visibility="visible",
        )

        partners = cache.list_partners(firm["id"])
        partner_id = None
        if partners:
            options = ["(none)"] + [(p.get("name") or p.get("email")) for p in partners]
            sel = st.selectbox("Partner (optional)", options, key="_analyze_partner")
            if sel != "(none)":
                idx = options.index(sel) - 1
                partner_id = partners[idx]["id"]

        run_col, done_col, _ = st.columns([1, 1, 4])
        with run_col:
            run_clicked = st.button(
                "Run analysis",
                type="primary",
                key="_analyze_run",
                disabled=(deck_file is None),
            )
        with done_col:
            if last_result is not None:
                done_clicked = st.button("Done", type="secondary", key="_analyze_done")
                if done_clicked:
                    st.session_state[state_key_open] = False
                    st.session_state[state_key_result] = None
                    st.session_state[state_key_filename] = ""
                    st.rerun()

        if run_clicked and deck_file is not None:
            try:
                deck_text, _pages = _extract_uploaded_file(deck_file)
            except Exception as e:
                st.error(f"Could not read deck: {e}")
                return

            if not deck_text:
                st.error("No extractable text in this deck (image-only PDFs aren't supported yet).")
                return

            with st.spinner("Reading the deck and writing the memo..."):
                stream_placeholder = st.empty()
                chunks: list[str] = []

                def on_chunk(text: str) -> None:
                    chunks.append(text)
                    stream_placeholder.markdown("".join(chunks))

                result = run_analysis(
                    firm["id"],
                    deck_text=deck_text,
                    deck_filename=deck_file.name,
                    source="upload",
                    partner_id=partner_id,
                    stream_callback=on_chunk,
                )
                stream_placeholder.empty()

            st.session_state[state_key_result] = result
            st.session_state[state_key_filename] = deck_file.name
            cache.invalidate_all()
            st.rerun()

        if last_result is not None:
            st.html(
                f'<div style="height: 12px;"></div>'
            )
            _render_completed_triage(last_result)
            analysis_id = last_result.get("analysis_id")
            if analysis_id:
                st.markdown("**Share link** — no login required for the recipient")
                st.code(share_url_for(analysis_id), language=None)

    # Recent deals
    st.html('<div style="height: 8px;"></div>')
    st.html(section_label("Recent deals"))
    analyses = cache.list_analyses_for_firm(firm["id"], limit=50)
    if not analyses:
        st.html(
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 28px; text-align: center; "
            f'font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.6;">'
            f"No deals yet. Click <b>+ New analysis</b> above to triage your first deck."
            f"</div>"
        )
        return

    cards_html = "".join(deal_card(a) for a in analyses)
    st.html(cards_html)
