-- Add lesson_id to srs_records so concept SRS scores can be aggregated per-lesson.
-- Used by the gate check: avg(score) WHERE lesson_id = prev_lesson_id must be >= 3.0
-- to unlock the next lesson.

ALTER TABLE public.srs_records ADD COLUMN IF NOT EXISTS lesson_id text;

CREATE INDEX IF NOT EXISTS idx_srs_records_student_lesson
  ON public.srs_records (student_id, lesson_id);
