-- Migration: add student_courses table and course_id to roadmap_position
-- Step 2 & 3 from the course-scoping fix.

-- ─── student_courses ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS student_courses (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id  uuid        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  course_id   text        NOT NULL,
  enrolled_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (student_id, course_id)
);

-- Seed one row per persona (idempotent via ON CONFLICT DO NOTHING)
INSERT INTO student_courses (student_id, course_id) VALUES
  ('a0000001-0000-4000-8000-000000000001', 'python'),
  ('b0000002-0000-4000-8000-000000000002', 'MATH416'),
  ('c0000003-0000-4000-8000-000000000003', 'ALecFinal')
ON CONFLICT (student_id, course_id) DO NOTHING;

-- Verify
SELECT s.name, sc.course_id
FROM student_courses sc
JOIN students s ON s.id = sc.student_id;

-- ─── roadmap_position: add course_id and update PK ──────────────────────────
ALTER TABLE roadmap_position
  ADD COLUMN IF NOT EXISTS course_id text NOT NULL DEFAULT '';

ALTER TABLE roadmap_position
  DROP CONSTRAINT IF EXISTS roadmap_position_pkey;

ALTER TABLE roadmap_position
  ADD PRIMARY KEY (student_id, course_id);
