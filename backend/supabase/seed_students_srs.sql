-- Sample srs_records for students in seed_students.sql. Run after students are inserted.
-- concept_id matches backend/lesson_loop.py __main__ demo titles (Variables, Loops, Functions).
-- Idempotent per (student_id, concept_id). Requires create_srs_records.sql / ensure_srs_records_schema.sql.

insert into srs_records (
  student_id,
  concept_id,
  node_id,
  ease_factor,
  interval_days,
  repetitions,
  score,
  next_review_at
) values
-- Alice — mix of overdue and future reviews
(
  'a0000001-0000-4000-8000-000000000001',
  'Variables',
  'Variables',
  2.50,
  1,
  1,
  4,
  timezone('utc', now()) - interval '2 days'
),
(
  'a0000001-0000-4000-8000-000000000001',
  'Loops',
  'Loops',
  2.60,
  6,
  2,
  3,
  timezone('utc', now()) + interval '3 days'
),
(
  'a0000001-0000-4000-8000-000000000001',
  'Functions',
  'Functions',
  2.36,
  1,
  0,
  2,
  timezone('utc', now()) + interval '1 day'
),
-- Bob — stronger ease, one concept overdue
(
  'b0000002-0000-4000-8000-000000000002',
  'Variables',
  'Variables',
  2.70,
  6,
  2,
  5,
  timezone('utc', now()) - interval '1 day'
),
(
  'b0000002-0000-4000-8000-000000000002',
  'Loops',
  'Loops',
  2.50,
  1,
  1,
  4,
  timezone('utc', now()) + interval '5 days'
),
(
  'b0000002-0000-4000-8000-000000000002',
  'Functions',
  'Functions',
  2.50,
  1,
  0,
  3,
  timezone('utc', now()) + interval '12 hours'
),
-- Charles — retrieval-focused profile; staggered schedule
(
  'c0000003-0000-4000-8000-000000000003',
  'Variables',
  'Variables',
  2.50,
  1,
  0,
  3,
  timezone('utc', now()) - interval '12 hours'
),
(
  'c0000003-0000-4000-8000-000000000003',
  'Loops',
  'Loops',
  2.42,
  1,
  1,
  4,
  timezone('utc', now()) + interval '2 days'
),
(
  'c0000003-0000-4000-8000-000000000003',
  'Functions',
  'Functions',
  2.50,
  6,
  2,
  5,
  timezone('utc', now()) + interval '7 days'
)
on conflict (student_id, concept_id) do nothing;
