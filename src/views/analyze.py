"""Analyze tab — daily deal-triage surface.

Layout:
  - Header (Analyze + subtitle) with "+ New analysis" button on the right.
  - "+ New analysis" opens a modal dialog with manual metadata fields:
    analysis name, company name, website, investment sought, analyst persona.
  - On submit: run analysis (real if API key available; mock otherwise) and
    display the verdict, why bullets, and questions to ask.
  - Below: "Recent deals" — list of past analyses (moved here from Analytics).
"""

from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import streamlit as st
from pypdf import PdfReader

from src import cache, db
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
    ACCENT,
    ACCENT_DARK,
    ACCENT_MUTED,
    ASK_BG,
    ASK_BORDER,
    ASK_TEXT,
    BG_CARD,
    BG_ELEVATED,
    BORDER_DEFAULT,
    FONT_SANS,
    FONT_SERIF,
    PASS_DOT,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from src.views._helpers import page_header


ANALYST_PERSONAS = [
    {
        "label": "Strategic Lead",
        "focus": "thesis fit, defensibility, long-term wedge",
    },
    {
        "label": "Market Analyst",
        "focus": "market sizing, timing, competitive landscape",
    },
    {
        "label": "Founder Specialist",
        "focus": "team quality, founder-market fit, execution signal",
    },
]

# Session keys
_LOCAL_ANALYSES_KEY = "_analyze_local_store"
_DIALOG_OPEN_KEY = "_analyze_dialog_open"


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


def _local_analyses(firm_id: str) -> list[dict]:
    store = st.session_state.setdefault(_LOCAL_ANALYSES_KEY, {})
    return store.setdefault(firm_id, [])


def _all_analyses(firm: dict) -> list[dict]:
    """Combine DB analyses with session-state ones."""
    try:
        db_rows = cache.list_analyses_for_firm(firm["id"], limit=50) or []
    except Exception:
        db_rows = []
    local = _local_analyses(firm["id"])
    return local + db_rows


def _mock_analysis_result(metadata: dict, deck_text: str) -> dict:
    """Generate a plausible analysis when the Anthropic API key is missing.
    Outputs the same shape as `src.analyze.run_analysis`. Verdict cycles
    through the three values deterministically from the seed so the mock
    isn't always the same."""
    seed = (metadata.get("analysis_name") or "") + (metadata.get("company_name") or "")
    verdict_choice = int(hashlib.md5(seed.encode("utf-8")).hexdigest()[:2], 16) % 3
    verdict = ("Take meeting", "Ask first", "Pass")[verdict_choice]

    company = metadata.get("company_name") or "the company"
    persona = metadata.get("analyst_persona") or ANALYST_PERSONAS[0]["label"]

    bullets = [
        {
            "text": f"Thesis alignment is strong — {company} hits the stage and sector you back.",
            "citation_quote": "we back companies that change the shape of a market",
            "citation_filename": "investment_thesis.md",
        },
        {
            "text": f"Founder signal looks credible based on what's in the deck.",
            "citation_quote": "domain expertise compounds over time",
            "citation_filename": "thesis_v2.md",
        },
        {
            "text": f"Competitive landscape is reasonable but not blue ocean.",
            "citation_quote": "wedge first, platform later",
            "citation_filename": "founding_statement.md",
        },
    ]

    questions = [
        f"What's {company}'s month-over-month retention by cohort?",
        f"How does the wedge expand into the platform you describe in slide 7?",
        f"Which two of your competitors have lost a customer to you, and why?",
    ]

    full_memo = (
        f"# {metadata.get('analysis_name') or company}\n\n"
        f"**Analyst persona:** {persona}\n\n"
        f"## Verdict — {verdict}\n\n"
        f"This is a mock analysis generated locally because no Anthropic API "
        f"key is configured. Plug a real key into `.env` to get live triage.\n\n"
        f"## Why\n\n"
        + "\n".join(f"- {b['text']}" for b in bullets)
        + f"\n\n## Questions to ask\n\n"
        + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    )

    return {
        "verdict": verdict,
        "bullets": bullets,
        "questions": questions,
        "full_memo_md": full_memo,
        "analysis_id": str(uuid.uuid4()),
        "deck_id": str(uuid.uuid4()),
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_mock": True,
    }


