-- lesson_sessions: read-only history of completed adaptive lesson sessions.
-- One row per session_id. Stores the conversation transcript so a student can
-- revisit a past lesson and see the message log without re-running the loop.
--
-- Safe to run repeatedly in the Supabase SQL editor.

create table if not exists public.lesson_sessions (
  session_id    uuid primary key,
  student_id    uuid not null references public.students (id) on delete cascade,
  course_id     text not null,
  lesson_id     text,
  concept_id    text not null,
  concept_name  text,
  mode          text,
  score         integer check (score between 0 and 5),
  passed        boolean not null default false,
  transcript    jsonb not null default '[]'::jsonb,
  metadata      jsonb,
  started_at    timestamptz,
  completed_at  timestamptz not null default now()
);

create index if not exists idx_lesson_sessions_student_concept
  on public.lesson_sessions (student_id, concept_id, completed_at desc);

create index if not exists idx_lesson_sessions_student_completed
  on public.lesson_sessions (student_id, completed_at desc);

comment on table public.lesson_sessions is
  'Persisted read-only record of a completed adaptive lesson session. One row per session_id; '
  'transcript is the full message log captured by adaptive_session.complete_lesson.';
