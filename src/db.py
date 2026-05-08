"""Single source of truth for database access.

Every module that needs to read or write project data goes through this
module — nothing else should `import supabase` directly. Authentication uses
the service-role key from `SUPABASE_SERVICE_ROLE_KEY` (full access; row-level
security is bypassed). For Phase 1 we are single-tenant: every operation
implicitly scopes to the default firm via `get_or_create_default_firm()`.

Schema lives in supabase/migrations/0001_init.sql. If the schema changes,
update both there and here.
"""

from __future__ import annotations

import functools
import os
from functools import lru_cache
from typing import Any

import httpx
from supabase import Client, create_client

DEFAULT_FIRM_SLUG = "forge"
DEFAULT_FIRM_NAME = "Forge Ventures"


# ----- Client -----------------------------------------------------------------


@lru_cache(maxsize=1)
def client() -> Client:
    """Return a process-cached Supabase client.

    Reads `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from the environment
    on first call and caches the result. Streamlit reruns reuse the cached
    client. Stale-connection recovery is handled by `@_resilient` on the
    public functions below.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the "
            "environment (typically via .env locally, or Streamlit Cloud "
            "secrets in production)."
        )
    return create_client(url, key)


# Errors that indicate a transient network or stale-connection problem.
# In long-running Streamlit sessions the cached httpx pool's keep-alive
# connections can be dropped server-side; the next request fails with
# "Server disconnected" until the pool is rebuilt.
_TRANSIENT_HTTPX_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    httpx.WriteError,
)


def _resilient(fn):
    """Decorator: on transient httpx errors, drop the cached client and retry once.

    Apply to every db function that directly hits Supabase. Internal helper
    functions that wrap other db functions don't need this — the inner call
    will retry on its own.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except _TRANSIENT_HTTPX_ERRORS:
            client.cache_clear()
            return fn(*args, **kwargs)

    return wrapper


# ----- Firms ------------------------------------------------------------------


@_resilient
def get_firm_by_slug(slug: str) -> dict | None:
    res = client().table("firms").select("*").eq("slug", slug).limit(1).execute()
    return res.data[0] if res.data else None


@_resilient
def create_firm(slug: str, name: str, profile_md: str | None = None) -> dict:
    payload: dict[str, Any] = {"slug": slug, "name": name}
    if profile_md is not None:
        payload["profile_md"] = profile_md
    res = client().table("firms").insert(payload).execute()
    return res.data[0]


@_resilient
def get_firm(firm_id: str) -> dict | None:
    res = client().table("firms").select("*").eq("id", firm_id).limit(1).execute()
    return res.data[0] if res.data else None


def get_or_create_default_firm() -> dict:
    """Return the Forge Ventures row, creating it on first call."""
    firm = get_firm_by_slug(DEFAULT_FIRM_SLUG)
    if firm is None:
        firm = create_firm(DEFAULT_FIRM_SLUG, DEFAULT_FIRM_NAME)
    return firm


@_resilient
def update_firm_profile(firm_id: str, profile_md: str) -> None:
    client().table("firms").update({"profile_md": profile_md}).eq(
        "id", firm_id
    ).execute()


@_resilient
def get_firm_profile(firm_id: str) -> str | None:
    res = client().table("firms").select("profile_md").eq("id", firm_id).limit(1).execute()
    if not res.data:
        return None
    return res.data[0].get("profile_md")


# ----- Documents (firm corpus) -----------------------------------------------


@_resilient
def list_documents(firm_id: str) -> list[dict]:
    res = (
        client()
        .table("documents")
        .select("*")
        .eq("firm_id", firm_id)
        .order("filename")
        .execute()
    )
    return res.data or []


@_resilient
def count_documents(firm_id: str) -> int:
    res = (
        client()
        .table("documents")
        .select("id", count="exact")
        .eq("firm_id", firm_id)
        .execute()
    )
    return res.count or 0


def total_corpus_chars(firm_id: str) -> int:
    """Sum of LENGTH(content) across the firm's documents. One round trip."""
    docs = list_documents(firm_id)
    return sum(len(d.get("content") or "") for d in docs)


