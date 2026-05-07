"""Analyze a new pitch deck against the firm's profile and historical archive.

Produces two artifacts in one Claude call:

  1) A compact TRIAGE BLOCK — verdict + 3 reasoning bullets (with inline
     citations to the firm's own docs) + optional 3 follow-up questions.
     This is the email-reply payload.
  2) A FULL MEMO — the deeper analysis, accessed via link.

CLI:
    python -m src.analyze data/incoming_decks/<deck_filename>
    → writes data/analyses/<stem>.memo.md  (full memo)
            data/analyses/<stem>.triage.md (triage block only)

Library:
    from src.analyze import analyze_deck
    result = analyze_deck(deck_text, deck_filename, profile_text, corpus_text)
    # result is a dict: {verdict, bullets, questions, full_memo_md,
    #                    triage_md, raw_response, usage}
"""

from __future__ import annotations

import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable

import anthropic
from dotenv import load_dotenv

from src.config import ANALYSES_DIR, DB_PATH, PROFILE_PATH, ensure_dirs

load_dotenv()
ensure_dirs()


# ----- Prompt -------------------------------------------------------------

INSTRUCTIONS = """You are an investment analyst at this firm. A new pitch deck has just landed. Your job: produce TWO outputs, in one response, in this order:

# OUTPUT 1 — TRIAGE BLOCK (the email reply)

This is what the partner reads in 30 seconds before deciding whether to engage. It MUST follow this exact format:

```
VERDICT: <Take meeting | Pass | Ask first>

WHY:
• <Bullet 1 — one concrete claim, max ~25 words, ending with a verbatim short quote (max 12 words) from a firm doc and that doc's filename in parens>
• <Bullet 2 — same shape>
• <Bullet 3 — same shape>
```

If — and ONLY if — VERDICT is "Ask first", append this section right after WHY:

```
ASK FIRST:
1. <Question — testing one specific load-bearing assumption in the deck>
2. <Question>
3. <Question>
```

Citation format inside each WHY bullet, exactly like this:
  • Strong vertical-network fit — matches your 2018 thesis on "trusted brands that broaden access" (03_firm_thesis_v3_2018.md).
  • Mid-market wedge replays a pattern you've already executed — Casetext was "the law" vertical (02_firm_thesis_v2_2015.md).

Hard rules for the triage block:
- VERDICT is opinionated. Pick exactly ONE of the three. No "it depends," no hedging.

- How to choose between the three verdicts. The deciding question is:

  > "Imagine the founder never replies and you must decide right now from the deck alone. What's your call?"

  • **Take meeting** — "I'd put it on this week's calendar even with zero further info." Thesis fit is clear and the deck's load-bearing claims look strong enough that, while questions remain, the questions shape the meeting agenda, not the yes/no decision. The deal clears the bar to engage; diligence depth is decided in the meeting itself.

  • **Ask first** — "I can't decide yet — I need answers to a small number of specific questions before I'll commit a partner's hour." There are 2–3 load-bearing claims whose answers would *individually flip* your verdict between Take meeting and Pass. Examples: self-reported retention with no cohort breakdown (good cohort curves → take it; bad ones → pass); a moat claim that depends on whether data is pooled or per-tenant; pre-revenue with vague monetization in a category whose monetization shape decides the deal.

  • **Pass** — "I'd pass even with perfect answers." Off-thesis (a category the firm has explicitly stepped back from, or a structural mismatch with stage/sector), AND the disqualifier is NOT one of the firm's known-bad pass reasons.

- Verifiable vs. self-reported claims: this is the single most important call to make.
  - A claim is **verifiable** if a partner could confirm it during normal diligence (revenue, named customers, prior funding, team backgrounds, regulatory standing). These do NOT make a question gating — you can verify them after the meeting.
  - A claim is **self-reported and material** if it sits at the heart of the investment thesis and the deck offers no way to verify it (retention cohort curves, engagement depth, organic growth attribution, network density). For these, asking before the meeting IS the diligence — without the answer, the meeting itself is misallocated time.

- Test for each follow-up question you might raise: "if the honest answer to this is unfavorable, would I pass?" Count the questions where the answer is yes.
  - **0 such questions** → Take meeting. Open questions remain but they're agenda items, not gates.
  - **1** → Take meeting unless that single question is the entire crux of the deal (rare).
  - **2+** → Ask first. The questions become a precondition, not part of the meeting.

- Concrete calibration:
  - A B2B deal with verifiable revenue, a credentialed team in a thesis-aligned vertical, and a coherent moat story is almost always **Take meeting**, even if the moat-mechanism detail or a roadmap branching choice is ambiguous in the deck. Those are agenda items.
  - A consumer deal whose central thesis rests on **self-reported retention or engagement metrics with no cohort breakdown** is almost always **Ask first** until you've seen the curves. "Strong team, fast growth" does NOT clear the bar if the metric that would justify the investment is unverified.

- Do not default either way. Pick the verdict that survives the "imagine the founder never replies" test.

- Each WHY bullet MUST end with a citation in the form `(filename.md)`. The default is to also embed a verbatim short quote (max 12 words) from that file inside the bullet, BUT with these strict rules:

  1. **Verbatim only.** The quote inside double-quotes must be a CHARACTER-FOR-CHARACTER substring of the cited file. Do not change "through" to "by," do not normalize punctuation, do not paraphrase. If the file says "differentiated through user experience," do NOT write "differentiated by user experience" — that exact phrasing belongs to a different file.

  2. **Quote source = cited file.** If the phrase you want lives in `02_firm_thesis_v2_2015.md`, your citation MUST be `02_firm_thesis_v2_2015.md` — even if the same idea appears in another doc. Never cross the streams.

  3. **Read naturally.** The quote must flow as English when embedded mid-sentence. Awkward parenthetical fragments (e.g. "the law (Casetext)" sitting in the middle of prose) are forbidden. If no quote from the cited file flows naturally, DROP THE QUOTE and cite the file alone — `... replays Casetext, our prior legal vertical bet (02_firm_thesis_v2_2015.md).` File-only citations are perfectly acceptable; a strained quote is not.

  4. **No fabrication.** Better to omit the quote than invent one that "sounds like" something the firm would say.

- SUPPRESS red flags that match the firm's known-bad pass reasons. If the firm's pass-reason archive explicitly calls out a failure mode like "crowded market," "valuation feels high while marketplace is doubling," or "rookie team in regulated space," do NOT use that as a reason to pass. The archive is the source of truth on what NOT to pass on. Note: suppressing a flag does NOT mean upgrading the verdict — a deal can still be Ask first or Pass for other reasons.

- Do NOT include "considerations on both sides," hedged analysis, or trailing caveats. Partners want signal.

- Do NOT wrap your response in markdown code fences (```). Emit the triage block as plain text, the delimiter as a plain line, and the full memo as plain markdown with H2 headings. Code fences inside example tool snippets are fine; they must not surround the response itself.

# OUTPUT 2 — FULL MEMO (deeper analysis, accessed via link)

After the triage block, emit a single line containing exactly:

---FULL-MEMO-BELOW---

Then the full memo using these markdown H2 headings, in this order:

## Fit summary
One opinionated sentence consistent with the verdict, then 2–3 sentences of why, citing thesis aspects.

## Where it maps to our thesis
Bulleted thesis-mapping. Quote the firm's words and tie each quote to a specific element of the deck.

## Comparable past deals
2–4 companies from the firm's archive (portfolio OR pass-reason archive). For each: name, what we did, how this deal is similar/different.

## Red flags
3–5 risks specific to *this* deck. The same suppression rule from OUTPUT 1 applies: if a flag matches the firm's known-bad pass reasons, explicitly suppress it. Do not raise it.

## Questions for the founder
4–6 sharp questions, each testing a load-bearing assumption.

## Recommendation
One sentence consistent with the verdict."""


