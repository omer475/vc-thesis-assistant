"""Centralized paths and config.

After the Supabase migration (Step 2) the project no longer uses a local
SQLite database. The remaining `data/` directories are for:

  - committed example fixtures (firm_docs/, incoming_decks/) that the
    bootstrap seeds into Supabase on first run, and
  - convenience exports written by CLI commands (firm_profile.md,
    analyses/<stem>.{memo,triage}.md) so users can grep them on disk.

`DATA_DIR` is still controllable via env var so a future production deploy
can point convenience exports at a writable persistent location if needed.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DATA_DIR = PROJECT_ROOT / "data"

DATA_DIR = Path(os.environ.get("DATA_DIR", str(EXAMPLE_DATA_DIR)))

DOCS_DIR = DATA_DIR / "firm_docs"
INCOMING_DECKS_DIR = DATA_DIR / "incoming_decks"
ANALYSES_DIR = DATA_DIR / "analyses"
PROFILE_PATH = DATA_DIR / "firm_profile.md"


def ensure_dirs() -> None:
    """Create the runtime data directories if they don't exist."""
    for d in (DATA_DIR, DOCS_DIR, INCOMING_DECKS_DIR, ANALYSES_DIR):
        d.mkdir(parents=True, exist_ok=True)


def is_running_in_production() -> bool:
    """True if DATA_DIR is set to something other than the repo's data/ dir."""
    return DATA_DIR.resolve() != EXAMPLE_DATA_DIR.resolve()
