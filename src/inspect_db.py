"""Inspect the firm's Supabase data — documents, profile state, recent analyses.

Usage:
    python -m src.inspect_db
"""

from __future__ import annotations

from dotenv import load_dotenv

from src import db

load_dotenv()


def main() -> None:
    firm = db.get_or_create_default_firm()
    print(f"Firm: {firm['name']} (slug={firm['slug']}, id={firm['id']})")
    print(f"Profile: {'generated' if firm.get('profile_md') else 'not generated'}")
    print()

    docs = db.list_documents(firm["id"])
    if not docs:
        print("No documents in corpus. Run `python -m src.ingest` first.")
        return

    print(f"{len(docs)} document(s):")
    print()
    print(f"{'Filename':<55}  {'Pages':>5}  {'Chars':>8}  Ingested")
    print("-" * 100)
    for d in docs:
        fname = d["filename"]
        if len(fname) > 55:
            fname = fname[:52] + "..."
        chars = len(d.get("content") or "")
        print(
            f"{fname:<55}  "
            f"{d['page_count']:>5}  "
            f"{chars:>8,}  "
            f"{d['ingested_at'][:19].replace('T', ' ')}"
        )

    analyses = db.list_analyses_for_firm(firm["id"], limit=20)
    if analyses:
        print()
        print(f"{len(analyses)} most-recent analyses:")
        for a in analyses:
            deck = a.get("deck") or {}
            label = deck.get("original_filename") or deck.get("subject") or "(no name)"
            print(
                f"  [{a['verdict']:<13}]  {label:<40}  "
                f"{a['created_at'][:19].replace('T', ' ')}"
            )


if __name__ == "__main__":
    main()
