"""Ingest documents from data/firm_docs/ into the firm's Supabase corpus.

Supported file types: .pdf, .md, .txt

CLI:
    python -m src.ingest

Drop the firm's memos, notes, and thesis docs into data/firm_docs/, then
run this script. Each document is stored once per firm; re-running is
safe (`unique (firm_id, filename)` makes it idempotent).
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader

from src import db
from src.config import DOCS_DIR, ensure_dirs

load_dotenv()
ensure_dirs()

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


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


def ingest_one(firm_id: str, filename: str, text: str, page_count: int) -> str:
    """Insert one document. Returns 'inserted' / 'exists' / 'no-text' / 'error:<msg>'."""
    if not text:
        return "no-text"
    row = db.insert_document(firm_id, filename, text, page_count)
    return "inserted" if row else "exists"


def ingest_directory(firm_id: str, dir_path: Path) -> dict[str, int]:
    """Walk dir_path and ingest every supported file. Returns counts by status."""
    counts = {"inserted": 0, "exists": 0, "no-text": 0, "error": 0}
    if not dir_path.exists():
        return counts

    docs = sorted(p for p in dir_path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    for path in docs:
        try:
            text, page_count = extract(path)
        except Exception as e:
            print(f"[error]  {path.name}: failed to read ({e}) — skipping")
            counts["error"] += 1
            continue

        status = ingest_one(firm_id, path.name, text, page_count)
        if status == "inserted":
            print(f"[ok]     {path.name} ({page_count} pages, {len(text):,} chars)")
            counts["inserted"] += 1
        elif status == "exists":
            print(f"[exists] {path.name}: already ingested")
            counts["exists"] += 1
        elif status == "no-text":
            print(f"[no-text] {path.name}: no extractable text (image-only PDF?)")
            counts["no-text"] += 1
    return counts


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    docs = sorted(p for p in DOCS_DIR.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)

    if not docs:
        print(f"No documents found in {DOCS_DIR}.")
        print(f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        print("Drop the firm's memos and notes into that folder, then run again.")
        return

    firm = db.get_or_create_default_firm()
    print(f"Ingesting into firm: {firm['name']} (slug={firm['slug']}, id={firm['id']})")

    counts = ingest_directory(firm["id"], DOCS_DIR)

    print()
    print(
        f"Done. Inserted: {counts['inserted']}  |  Already in DB: {counts['exists']}  "
        f"|  No text: {counts['no-text']}  |  Errors: {counts['error']}"
    )


if __name__ == "__main__":
    main()
