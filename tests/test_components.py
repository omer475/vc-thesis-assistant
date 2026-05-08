"""Tests for src.components helpers.

Run:
    python -m tests.test_components
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src.*` importable when this script is run directly.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.components import pretty_filename


PRETTY_FILENAME_CASES = [
    ("01_firm_thesis_v1_2012.md", "Thesis v1 (2012)"),
    ("02_firm_thesis_v2_2015.md", "Thesis v2 (2015)"),
    ("03_firm_thesis_v3_2018.md", "Thesis v3 (2018)"),
    ("04_firm_thesis_four_futures_2024.md", 'Thesis "Four Futures" (2024)'),
    ("05_founding_statement_2005.md", "Founding statement (2005)"),
    ("06_pass_reasons_archive.md", "Pass reasons archive"),
    # Edge cases — sensible defaults
    ("readme.md", "Readme"),
    ("memo.pdf", "Memo"),
    ("notes_about_widgets.txt", "Notes about widgets"),
]


def run() -> int:
    failures = []
    print("pretty_filename:")
    for input_, expected in PRETTY_FILENAME_CASES:
        got = pretty_filename(input_)
        ok = got == expected
        marker = "OK  " if ok else "FAIL"
        print(f"  [{marker}]  {input_!r:55s} -> {got!r}")
        if not ok:
            failures.append(("pretty_filename", input_, expected, got))

    # parse_pasted_pass_reasons
    print()
    print("parse_pasted_pass_reasons:")
    from src.views.crm import parse_pasted_pass_reasons

    paste_sample = (
        "Stripe — passed 2010\n"
        "Two college kids with a toy. Lesson: don't pattern-match.\n"
        "\n"
        "Notion: passed 2018\n"
        "Wikis are dead. Bad take.\n"
        "\n"
        "Random unstructured paragraph with no company name in it. Just notes.\n"
        "\n"
        "Passed on Anthropic in 2021 because 'research lab not a company.'\n"
    )
    parsed = parse_pasted_pass_reasons(paste_sample)
    expected = [
        ("Stripe", True),
        ("Notion", True),
        (None, True),
        ("Anthropic", True),
    ]
    if len(parsed) != len(expected):
        failures.append(
            ("parse_pasted", "len", len(expected), len(parsed))
        )
    for got, (want_co, _) in zip(parsed, expected):
        company = got.get("company_name")
        ok = company == want_co
        marker = "OK  " if ok else "FAIL"
        print(f"  [{marker}]  expected company={want_co!r:15s}  got={company!r}")
        if not ok:
            failures.append(("parse_pasted", "company", want_co, company))

    print()
    if failures:
        print(f"{len(failures)} failure(s):")
        for fail in failures:
            print(f"  {fail}")
        return 1
    total = len(PRETTY_FILENAME_CASES) + len(parsed)
    print(f"{total} cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
