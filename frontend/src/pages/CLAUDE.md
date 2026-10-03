# Pages

One file per route; routes are registered in `src/App.tsx`. A page owns its data fetching (through `src/api/`) and its loading and error states, and gets the current student from `usePersona()`.

`InteractiveLessonPage` drives the lesson as a state machine held by the backend: it sends a tick or a widget result and renders whatever state comes back. Do not advance lesson stages on the client.
