# Claude Code Brief — VC Thesis Assistant, Phase 1

**Read this entire brief before writing any code.**

You are working on `vc-thesis-assistant`, an existing Python project owned by Omer Sogancioglu (GitHub: `omer475`). The repo is at `~/vc-thesis-assistant` on his machine, also at `https://github.com/omer475/vc-thesis-assistant`. Your job is to evolve it from a Streamlit demo into a tool good enough that a VC firm sees the output and says "I want this on my desk."

This brief gives you:
1. How to orient yourself
2. The product change being made
3. A locked-in tech stack — do not propose alternatives
4. Phase 1 scope (5 steps, in execution order, with full specs)
5. What NOT to do
6. Checkpoints where you must stop and confirm with Omer before proceeding

---

## Step 0 — Orient yourself before doing anything

Before any code change:

- `ls -la` the repo, read `README.md`
- Read these files end-to-end so you understand the current pipeline:
  - `src/config.py`, `src/ingest.py`, `src/profile.py`, `src/analyze.py`, `src/app.py`, `src/bootstrap.py`, `src/inspect_db.py`
- Read the example data: `data/firm_profile.md`, one of `data/firm_docs/*.md`, both decks in `data/incoming_decks/`, both example memos in `data/analyses/`
- Confirm the existing app runs locally (`source venv/bin/activate && streamlit run src/app.py`). If anything is broken, fix that before proceeding with new work.

**Then stop and report back to Omer with:**
- One-paragraph summary of the repo's current state
- Anything broken or unclear in this brief
- Your proposed execution sequence for Phase 1 with rough time estimates per step
- The list of credentials Omer needs to paste into `.env` before Step 2 begins

Do not proceed past this checkpoint without his confirmation.

---

## What the product is becoming (Phase 1 scope)

**Today:** a Streamlit app where you upload firm docs and pitch decks and get a one-page memo.

**End of Phase 1:** the same Streamlit app, but materially better as a product:
- Sharper, more opinionated triage output (verdict + 3 cited bullets) on top of a deeper memo
- Real persistence on Postgres (Supabase) — firm data and analyses survive restarts
- Shareable read-only deal-link pages (an unguessable URL Omer can hand to a partner — no login required for the partner)
- Automatic pull of pass-reason notes from a firm's CRM (Affinity), feeding the killer "suppress bad-pass red flags" feature
- A clean six-tab admin app

**What Phase 1 is NOT:** the full email-forwarding workflow. Email automation (Resend, FastAPI worker, Render hosting) is Phase 2 — only built once a real design partner is committed to using it daily. Right now there is no partner, so building email infra would mean automating a workflow with zero users. Don't do it.

There are two user roles even without email:
- **Partner (the user):** receives a link from Omer (manually shared via text/Slack/email), opens it, reads the analysis. No login.
- **Admin (Omer initially):** uploads firm docs, manages the firm profile and partner allowlist, connects the CRM, runs analyses, copies share links. Uses the web app.

---

## Tech stack — locked

Do not propose alternatives, do not yak-shave.

| Layer | Tool |
|---|---|
| Language | Python 3.12 |
| LLM | Claude Opus 4.7 via `anthropic` SDK (existing) |
| Web app | Streamlit (existing — kept; covers admin AND public deal pages) |
| Database | Supabase (Postgres) — replaces SQLite |
| Hosting | Streamlit Community Cloud (existing) |
| PDF extraction | `pypdf` (existing) |
| Secrets | `python-dotenv` locally; `st.secrets` on Streamlit Cloud (existing pattern) |

**Not in scope this phase:** FastAPI, Render, Resend, any email service, any new domain configuration.

---

## Phase 1 — five steps in order

After each step: commit, push, and ask Omer to test before moving to the next. Conventional commit messages (`feat:`, `fix:`, `refactor:`, `chore:`).

---

### Step 1 — Sharpen the analysis output format

Highest-value, lowest-risk change. Do this first; no infra work yet.

**Goal:** Replace the one-page memo as the *primary* output with a compact triage verdict that a partner can read in 30 seconds. The full memo is still generated and stored, but it becomes the secondary "deep-dive" artifact accessed via the deal-link page.

**Output spec.** Every analysis must produce both:

**1. A triage block** (top of the deal page, also savable as a standalone file):

