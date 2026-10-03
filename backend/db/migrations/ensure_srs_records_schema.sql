-- One-shot repair for srs_records so it matches backend/srs.py + create_srs_records.sql.
-- Run the whole script in Supabase SQL Editor for the project in SUPABASE_URL.
--
-- Why errors looked "one column at a time": PostgREST validates the upsert payload and
-- reports the first unknown column (PGRST204). Fixing one reveals the next — your table
-- was likely created incrementally or is missing columns that the Python client sends.

-- 1) Rename legacy reserved column name `interval` → interval_days (app uses interval_days).
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'srs_records' and column_name = 'interval'
  ) and not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'srs_records' and column_name = 'interval_days'
  ) then
    execute 'alter table public.srs_records rename column "interval" to interval_days';
  end if;
end $$;

-- 2) Add every column the API writes (safe if already present).
alter table public.srs_records add column if not exists ease_factor double precision not null default 2.5;
alter table public.srs_records add column if not exists interval_days integer not null default 1;
alter table public.srs_records add column if not exists repetitions integer not null default 0;
alter table public.srs_records add column if not exists score integer;
alter table public.srs_records add column if not exists next_review_at timestamptz;
alter table public.srs_records add column if not exists created_at timestamptz not null default now();
alter table public.srs_records add column if not exists updated_at timestamptz not null default now();
alter table public.srs_records add column if not exists concept_id text;
alter table public.srs_records add column if not exists node_id text;

-- 3) concept_id NOT NULL only when safe (skip if you still have NULL concept_ids).
-- alter table public.srs_records alter column concept_id set not null;

-- 4) Upsert needs UNIQUE (student_id, concept_id). If missing:
--    alter table public.srs_records add constraint srs_records_student_concept_unique
--      unique (student_id, concept_id);

-- 5) Legacy tables: node_id NOT NULL while the app only upserts concept_id (same Neo4j id).
--    Backfill, then allow NULL so inserts match backend/srs.py.
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'srs_records' and column_name = 'node_id'
  ) then
    update public.srs_records
    set node_id = concept_id
    where node_id is null and concept_id is not null;
    alter table public.srs_records alter column node_id drop not null;
  end if;
end $$;
