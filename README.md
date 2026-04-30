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
- [ ] Phase 1 — PDF reader + local document store
- [ ] Phase 2 — Firm-profile generator
- [ ] Phase 3 — Deal-analysis pipeline
- [ ] Phase 4 — Streamlit web UI
- [ ] Phase 5 — First design-partner firm onboarded

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
