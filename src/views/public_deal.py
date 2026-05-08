"""Public deal-page renderer.

Triggered by `?deal=<analysis_id>` in the URL. Renders the read-only,
login-free view of an analysis. Everything is one HTML block (no Streamlit
components inside the card) so layout is deterministic and there is no
admin chrome.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import streamlit as st
from markdown_it import MarkdownIt

from src import cache, db
from src.components import pretty_filename, section_label, verdict_pill
from src.styles import (
    ASK_BG,
    ASK_BORDER,
    ASK_TEXT,
    BG_CARD,
    BG_SIDEBAR,
    BORDER_DEFAULT,
    RADIUS_LG,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    inject_global_css,
    inject_public_mode_css,
)

_MD = MarkdownIt()


# ----- helpers ---------------------------------------------------------------


def _format_timestamp(iso: str) -> str:
    """Format an ISO timestamp from the DB into something readable."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso[:19].replace("T", " ")
    return dt.strftime("%b %-d, %Y · %H:%M UTC")


def _escape(value: str | None) -> str:
    return html.escape(value or "", quote=True)


def _bullet_html(bullet: dict[str, Any], n: int, *, is_last: bool) -> str:
    text = _escape(bullet.get("text"))
    quote = bullet.get("citation_quote")
    fname = bullet.get("citation_filename")

    citation_html = ""
    if fname:
        pretty = _escape(pretty_filename(fname))
        if quote:
            citation_html = (
                f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; '
                f'margin-top: 6px; line-height: 1.5;">'
                f'"{_escape(quote)}" · '
                f'<span title="{_escape(fname)}" style="color: {TEXT_SECONDARY};">'
                f"{pretty}</span></div>"
            )
        else:
            citation_html = (
                f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; '
                f'margin-top: 6px;">'
                f'<span title="{_escape(fname)}">{pretty}</span></div>'
            )

    border_bottom = (
        "" if is_last else f"border-bottom: 0.5px solid {BORDER_DEFAULT};"
    )

    return (
        f'<li style="display: flex; gap: 14px; padding: 14px 0; '
        f"{border_bottom}"
        f' list-style: none;">'
        f'<div style="flex: 0 0 22px; width: 22px; height: 22px; '
        f"border-radius: 99px; background: {BG_SIDEBAR}; color: {TEXT_PRIMARY}; "
        f"display: flex; align-items: center; justify-content: center; "
        f'font-size: 12px; font-weight: 500; margin-top: 1px; line-height: 1;">'
        f"{n}</div>"
        f'<div style="flex: 1; min-width: 0;">'
        f'<div style="font-size: 15px; line-height: 1.6; color: {TEXT_PRIMARY};">'
        f"{text}</div>"
        f"{citation_html}"
        f"</div>"
        f"</li>"
    )


def _ask_first_html(questions: list[str]) -> str:
    questions_lis = "".join(
        f'<li style="margin-bottom: 8px; line-height: 1.55;">{_escape(q)}</li>'
        for q in questions
    )
    return (
        f'<div style="margin-top: 28px;">'
        f'{section_label("Ask first")}'
        f'<div style="background: {ASK_BG}; border: 0.5px solid {ASK_BORDER}; '
        f"border-radius: {RADIUS_MD}; padding: 16px 20px; color: {ASK_TEXT}; "
        f'font-size: 14px;">'
        f'<ol style="margin: 0; padding-left: 20px;">{questions_lis}</ol>'
        f"</div></div>"
    )


def _memo_html(full_memo_md: str) -> str:
    if not full_memo_md:
        return ""
    rendered = _MD.render(full_memo_md)
    return (
        f'<details style="margin-top: 28px;">'
        f'<summary style="cursor: pointer; font-size: 13px; color: {TEXT_SECONDARY}; '
        f"padding: 14px 0; border-top: 0.5px solid {BORDER_DEFAULT}; "
        f"border-bottom: 0.5px solid {BORDER_DEFAULT}; list-style: none; "
        f'user-select: none;">'
        f'<span style="font-weight: 500;">Full memo — deeper analysis</span>'
        f"</summary>"
        f'<div style="padding: 16px 0 4px 0; font-size: 14px; line-height: 1.7; '
        f'color: {TEXT_PRIMARY};">{rendered}</div>'
        f"</details>"
    )