```
VERDICT: <Take meeting | Pass | Ask first>

WHY:
• <Bullet 1 — concrete claim, with an inline short quote from a firm doc, max ~25 words>
• <Bullet 2 — same shape>
• <Bullet 3 — same shape>

[If VERDICT = "Ask first":]
ASK FIRST:
1. <Question>
2. <Question>
3. <Question>
```

**2. A full memo** (existing format, lightly tightened) saved as before — this is what the deal-link page expands to show.

**Hard rules for the triage block:**

- The verdict is opinionated. No "it depends." Pick one of three.
- Each bullet must cite a specific firm doc — file name + verbatim short quote (max 12 words). Format example: `…matches your 2018 thesis on "broad-based prosperity as Trojan horse" (03_firm_thesis_v3_2018.md)`.
- "Ask first" is reserved for borderline deals where 2-3 specific founder answers would settle the call. Use sparingly.
- **Suppress red flags that match the firm's known-bad pass reasons.** This is the killer feature — keep it explicit in the prompt.
- Do NOT include "considerations on both sides" type balance. VCs want signal, not analysis.

**Files to change:**
- `src/analyze.py` — update the system prompt and parse output into a structured object: `{verdict, bullets: [{text, citation_filename, citation_quote}], questions (optional, list of 3), full_memo_md}`. Existing CLI behaviour (writing to `data/analyses/<stem>.memo.md`) keeps working but additionally writes `<stem>.triage.md` with just the triage block.
- `src/app.py` — the "Analyze a Deal" tab displays the triage block prominently at the top, then the full memo collapsed below.

**Test:**
Run on both example decks.
- `contractai_seriesA.md` should produce `VERDICT: Take meeting`
- `wisp_seed.md` should produce `VERDICT: Pass` or `VERDICT: Ask first`

If either fails, iterate the prompt until it passes.

**Checkpoint:** show Omer the triage outputs side-by-side with the existing full memos before moving on.

---

### Step 2 — Migrate to Supabase

**Goal:** Replace SQLite with Postgres on Supabase so data survives restarts and supports multi-firm in the future.

**Status going in:** Omer has already created the Supabase project. He will paste the project URL and service-role key into `.env` when you reach this step. He will run the migration in the Supabase SQL editor — **you do not push schema changes to Supabase yourself**, you generate the migration file and he runs it.

**Schema** — generate a migration file at `supabase/migrations/0001_init.sql`:

```sql
-- one row per firm using the product
create table firms (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,            -- e.g. 'forge'
  name text not null,
  profile_md text,
  affinity_api_key text,                -- nullable; plain text for v1
  affinity_passed_status_id text,       -- per-firm Affinity config
  created_at timestamptz default now()
);

-- firm corpus documents
create table documents (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid references firms(id) on delete cascade,
  filename text not null,
  page_count int not null,
  content text not null,
  ingested_at timestamptz default now(),
  unique (firm_id, filename)
);

-- partners at a firm — used for analytics and the partner allowlist UI
create table partners (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid references firms(id) on delete cascade,
  name text,
  email text not null,
  created_at timestamptz default now(),
  unique (firm_id, email)
);

-- every incoming pitch deck
create table decks (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid references firms(id) on delete cascade,
  partner_id uuid references partners(id),
  source text not null,                 -- 'upload' | 'api' (email comes in Phase 2)
  original_filename text,
  subject text,
  content text not null,
  received_at timestamptz default now()
);

-- analysis output for a deck
create table analyses (
  id uuid primary key default gen_random_uuid(),
  deck_id uuid references decks(id) on delete cascade,
  verdict text not null,                -- 'Take meeting' | 'Pass' | 'Ask first'
  bullets jsonb not null,               -- [{text, citation_filename, citation_quote}, ...]
  questions jsonb,                      -- [string, string, string] when verdict = 'Ask first'
  full_memo_md text not null,
  tokens_in int,
  tokens_out int,
  cache_read_tokens int,
  cache_write_tokens int,
  latency_ms int,
  created_at timestamptz default now()
);

-- known pass reasons (manual upload or synced from Affinity)
create table pass_reasons (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid references firms(id) on delete cascade,
  source text not null,                 -- 'manual' | 'affinity'
  company_name text,
  reason_text text not null,
  deal_date date,
  ingested_at timestamptz default now()
);

-- outcome tracking (filled in after the fact)
create table outcomes (
  id uuid primary key default gen_random_uuid(),
  deck_id uuid references decks(id) on delete cascade unique,
  took_meeting boolean,
  invested boolean,
  notes text,
  updated_at timestamptz default now()
);

create index on documents (firm_id);
create index on partners (firm_id);
create index on decks (firm_id, received_at desc);
create index on analyses (deck_id);
create index on pass_reasons (firm_id);
```

