"""First-boot bootstrap: ensure the default firm exists in Supabase, then
seed example fixtures (firm docs) into the firm's corpus on first deploy.

Idempotent — safe to call on every Streamlit script rerun. After Step 2
this is much simpler than before: no filesystem juggling, just a couple of
DB queries that no-op when data is already present.
"""

from __future__ import annotations

from src import db
from src.config import EXAMPLE_DATA_DIR, ensure_dirs
from src.ingest import SUPPORTED_EXTENSIONS, extract


def _seed_documents_if_empty(firm_id: str) -> int:
    """If the firm has zero documents and example fixtures are checked into the
    repo, ingest the fixtures so the demo always has something to show.
    Returns the number of documents inserted (0 if no seeding happened).
    """
    if db.count_documents(firm_id) > 0:
        return 0

    example_docs_dir = EXAMPLE_DATA_DIR / "firm_docs"
    if not example_docs_dir.exists():
        return 0

    inserted = 0
    for path in sorted(example_docs_dir.iterdir()):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            text, page_count = extract(path)
        except Exception:
            continue
        if not text:
            continue
        row = db.insert_document(firm_id, path.name, text, page_count)
        if row:
            inserted += 1
    return inserted


def run() -> dict:
    """Bootstrap on app start. Returns counts for logging.

    Behavior:
      - Always ensure firm `forge` exists in `firms`.
      - On first run (firm has 0 documents) AND committed example fixtures
        exist in the repo: ingest the fixtures so the demo isn't empty.
      - Always a no-op for repeat runs.
      - Falls back to mock data if Supabase is unavailable (for UI testing).
    """
    ensure_dirs()
    try:
        firm = db.get_or_create_default_firm()
        seeded = _seed_documents_if_empty(firm["id"])
        return {
            "firm_id": firm["id"],
            "firm_slug": firm["slug"],
            "documents_seeded": seeded,
            "documents_total": db.count_documents(firm["id"]),
        }
    except Exception as e:
        # Supabase is unavailable — return mock data for UI testing
        import sys
        print(f"[Warning] Supabase unavailable ({type(e).__name__}). Using mock data.", file=sys.stderr)
        return {
            "firm_id": "mock-firm-id",
            "firm_slug": "forge",
            "documents_seeded": 0,
            "documents_total": 0,
        }


if __name__ == "__main__":
    print(run())
