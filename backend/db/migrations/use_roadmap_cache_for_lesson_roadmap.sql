-- Migration: reuse the existing `roadmap_cache` table for the lecture-grouped,
-- LLM-refined lesson roadmap. Assumes one course per student, so caching by
-- student_id is equivalent to caching by course (and avoids a new table).

-- Drop the short-lived table from the previous attempt.
DROP TABLE IF EXISTS course_lesson_roadmaps CASCADE;

-- Wipe the existing rows: they're in the old `[uuid, uuid, ...]` shape and
-- the column type itself is changing below.
DELETE FROM roadmap_cache;

-- The column was originally typed as `jsonb[]` (a postgres array of jsonb)
-- which rejects our top-level dict payload. Switch it to plain `jsonb` so we
-- can store {course_id, lessons[], node_ids[], ...} as a single document.
ALTER TABLE roadmap_cache
  ALTER COLUMN roadmap DROP NOT NULL;
ALTER TABLE roadmap_cache
  ALTER COLUMN roadmap TYPE jsonb USING NULL::jsonb;
ALTER TABLE roadmap_cache
  ALTER COLUMN roadmap SET NOT NULL;

COMMENT ON COLUMN roadmap_cache.roadmap IS
  'Lecture-grouped, LLM-refined lesson roadmap for the student''s enrolled course. '
  'Shape: { course_id, lesson_count, lessons[{lesson_id,title,summary,concepts[],lecture_ids[]}], node_ids[] }.';

-- Make student_id the cache key so we can upsert cleanly. Idempotent.
ALTER TABLE roadmap_cache
  DROP CONSTRAINT IF EXISTS roadmap_cache_student_id_unique;
ALTER TABLE roadmap_cache
  ADD CONSTRAINT roadmap_cache_student_id_unique UNIQUE (student_id);
