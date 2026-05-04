"""Quick utility to inspect what's in the local document database.

Usage:
    python -m src.inspect_db
"""

from __future__ import annotations

import sqlite3

from src.config import DB_PATH


def main() -> None:
    if not DB_PATH.exists():
        print(f"No database yet at {DB_PATH}. Run `python -m src.ingest` first.")
        return

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, filename, page_count, length(content), ingested_at "
        "FROM documents ORDER BY id"
    ).fetchall()

    if not rows:
        print("Database exists but contains no documents.")
        return

    print(f"{len(rows)} document(s) in {DB_PATH}:")
    print()
    print(f"{'ID':>3}  {'Filename':<50}  {'Pages':>5}  {'Chars':>8}  Ingested")
    print("-" * 100)
    for row in rows:
        doc_id, filename, pages, chars, ingested_at = row
        fname = filename if len(filename) <= 50 else filename[:47] + "..."
        print(f"{doc_id:>3}  {fname:<50}  {pages:>5}  {chars:>8,}  {ingested_at}")

    conn.close()


if __name__ == "__main__":
    main()
