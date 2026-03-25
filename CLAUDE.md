
## Project Overview

**Generative Learning Platform (GLP)** - An AI-enhanced educational platform for personalized learning paths, currently focused on Financial Accounting content. The project is in early development with a functional frontend and sample backend code demonstrating AWS Bedrock integration.

## Development Commands

All commands should be run from the `frontend/` directory:

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start development server (http://localhost:5173)
```

**Note**: No backend server exists yet. All API calls are mocked in `frontend/src/api/`.

## Design System

Custom Tailwind configuration in `tailwind.config.js`:

- **Primary Color**: Forest green (`#2c5926`) - used for primary actions
- **Canvas Green**: `#287D3C` - Canvas LMS brand color
- **Secondary**: Warm yellow/amber tones for highlights
- **Accent**: Burnt orange (`#cc5500`) for CTAs
- **Typography**: DM Sans (headings), Inter/Lexend (body)
- **Icons**: Material Symbols Outlined from Google Fonts
- **Dark Mode**: Class-based (`dark:` prefix), toggled via AppLayout

Use semantic color names (`bg-primary`, `text-canvas-green`) rather than arbitrary values to maintain consistency.



## Important Notes for Development

1. **No Backend**: All API calls in `src/api/` are mocked. When building the backend, maintain the same TypeScript interfaces but replace mock implementations with real HTTP calls.

2. **Module Pattern**: Use `IncomeStatementPage.tsx` as a template when creating new learning modules. Maintain consistent structure: concept explanation, quiz, practice problems, resources.

4. **TypeScript Strict Mode**: Enabled in `tsconfig.json`. Unused variables will cause build errors. Keep code clean.

5. **Vite Build Tool**: Very fast HMR. Uses ES modules. No webpack config needed. Port 5173 by default.


7. **Learning Roadmap Data**: Hardcoded in `LearningRoadmap.tsx`. Should be moved to API/database when backend is implemented.

8. **Environment Variables**: `.env` contains AWS credentials. Never commit this file. Create `.env.example` for team reference.

## Workflow

1. Whenever making changes in the frontend, you **MUST** make sure to ALWAYS follow the design theme.

2. If making changes in the backend, make sure to run the relevant command and verify the output.