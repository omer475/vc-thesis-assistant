# VC Thesis Assistant

An AI assistant that analyzes new pitch decks against a VC firm's specific investment thesis, grounded in the firm's own historical memos and pass reasons.

## What it does

1. The firm uploads its old documents — investment memos, pass reasons, thesis docs.
2. The system reads them and builds a profile of how the firm thinks.
3. When a new pitch deck arrives, the system writes a 1-page opinion: fit score, comparable past deals, red flags, suggested questions — all citing the firm's actual history.

## Why this approach

We use **retrieval-augmented generation** (the system looks up relevant past memos when answering, like a librarian with a card catalog) rather than training a custom LLM per firm. Cheaper, faster, more accurate, and answers come with citations to the actual source documents.

## Status

Phase 1 (per `BRIEF.md`) in progress:

- [x] Step 1 — Triage output format (verdict + cited bullets + full memo)
- [x] Step 2 — Supabase Postgres migration (data persists across restarts)
- [ ] Step 3 — Public deal-link pages
- [ ] Step 4 — Affinity connector
- [ ] Step 5 — Admin polish (six-tab structure, analytics)

## Architecture

- **Database:** Supabase Postgres (single source of truth for firms, documents, decks, analyses, pass reasons).
- **LLM:** Claude Opus 4.7 via the `anthropic` SDK with adaptive thinking and prompt caching.
- **Web UI:** Streamlit (admin app + public deal pages once Step 3 lands).
- **Hosting:** Streamlit Community Cloud (free tier).

Schema lives at `supabase/migrations/0001_init.sql`. CLI scripts (`src/ingest.py`, `src/profile.py`, `src/analyze.py`, `src/inspect_db.py`) and the Streamlit app (`src/app.py`) all share a single DB layer in `src/db.py` — no module imports the Supabase client directly.

## Deploy: two options

### Free — Streamlit Community Cloud (recommended for demos)

1. https://share.streamlit.io → sign in with GitHub
2. **New app** → pick this repo, branch `main`, main file path `src/app.py`
3. Click **Advanced settings** → paste into the "Secrets" box:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSWORD = "pick-any-password"
   ```
4. **Deploy**. Takes ~2 minutes.

Caveat: Streamlit Cloud's filesystem is ephemeral. The committed example data (Forge Ventures fixtures) is auto-ingested on every restart so the demo always works, but anyone uploading their own firm docs will see them disappear on the next restart. Fine for demos; not for real production use.

### Always-on — Render (~$8/month)

1. https://render.com → sign up with GitHub
2. New → **Blueprint** → connect this repo
3. Render reads `render.yaml` and prompts for two env vars:
   - `ANTHROPIC_API_KEY` — paste your key
   - `APP_PASSWORD` — pick anything; share it with people who should access the app
4. Apply. First deploy takes ~3 minutes.

The persistent disk (mounted at `/var/data`) keeps uploaded firm docs and the SQLite store across restarts. On first boot, the included example data (Forge Ventures fixtures) is auto-loaded so the demo isn't empty.

## Run the web UI

```bash
source venv/bin/activate
streamlit run src/app.py
```

Then open http://localhost:8501 — upload firm docs, generate the profile, drop in a deck, get a memo back.

## Or use it from the command line

```bash
source venv/bin/activate

# Drop docs into data/firm_docs/ then:
python -m src.ingest                                    # build corpus
python -m src.profile                                   # → data/firm_profile.md
python -m src.analyze data/incoming_decks/<deck>.md     # → data/analyses/<deck>.memo.md
```

## Setup

```bash
cd vc-thesis-assistant
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your Anthropic API key
```

## Project layout

```
vc-thesis-assistant/
├── src/                  # Python source
├── data/
│   ├── firm_docs/        # firm's historical memos/notes (gitignored)
│   └── incoming_decks/   # new pitch decks to analyze (gitignored)
├── tests/
├── .env                  # API keys (gitignored)
├── .env.example          # template
└── requirements.txt
```
