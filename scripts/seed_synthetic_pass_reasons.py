"""Seed 6-8 synthetic-but-plausible pass reasons into Forge Ventures.

Run:
    python -m scripts.seed_synthetic_pass_reasons

Used to validate the analyzer's "suppress bad-pass red flags" behavior
when no real Affinity workspace is available. Companies here are
deliberately DIFFERENT from the ones already in
`data/firm_docs/06_pass_reasons_archive.md` — that lets us also exercise
the (firm_id, company_name) dedupe path on subsequent re-runs.

Tone matches the existing archive: candid, partner-attributed, with a
"Lesson:" line so the analyzer can map a new deck to the lesson.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src.*` importable when run directly.
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv

from src import db

load_dotenv()


SYNTHETIC_REASONS: list[dict] = [
    {
        "company_name": "Stripe",
        "deal_date": "2010-08-01",
        "reason_text": (
            "Met the Collison brothers in 2010 at a small-batch payments-API pitch. "
            "A partner pattern-matched to a 'two college kids' archetype and called "
            "the seven-line-of-code demo a 'toy.' Passed at the seed.\n\n"
            "Lesson: 'College-age founders' is not a market signal. The infrastructure "
            "ergonomics that look like a toy at the Series A often become the moat."
        ),
    },
    {
        "company_name": "Notion",
        "deal_date": "2018-04-12",
        "reason_text": (
            "Reviewed the Series A. A partner argued 'wikis are dead' (citing the "
            "MediaWiki / Confluence stagnation) and that document-tool consolidation "
            "would crush a fresh entrant. Passed.\n\n"
            "Lesson: Categories pronounced 'dead' by incumbents are exactly where "
            "next-generation primitives reset the market. Stop quoting Confluence's "
            "decay as evidence about Notion."
        ),
    },
    {
        "company_name": "Figma",
        "deal_date": "2017-09-08",
        "reason_text": (
            "A partner test-drove the early browser-based Figma editor and reported "
            "'real designers will never give up native desktop performance.' Passed "
            "the Series A on technical-skepticism grounds.\n\n"
            "Lesson: When the collaboration UX is a step-change, designers DO trade a "
            "performance delta for it. We over-weighted technical purity over workflow "
            "transformation."
        ),
    },
    {
        "company_name": "Cloudflare",
        "deal_date": "2010-11-20",
        "reason_text": (
            "We saw an early CDN+security pitch and called the segment 'a "
            "commoditized infrastructure layer where Akamai is the incumbent.' "
            "Passed citing low gross margins.\n\n"
            "Lesson: Commodity-layer companies that win on developer ergonomics + "
            "broad horizontal expansion (workers, R2, etc.) end up high-margin. "
            "Margin-at-the-point-of-evaluation is not destiny."
        ),
    },
    {
        "company_name": "Discord",
        "deal_date": "2016-02-15",
        "reason_text": (
            "Saw the seed. Called it 'TeamSpeak with a coat of paint' and concluded "
            "'voice chat is a feature, not a product.' Passed.\n\n"
            "Lesson: Communities form around the primitive that matches the actual "
            "behavior. Voice-with-persistent-text, organized by communities, was a "
            "different shape than 'voice chat' — we under-distinguished."
        ),
    },
    {
        "company_name": "Replit",
        "deal_date": "2019-06-10",
        "reason_text": (
            "Met the team in 2019. A partner argued 'consumer-grade dev tools don't "
            "monetize — students won't pay, and pros won't switch from VS Code.' "
            "Passed.\n\n"
            "Lesson: Time-to-first-running-program for a beginner is a real wedge. "
            "We mis-modeled the GTM as 'IDE replacement' instead of 'environment for "
            "people who don't have one yet.'"
        ),
    },
    {
        "company_name": "Anthropic",
        "deal_date": "2021-04-01",
        "reason_text": (
            "Reviewed the seed in 2021. We dismissed the team as 'a research lab, "
            "not a company,' and assumed safety-focused frontier-model labs would "
            "lose to whoever shipped fastest. Passed.\n\n"
            "Lesson: 'Research lab vs. company' is a false dichotomy when the "
            "research IS the moat. Don't confuse founders' technical pedigree with "
            "lack of commercial intent."
        ),
    },
]


def main() -> None:
    firm = db.get_or_create_default_firm()
    print(f"Seeding pass reasons into firm: {firm['name']} ({firm['slug']})")
    print()

    counts = {"inserted": 0, "updated": 0}
    for entry in SYNTHETIC_REASONS:
        result = db.upsert_pass_reason(
            firm_id=firm["id"],
            source="manual",
            reason_text=entry["reason_text"],
            company_name=entry["company_name"],
            deal_date=entry.get("deal_date"),
        )
        action = result.get("action", "skipped")
        counts[action] = counts.get(action, 0) + 1
        print(f"  [{action:<8}] {entry['company_name']}")

    print()
    print(f"Done. Inserted: {counts.get('inserted', 0)}  ·  Updated: {counts.get('updated', 0)}")
    total = db.list_pass_reasons(firm["id"])
    print(f"Firm now has {len(total)} pass reasons in the DB.")


if __name__ == "__main__":
    main()
