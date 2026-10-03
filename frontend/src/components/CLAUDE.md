# Components

Shared, presentational pieces. Components take data through props and do not import from `src/api/`; the page that renders them does the fetching.

`AppLayout` wraps every signed-in page and owns the sidebar and dark-mode chrome, so new pages render inside it instead of building their own shell.

The interactive lesson's widgets (MCQ, flashcards, free response, video) are defined inside `pages/InteractiveLessonPage.tsx`, not in this folder. Their props follow the payload types in `src/api/interactiveLesson.ts`.
