"""Analytics tab — usage metrics over the last 30 days.

Stub for design step 3; full implementation lands in design step 8.
"""

from __future__ import annotations

from src.views._helpers import page_header, placeholder_card


def render_analytics_tab(firm: dict) -> None:
    page_header(
        title="Analytics",
        subtitle="Past 30 days.",
    )
    placeholder_card(
        "Analytics lands in design step 8: a 4-up grid of metric cards "
        "(deals analyzed, verdict mix, average latency, tokens used), a "
        "deals-over-time line chart, and a by-partner table."
    )
