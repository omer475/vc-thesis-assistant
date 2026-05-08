"""Generate the firm's strategy profile from its document corpus.

CLI:
    python -m src.profile

Reads every document from Supabase, sends them to Claude with prompt caching
enabled, writes the resulting profile to `firms.profile_md` (DB), and also
writes a convenience copy to `data/firm_profile.md`.
"""

from __future__ import annotations

from typing import Any, Callable

import anthropic
from dotenv import load_dotenv

from src import db
from src.config import PROFILE_PATH, ensure_dirs

load_dotenv()
ensure_dirs()

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


def generate_profile(
    firm_id: str,
    *,
    stream_callback: Callable[[str], None] | None = None,
    write_disk: bool = True,
    client: anthropic.Anthropic | None = None,
) -> dict[str, Any]:
    """Run profile generation. Updates `firms.profile_md` and (optionally) disk.

    Returns: {profile_md, usage}
    """
    corpus = db.assemble_corpus(firm_id)
    if not corpus.strip():
        raise RuntimeError(
            "Firm has no documents. Ingest at least one before generating a profile."
        )

    client = client or anthropic.Anthropic()
    chunks: list[str] = []

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
            chunks.append(text)
            if stream_callback is not None:
                stream_callback(text)
        message = stream.get_final_message()

    profile_text = "".join(chunks)

    db.update_firm_profile(firm_id, profile_text)
    if write_disk:
        PROFILE_PATH.write_text(profile_text)

    return {
        "profile_md": profile_text,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "cache_read_input_tokens": message.usage.cache_read_input_tokens,
            "cache_creation_input_tokens": message.usage.cache_creation_input_tokens,
        },
    }


def main() -> None:
    firm = db.get_or_create_default_firm()
    print(f"Firm: {firm['name']} ({firm['slug']})")

    n_docs = db.count_documents(firm["id"])
    if n_docs == 0:
        print("No documents in corpus. Run `python -m src.ingest` first.")
        return
    total_chars = db.total_corpus_chars(firm["id"])
    print(f"Corpus: {n_docs} documents, {total_chars:,} chars")
    print("Asking Claude to distill the firm's strategy. This may take ~30s...\n")
    print("---")

    def _print_chunk(text: str) -> None:
        print(text, end="", flush=True)

    result = generate_profile(firm["id"], stream_callback=_print_chunk)

    print("\n---\n")
    usage = result["usage"]
    print(
        f"Tokens   input: {usage['input_tokens']:,}   "
        f"cache write: {usage['cache_creation_input_tokens']:,}   "
        f"cache read: {usage['cache_read_input_tokens']:,}   "
        f"output: {usage['output_tokens']:,}"
    )
    print(f"Saved firm profile to firms.profile_md and {PROFILE_PATH}")


if __name__ == "__main__":
    main()