The migration file Omer runs will be clean-slate — `drop table if exists … cascade;` at the top, then the creates — so the migration is fully idempotent and re-runnable.

**Implementation:**

- Add `supabase` (the Python client) to `requirements.txt`
- Create `src/db.py` — single source of truth for DB access. All DB calls go through this module. Use the Supabase **service-role** key from env, not the anon key.
- Migrate `src/ingest.py`, `src/profile.py`, `src/analyze.py`, `src/inspect_db.py`, `src/bootstrap.py` to use the new schema.
- During bootstrap, ensure a default `firms` row for "Forge Ventures" (slug: `forge`) exists. All existing example data gets that `firm_id`.

**What to ask Omer for at the start of this step:**
- Supabase project URL
- Supabase service-role key

**Test:** all existing flows (ingest, profile, analyze, the Streamlit app, both CLI test decks) work end-to-end against Supabase, with no regression vs SQLite.

---

### Step 3 — Public deal-link pages

**Goal:** Every analysis gets a shareable read-only URL. Omer pastes the URL to a partner; they open it without logging in.

**Implementation:** add a "public view" mode to `src/app.py`, accessed via `?deal=<analysis_id>` query param.

- If the param is present: render the public view *only*. No sidebar, no admin chrome, no password gate.
- If absent: show the normal admin app (with password gate if `APP_PASSWORD` is set).

Streamlit reads query params via `st.query_params` (newer) or `st.experimental_get_query_params` (older). Use whichever the installed version supports; pin Streamlit version in requirements if needed.

**Layout for the public view:**

- Top-left: firm name (small, muted)
- Headline: deal name (use `decks.subject` or `original_filename`) or fallback "Deal Analysis"
- Big verdict badge: green for "Take meeting", red for "Pass", amber for "Ask first"
- Three reasoning bullets, citation rendered inline in muted text after each bullet
- "Ask first" questions block if present
- Collapsible: full memo (`st.expander`)
- Footer: "Generated by <firm name> Thesis Assistant — <timestamp>"

**In the admin app:** after running an analysis, show a "Copy share link" button that copies `https://<streamlit-app>/?deal=<analysis_id>` to clipboard. This is the manual share path until email automation arrives in Phase 2.

**Security note:** the link is unguessable (UUID), no auth — acceptable for v1. Document this in `README.md` as a known v1 tradeoff.

**Test:** run an analysis, copy the share link, open it in an incognito window or different browser, confirm the public view renders correctly with no admin chrome and no password prompt.

---

### Step 4 — Affinity connector

**Goal:** Automatically pull pass-reason notes from a firm's Affinity CRM and inject them into the firm corpus, so the "suppress bad-pass red flags" feature has real data to work with. Without this, every onboarded firm will have a thin pass-reason corpus and the feature won't fire.

**Implementation:**

- New module `src/affinity.py`
- Read Affinity API key from `firms.affinity_api_key` (set via admin UI). For v1 it's OK to also fall back to an `AFFINITY_API_KEY` env var.
- Sync function `sync_pass_reasons(firm_id)`:
  - Call Affinity API: list deals where status = `firms.affinity_passed_status_id`
  - For each passed deal, fetch its notes
  - Concatenate notes into a single `reason_text`
  - Upsert into `pass_reasons` (`source = 'affinity'`, dedupe by `firm_id + company_name`)
- The analyze pipeline already reads from the firm corpus — make sure `pass_reasons` rows are joined in when the corpus is assembled. If they aren't yet, fix that.

**Admin UI (CRM tab):** connection status (key present? last sync time? count of pass reasons synced?), button "Sync now" (triggers sync, shows progress), simple table of synced pass reasons.

