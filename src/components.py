"""HTML component helpers for the VC Thesis Assistant UI.

Each function in this module either:
  - returns an HTML string (for rendering via `st.markdown(..., unsafe_allow_html=True)`), or
  - is a thin wrapper around a native Streamlit component for consistency.

Visual constants come from `src.styles`. Tabler icons are loaded by the global
CSS injection.
"""

from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from typing import Any

import streamlit as st

# Explicit export list. Belt-and-suspenders against any environment that has
# trouble resolving module-level names — `__all__` makes the public surface
# unambiguous and discoverable.
__all__ = [
    "esc_html",
    "verdict_pill",
    "VERDICT_THEMES",
    "section_label",
    "pretty_filename",
    "primary_button",
    "secondary_button",
    "format_relative_time",
    "share_url_for",
    "deal_card",
    "status_card_html",
    "metric_card",
    "data_table",
]

from src.styles import (
    ASK_BG,
    ASK_BORDER,
    ASK_DOT,
    ASK_TEXT,
    BG_CARD,
    BG_SIDEBAR,
    BG_TABLE_HEAD,
    BORDER_DEFAULT,
    BORDER_HOVER,
    PASS_BG,
    PASS_BORDER,
    PASS_DOT,
    PASS_TEXT,
    RADIUS_MD,
    TAKE_BG,
    TAKE_BORDER,
    TAKE_DOT,
    TAKE_TEXT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)


