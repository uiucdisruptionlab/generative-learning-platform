-- Seed students for local / staging tests. Run in Supabase SQL editor after schema exists.
-- Fixed UUIDs let backend/supabase_client.py demo target Alice without a lookup.
-- Already applied to Supabase. Run only if resetting the database.

insert into students (
  id,
  name,
  academic_level,
  major_or_field,
  learning_goals,
  interests,
  weekly_hours,
  preferred_formats,
  llm_profile
) values
(
  'a0000001-0000-4000-8000-000000000001',
  'Alice',
  'Undergraduate',
  'Finance + Data Science',
  '{
    "primary_focus": "Learn Python fundamentals",
    "coding_experience": "beginner",
    "target_course": "Introduction to Computer Science and Programming in Python"
  }'::jsonb,
  '[
    "programming",
    "python",
    "data science",
    "finance"
  ]'::jsonb,
  5,
  '["videos", "hands-on problems", "practice exercises"]'::jsonb,
  '{
    "learning_style_summary": "Beginner coder; responds well to video instruction and hands-on practice.",
    "subject_confidence": "beginner",
    "notes": "Learning Python fundamentals with a focus on applying them to finance and data science."
  }'::jsonb
),
(
  'b0000002-0000-4000-8000-000000000002',
  'Bob',
  'Undergraduate',
  'Business',
  '{
    "primary_focus": "Economic development and public finance",
    "topic_familiarity": "very_familiar"
  }'::jsonb,
  '[
    "economic development",
    "public policy",
    "finance",
    "business"
  ]'::jsonb,
  2,
  '["reading", "worked examples", "AI interaction"]'::jsonb,
  '{
    "learning_style_summary": "Very familiar with the subject; prefers reading, concrete examples, and conversational AI support.",
    "subject_confidence": "comfortable",
    "notes": "Studying financing and economic development with strong prior knowledge of the topic."
  }'::jsonb
),
(
  'c0000003-0000-4000-8000-000000000003',
  'Charles',
  'Undergraduate',
  'Accounting',
  '{
    "primary_focus": "Financial and managerial accounting foundations",
    "coding_experience": "not_primary"
  }'::jsonb,
  '[
    "financial accounting",
    "managerial accounting",
    "business",
    "finance"
  ]'::jsonb,
  10,
  '["flashcards", "practice questions"]'::jsonb,
  '{
    "learning_style_summary": "Prefers retrieval practice via flashcards and targeted practice questions.",
    "subject_confidence": "somewhat_familiar",
    "notes": "Building foundations in financial and managerial accounting through active recall."
  }'::jsonb
)
on conflict (id) do nothing;

-- SRS sample rows: backend/supabase/seed_students_srs.sql (run after this file).