**Stop and ask Omer for:**
- Whether to build against Affinity or Attio (he doesn't have a design partner yet, so default to Affinity unless he says otherwise — Affinity is more common in VC and has a cleaner API). Structure the code so swapping later is one file.
- A test Affinity API key + the firm's "Passed" status ID (he will use a sandbox or a personal test workspace if no design partner is available).

**Test:** sync runs, populates `pass_reasons`. Run analyze on a deck whose pitch overlaps with a synced pass-reason — confirm the resulting verdict suppresses or correctly reframes the matching red flag.

---

### Step 5 — Admin polish

**Goal:** the admin app feels like a product, not a demo. This is what Omer screen-shares to a prospective design partner.

**Changes to `src/app.py`:**

- Restructure tabs to exactly: **Analyze · Firm setup · Partners · CRM · Analytics · Settings**. "Analyze" is the default/landing tab — this is the daily-use surface; everything else is configuration.
- **Analyze:** the primary daily-use tab. List of past deals at the top, each clickable to open the public deal-link page. "New analysis" CTA at the top runs the deck-upload + triage flow. After an analysis completes, surface the verdict, bullets, questions (if any), full-memo expander, and a "Copy share link" button.
- **Firm setup:** existing doc upload + profile generation, cleaner layout, max 3 primary actions visible. (No analyze flow here — that lives in its own tab now.)
- **Partners:** list partners (table: name, email, added). Add partner (name + email form). Remove partner (button). All operations write to `partners` table.
- **CRM:** the Step 4 UI (Affinity status + sync).
- **Analytics:** simple metrics for the past 7 / 30 days:
  - Deals analyzed (count)
  - Verdict mix (Take meeting / Pass / Ask first counts)
  - Per-partner usage (deals received by each partner — for now, partner is whoever Omer assigns at upload)
  - Average latency (ms)
  - Total tokens in/out, cache read/write
- **Settings:** firm slug, API key status indicator (present/missing), password change, danger zone (delete firm — not implemented in v1, just placeholder).

- **Sidebar:** firm name at top + 3 status indicators:
  - Corpus size (`X documents, Y characters`)
  - Last CRM sync (or "not connected")
  - Deals this week (count)

- Strip current visual cruft. Use `st.columns` for layout. No more than 3 primary actions per screen.

**Test:** click through every tab, every button. No errors. End-to-end smoke test: upload firm docs → generate profile → upload deck → see triage → copy share link → open in incognito → see public deal page.

---

## Working principles (apply throughout)

- **Commit + push after each step.** Conventional commit messages.
- **Ask before destructive changes.** Schema changes, deletions, force-pushes, `.env` modifications — always confirm.
- **Don't add features outside this brief.** If you spot an obvious improvement, write it in `NOTES.md` and keep moving.
- **Run the test decks after every change to `analyze.py`.** Both `contractai_seriesA.md` and `wisp_seed.md`. Catch regressions fast.
- **Errors are visible, not swallowed.** If analyze fails, the admin UI should surface the error clearly.
- **Streaming is fine in Streamlit.** Keep the existing streaming pattern for live UX.
- **Keep the prompt-cache strategy intact.** It works; don't restructure it.

---

## What NOT to do in Phase 1

- Do **not** build the email worker, FastAPI service, Resend integration, Render deployment, or any inbound-email flow. That's Phase 2.
- Do **not** migrate to Next.js, React, or any non-Streamlit frontend.
- Do **not** build per-partner profiles (every partner uses the firm profile in v1).
- Do **not** add embeddings, pgvector, or RAG retrieval — corpus stays in-context.
- Do **not** add multi-tenant auth — one firm per deployment, password-gated admin.
- Do **not** add billing, Stripe, or paywalls.
- Do **not** build a Slack integration.
- Do **not** add vision / image-PDF parsing.
- Do **not** rewrite `analyze.py`'s core RAG logic — only its output format.
- Do **not** rotate or change the Anthropic API key.

---

## Definition of Done for Phase 1

When all of the below are true, Phase 1 ships:

- Triage output format is locked in and produces the right verdicts on both example decks
- All firm/deck/analysis data lives in Supabase and survives restarts
- Every analysis has a shareable public URL that renders cleanly without login
- Affinity sync pulls pass reasons into the corpus and demonstrably influences verdicts
- The admin app has the six-tab structure (Analyze · Firm setup · Partners · CRM · Analytics · Settings) and weekly analytics
- Both example test decks still produce expected verdicts
- A new firm can be set up end-to-end (docs → profile → deck → triage → share link) inside the admin app

Phase 2 (email automation, per-partner profiles, outcomes loop, thesis drift) starts only after a design partner commits.
