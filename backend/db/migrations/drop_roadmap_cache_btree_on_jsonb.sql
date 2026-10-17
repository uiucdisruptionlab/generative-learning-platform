-- Migration: drop the btree index on roadmap_cache.roadmap (jsonb).
--
-- The legacy index `idx_roadmap_cache_node_ids` btree-indexes the entire
-- `roadmap` jsonb document. Btree entries cap at ~2704 bytes, so any roadmap
-- whose serialized form exceeds that cannot be inserted/updated:
--
--   ERROR: index row size 2888 exceeds btree version 4 maximum 2704
--          for index "idx_roadmap_cache_node_ids"
--
-- The application catches and logs this on write, which silently disables the
-- cache and forces a full rebuild on every read. The index is not used by any
-- query path. Drop it.
--
-- Also tighten `student_id` to NOT NULL since the unique constraint and our
-- upserts both key on it.

DROP INDEX IF EXISTS public.idx_roadmap_cache_node_ids;

ALTER TABLE public.roadmap_cache
  ALTER COLUMN student_id SET NOT NULL;