def _persist_mock_analysis(firm_id: str, result: dict) -> None:
    """Stash a mock analysis into session_state so it shows in Recent deals."""
    metadata = result.get("metadata", {})
    deck = {
        "subject": metadata.get("analysis_name") or metadata.get("company_name"),
        "original_filename": metadata.get("deck_filename"),
        "firm_id": firm_id,
        "partner_id": None,
    }
    row = {
        "id": result["analysis_id"],
        "verdict": result["verdict"],
        "bullets": result["bullets"],
        "questions": result["questions"],
        "full_memo_md": result["full_memo_md"],
        "created_at": result["created_at"],
        "deck": deck,
        "partner": None,
        "metadata": metadata,
    }
    _local_analyses(firm_id).insert(0, row)


def _render_completed_triage(result: dict) -> None:
    """Render the full analysis result: verdict, bullets, questions."""
    verdict = result.get("verdict") or "Unknown"
    bullets = result.get("bullets") or []
    questions = result.get("questions") or []

    # Verdict pill row
    pill_html = verdict_pill(verdict, "lg")
    st.html(
        f'<div style="margin-bottom: 20px; display: flex; align-items: center; '
        f'gap: 14px;">{pill_html}'
        + (
            f'<span style="font-size: 12px; color: {TEXT_TERTIARY}; '
            f'letter-spacing: 0.04em;">Mock output — connect an API key for live analysis</span>'
            if result.get("is_mock")
            else ""
        )
        + f"</div>"
    )

    # Why bullets
    if bullets:
        items = []
        for i, b in enumerate(bullets, 1):
            text = esc_html(b.get("text"))
            items.append(
                f'<li style="display: flex; gap: 14px; padding: 16px 0; '
                f'list-style: none; border-bottom: 1px solid {BORDER_DEFAULT};">'
                f'<div style="flex: 0 0 28px; width: 28px; height: 28px; '
                f"border-radius: 99px; background: {ACCENT_DARK}; color: {ACCENT}; "
                f"display: flex; align-items: center; justify-content: center; "
                f'font-size: 12px; font-weight: 500; line-height: 1;">{i}</div>'
                f'<div style="font-size: 15px; line-height: 1.65; color: {TEXT_PRIMARY};">'
                f"{text}</div>"
                f"</li>"
            )
        if items:
            items[-1] = items[-1].replace(
                f"border-bottom: 1px solid {BORDER_DEFAULT};", ""
            )
        st.html(
            f'<div style="margin-top: 4px;">'
            f'<div class="vc-section-label">Why</div>'
            f'<ol style="list-style: none; padding: 0; margin: 0; '
            f'background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f'border-radius: {RADIUS_MD}; padding: 4px 22px;">'
            f'{"".join(items)}'
            f"</ol>"
            f"</div>"
        )

    # Questions to ask
    if questions:
        qs = "".join(
            f'<li style="margin-bottom: 12px; line-height: 1.65; '
            f'color: {TEXT_PRIMARY};">{esc_html(q)}</li>'
            for q in questions
        )
        st.html(
            f'<div style="margin-top: 28px;">'
            f'<div class="vc-section-label">Questions to ask</div>'
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 24px 28px; font-size: 15px;\">"
            f'<ol style="margin: 0; padding-left: 24px; color: {TEXT_SECONDARY};">{qs}</ol>'
            f"</div></div>"
        )


# ----- new-analysis dialog ---------------------------------------------------


