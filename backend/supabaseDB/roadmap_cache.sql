-- Migration: Add roadmap_cache table
-- Run this in Supabase SQL editor to create the roadmap_cache table

create table if not exists roadmap_cache (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references students(id) on delete cascade not null,
  node_ids text[] not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add indexes for performance
create index if not exists idx_roadmap_cache_node_ids on roadmap_cache(node_ids);