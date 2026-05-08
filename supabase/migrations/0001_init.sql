-- =============================================================================
-- 0001_init.sql — VC Thesis Assistant initial schema
--
-- Clean-slate migration. Drops every project table first, then creates fresh.
-- Safe to re-run during early development; will wipe all data when re-run.
-- =============================================================================

-- ----- drop existing (reverse FK order, with cascade as belt-and-suspenders) --
drop table if exists outcomes      cascade;
drop table if exists pass_reasons  cascade;
drop table if exists analyses      cascade;
drop table if exists decks         cascade;
drop table if exists partners      cascade;
drop table if exists documents     cascade;
drop table if exists firms         cascade;


-- ----- create -----------------------------------------------------------------

-- one row per firm using the product
create table firms (
  id                          uuid          primary key default gen_random_uuid(),
  slug                        text          unique not null,            -- e.g. 'forge'
  name                        text          not null,
  profile_md                  text,
  affinity_api_key            text,                                     -- nullable; plain text for v1
  affinity_passed_status_id   text,                                     -- per-firm Affinity config
  created_at                  timestamptz   default now()
);

-- firm corpus documents
create table documents (
  id            uuid          primary key default gen_random_uuid(),
  firm_id       uuid          references firms(id) on delete cascade,
  filename      text          not null,
  page_count    int           not null,
  content       text          not null,
  ingested_at   timestamptz   default now(),
  unique (firm_id, filename)
);

-- partners at a firm — used for analytics and the partner allowlist UI
create table partners (
  id          uuid          primary key default gen_random_uuid(),
  firm_id     uuid          references firms(id) on delete cascade,
  name        text,
  email       text          not null,
  created_at  timestamptz   default now(),
  unique (firm_id, email)
);

-- every incoming pitch deck
create table decks (
  id                  uuid          primary key default gen_random_uuid(),
  firm_id             uuid          references firms(id) on delete cascade,
  partner_id          uuid          references partners(id),
  source              text          not null,                           -- 'upload' | 'api'  (email = phase 2)
  original_filename   text,
  subject             text,
  content             text          not null,
  received_at         timestamptz   default now()
);

-- analysis output for a deck
create table analyses (
  id                          uuid          primary key default gen_random_uuid(),
  deck_id                     uuid          references decks(id) on delete cascade,
  verdict                     text          not null,                   -- 'Take meeting' | 'Pass' | 'Ask first'
  bullets                     jsonb         not null,                   -- [{text, citation_filename, citation_quote}, ...]
  questions                   jsonb,                                    -- [string, string, string] when verdict = 'Ask first'
  full_memo_md                text          not null,
  tokens_in                   int,
  tokens_out                  int,
  cache_read_tokens           int,
  cache_write_tokens          int,
  latency_ms                  int,
  created_at                  timestamptz   default now()
);

-- known pass reasons (manual upload or synced from Affinity)
create table pass_reasons (
  id            uuid          primary key default gen_random_uuid(),
  firm_id       uuid          references firms(id) on delete cascade,
  source        text          not null,                                 -- 'manual' | 'affinity'
  company_name  text,
  reason_text   text          not null,
  deal_date     date,
  ingested_at   timestamptz   default now()
);

-- outcome tracking (filled in after the fact)
create table outcomes (
  id            uuid          primary key default gen_random_uuid(),
  deck_id       uuid          references decks(id) on delete cascade unique,
  took_meeting  boolean,
  invested      boolean,
  notes         text,
  updated_at    timestamptz   default now()
);


-- ----- indexes ----------------------------------------------------------------

create index on documents     (firm_id);
create index on partners      (firm_id);
create index on decks         (firm_id, received_at desc);
create index on analyses      (deck_id);
create index on pass_reasons  (firm_id);
