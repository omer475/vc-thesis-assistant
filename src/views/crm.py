"""CRM tab — sync pass reasons from Affinity.

Stub for design step 3; functional Affinity logic lands as BRIEF.md Step 4
(after design step 6); the UI on top of it is design step 7.
"""

from __future__ import annotations

from src.views._helpers import page_header, placeholder_card


def render_crm_tab(firm: dict) -> None:
    page_header(
        title="CRM",
        subtitle="Sync pass reasons from your CRM into the firm corpus.",
    )
    placeholder_card(
        "Affinity sync lands in BRIEF.md step 4 (functional logic) and design "
        "step 7 (UI). When connected, this tab will show sync status, a table "
        "of imported pass reasons, and a sync-now button — feeding the killer "
        "&ldquo;suppress bad-pass red flags&rdquo; behavior in the analyzer."
    )