@st.dialog("New analysis", width="large")
def _new_analysis_dialog(firm: dict) -> None:
    st.html(
        f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; '
        f'margin-bottom: 24px; line-height: 1.6;">'
        f"Drop a pitch deck and add the context that frames the analysis. "
        f"Required fields are marked with a dot."
        f"</div>"
    )

    deck_file = st.file_uploader(
        "Pitch deck · .pdf .md .txt",
        type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
        accept_multiple_files=False,
        key="_an_deck",
    )

    st.html('<div style="height: 8px;"></div>')

    col_a, col_b = st.columns(2)
    with col_a:
        analysis_name = st.text_input(
            "Analysis name •",
            key="_an_name",
            placeholder="e.g. ContractAI Series A · May 2026",
        )
    with col_b:
        company_name = st.text_input(
            "Company name •",
            key="_an_company",
            placeholder="ContractAI",
        )

    col_c, col_d = st.columns(2)
    with col_c:
        company_url = st.text_input(
            "Company website",
            key="_an_url",
            placeholder="https://contractai.com",
        )
    with col_d:
        investment_sought = st.text_input(
            "Investment sought",
            key="_an_amount",
            placeholder="$5M Series A",
        )

    persona_label = st.selectbox(
        "Analyst persona",
        options=[p["label"] for p in ANALYST_PERSONAS],
        key="_an_persona",
        help="Different personas weight the analysis toward different factors.",
    )
    persona = next(p for p in ANALYST_PERSONAS if p["label"] == persona_label)
    st.html(
        f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; '
        f'margin-top: -8px; margin-bottom: 16px; letter-spacing: 0.02em;">'
        f"Focus · {persona['focus']}</div>"
    )

    # Partner select (optional)
    try:
        partners = cache.list_partners(firm["id"]) or []
    except Exception:
        partners = []
    if partners:
        options = ["(none)"] + [(p.get("name") or p.get("email")) for p in partners]
        partner_sel = st.selectbox("Partner (optional)", options, key="_an_partner")
    else:
        partner_sel = "(none)"

    st.html('<div style="height: 16px;"></div>')

    col_run, col_cancel = st.columns([1, 1])
    with col_run:
        run_clicked = st.button(
            "Run analysis",
            type="primary",
            key="_an_run",
            use_container_width=True,
            disabled=not (deck_file and analysis_name.strip() and company_name.strip()),
        )
    with col_cancel:
        if st.button("Cancel", type="secondary", key="_an_cancel", use_container_width=True):
            st.rerun()

    if run_clicked and deck_file:
        try:
            deck_text, pages = _extract_uploaded_file(deck_file)
        except Exception as e:
            st.error(f"Could not read deck: {e}")
            return
        if not deck_text:
            st.error("No extractable text in this deck.")
            return

        metadata = {
            "analysis_name": analysis_name.strip(),
            "company_name": company_name.strip(),
            "company_url": company_url.strip(),
            "investment_sought": investment_sought.strip(),
            "analyst_persona": persona_label,
            "deck_filename": deck_file.name,
        }

        with st.spinner("Reading the deck and forming a verdict..."):
            result = _run_analysis_with_fallback(firm, deck_text, metadata)

        st.session_state["_an_last_result"] = result
        st.success("Analysis complete.")
        st.rerun()


def _run_analysis_with_fallback(firm: dict, deck_text: str, metadata: dict) -> dict:
    """Try real analysis via Claude; fall back to mock if the API key is
    missing or the call fails."""
    import os
    import traceback

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    use_real = api_key and not api_key.startswith("sk-dummy")

    if not use_real:
        st.warning(
            "ANTHROPIC_API_KEY isn't set on this deployment — showing mock "
            "output. Add it under Streamlit Cloud → Manage app → Settings → "
            "Secrets to enable real analysis."
        )
    else:
        try:
            from src.analyze import run_analysis
            result = run_analysis(
                firm["id"],
                deck_text=deck_text,
                deck_filename=metadata["deck_filename"],
                source="upload",
                partner_id=None,
                analyst_persona=metadata.get("analyst_persona") or None,
            )
            result["metadata"] = metadata
            result["created_at"] = datetime.now(timezone.utc).isoformat()
            return result
        except Exception as e:
            st.error(
                f"Live analysis failed — falling back to mock. "
                f"**{type(e).__name__}:** {e}"
            )
            with st.expander("Full traceback (for debugging)"):
                st.code(traceback.format_exc(), language="python")

    result = _mock_analysis_result(metadata, deck_text)
    _persist_mock_analysis(firm["id"], result)
    return result


