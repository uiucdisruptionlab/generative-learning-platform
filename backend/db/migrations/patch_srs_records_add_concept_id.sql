-- Run this in the SQL Editor for the SAME Supabase project as SUPABASE_URL in .env.
-- Fixes PostgREST error: column srs_records.concept_id does not exist (42703).
-- Safe if the column already exists.

alter table public.srs_records add column if not exists concept_id text;

-- If you added NOT NULL / unique later, backfill existing rows first, then:
--   alter table public.srs_records alter column concept_id set not null;
--   alter table public.srs_records add constraint srs_records_student_concept_unique unique (student_id, concept_id);

-- Optional (if PostgREST seems stale): notify pgrst, 'reload schema';