USER_PROMPT_TEMPLATE = (
    '<new_deck filename="{filename}">\n'
    "{deck}\n"
    "</new_deck>\n\n"
    "Produce the triage block and full memo now, exactly per the instructions. "
    "Remember: VERDICT must be one of Take meeting | Pass | Ask first."
)

DELIMITER = "---FULL-MEMO-BELOW---"


# ----- Parser -------------------------------------------------------------

_VERDICT_VALUES = ("Take meeting", "Pass", "Ask first")

_QUOTE_CHAR_CLASS = r'["“”“”]'
_BULLET_PREFIX = r"^[\s]*[•\-\*][\s]*"


def _normalize_verdict(raw: str) -> str:
    """Coerce the model's verdict line into one of the three canonical values."""
    s = raw.strip().strip(".").strip()
    low = s.lower()
    if "take" in low:
        return "Take meeting"
    if "ask" in low:
        return "Ask first"
    if "pass" in low:
        return "Pass"
    return s  # leave unchanged; downstream callers can flag it


def _parse_bullet(line: str) -> dict[str, Any]:
    """Extract {text, citation_filename, citation_quote} from a single bullet."""
    text = re.sub(_BULLET_PREFIX, "", line.rstrip()).strip()

    fname_match = re.search(r"\(([^()]+\.(?:md|pdf|txt))\)", text)
    citation_filename = fname_match.group(1) if fname_match else None

    quotes = re.findall(rf"{_QUOTE_CHAR_CLASS}([^“”\"]{{1,200}}?){_QUOTE_CHAR_CLASS}", text)
    citation_quote = quotes[-1] if quotes else None

    return {
        "text": text,
        "citation_filename": citation_filename,
        "citation_quote": citation_quote,
    }


