# Frontend

React + Vite + Tailwind. Commands run from this directory:

```bash
npm install          # Install dependencies
npm run dev          # Start development server (http://localhost:5173)
npm run build        # Typecheck, then production build
npm run lint         # ESLint
npm run typecheck    # tsc --noEmit
npm run format:check # Prettier
```

## Design System

Frontend changes follow this design system, so pages stay visually consistent. The tokens live in `tailwind.config.js` (UIUC Illini palette):

- **Primary**: Illini orange (`#FF5F05`, `primary`) - used for primary actions
- **Accent**: Illini blue (`#13294B`, `accent`)
- **Secondary**: `#FCB316` (`secondary`) for highlights
- **Industrial blue**: `#1D58A7` (`industrial`) for outlines and supporting accents
- **Typography**: DM Sans (headings), Inter/Lexend (body)
- **Icons**: Material Symbols Outlined from Google Fonts
- **Dark Mode**: Class-based (`dark:` prefix)

Use semantic color names (`bg-primary`, `text-accent`) rather than arbitrary values.

## Conventions

- All backend calls go through `src/api/`. Pages and components import from there and do not call `fetch` themselves, which keeps the response types in one place.
- TypeScript strict mode is on with `noUnusedLocals` and `noUnusedParameters`, so unused variables fail the build.