@_resilient
def insert_document(
    firm_id: str, filename: str, content: str, page_count: int
) -> dict | None:
    """Insert a document. Returns the row, or None if the (firm_id, filename)
    pair already exists (UNIQUE constraint — idempotent ingest)."""
    try:
        res = (
            client()
            .table("documents")
            .insert(
                {
                    "firm_id": firm_id,
                    "filename": filename,
                    "content": content,
                    "page_count": page_count,
                }
            )
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        # Postgres duplicate-key errors surface as exceptions in supabase-py;
        # treat as "already ingested" rather than re-raise.
        if "duplicate key" in str(e).lower() or "23505" in str(e):
            return None
        raise


def assemble_corpus(firm_id: str) -> str:
    """Concatenate every firm document into a single string for the system prompt.
    Format matches what `analyze_deck` and `generate_profile` expect.
    """
    docs = list_documents(firm_id)
    parts = [f"=== {d['filename']} ===\n\n{d['content']}" for d in docs]
    return "\n\n---\n\n".join(parts)


# ----- Decks ------------------------------------------------------------------


@_resilient
def insert_deck(
    firm_id: str,
    *,
    source: str,
    content: str,
    original_filename: str | None = None,
    subject: str | None = None,
    partner_id: str | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "firm_id": firm_id,
        "source": source,
        "content": content,
    }
    if original_filename is not None:
        payload["original_filename"] = original_filename
    if subject is not None:
        payload["subject"] = subject
    if partner_id is not None:
        payload["partner_id"] = partner_id
    res = client().table("decks").insert(payload).execute()
    return res.data[0]


# ----- Analyses ---------------------------------------------------------------


@_resilient
def insert_analysis(
    deck_id: str,
    *,
    verdict: str,
    bullets: list[dict],
    questions: list[str] | None,
    full_memo_md: str,
    usage: dict | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "deck_id": deck_id,
        "verdict": verdict,
        "bullets": bullets,
        "questions": questions,
        "full_memo_md": full_memo_md,
    }
    if usage:
        payload["tokens_in"] = usage.get("input_tokens")
        payload["tokens_out"] = usage.get("output_tokens")
        payload["cache_read_tokens"] = usage.get("cache_read_input_tokens")
        payload["cache_write_tokens"] = usage.get("cache_creation_input_tokens")
        payload["latency_ms"] = usage.get("latency_ms")
    res = client().table("analyses").insert(payload).execute()
    return res.data[0]


@_resilient
def get_analysis(analysis_id: str) -> dict | None:
    """Fetch an analysis row joined with its parent deck (for the public view)."""
    res = (
        client()
        .table("analyses")
        .select("*, deck:decks(*)")
        .eq("id", analysis_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


@_resilient
def list_analyses_for_firm(firm_id: str, limit: int = 100) -> list[dict]:
    """Recent analyses for a firm, joined with their decks."""
    res = (
        client()
        .table("analyses")
        .select("*, deck:decks!inner(*)")
        .eq("deck.firm_id", firm_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def count_deals_this_week(firm_id: str) -> int:
    """Count analyses for this firm created in the last 7 days.

    Implemented client-side (one query + filter) rather than via a count
    aggregate because PostgREST's filter-through-foreign-table syntax is
    fiddly and the volumes are low. Revisit if this becomes a bottleneck.
    """
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    analyses = list_analyses_for_firm(firm_id, limit=500)
    return sum(1 for a in analyses if (a.get("created_at") or "") >= cutoff)


# ----- Pass reasons -----------------------------------------------------------


@_resilient
def list_pass_reasons(firm_id: str) -> list[dict]:
    res = (
        client()
        .table("pass_reasons")
        .select("*")
        .eq("firm_id", firm_id)
        .order("ingested_at", desc=True)
        .execute()
    )
    return res.data or []


@_resilient
def insert_pass_reason(
    firm_id: str,
    source: str,
    reason_text: str,
    company_name: str | None = None,
    deal_date: str | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "firm_id": firm_id,
        "source": source,
        "reason_text": reason_text,
    }
    if company_name is not None:
        payload["company_name"] = company_name
    if deal_date is not None:
        payload["deal_date"] = deal_date
    res = client().table("pass_reasons").insert(payload).execute()
    return res.data[0]