# ----- main entry point ------------------------------------------------------


def render_analyze_tab(firm: dict) -> None:
    page_header(
        title="Analyze",
        subtitle="Triage incoming decks against your investor profile.",
    )

    # Header row: + New analysis button on the right
    head_col, btn_col = st.columns([4, 1.2])
    with btn_col:
        if st.button("+ New analysis", type="primary", key="_an_open", use_container_width=True):
            st.session_state.pop("_an_last_result", None)
            _new_analysis_dialog(firm)

    # Show last result inline (when present from this session)
    last_result = st.session_state.get("_an_last_result")
    if last_result is not None:
        meta = last_result.get("metadata", {})
        st.html('<div style="height: 16px;"></div>')
        st.html(
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f'border-radius: {RADIUS_LG}; padding: 32px 36px; margin-bottom: 28px;">'
            f'<div class="vc-section-label">Latest analysis</div>'
            f'<h2 style="font-family: {FONT_SERIF}; font-size: 28px; font-weight: 500; '
            f'color: {TEXT_PRIMARY}; margin: 4px 0 6px 0; line-height: 1.2;">'
            f'{esc_html(meta.get("analysis_name") or meta.get("company_name") or "Untitled analysis")}'
            f"</h2>"
            + (
                f'<div style="font-size: 13px; color: {TEXT_TERTIARY}; '
                f'margin-bottom: 22px;">'
                + esc_html(meta.get("company_name", ""))
                + (f' · <a href="{esc_html(meta["company_url"])}" target="_blank" '
                   f'style="color: {ACCENT};">{esc_html(meta["company_url"])}</a>'
                   if meta.get("company_url") else "")
                + (f' · {esc_html(meta["investment_sought"])}'
                   if meta.get("investment_sought") else "")
                + (f' · {esc_html(meta["analyst_persona"])}'
                   if meta.get("analyst_persona") else "")
                + "</div>"
                if meta else ""
            )
            + f"</div>"
        )
        _render_completed_triage(last_result)

        analysis_id = last_result.get("analysis_id")
        if analysis_id:
            st.html('<div style="height: 20px;"></div>')
            st.markdown("**Share link** — no login required for the recipient")
            st.code(share_url_for(analysis_id), language=None)
        return

    # No active result — show a calm empty state pointing to "+ New analysis"
    analyses = _all_analyses(firm)
    if not analyses:
        st.html(
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 56px 40px; text-align: center; "
            f'line-height: 1.7; margin-top: 16px;">'
            f'<div style="font-family: {FONT_SERIF}; font-size: 22px; color: {TEXT_PRIMARY}; '
            f'margin-bottom: 8px;">Run your first analysis</div>'
            f'<div style="font-size: 14px; color: {TEXT_SECONDARY}; max-width: 380px; margin: 0 auto;">'
            f"Click <span style=\"color: {TEXT_PRIMARY};\">+ New analysis</span> above to "
            f"upload a deck and see a verdict in seconds. Past analyses live under "
            f"<span style=\"color: {TEXT_PRIMARY};\">Analytics</span>."
            f"</div>"
            f"</div>"
        )
    else:
        # Subtle hint card — past deals live under Analytics now
        st.html(
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 28px; text-align: center; "
            f'margin-top: 16px;">'
            f'<div style="font-size: 14px; color: {TEXT_SECONDARY}; line-height: 1.7;">'
            f"You have <span style=\"color: {TEXT_PRIMARY}; font-weight: 500;\">"
            f'{len(analyses)} past {("deal" if len(analyses) == 1 else "deals")}</span>. '
            f"View them under <span style=\"color: {TEXT_PRIMARY};\">Analytics → Recent deals</span>."
            f"</div></div>"
        )
