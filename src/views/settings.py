"""Settings tab — firm identity, security, danger zone.

Stub for design step 3; full implementation lands in design step 9.
"""

from __future__ import annotations

from src.views._helpers import page_header, placeholder_card


def render_settings_tab(firm: dict) -> None:
    page_header(
        title="Settings",
        subtitle="Firm configuration.",
    )
    placeholder_card(
        "Settings lands in design step 9: identity display (firm slug, email "
        "address, Anthropic API key state), password change form, and a "
        "danger-zone placeholder for &ldquo;Delete this firm&rdquo; (disabled "
        "in v1)."
    )