def _footer_html(firm_name: str, timestamp: str) -> str:
    return (
        f'<footer style="margin-top: 28px; padding-top: 16px; '
        f"border-top: 0.5px solid {BORDER_DEFAULT}; "
        f"display: flex; justify-content: space-between; "
        f"align-items: center; gap: 12px; "
        f'font-size: 12px; color: {TEXT_TERTIARY};">'
        f'<span>{_escape(firm_name)} Thesis Assistant</span>'
        f"<span>{_escape(timestamp)}</span>"
        f"</footer>"
    )


def _card_open(extra_padding: bool = False) -> str:
    pad = "32px" if extra_padding else "32px"
    return (
        f'<div style="max-width: 720px; margin: 0 auto; '
        f"background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; "
        f'border-radius: {RADIUS_LG}; padding: {pad};">'
    )


def _card_close() -> str:
    return "</div>"


# ----- public API ------------------------------------------------------------


def render_not_found() -> None:
    not_found_html = (
        f"{_card_open()}"
        f'{section_label("Deal not found")}'
        f'<p style="font-size: 15px; line-height: 1.6; color: {TEXT_PRIMARY}; margin: 0;">'
        f"This share link no longer exists or has expired. "
        f"Ask the operator to send you a fresh link."
        f"</p>"
        f"{_card_close()}"
    )
    st.html(not_found_html)


def render_public_deal_page(analysis_id: str) -> None:
    """Render the login-free public deal page.

    The whole card is one st.html block — no Streamlit components inside.
    """
    st.set_page_config(
        page_title="Deal Analysis",
        page_icon="V",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    inject_global_css()
    inject_public_mode_css()

    analysis = db.get_analysis(analysis_id)
    if not analysis:
        render_not_found()
        return

    deck = analysis.get("deck") or {}
    firm_id = deck.get("firm_id")
    firm = cache.get_firm(firm_id) if firm_id else None
    firm_name = firm["name"] if firm else "Unknown firm"

    headline = (
        deck.get("subject")
        or deck.get("original_filename")
        or "Deal Analysis"
    )
    verdict = analysis.get("verdict") or "Unknown"
    bullets = analysis.get("bullets") or []
    questions = analysis.get("questions") or []
    full_memo_md = analysis.get("full_memo_md") or ""
    timestamp = _format_timestamp(analysis.get("created_at") or "")

    # Bullets (numbered, with citations, divider between but not after last)
    bullets_html = ""
    if bullets:
        bullets_html = "".join(
            _bullet_html(b, i + 1, is_last=(i == len(bullets) - 1))
            for i, b in enumerate(bullets)
        )
        bullets_block = (
            f'{section_label("Why")}'
            f'<ol style="list-style: none; padding: 0; margin: 0;">{bullets_html}</ol>'
        )
    else:
        bullets_block = ""

    # Ask first (only if verdict matches and questions exist)
    ask_block = (
        _ask_first_html(questions) if verdict == "Ask first" and questions else ""
    )

    page_html = (
        f"{_card_open(extra_padding=True)}"
        f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; '
        f"letter-spacing: 0.06em; text-transform: uppercase; "
        f'font-weight: 500; margin-bottom: 8px;">{_escape(firm_name)}</div>'
        f'<h1 style="font-size: 22px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'margin: 0 0 20px 0; line-height: 1.3;">{_escape(headline)}</h1>'
        f'<div style="margin-bottom: 28px;">{verdict_pill(verdict, "lg")}</div>'
        f"{bullets_block}"
        f"{ask_block}"
        f"{_memo_html(full_memo_md)}"
        f"{_footer_html(firm_name, timestamp)}"
        f"{_card_close()}"
    )

    st.html(page_html)
