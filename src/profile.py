"""Generate a structured profile of the firm's investment strategy from the
documents stored in data/firm.db.

Usage:
    python -m src.profile

Reads every document from the local SQLite store, sends them to Claude with
prompt caching enabled, and writes the resulting profile to
data/firm_profile.md.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "firm.db"
PROFILE_PATH = PROJECT_ROOT / "data" / "firm_profile.md"

INSTRUCTIONS = """You are an experienced venture-capital partner reviewing a firm's archive of memos, thesis docs, and pass-reason notes.

Your job: distill the firm's actual investment strategy into a clear, structured profile that another partner could read in five minutes and understand exactly how this firm thinks.

The profile must cover, in this order, using markdown H2 headings:

1. **Sectors and themes** — what the firm invests in. Quote specific phrases from the corpus.
2. **Stages and check sizes** — seed, Series A, growth, etc. If the corpus does not specify, write "Not stated in corpus."
3. **Geography** — if specified, otherwise note its absence.
4. **What the firm passes on (patterns)** — concrete patterns from the pass-reason archive. List 4–7 patterns. For each, name the recurring failure mode and cite at least one company from the archive that exemplifies it.
5. **Core principles** — the 3–5 ideas that show up repeatedly across the thesis evolution. Quote the corpus.
6. **Tone and voice** — how the firm describes itself and its work. Two or three sentences.
7. **Notable past investments** — companies named in the corpus, grouped by sector/stage where possible.

Be concrete. Avoid generic VC-speak. When you cite a phrase, put it in quotation marks. If the corpus contradicts itself across documents, note the contradiction and which document is more recent.

Write the profile as if it will be loaded into another tool that uses it to evaluate new pitch decks — so optimize for *usefulness as a reference document*, not for tone."""

USER_PROMPT = "Produce the firm profile now, structured exactly as the instructions specify."


def load_corpus(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT filename, content FROM documents ORDER BY filename"
    ).fetchall()
    parts = [f"=== {filename} ===\n\n{content}" for filename, content in rows]
    return "\n\n---\n\n".join(parts)


def main() -> None:
    if not DB_PATH.exists():
        print("No documents ingested yet. Run `python -m src.ingest` first.")
        return

    conn = sqlite3.connect(DB_PATH)
    corpus = load_corpus(conn)
    conn.close()

    if not corpus:
        print("No documents in database. Add docs to data/firm_docs/ and run ingest.")
        return

    print(f"Loaded {len(corpus):,} chars of firm documents from {DB_PATH.name}")
    print("Asking Claude to distill the firm's strategy. This may take ~30s...\n")
    print("---")

    client = anthropic.Anthropic()

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[
            {"type": "text", "text": INSTRUCTIONS},
            {
                "type": "text",
                "text": f"<firm_corpus>\n{corpus}\n</firm_corpus>",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": USER_PROMPT}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        message = stream.get_final_message()

    print("\n---\n")
    usage = message.usage
    print(f"Tokens   input: {usage.input_tokens:,}   "
          f"cache write: {usage.cache_creation_input_tokens:,}   "
          f"cache read: {usage.cache_read_input_tokens:,}   "
          f"output: {usage.output_tokens:,}")

    profile_text = "\n".join(b.text for b in message.content if b.type == "text")
    PROFILE_PATH.write_text(profile_text)
    print(f"Saved firm profile → {PROFILE_PATH}")


if __name__ == "__main__":
    main()