def _strip_code_fences(text: str) -> str:
    """Drop standalone code-fence lines.

    Defensive guard against models that ignore the no-code-fence instruction.
    A VC investment memo should never legitimately contain code blocks, so
    removing every standalone ``` line is safe and prevents fence characters
    from being mis-parsed as bullets, questions, or content.
    """
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("```")
    )


def parse_response(raw: str) -> dict[str, Any]:
    """Parse Claude's raw response into a structured triage + full-memo object."""
    raw = _strip_code_fences(raw)

    if DELIMITER in raw:
        triage_section, full_memo = raw.split(DELIMITER, 1)
    else:
        # Fallback: assume the full memo starts at the first H2 heading.
        h2_match = re.search(r"^##\s+Fit summary", raw, re.MULTILINE)
        if h2_match:
            triage_section = raw[: h2_match.start()]
            full_memo = raw[h2_match.start() :]
        else:
            triage_section = raw
            full_memo = ""

    triage_section = triage_section.strip()
    full_memo = full_memo.strip()

    # Verdict
    verdict_match = re.search(
        r"^\s*VERDICT\s*:\s*(.+?)\s*$", triage_section, re.IGNORECASE | re.MULTILINE
    )
    verdict = _normalize_verdict(verdict_match.group(1)) if verdict_match else "Unknown"

    # Bullets in the WHY block
    why_match = re.search(
        r"WHY\s*:\s*\n(.*?)(?=\n\s*\n|\nASK\s*FIRST|\Z)",
        triage_section,
        re.IGNORECASE | re.DOTALL,
    )
    bullets: list[dict[str, Any]] = []
    if why_match:
        for line in why_match.group(1).splitlines():
            if re.match(_BULLET_PREFIX, line) and len(line.strip()) > 2:
                bullets.append(_parse_bullet(line))

    # Questions only if Ask first
    questions: list[str] | None = None
    if verdict == "Ask first":
        ask_match = re.search(
            r"ASK\s*FIRST\s*:\s*\n(.*?)(?=\n\s*\n|\Z)",
            triage_section,
            re.IGNORECASE | re.DOTALL,
        )
        if ask_match:
            qs: list[str] = []
            for line in ask_match.group(1).splitlines():
                line = line.strip()
                if not line:
                    continue
                # Strip "1." / "1)" / "•" / "-"
                line = re.sub(r"^\s*(?:\d+[.)]|[•\-\*])\s*", "", line)
                if line:
                    qs.append(line)
            questions = qs[:5] if qs else None

    return {
        "verdict": verdict,
        "bullets": bullets,
        "questions": questions,
        "full_memo_md": full_memo,
        "triage_md": triage_section,
    }


