"""Analytics tab — usage metrics for the past 30 days.

Layout:
  - 4-up grid of metric cards (Deals analyzed, Verdict mix, Avg latency,
    Tokens used).
  - "Deals over time" — daily line chart of analysis count.
  - "By partner" — data_table.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from src import cache, db
from src.components import deal_card, esc_html, data_table, metric_card, section_label
from src.styles import (
    ASK_DOT,
    BG_CARD,
    BORDER_DEFAULT,
    FONT_SERIF,
    PASS_DOT,
    RADIUS_MD,
    TAKE_DOT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from src.views._helpers import page_header

WINDOW_DAYS = 30


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _verdict_mix_html(counts: dict[str, int]) -> str:
    take = counts.get("Take meeting", 0)
    ask = counts.get("Ask first", 0)
    fail = counts.get("Pass", 0)
    return (
        f'<span style="display: inline-flex; gap: 12px; font-size: 14px;">'
        f'<span style="display: inline-flex; align-items: center; gap: 4px;">'
        f'<span style="display: inline-block; width: 6px; height: 6px; '
        f'border-radius: 99px; background: {TAKE_DOT};"></span>'
        f'<span style="font-weight: 500; color: {TEXT_PRIMARY};">{take}</span></span>'
        f'<span style="display: inline-flex; align-items: center; gap: 4px;">'
        f'<span style="display: inline-block; width: 6px; height: 6px; '
        f'border-radius: 99px; background: {ASK_DOT};"></span>'
        f'<span style="font-weight: 500; color: {TEXT_PRIMARY};">{ask}</span></span>'
        f'<span style="display: inline-flex; align-items: center; gap: 4px;">'
        f'<span style="display: inline-block; width: 6px; height: 6px; '
        f'border-radius: 99px; background: {PASS_DOT};"></span>'
        f'<span style="font-weight: 500; color: {TEXT_PRIMARY};">{fail}</span></span>'
        f"</span>"
    )


def render_analytics_tab(firm: dict) -> None:
    page_header(
        title="Analytics",
        subtitle=f"Verdict mix, throughput, and partner activity over the past {WINDOW_DAYS} days.",
    )

    cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).isoformat()
    # Combine DB + session-state analyses so local mock data shows up too
    try:
        db_rows = cache.list_analyses_for_firm(firm["id"], limit=500) or []
    except Exception:
        db_rows = []
    local_rows = (st.session_state.get("_analyze_local_store") or {}).get(firm["id"], [])
    all_analyses = local_rows + db_rows
    window = [a for a in all_analyses if (a.get("created_at") or "") >= cutoff]

    # Metrics
    n_deals = len(window)
    verdict_counts: dict[str, int] = defaultdict(int)
    total_latency = 0
    n_with_latency = 0
    total_in = total_out = 0
    for a in window:
        verdict_counts[a.get("verdict") or "Unknown"] += 1
        if a.get("latency_ms") is not None:
            total_latency += a["latency_ms"]
            n_with_latency += 1
        total_in += a.get("tokens_in") or 0
        total_out += a.get("tokens_out") or 0

    avg_latency = (
        f"{round(total_latency / n_with_latency / 1000, 1)}s"
        if n_with_latency
        else "—"
    )
    total_tokens = total_in + total_out

    # 4-up grid via st.columns
    cols = st.columns(4)
    metrics = [
        ("Deals analyzed", str(n_deals), f"in past {WINDOW_DAYS}d"),
        ("Verdict mix", _verdict_mix_html(verdict_counts), "Take · Ask · Pass"),
        ("Avg latency", avg_latency, "per analysis"),
        ("Tokens used", _format_tokens(total_tokens), f"in · {_format_tokens(total_out)} out"),
    ]
    for col, (label, value, hint) in zip(cols, metrics):
        with col:
            # metric_card normally escapes value, but the verdict-mix value is
            # raw HTML — render that one inline; everything else via card.
            if label == "Verdict mix":
                from src.styles import BG_CARD as _BG, BORDER_DEFAULT as _BD
                st.html(
                    f'<div style="background: {_BG}; border: 1px solid {_BD}; '
                    f'border-radius: {RADIUS_MD}; padding: 22px 24px;">'
                    f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; '
                    f'margin-bottom: 10px; letter-spacing: 0.12em; '
                    f'text-transform: uppercase; font-weight: 500;">{label}</div>'
                    f"<div>{value}</div>"
                    f'<div style="font-size: 11px; color: {TEXT_TERTIARY}; '
                    f'margin-top: 10px; letter-spacing: 0.02em;">{hint}</div>'
                    f"</div>"
                )
            else:
                st.html(metric_card(label, value, hint))

    # Deals over time chart
    st.html('<div style="height: 28px;"></div>')
    st.html(section_label("Deals over time"))
    if window:
        # Bucket by day
        per_day: dict[str, int] = defaultdict(int)
        for a in window:
            day = (a.get("created_at") or "")[:10]
            if day:
                per_day[day] += 1
        # Fill in missing days with zero
        start = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS - 1)).date()
        days = [start + timedelta(days=i) for i in range(WINDOW_DAYS)]
        df = pd.DataFrame(
            {
                "date": [d.isoformat() for d in days],
                "deals": [per_day.get(d.isoformat(), 0) for d in days],
            }
        )
        st.line_chart(df, x="date", y="deals", height=220, color="#9AB8A8")
    else:
        st.html(
            f'<div style="background: {BG_CARD}; border: 0.5px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 24px; text-align: center; "
            f'font-size: 13px; color: {TEXT_TERTIARY};">'
            f"No deals analyzed in the past {WINDOW_DAYS} days."
            f"</div>"
        )

    # By-partner table
    st.html('<div style="height: 28px;"></div>')
    st.html(section_label("By partner"))
    try:
        partners = cache.list_partners(firm["id"]) or []
    except Exception:
        partners = []

    by_partner: dict[str | None, list[dict]] = defaultdict(list)
    for a in window:
        deck = a.get("deck") or {}
        by_partner[deck.get("partner_id")].append(a)

    if not by_partner:
        st.html(
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 24px; text-align: center; "
            f'font-size: 13px; color: {TEXT_TERTIARY};">'
            f"No partner activity in this window."
            f"</div>"
        )
    else:
        partner_lookup = {p["id"]: p for p in partners}
        rows = []
        for partner_id, items in sorted(by_partner.items(), key=lambda x: -len(x[1])):
            if partner_id is None:
                name = "Unassigned"
            else:
                p = partner_lookup.get(partner_id, {})
                name = p.get("name") or p.get("email") or "Unknown"
            v_counts: dict[str, int] = defaultdict(int)
            for a in items:
                v_counts[a.get("verdict") or "Unknown"] += 1
            last_at = max((a.get("created_at") or "") for a in items)
            rows.append(
                [
                    esc_html(name),
                    str(len(items)),
                    _verdict_mix_html(v_counts),
                    f'<span style="color: {TEXT_SECONDARY};">{last_at[:10]}</span>',
                ]
            )
        st.html(data_table(["Partner", "Deals", "Verdict mix", "Last activity"], rows))

    # ----- Recent deals (moved here from the Analyze tab) -----
    st.html('<div style="height: 36px;"></div>')
    st.html(section_label("Recent deals"))
    if not all_analyses:
        st.html(
            f'<div style="background: {BG_CARD}; border: 1px solid {BORDER_DEFAULT}; '
            f"border-radius: {RADIUS_MD}; padding: 40px; text-align: center; "
            f'line-height: 1.7;">'
            f'<div style="font-family: {FONT_SERIF}; font-size: 18px; color: {TEXT_PRIMARY}; '
            f'margin-bottom: 6px;">No deals analyzed yet</div>'
            f'<div style="font-size: 14px; color: {TEXT_SECONDARY};">'
            f"Head to the <span style=\"color: {TEXT_PRIMARY};\">Analyze</span> tab to "
            f"triage your first deck."
            f"</div></div>"
        )
        return
    cards_html = "".join(deal_card(a) for a in all_analyses[:50])
    st.html(cards_html)
