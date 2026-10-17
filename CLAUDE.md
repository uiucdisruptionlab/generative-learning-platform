## Project Overview

**Generative Learning Platform (GLP)** - An AI-enhanced educational platform for personalized learning paths, currently focused on Financial Accounting content.

- `frontend/` - React + Vite + Tailwind app. See `frontend/CLAUDE.md`.
- `backend/` - FastAPI app that builds roadmaps and generates lessons. See `backend/CLAUDE.md`.

## Cross-workspace contract

The frontend talks to the backend over HTTP only, at `VITE_API_URL` (default `http://localhost:8000`). The backend's CORS allowlist accepts `http://localhost:5173` and `http://127.0.0.1:5173` only, so the Vite dev server stays on port 5173.

When an endpoint's request or response shape changes, update the matching TypeScript types in `frontend/src/api/` in the same change. Nothing generates them.

## Environment Variables

`.env` files hold service credentials (AWS, OpenAI, Pinecone, Neo4j, Supabase, YouTube). Never commit them.

## Pull requests and issues

Every pull request body follows `.github/pull_request_template.md`: fill in all four sections and keep the headings. GitHub applies the template only when a pull request is opened in the browser, so when opening one from the command line, pass the template as the body and fill it in. Every issue follows `.github/ISSUE_TEMPLATE.md` in the same way.

## CI

`.github/workflows/lint.yml` runs on every pull request and on pushes to `main`: Ruff on `backend/`, and ESLint plus `tsc --noEmit` on `frontend/`. Run the same commands locally before pushing (`ruff check .`, `npm run lint`, `npm run typecheck`). The Ruff version is pinned in the workflow; bump it there when upgrading.

## Living documentation

This project uses per-folder CLAUDE.md files. After any session where you introduce a new
module, dependency, or architectural convention, update the CLAUDE.md closest to where the
change lives - not this file unless the change is project-wide. Write what a future agent
could not derive from reading the code: rules, boundaries, ownership decisions.
