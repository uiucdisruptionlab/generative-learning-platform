# Static Data

Client-side constants and shared view types, not fetched data. Student profiles and roadmaps come from the backend through `src/api/`; do not add course or roadmap content here.

`personas.ts` holds display details for the demo personas only. The backend's copy of each student (Supabase `students`) is the one lessons are personalized from, so a persona edited here does not change lesson content.

`roadmapTypes.ts` holds the roadmap view types that the roadmap components and pages share.
