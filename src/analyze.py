"""Analyze a new pitch deck against the firm's profile and historical archive.

Usage:
    python -m src.analyze data/incoming_decks/<deck_filename>

The output memo is written to data/analyses/<deck_filename>.memo.md.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "firm.db"
PROFILE_PATH = PROJECT_ROOT / "data" / "firm_profile.md"
ANALYSES_DIR = PROJECT_ROOT / "data" / "analyses"

INSTRUCTIONS = """You are an investment analyst at this firm. A new pitch deck has just landed. Your job: produce a one-page fit memo that a partner will read in two minutes before deciding whether to take the meeting.

You have three resources:
- The firm's strategy profile (distilled from internal thesis docs)
- The firm's full historical corpus (every memo, thesis doc, and pass-reason note we've ever written)
- The new pitch deck itself

Your memo must follow exactly this structure:

## Fit summary
One sentence ("strong fit" / "borderline" / "off-thesis"). Then 2–3 sentences explaining why, citing the specific aspects of the firm's thesis that this deal does or does not match.

## Where it maps to our thesis
Bullet list. For each match, quote the firm's own words from the corpus and tie them to a specific element of this deck.

## Comparable past deals
Identify 2–4 companies from our historical archive (portfolio OR pass-reason archive) that this deck most resembles. For each, name the company, what we did about it, and the specific way the new deal is similar or different.

## Red flags
3–5 risks. Be specific to *this* deck — not generic VC concerns. Where a flag matches a known pattern in our pass-reason archive, name the pattern explicitly. **Important:** if a "red flag" we're tempted to raise corresponds to one of our self-identified bad pass reasons (e.g., "crowded market," "valuation feels high while marketplace is doubling"), call that out — we should suppress that flag, not amplify it.

## Questions for the founder
4–6 sharp questions a partner should ask in the first meeting. Each should test a specific load-bearing assumption in the deck.

## Recommendation
Take the meeting / pass / take the meeting only if X. One sentence."""


def load_corpus(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT filename, content FROM documents ORDER BY filename"
    ).fetchall()
    parts = [f"=== {filename} ===\n\n{content}" for filename, content in rows]
    return "\n\n---\n\n".join(parts)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m src.analyze <path-to-deck>")
        sys.exit(1)

    deck_path = Path(sys.argv[1])
    if not deck_path.exists():
        print(f"Deck not found: {deck_path}")
        sys.exit(1)

    if not DB_PATH.exists():
        print("No firm corpus yet. Run `python -m src.ingest` first.")
        sys.exit(1)

    if not PROFILE_PATH.exists():
        print("No firm profile yet. Run `python -m src.profile` first.")
        sys.exit(1)

    deck_text = deck_path.read_text(encoding="utf-8")
    profile_text = PROFILE_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    corpus = load_corpus(conn)
    conn.close()

    print(f"Analyzing: {deck_path.name}")
    print(f"  corpus:  {len(corpus):,} chars")
    print(f"  profile: {len(profile_text):,} chars")
    print(f"  deck:    {len(deck_text):,} chars")
    print("\n--- memo ---\n")

    client = anthropic.Anthropic()

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[
            {"type": "text", "text": INSTRUCTIONS},
            {
                "type": "text",
                "text": (
                    f"<firm_profile>\n{profile_text}\n</firm_profile>\n\n"
                    f"<firm_corpus>\n{corpus}\n</firm_corpus>"
                ),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"<new_deck filename=\"{deck_path.name}\">\n"
                    f"{deck_text}\n"
                    f"</new_deck>\n\n"
                    "Produce the fit memo now, exactly per the instructions."
                ),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        message = stream.get_final_message()

    print("\n\n---\n")
    usage = message.usage
    print(f"Tokens   input: {usage.input_tokens:,}   "
          f"cache write: {usage.cache_creation_input_tokens:,}   "
          f"cache read: {usage.cache_read_input_tokens:,}   "
          f"output: {usage.output_tokens:,}")

    memo_text = "\n".join(b.text for b in message.content if b.type == "text")
    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYSES_DIR / f"{deck_path.stem}.memo.md"
    out_path.write_text(memo_text)
    print(f"Saved memo → {out_path}")


if __name__ == "__main__":
    main()
