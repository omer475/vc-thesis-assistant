"""Firm setup tab — corpus + firm profile.

Two sections:
  1. Documents — upload, table of current corpus, delete
  2. Firm profile — status card with View / Regenerate actions
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import streamlit as st
from pypdf import PdfReader

from src import db
from src.components import (
    _esc,
    data_table,
    format_relative_time,
    section_label,
    status_card_html,
)
from src.ingest import SUPPORTED_EXTENSIONS
from src.profile import generate_profile
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


def _section_count(profile_md: str) -> int:
    """Count H2 sections in the profile (the spec format)."""
    return sum(1 for line in (profile_md or "").splitlines() if line.startswith("## "))


# ----- documents section -----------------------------------------------------


def _render_documents_section(firm: dict) -> None:
    docs = db.list_documents(firm["id"])

    # Section header with count + Upload button
    head_col, btn_col = st.columns([4, 1])
    with head_col:
        st.html(
            f'<div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px;">'
            f'<div class="vc-section-label" style="margin-bottom: 0;">'
            f"Documents · {len(docs)}</div>"
            f"</div>"
        )
    with btn_col:
        if st.button(
            "Upload docs", type="primary", key="_fs_upload_open"
        ):
            st.session_state["_fs_upload_open"] = not st.session_state.get(
                "_fs_upload_open_state", False
            )
            st.session_state["_fs_upload_open_state"] = (
                not st.session_state.get("_fs_upload_open_state", False)
            )

    if st.session_state.get("_fs_upload_open_state"):
        st.html(
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f'border-radius: {RADIUS_MD}; padding: 18px 20px; margin-bottom: 16px;">'
            f'<div class="vc-section-label" style="margin-bottom: 12px;">Upload documents</div>'
            f"</div>"
        )
        uploaded = st.file_uploader(
            "Drop documents here",
            type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
            accept_multiple_files=True,
            key="_fs_doc_upload",
            label_visibility="collapsed",
        )
        save_col, cancel_col, _ = st.columns([1, 1, 4])
        with save_col:
            save_clicked = st.button(
                "Save and ingest",
                type="primary",
                key="_fs_save",
                disabled=not uploaded,
            )
        with cancel_col:
            if st.button("Cancel", type="secondary", key="_fs_cancel"):
                st.session_state["_fs_upload_open_state"] = False
                st.rerun()

        if save_clicked and uploaded:
            results = []
            for f in uploaded:
                try:
                    text, pages = _extract_uploaded_file(f)
                except Exception as e:
                    results.append((f.name, False, f"failed to read ({e})"))
                    continue
                if not text:
                    results.append((f.name, False, "no extractable text"))
                    continue
                row = db.insert_document(firm["id"], f.name, text, pages)
                if row:
                    results.append((f.name, True, f"{pages} pages, {len(text):,} chars"))
                else:
                    results.append((f.name, False, "already ingested"))
            for name, ok, msg in results:
                if ok:
                    st.success(f"{name}: {msg}")
                else:
                    st.warning(f"{name}: {msg}")
            st.session_state["_fs_upload_open_state"] = False
            st.rerun()

    # Table
    if not docs:
        st.html(
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 28px; text-align: center; "
            f'font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.6;">'
            f"No documents yet. Upload firm thesis docs, pass-reason archives, "
            f"or any prose that defines your firm's strategy."
            f"</div>"
        )
        return

    rows = []
    for d in docs:
        chars = len(d.get("content") or "")
        rows.append(
            [
                _esc(d["filename"]),
                f'<span style="color: {TEXT_SECONDARY};">{d["page_count"]}</span>',
                f'<span style="color: {TEXT_SECONDARY};">'
                f'{format_relative_time(d.get("ingested_at"))}</span>',
                f'<span style="color: {TEXT_TERTIARY}; font-size: 12px;">'
                f"{chars:,} chars</span>",
            ]
        )
    st.html(data_table(["Filename", "Pages", "Ingested", ""], rows))

    # Delete control (kept simple — Streamlit row-level icon-buttons fight the
    # styled HTML table, so we expose deletion via a dropdown below)
    with st.expander("Delete a document", expanded=False):
        options = ["(pick one)"] + [d["filename"] for d in docs]
        sel = st.selectbox("File", options, key="_fs_delete_select")
        if sel != "(pick one)":
            target = next((d for d in docs if d["filename"] == sel), None)
            if target and st.button(
                f"Permanently delete '{sel}'", type="secondary", key="_fs_delete_btn"
            ):
                db.delete_document(target["id"])
                st.success(f"Deleted {sel}.")
                st.rerun()


# ----- profile section -------------------------------------------------------


@st.dialog("Firm profile")
def _show_profile_dialog(profile_md: str) -> None:
    st.markdown(profile_md)


def _render_profile_section(firm: dict) -> None:
    st.html('<div style="height: 28px;"></div>')
    st.html(section_label("Firm profile"))

    profile_md = firm.get("profile_md") or db.get_firm_profile(firm["id"]) or ""
    n_docs = db.count_documents(firm["id"])

    if profile_md:
        sections = _section_count(profile_md)
        title = f"Distilled from your {n_docs} documents."
        subtitle = f"{sections} sections · ~{len(profile_md):,} chars"
    else:
        title = "No profile yet."
        subtitle = f"Generate a profile from your {n_docs} document(s) to start analyzing decks."

    st.html(status_card_html(title, subtitle))

    # Action buttons row
    view_col, regen_col, _ = st.columns([1, 1, 4])
    with view_col:
        view_clicked = st.button(
            "View",
            type="secondary",
            key="_fs_profile_view",
            disabled=not profile_md,
        )
    with regen_col:
        regen_label = "Regenerate" if profile_md else "Generate profile"
        regen_clicked = st.button(
            regen_label,
            type="primary",
            key="_fs_profile_regen",
            disabled=n_docs == 0,
        )

    if view_clicked and profile_md:
        _show_profile_dialog(profile_md)

    if regen_clicked:
        with st.spinner("Distilling the firm's strategy..."):
            placeholder = st.empty()
            chunks: list[str] = []

            def on_chunk(text: str) -> None:
                chunks.append(text)
                placeholder.markdown("".join(chunks))

            result = generate_profile(firm["id"], stream_callback=on_chunk)
            placeholder.empty()

        usage = result["usage"]
        st.success("Profile generated and saved.")
        st.caption(
            f"Tokens — input: {usage['input_tokens']:,}  ·  "
            f"cache write: {usage['cache_creation_input_tokens']:,}  ·  "
            f"cache read: {usage['cache_read_input_tokens']:,}  ·  "
            f"output: {usage['output_tokens']:,}"
        )


# ----- main entry point ------------------------------------------------------


def render_firm_setup_tab(firm: dict) -> None:
    page_header(
        title="Firm setup",
        subtitle="The corpus and profile that ground every analysis.",
    )
    _render_documents_section(firm)
    _render_profile_section(firm)
