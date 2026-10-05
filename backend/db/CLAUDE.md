
# Database (Supabase)

`supabase_client.py` is the only module that creates the Supabase client; everything else imports `get_supabase_client` and `get_student_profile` from `db.supabase_client`. It loads the repo-root `.env` first and then `backend/.env`, which overrides it.

`migrations/` are plain SQL files; this repo has no migration runner and the file names carry no ordering. Write each one so it is safe to run twice (`IF NOT EXISTS`), and add a new file instead of editing one that has been applied.

The demo student UUIDs in `seed_students.sql` are also hardcoded in `frontend/src/auth/studentIdentity.ts`.
