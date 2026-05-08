"""Analyze tab — daily deal-triage surface.

Stub for design step 3; full implementation lands in design step 4.
"""

from __future__ import annotations

from src.views._helpers import page_header, placeholder_card


def render_analyze_tab(firm: dict) -> None:
    page_header(
        title="Analyze",
        subtitle="Triage incoming decks against the firm's thesis.",
    )
    placeholder_card(
        "Full daily-use surface lands in design step 4: a list of recent deals "
        "(each clickable to its public deal page) and a + New analysis flow that "
        "streams the triage block into an inline section. For now, use the CLI "
        "(<code>python -m src.analyze data/incoming_decks/&lt;deck&gt;.md</code>) "
        "or wait for step 4."
    )
