"""Affinity CRM connector.

Pulls pass-reason notes for opportunities (deals) marked as "Passed" in a
firm's Affinity workspace and upserts them into the local `pass_reasons`
table so the analyzer can ground "suppress bad-pass red flags" reasoning
in the firm's actual archive.

Authentication: Affinity v1 REST API uses HTTP Basic auth with an empty
username and the API key as the password. Reference:
https://api-docs.affinity.co/

This module is structured so it can be tested against a real workspace
when one is available; until then,
`scripts/seed_synthetic_pass_reasons.py` gives the analyzer something
to chew on.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from src import db

AFFINITY_BASE_URL = "https://api.affinity.co"


# ----- Errors ----------------------------------------------------------------


class AffinityError(Exception):
    """Affinity API call failed."""


class AffinityNotConfigured(AffinityError):
    """The firm has no Affinity API key + Passed status ID configured."""


# ----- Client ----------------------------------------------------------------


class AffinityClient:
    """Thin wrapper around the Affinity v1 REST API.

    Designed to be small enough that swapping to Attio is one file: subclass
    or replace the methods that hit `/lists`, `/list-entries`, `/notes`.
    """

    def __init__(self, api_key: str, *, base_url: str = AFFINITY_BASE_URL):
        if not api_key:
            raise AffinityNotConfigured("Affinity API key is empty.")
        self._client = httpx.Client(
            base_url=base_url,
            auth=("", api_key),
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AffinityClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- HTTP --

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = self._client.get(path, params=params)
        if resp.status_code == 401:
            raise AffinityError("Affinity rejected the API key (401 unauthorized).")
        if resp.status_code == 429:
            raise AffinityError("Affinity rate limit hit (429). Wait and retry.")
        if resp.status_code >= 400:
            raise AffinityError(
                f"Affinity GET {path} failed: {resp.status_code} {resp.text[:200]}"
            )
        return resp.json()

    # -- Endpoints we use --

    def list_lists(self) -> list[dict]:
        """Every list the API key can see."""
        return self._get("/lists") or []

    def list_entries(self, list_id: int | str, page_size: int = 500) -> list[dict]:
        """All entries (deals) in a given list. Paginates if needed."""
        out: list[dict] = []
        next_token: str | None = None
        while True:
            params: dict[str, Any] = {"list_id": list_id, "page_size": page_size}
            if next_token:
                params["page_token"] = next_token
            data = self._get(f"/lists/{list_id}/list-entries", params=params)
            if isinstance(data, list):
                out.extend(data)
                break  # v1 list-entries returns a flat list
            entries = data.get("list_entries") or []
            out.extend(entries)
            next_token = data.get("next_page_token")
            if not next_token:
                break
        return out

    def get_field_values(self, opportunity_id: int) -> list[dict]:
        return self._get("/field-values", params={"opportunity_id": opportunity_id}) or []

    def list_notes(self, opportunity_id: int) -> list[dict]:
        return self._get("/notes", params={"opportunity_id": opportunity_id}) or []

    def get_opportunity(self, opportunity_id: int) -> dict:
        return self._get(f"/opportunities/{opportunity_id}")


# ----- Sync orchestration ----------------------------------------------------


def _passed_entries(
    client: AffinityClient, list_id: int | str, passed_status_id: str
) -> list[dict]:
    """Return list entries whose status field-value matches the Passed status."""
    entries = client.list_entries(list_id)
    passed = []
    for entry in entries:
        opp_id = entry.get("entity_id") or entry.get("opportunity_id") or entry.get("id")
        if not opp_id:
            continue
        try:
            field_values = client.get_field_values(opp_id)
        except AffinityError:
            continue
        # Affinity status fields surface as a value with a `dropdown_option_id`
        # or `value` field equal to the configured passed_status_id.
        for fv in field_values:
            value = fv.get("value")
            if isinstance(value, dict):
                # Dropdown values are dicts with `id` (the option id)
                if str(value.get("id")) == str(passed_status_id):
                    passed.append({**entry, "_field_values": field_values})
                    break
            elif str(value) == str(passed_status_id):
                passed.append({**entry, "_field_values": field_values})
                break
    return passed


def _company_name_from_entry(client: AffinityClient, entry: dict) -> str | None:
    """Best-effort name extraction from a list entry / opportunity."""
    # Different Affinity workspaces return slightly different shapes.
    name = entry.get("entity", {}).get("name") if isinstance(entry.get("entity"), dict) else None
    if name:
        return name
    name = entry.get("name") or entry.get("opportunity_name")
    if name:
        return name
    opp_id = entry.get("entity_id") or entry.get("opportunity_id")
    if opp_id:
        try:
            opp = client.get_opportunity(opp_id)
            return opp.get("name") if isinstance(opp, dict) else None
        except AffinityError:
            return None
    return None


def _flatten_notes(notes: list[dict]) -> str:
    """Concatenate notes into a single reason_text block."""
    if not notes:
        return ""
    parts: list[str] = []
    for n in sorted(notes, key=lambda x: x.get("created_at") or ""):
        body = (n.get("content") or "").strip()
        if not body:
            continue
        when = (n.get("created_at") or "")[:10]
        prefix = f"[{when}] " if when else ""
        parts.append(f"{prefix}{body}")
    return "\n\n".join(parts)


def sync_pass_reasons(firm_id: str) -> dict[str, int]:
    """Sync Affinity passed-deal notes into the firm's pass_reasons table.

    Reads the firm's stored API key + passed_status_id, walks every list the
    key can see, finds entries whose status matches passed_status_id, fetches
    each entry's notes, and upserts (firm_id, company_name) -> reason_text.

    Returns counts: {fetched, inserted, updated, skipped}.
    """
    firm = db.get_firm(firm_id)
    if not firm:
        raise AffinityError(f"Firm {firm_id} not found.")
    api_key = firm.get("affinity_api_key")
    passed_status_id = firm.get("affinity_passed_status_id")
    if not api_key or not passed_status_id:
        raise AffinityNotConfigured(
            "Firm has no Affinity API key + Passed status ID configured."
        )

    counts = {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

    with AffinityClient(api_key) as client:
        lists = client.list_lists()
        for lst in lists:
            list_id = lst.get("id")
            if not list_id:
                continue
            try:
                passed = _passed_entries(client, list_id, passed_status_id)
            except AffinityError:
                continue

            for entry in passed:
                counts["fetched"] += 1
                opp_id = entry.get("entity_id") or entry.get("opportunity_id") or entry.get("id")
                if not opp_id:
                    counts["skipped"] += 1
                    continue
                try:
                    notes = client.list_notes(opp_id)
                except AffinityError:
                    counts["skipped"] += 1
                    continue
                reason_text = _flatten_notes(notes)
                if not reason_text:
                    counts["skipped"] += 1
                    continue
                company = _company_name_from_entry(client, entry)
                action = db.upsert_pass_reason(
                    firm_id,
                    source="affinity",
                    reason_text=reason_text,
                    company_name=company,
                )
                if action.get("action") == "inserted":
                    counts["inserted"] += 1
                elif action.get("action") == "updated":
                    counts["updated"] += 1
                else:
                    counts["skipped"] += 1

    return counts
