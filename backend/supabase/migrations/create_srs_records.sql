-- srs_records: spaced repetition state per student + Neo4j concept node (concept_id is text, not content_items.id).
-- Run in Supabase SQL editor or via your migration runner.

create table if not exists srs_records (
  id              uuid primary key default gen_random_uuid(),
  student_id      uuid not null references students (id) on delete cascade,
  concept_id      text not null,
  ease_factor     float not null default 2.5,
  interval        int not null default 1,
  repetitions     int not null default 0,
  score           int check (score between 0 and 5),
  next_review_at  timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (student_id, concept_id)
);
