"""HTML component helpers for the VC Thesis Assistant UI.

Each function in this module either:
  - returns an HTML string (for rendering via `st.markdown(..., unsafe_allow_html=True)`), or
  - is a thin wrapper around a native Streamlit component for consistency.

Visual constants come from `src.styles`. Tabler icons are loaded by the global
CSS injection.
"""

from __future__ import annotations

import re

import streamlit as st

from src.styles import (
    ASK_BG,
    ASK_BORDER,
    ASK_DOT,
    ASK_TEXT,
    BG_SIDEBAR,
    BORDER_DEFAULT,
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
