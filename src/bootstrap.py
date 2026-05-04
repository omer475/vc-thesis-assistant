"""First-boot bootstrap: seed example data into DATA_DIR and auto-ingest.

In production (DATA_DIR != repo/data/), the persistent disk starts empty on
first deploy. This module copies the committed example firm docs and decks
into DATA_DIR if it's empty, and runs ingestion so the demo immediately
shows something.

Idempotent — safe to call on every startup.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone

from src.config import (
    DATA_DIR,
    DB_PATH,
    DOCS_DIR,
    EXAMPLE_DATA_DIR,
    INCOMING_DECKS_DIR,
    ensure_dirs,
    is_running_in_production,
)
from src.ingest import SUPPORTED_EXTENSIONS, extract, init_db


def _copy_files_if_target_empty(source_dir, target_dir) -> int:
    if not source_dir.exists():
        return 0
    target_dir.mkdir(parents=True, exist_ok=True)
    if any(p for p in target_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS):
        return 0
    copied = 0
    for f in source_dir.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            shutil.copy(f, target_dir / f.name)
            copied += 1
    return copied


def _ingest_pending(docs_dir) -> int:
    docs = sorted(p for p in docs_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not docs:
        return 0
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    ingested = 0
    for path in docs:
        try:
            text, page_count = extract(path)
        except Exception:
            continue
        if not text:
            continue
        try:
            conn.execute(
                "INSERT INTO documents (filename, page_count, content, ingested_at) "
                "VALUES (?, ?, ?, ?)",
                (path.name, page_count, text, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            ingested += 1
        except sqlite3.IntegrityError:
            pass
    conn.close()
    return ingested


def run() -> dict:
    """Run the boot bootstrap. Returns counts for logging."""
    ensure_dirs()

    if not is_running_in_production():
        return {"skipped": "local dev — DATA_DIR is the repo data/ dir"}

    docs_copied = _copy_files_if_target_empty(
        EXAMPLE_DATA_DIR / "firm_docs", DOCS_DIR
    )
    decks_copied = _copy_files_if_target_empty(
        EXAMPLE_DATA_DIR / "incoming_decks", INCOMING_DECKS_DIR
    )

    ingested = _ingest_pending(DOCS_DIR)

    return {
        "docs_copied": docs_copied,
        "decks_copied": decks_copied,
        "documents_ingested": ingested,
    }


if __name__ == "__main__":
    print(run())
