"""Streamlit-aware caching layer over src.db.

Streamlit reruns the entire script on every widget interaction (button click,
text-input change, etc). Without caching, every rerun hits Supabase 5-10
times: the sidebar status block, the deal list, the document table, the
firm profile, the partner list, the pass reasons. Each round trip is
~100-300ms and they add up to a sluggish UI.

These wrappers collapse repeat reads within a short window into a single
DB call. After any mutation (upload, delete, run analysis, sync CRM, etc.)
the caller invokes `invalidate_all()` to drop the cache so the next read
sees fresh data.

Default TTL: 30 seconds. Long enough to absorb a burst of clicks without
hitting Supabase; short enough that any drift from external mutations
(e.g., another partner adding a doc) heals quickly.
"""

from __future__ import annotations

import streamlit as st

from src import db

_TTL = 30  # seconds


@st.cache_data(ttl=_TTL, show_spinner=False)
def list_documents(firm_id: str) -> list[dict]:
    return db.list_documents(firm_id)


@st.cache_data(ttl=_TTL, show_spinner=False)
def list_analyses_for_firm(firm_id: str, limit: int = 100) -> list[dict]:
    return db.list_analyses_for_firm(firm_id, limit=limit)


@st.cache_data(ttl=_TTL, show_spinner=False)
def list_partners(firm_id: str) -> list[dict]:
    return db.list_partners(firm_id)


@st.cache_data(ttl=_TTL, show_spinner=False)
def list_pass_reasons(firm_id: str) -> list[dict]:
    return db.list_pass_reasons(firm_id)


@st.cache_data(ttl=_TTL, show_spinner=False)
def get_firm(firm_id: str) -> dict | None:
    return db.get_firm(firm_id)


@st.cache_data(ttl=_TTL, show_spinner=False)
def get_firm_profile(firm_id: str) -> str | None:
    return db.get_firm_profile(firm_id)


# ----- derived metrics (computed in Python from the cached list) -------------


def count_documents(firm_id: str) -> int:
    return len(list_documents(firm_id))


def total_corpus_chars(firm_id: str) -> int:
    return sum(len(d.get("content") or "") for d in list_documents(firm_id))


def count_deals_this_week(firm_id: str) -> int:
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    return sum(
        1
        for a in list_analyses_for_firm(firm_id, limit=200)
        if (a.get("created_at") or "") >= cutoff
    )


# ----- invalidation ----------------------------------------------------------


def invalidate_all() -> None:
    """Clear every cache. Call this after any write to the DB so the next
    read pulls fresh data."""
    list_documents.clear()
    list_analyses_for_firm.clear()
    list_partners.clear()
    list_pass_reasons.clear()
    get_firm.clear()
    get_firm_profile.clear()
