"""Partners tab — allowlist of partners whose decks get analyzed.

Stub for design step 3; full implementation lands in design step 6.
"""

from __future__ import annotations

from src.views._helpers import page_header, placeholder_card


def render_partners_tab(firm: dict) -> None:
    page_header(
        title="Partners",
        subtitle="Allowlist of partners whose forwarded decks will be analyzed.",
    )
    placeholder_card(
        "Partner CRUD lands in design step 6: a table of partners (name, email, "
        "joined date), and a +&nbsp;Add partner form. Email forwarding itself is "
        "Phase 2 work; this allowlist sets up the data model for it."
    )
