# Contexts

`PersonaContext` is the single source of the current student. Read `studentId` from `usePersona()` instead of resolving a persona to an id yourself, so every page agrees on who is signed in.

The selected persona is held in React state only, so it resets to the default on a full page reload.
