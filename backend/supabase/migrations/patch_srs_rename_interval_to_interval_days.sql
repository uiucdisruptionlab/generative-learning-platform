-- Fixes PostgREST PGRST204: Could not find the 'interval' column ...
-- SQL reserves "interval" as a type name; the API column is now interval_days (matches srs.py).

alter table public.srs_records add column if not exists interval_days int not null default 1;

-- Only if psql \\d srs_records shows a quoted column literally named "interval":
-- alter table public.srs_records rename column "interval" to interval_days;
