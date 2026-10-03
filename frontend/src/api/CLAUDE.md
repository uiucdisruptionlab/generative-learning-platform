# API Layer

This folder is the only place that talks to the backend. Each file reads `VITE_API_URL` (default `http://localhost:8000`) and exports typed functions; pages and components import those and never call `fetch` themselves.

The exported types mirror the backend's JSON by hand. When an endpoint's shape changes in `backend/server.py`, change the type here in the same commit, because nothing generates or validates them.

`onboarding.ts` consumes a server-sent event stream (`/chat/stream`) through an async generator. Other endpoints are plain request/response.
