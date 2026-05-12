-- 0002_persona.sql
-- Persist the analyst persona that was selected when an analysis was run,
-- so downstream analytics can compare verdicts/bullets across the three
-- personas wired into the prompt (Strategic Lead, Market Analyst, Founder
-- Specialist). Nullable + idempotent — safe to re-run.

alter table analyses
  add column if not exists analyst_persona text;
