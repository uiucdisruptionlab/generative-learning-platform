-- Migration: Add srs_records table
-- Run this in Supabase SQL editor to create the srs_records table
-- SRS = Spaced Repetition System for tracking review schedules

create table if not exists srs_records (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references students(id) on delete cascade not null,
  node_id text not null,
  ease_factor real default 2.5 not null,
  interval_days integer default 1 not null,
  next_review_at timestamp with time zone not null,
  last_reviewed_at timestamp with time zone
);

-- Add updated_at trigger
create trigger update_srs_records_updated_at
  before update on srs_records
  for each row execute function update_updated_at_column();

-- Add indexes for performance
create index if not exists idx_srs_records_node_id on srs_records(node_id);
create index if not exists idx_srs_records_next_review on srs_records(next_review_at);
create index if not exists idx_srs_records_last_reviewed on srs_records(last_reviewed_at);