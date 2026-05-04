"""Centralized paths and config.

In local dev, DATA_DIR defaults to <repo>/data/ — exactly what we had before.

In production (e.g., Render), set DATA_DIR=/var/data (or wherever the
persistent disk is mounted). All file/db paths read from DATA_DIR, so the
same code runs locally and on the deployed server with no other changes.
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
DB_PATH = DATA_DIR / "firm.db"
PROFILE_PATH = DATA_DIR / "firm_profile.md"


def ensure_dirs() -> None:
    """Create the runtime data directories if they don't exist."""
    for d in (DATA_DIR, DOCS_DIR, INCOMING_DECKS_DIR, ANALYSES_DIR):
        d.mkdir(parents=True, exist_ok=True)


def is_running_in_production() -> bool:
    """True if DATA_DIR is set to something other than the repo's data/ dir."""
    return DATA_DIR.resolve() != EXAMPLE_DATA_DIR.resolve()
