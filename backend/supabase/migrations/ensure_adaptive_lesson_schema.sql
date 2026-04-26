-- Adaptive lesson loop state from ARCHITECTURE.md.
-- Safe to run repeatedly in the Supabase SQL editor.

create table if not exists public.roadmap_position (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students (id) on delete cascade,
  current_index integer not null default 0,
  updated_at timestamptz not null default now(),
  unique (student_id)
);

alter table public.srs_records add column if not exists concept_id text;
alter table public.srs_records add column if not exists node_id text;
alter table public.srs_records add column if not exists last_score integer;
alter table public.srs_records add column if not exists attempts integer not null default 0;
alter table public.srs_records add column if not exists last_reviewed_at timestamptz;

update public.srs_records
set concept_id = node_id
where concept_id is null and node_id is not null;

update public.srs_records
set node_id = concept_id
where node_id is null and concept_id is not null;

update public.srs_records
set last_score = score
where last_score is null and score is not null;

update public.srs_records
set attempts = repetitions
where attempts = 0 and repetitions is not null and repetitions > 0;

-- Run manually if your database does not already have this constraint:
-- alter table public.srs_records
--   add constraint srs_records_student_concept_unique unique (student_id, concept_id);
