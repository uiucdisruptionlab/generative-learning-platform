-- Migration: Create students table
-- This table stores student profile information

create table if not exists students (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  academic_level text,
  major_or_field text,
  learning_goals jsonb,
  interests text[],
  weekly_hours integer,
  preferred_formats text[],
  llm_profile jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add updated_at trigger
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = timezone('utc'::text, now());
  return new;
end;
$$ language 'plpgsql';

create trigger update_students_updated_at
  before update on students
  for each row execute function update_updated_at_column();

-- Add indexes for performance
create index if not exists idx_students_name on students(name);
create index if not exists idx_students_major on students(major_or_field);