# VC Thesis Assistant

An AI assistant that analyzes new pitch decks against a VC firm's specific investment thesis, grounded in the firm's own historical memos and pass reasons.

## What it does

1. The firm uploads its old documents — investment memos, pass reasons, thesis docs.
2. The system reads them and builds a profile of how the firm thinks.
3. When a new pitch deck arrives, the system writes a 1-page opinion: fit score, comparable past deals, red flags, suggested questions — all citing the firm's actual history.

## Why this approach

We use **retrieval-augmented generation** (the system looks up relevant past memos when answering, like a librarian with a card catalog) rather than training a custom LLM per firm. Cheaper, faster, more accurate, and answers come with citations to the actual source documents.

## Status

Early MVP. Building in 5 phases:

- [x] Phase 0 — Project skeleton
- [x] Phase 1 — Document reader + local SQLite store (.pdf, .md, .txt)
- [x] Phase 2 — Firm-profile generator (Claude Opus 4.7, prompt-cached)
- [x] Phase 3 — Deal-analysis pipeline
- [x] Phase 4 — Streamlit web UI
- [x] Phase 5 — Render deploy config (persistent disk, password-gated)
- [ ] Phase 6 — First design-partner firm onboarded

## Deploy on Render (~$8/month)

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
