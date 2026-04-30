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
- [ ] Phase 5 — First design-partner firm onboarded

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
