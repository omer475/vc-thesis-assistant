"""Ingest PDF documents from data/firm_docs/ into a local SQLite database.

Usage:
    python -m src.ingest

Drop the firm's memos, notes, and thesis docs (as PDFs) into data/firm_docs/,
then run this script. Each document is stored once; re-running is safe.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "data" / "firm_docs"
DB_PATH = PROJECT_ROOT / "data" / "firm.db"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            filename     TEXT NOT NULL UNIQUE,
            page_count   INTEGER NOT NULL,
            content      TEXT NOT NULL,
            ingested_at  TEXT NOT NULL
        )
        """
    )
    conn.commit()


def extract_pdf_text(pdf_path: Path) -> tuple[str, int]:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip(), len(reader.pages)


def ingest() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(DOCS_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No PDFs found in {DOCS_DIR}.")
        print("Drop the firm's memos and notes into that folder, then run again.")
        return

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    ingested = 0
    skipped = 0
    no_text = 0

    for pdf_path in pdfs:
        try:
            text, page_count = extract_pdf_text(pdf_path)
        except Exception as e:
            print(f"[error]  {pdf_path.name}: failed to read ({e}) — skipping")
            skipped += 1
            continue

        if not text:
            print(f"[no-text] {pdf_path.name}: no extractable text (image-only PDF). "
                  "Will need vision-based extraction in a later phase.")
            no_text += 1
            continue

        try:
            conn.execute(
                "INSERT INTO documents (filename, page_count, content, ingested_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    pdf_path.name,
                    page_count,
                    text,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            print(f"[ok]     {pdf_path.name} ({page_count} pages, {len(text):,} chars)")
            ingested += 1
        except sqlite3.IntegrityError:
            print(f"[exists] {pdf_path.name}: already ingested, skipping")
            skipped += 1

    conn.close()

    print()
    print(f"Done. Ingested: {ingested}  |  Already in DB: {skipped}  |  No text: {no_text}")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    ingest()
