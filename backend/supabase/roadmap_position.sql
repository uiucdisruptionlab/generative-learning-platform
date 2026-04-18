-- Migration: Add roadmap_position table
-- Run this in Supabase SQL editor to create the roadmap_position table

create table if not exists roadmap_position (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references students(id) on delete cascade not null,
  current_index integer not null default 0,
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

create trigger update_roadmap_position_updated_at
  before update on roadmap_position
  for each row execute function update_updated_at_column();

-- Add indexes for performance
create index if not exists idx_roadmap_position_current_index on roadmap_position(current_index);