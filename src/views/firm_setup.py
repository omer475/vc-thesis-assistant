"""Firm setup tab — corpus, profile, and identity.

Stub for design step 3; full implementation lands in design step 5.
"""

from __future__ import annotations

from src.views._helpers import page_header, placeholder_card


def render_firm_setup_tab(firm: dict) -> None:
    page_header(
        title="Firm setup",
        subtitle="The corpus and profile that ground every analysis.",
    )
    placeholder_card(
        "Full firm-setup surface lands in design step 5: documents table with "
        "upload + delete, and a status card for the firm profile with view / "
        "regenerate actions. For now, the corpus and profile already exist in "
        "Supabase from the earlier ingest + profile runs."
    )
