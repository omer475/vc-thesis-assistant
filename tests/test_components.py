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
    for input_, expected in PRETTY_FILENAME_CASES:
        got = pretty_filename(input_)
        ok = got == expected
        marker = "OK  " if ok else "FAIL"
        print(f"  [{marker}]  {input_!r:55s} -> {got!r}")
        if not ok:
            failures.append((input_, expected, got))

    print()
    if failures:
        print(f"{len(failures)} failure(s):")
        for input_, expected, got in failures:
            print(f"  {input_!r}")
            print(f"    expected: {expected!r}")
            print(f"    got:      {got!r}")
        return 1
    print(f"{len(PRETTY_FILENAME_CASES)} passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