# ----- Library API --------------------------------------------------------


def analyze_deck(
    deck_text: str,
    deck_filename: str,
    profile_text: str,
    corpus_text: str,
    *,
    stream_callback: Callable[[str], None] | None = None,
    client: anthropic.Anthropic | None = None,
) -> dict[str, Any]:
    """Run the analysis pipeline. Returns a structured result.

    If stream_callback is provided, it's invoked with each text delta as the
    response streams in. The streaming itself is always used (avoids long-
    running-request HTTP timeouts).
    """
    client = client or anthropic.Anthropic()
    chunks: list[str] = []
    started_at = time.monotonic()

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
                    f"<firm_corpus>\n{corpus_text}\n</firm_corpus>"
                ),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    filename=deck_filename, deck=deck_text
                ),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
            if stream_callback is not None:
                stream_callback(text)
        message = stream.get_final_message()

    elapsed_ms = int((time.monotonic() - started_at) * 1000)
    raw = "".join(chunks)

    parsed = parse_response(raw)
    parsed["raw_response"] = raw
    parsed["usage"] = {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "cache_read_input_tokens": message.usage.cache_read_input_tokens,
        "cache_creation_input_tokens": message.usage.cache_creation_input_tokens,
        "latency_ms": elapsed_ms,
    }
    return parsed


def load_corpus(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT filename, content FROM documents ORDER BY filename"
    ).fetchall()
    parts = [f"=== {filename} ===\n\n{content}" for filename, content in rows]
    return "\n\n---\n\n".join(parts)


# ----- CLI ----------------------------------------------------------------


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
    print("\n--- response (streaming) ---\n")

    def _print_chunk(text: str) -> None:
        print(text, end="", flush=True)

    result = analyze_deck(
        deck_text=deck_text,
        deck_filename=deck_path.name,
        profile_text=profile_text,
        corpus_text=corpus,
        stream_callback=_print_chunk,
    )

    print("\n\n--- parsed ---\n")
    print(f"VERDICT: {result['verdict']}")
    print(f"BULLETS: {len(result['bullets'])}")
    for i, b in enumerate(result["bullets"], 1):
        cite = (
            f"[{b['citation_filename']}: \"{b['citation_quote']}\"]"
            if b["citation_filename"]
            else "[no citation parsed]"
        )
        print(f"  {i}. {cite}")
    if result["questions"]:
        print(f"QUESTIONS ({len(result['questions'])}):")
        for i, q in enumerate(result["questions"], 1):
            print(f"  {i}. {q}")

    usage = result["usage"]
    print(
        f"\nTokens   input: {usage['input_tokens']:,}   "
        f"cache write: {usage['cache_creation_input_tokens']:,}   "
        f"cache read: {usage['cache_read_input_tokens']:,}   "
        f"output: {usage['output_tokens']:,}   "
        f"latency: {usage['latency_ms']:,}ms"
    )

    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
    memo_path = ANALYSES_DIR / f"{deck_path.stem}.memo.md"
    triage_path = ANALYSES_DIR / f"{deck_path.stem}.triage.md"
    memo_path.write_text(result["full_memo_md"])
    triage_path.write_text(result["triage_md"])
    print(f"\nSaved memo   → {memo_path}")
    print(f"Saved triage → {triage_path}")


if __name__ == "__main__":
    main()