def esc_html(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


# ----- Verdict pill ----------------------------------------------------------

VERDICT_THEMES: dict[str, dict[str, str]] = {
    "Take meeting": {
        "bg": TAKE_BG,
        "text": TAKE_TEXT,
        "border": TAKE_BORDER,
        "dot": TAKE_DOT,
        "icon": "ti-circle-check",
    },
    "Ask first": {
        "bg": ASK_BG,
        "text": ASK_TEXT,
        "border": ASK_BORDER,
        "dot": ASK_DOT,
        "icon": "ti-help-circle",
    },
    "Pass": {
        "bg": PASS_BG,
        "text": PASS_TEXT,
        "border": PASS_BORDER,
        "dot": PASS_DOT,
        "icon": "ti-circle-x",
    },
}

_FALLBACK_THEME = {
    "bg": BG_SIDEBAR,
    "text": TEXT_PRIMARY,
    "border": BORDER_DEFAULT,
    "dot": TEXT_TERTIARY,
    "icon": "ti-help",
}


def verdict_pill(verdict: str, size: str = "lg") -> str:
    """Return an inline HTML span styled as a verdict pill.

    `size`:
      - "lg" — used on the deal page (icon + label, ~28px tall)
      - "sm" — used in deal-list rows (colored dot + label, ~20px tall)
    """
    theme = VERDICT_THEMES.get(verdict, _FALLBACK_THEME)
    if size == "lg":
        return (
            f'<span style="'
            f"display: inline-flex; align-items: center; gap: 8px; "
            f"background: {theme['bg']}; color: {theme['text']}; "
            f"border: 0.5px solid {theme['border']}; "
            f"padding: 8px 14px; border-radius: {RADIUS_MD}; "
            f"font-size: 14px; font-weight: 500; line-height: 1;"
            f'">'
            f'<i class="ti {theme["icon"]}" style="font-size: 16px;"></i>'
            f"<span>{verdict}</span>"
            f"</span>"
        )
    if size == "sm":
        return (
            f'<span style="'
            f"display: inline-flex; align-items: center; gap: 6px; "
            f"background: {theme['bg']}; color: {theme['text']}; "
            f"padding: 2px 8px; border-radius: 99px; "
            f"font-size: 11px; font-weight: 500; line-height: 1.4;"
            f'">'
            f'<span style="display: inline-block; width: 5px; height: 5px; '
            f'border-radius: 99px; background: {theme["dot"]};"></span>'
            f"<span>{verdict}</span>"
            f"</span>"
        )
    raise ValueError(f"verdict_pill: unknown size {size!r} (expected 'lg' or 'sm')")


# ----- Section label ---------------------------------------------------------


def section_label(text: str) -> str:
    """Small uppercase, letter-spaced muted label introducing a section."""
    return f'<div class="vc-section-label">{text}</div>'


# ----- Pretty filename -------------------------------------------------------

# Heuristics validated by `tests/test_components.py` against all 6 example
# fixture filenames.

_THESIS_VERSION_RE = re.compile(r"^firm_thesis_v(\d+)_(\d{4})$")
_THESIS_NAMED_RE = re.compile(r"^firm_thesis_(.+)_(\d{4})$")
_TRAILING_YEAR_RE = re.compile(r"^(.+)_(\d{4})$")
_EXT_RE = re.compile(r"\.(md|pdf|txt)$", re.IGNORECASE)
_NUMERIC_PREFIX_RE = re.compile(r"^\d+_")


def pretty_filename(filename: str) -> str:
    """Convert a raw firm-doc filename into a human-readable label.

    Examples (all validated by the unit test):
      01_firm_thesis_v1_2012.md           -> Thesis v1 (2012)
      02_firm_thesis_v2_2015.md           -> Thesis v2 (2015)
      03_firm_thesis_v3_2018.md           -> Thesis v3 (2018)
      04_firm_thesis_four_futures_2024.md -> Thesis "Four Futures" (2024)
      05_founding_statement_2005.md       -> Founding statement (2005)
      06_pass_reasons_archive.md          -> Pass reasons archive
    """
    name = _EXT_RE.sub("", filename)
    name = _NUMERIC_PREFIX_RE.sub("", name)

    m = _THESIS_VERSION_RE.match(name)
    if m:
        return f"Thesis v{m.group(1)} ({m.group(2)})"

    m = _THESIS_NAMED_RE.match(name)
    if m:
        title = " ".join(w.capitalize() for w in m.group(1).split("_"))
        return f'Thesis "{title}" ({m.group(2)})'

    m = _TRAILING_YEAR_RE.match(name)
    if m:
        body = m.group(1).replace("_", " ").strip()
        body = body[0].upper() + body[1:] if body else body
        return f"{body} ({m.group(2)})"

    body = name.replace("_", " ").strip()
    return body[0].upper() + body[1:] if body else body


# ----- Buttons (thin wrappers around native st.button) -----------------------


def primary_button(label: str, *, key: str | None = None, disabled: bool = False) -> bool:
    """Native primary button styled by global CSS. Returns True when clicked."""
    return st.button(label, type="primary", key=key, disabled=disabled)


def secondary_button(label: str, *, key: str | None = None, disabled: bool = False) -> bool:
    """Native secondary button styled by global CSS. Returns True when clicked."""
    return st.button(label, type="secondary", key=key, disabled=disabled)


# ----- Time formatting -------------------------------------------------------


def format_relative_time(iso: str | None) -> str:
    """Format an ISO timestamp as a short relative-time label.

    Examples: 'just now', '12 min ago', '3h ago', '2d ago', 'May 5'.
    """
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso[:10]
    now = datetime.now(timezone.utc)
    diff = (now - dt).total_seconds()
    if diff < 0:
        return dt.strftime("%b %-d")
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{int(diff // 60)} min ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    if diff < 86400 * 7:
        return f"{int(diff // 86400)}d ago"
    return dt.strftime("%b %-d")


# ----- Share URL -------------------------------------------------------------


def share_url_for(analysis_id: str) -> str:
    """Build the public deal-page URL. Reads APP_PUBLIC_URL or defaults to localhost."""
    base = os.environ.get("APP_PUBLIC_URL", "http://localhost:8501").rstrip("/")
    return f"{base}/?deal={analysis_id}"


# ----- Deal card -------------------------------------------------------------


def deal_card(deal: dict[str, Any]) -> str:
    """A row in the Analyze tab's deal list — clickable link to ?deal=<id>.

    Expects a dict with: id (analysis id), verdict, deck (joined deck row),
    created_at, optional partner.
    """
    deck = deal.get("deck") or {}
    title = (
        deck.get("subject")
        or deck.get("original_filename")
        or "(unnamed deck)"
    )
    verdict = deal.get("verdict") or "Unknown"
    when = format_relative_time(deal.get("created_at"))

    partner_name = ""
    partner = deal.get("partner") or {}
    if partner:
        partner_name = partner.get("name") or partner.get("email") or ""

    bottom_parts = [p for p in (partner_name, when) if p]
    bottom_html = " · ".join(esc_html(p) for p in bottom_parts) if bottom_parts else ""

    href = share_url_for(deal.get("id") or "")
    pill = verdict_pill(verdict, "sm")

    return (
        f'<a href="{esc_html(href)}" target="_self" class="vc-deal-card" '
        f"style=\"display: block; text-decoration: none; "
        f"background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; "
        f"border-radius: {RADIUS_MD}; padding: 14px 16px; "
        f'margin-bottom: 8px; transition: border-color 0.12s ease;">'
        f'<div style="display: flex; align-items: center; gap: 16px;">'
        f'<div style="flex: 1; min-width: 0;">'
        f'<div style="font-size: 14px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'line-height: 1.3; margin-bottom: 4px; overflow: hidden; '
        f'text-overflow: ellipsis; white-space: nowrap;">{esc_html(title)}</div>'
        f'<div style="font-size: 12px; color: {TEXT_TERTIARY};">{bottom_html}</div>'
        f"</div>"
        f'<div style="flex: 0 0 auto;">{pill}</div>'
        f"</div>"
        f"</a>"
    )


# ----- Status card -----------------------------------------------------------


def status_card_html(
    title: str,
    subtitle: str = "",
    *,
    accent: str | None = None,
) -> str:
    """The shared 'state + actions' card surface used in Firm setup and CRM.

    Returns the OPENING + content of the card; callers should render any action
    buttons inside the card via Streamlit components, then close with
    `status_card_close_html()`. We split it because Streamlit buttons can't
    live inside a raw HTML string.
    """
    border = accent or BORDER_DEFAULT
    sub_html = (
        f'<div style="font-size: 13px; color: {TEXT_SECONDARY}; '
        f'margin-top: 6px; line-height: 1.5;">{esc_html(subtitle)}</div>'
        if subtitle
        else ""
    )
    return (
        f'<div style="background: {BG_CARD}; border: 0.5px solid {border}; '
        f'border-radius: {RADIUS_MD}; padding: 18px 20px;">'
        f'<div style="font-size: 14px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'line-height: 1.4;">{esc_html(title)}</div>'
        f"{sub_html}"
        f"</div>"
    )


# ----- Metric card -----------------------------------------------------------


def metric_card(label: str, value: str, hint: str = "") -> str:
    hint_html = (
        f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; '
        f'margin-top: 6px;">{esc_html(hint)}</div>'
        if hint
        else ""
    )
    return (
        f'<div style="background: {BG_SIDEBAR}; border-radius: {RADIUS_MD}; '
        f'padding: 16px 18px;">'
        f'<div style="font-size: 12px; color: {TEXT_SECONDARY}; '
        f'margin-bottom: 6px;">{esc_html(label)}</div>'
        f'<div style="font-size: 22px; font-weight: 500; color: {TEXT_PRIMARY}; '
        f'line-height: 1.1;">{esc_html(value)}</div>'
        f"{hint_html}"
        f"</div>"
    )


# ----- Data table ------------------------------------------------------------


def data_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a styled table as HTML.

    `headers` are plain strings (uppercased and tracked in CSS).
    `rows` are lists of HTML strings — caller is responsible for any escaping
    needed inside cell content.
    """
    head_cells = "".join(
        f'<th style="text-align: left; padding: 9px 14px; '
        f"font-size: 11px; font-weight: 500; "
        f"text-transform: uppercase; letter-spacing: 0.04em; "
        f'color: {TEXT_TERTIARY};">{esc_html(h)}</th>'
        for h in headers
    )

    if not rows:
        return (
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f'border-radius: {RADIUS_MD}; overflow: hidden;">'
            f'<table style="width: 100%; border-collapse: collapse; '
            f'background: {BG_TABLE_HEAD};">'
            f"<thead><tr>{head_cells}</tr></thead></table>"
            f'<div style="padding: 28px 16px; text-align: center; '
            f'font-size: 13px; color: {TEXT_TERTIARY};">No rows yet.</div>'
            f"</div>"
        )

    body_rows = []
    for i, row in enumerate(rows):
        is_last = i == len(rows) - 1
        border = (
            "" if is_last else f"border-bottom: 0.5px solid {BORDER_DEFAULT};"
        )
        cells = "".join(
            f'<td style="padding: 11px 14px; font-size: 13px; '
            f'color: {TEXT_PRIMARY}; vertical-align: middle;">{cell}</td>'
            for cell in row
        )
        body_rows.append(
            f'<tr style="{border}">{cells}</tr>'
        )
    body_html = "".join(body_rows)

    return (
        f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
        f'border-radius: {RADIUS_MD}; overflow: hidden;">'
        f'<table style="width: 100%; border-collapse: collapse;">'
        f'<thead style="background: {BG_TABLE_HEAD};"><tr>{head_cells}</tr></thead>'
        f"<tbody>{body_html}</tbody>"
        f"</table>"
        f"</div>"
    )
