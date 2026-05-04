"""Ingest documents from data/firm_docs/ into a local SQLite database.

Supported file types: .pdf, .md, .txt

Usage:
    python -m src.ingest

Drop the firm's memos, notes, and thesis docs into data/firm_docs/, then run
this script. Each document is stored once; re-running is safe.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader

from src.config import DATA_DIR, DB_PATH, DOCS_DIR, ensure_dirs

load_dotenv()
ensure_dirs()

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


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


def extract_text_file(path: Path) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    page_count = max(1, text.count("\n\n") // 5 + 1)
    return text, page_count


def extract(path: Path) -> tuple[str, int]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix in {".md", ".txt"}:
        return extract_text_file(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def ingest() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    docs = sorted(p for p in DOCS_DIR.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)

    if not docs:
        print(f"No documents found in {DOCS_DIR}.")
        print(f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        print("Drop the firm's memos and notes into that folder, then run again.")
        return

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    ingested = 0
    skipped = 0
    no_text = 0

    for path in docs:
        try:
            text, page_count = extract(path)
        except Exception as e:
            print(f"[error]  {path.name}: failed to read ({e}) — skipping")
            skipped += 1
            continue

        if not text:
            print(f"[no-text] {path.name}: no extractable text "
                  "(image-only PDF — needs vision-based extraction in a later phase).")
            no_text += 1
            continue

        try:
            conn.execute(
                "INSERT INTO documents (filename, page_count, content, ingested_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    path.name,
                    page_count,
                    text,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            print(f"[ok]     {path.name} ({page_count} pages, {len(text):,} chars)")
            ingested += 1
        except sqlite3.IntegrityError:
            print(f"[exists] {path.name}: already ingested, skipping")
            skipped += 1

    conn.close()

    print()
    print(f"Done. Ingested: {ingested}  |  Already in DB: {skipped}  |  No text: {no_text}")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    ingest()
