# lesson-loop-patch Branch — Merge Guide & Technical Reference

This document covers everything merged into `lesson-loop-patch` so you can merge safely and continue building on top of it. The primary deliverable of this branch is a **working end-to-end Spaced Repetition System (SRS)** wired into the interactive lesson loop.

---

## Table of Contents

1. [What This Branch Does](#1-what-this-branch-does)
2. [Files Changed](#2-files-changed)
3. [How the SRS Works](#3-how-the-srs-works)
4. [How the Interactive Lesson Loop Works](#4-how-the-interactive-lesson-loop-works)
5. [API Endpoints Added / Changed](#5-api-endpoints-added--changed)
6. [Key Bugs Fixed](#6-key-bugs-fixed)
7. [Environment Variables](#7-environment-variables)
8. [Running the Backend](#8-running-the-backend)
9. [Next Steps — Quality Student Responses](#9-next-steps--quality-student-responses)

---

## 1. What This Branch Does

Before this branch the lesson generation was a static one-shot call: hit `/lesson/{id}`, get back a JSON blob, display it. There was no memory of whether a student had seen a lesson before, no way to adapt difficulty on repeat visits, and no persistence of session state.

This branch adds:

- **SM-2 Spaced Repetition** (`backend/srs.py`) — every time a student completes a lesson, their score is written to `srs_records` in Supabase and the SM-2 algorithm schedules the next review.
- **Adaptive lesson content** — when a student revisits a lesson, the LLM prompt includes their prior score, ease factor, specific gaps, and specific strengths from the last attempt so the generated lesson adapts accordingly.
- **Interactive / dynamic lesson loop** (`backend/dynamic_lesson.py`) — a stateful, multi-turn teaching session. The tutor walks the student through three segments (concept → example → summary), running interactive checkpoints with MCQ, flashcard, free-response, or video widgets between each segment.
- **Session persistence** (`lesson_sessions` table) — when an interactive session reaches "complete," the full transcript and a performance verdict are written to Supabase.
- **Roadmap position tracking** — passing a lesson advances the student's position in the roadmap and marks the lesson complete in their `llm_profile`.

---

## 2. Files Changed

| File | What changed |
|---|---|
| `backend/srs.py` | Full SM-2 implementation. Covers `run_sm2`, `upsert_srs_record`, `get_srs_record`, `get_due_srs_records`, `advance_roadmap_progress`, `get_roadmap_position`, `set_roadmap_position`, `advance_roadmap_index`. |
| `backend/lesson_generator.py` | Added `load_lesson_sources()` (shared source bundle used by both static and interactive lesson), SRS record lookup before generation, and `_build_srs_context()` which formats prior performance into the LLM prompt. Also fixed Pinecone namespace resolution to try multiple candidate namespaces instead of failing on the first miss. |
| `backend/dynamic_lesson.py` | New file. Contains the entire interactive lesson loop — session creation, stage machine, LLM calls for overview / step / engage / closing / checkpoint-help, widget resolution, and `_save_session_to_db()`. |
| `backend/server.py` | Added `/lesson/interactive/start`, `/lesson/interactive/tick`, `/lesson/interactive/session/{id}`, `/lesson/interactive/widget`, `/srs/due`, `/srs/due/{student_id}`, `/lesson_history/{student_id}`, `/lesson_session/{session_id}`, `/roadmap_position/{student_id}`, `/roadmap/generate/{student_id}`, `/student/{student_id}`, `/student/{student_id}/courses`. Also wired SRS into `/lesson/score`. `adaptive_session.py`, `lesson_loop.py`, and `personas.py` were deleted — their logic now lives in `dynamic_lesson.py` and `srs.py`. |
| `backend/graphdb/roadmap_builder.py` | Minor update to lesson roadmap building (LLM-refined, per-student cached in Supabase `roadmap_cache` table). |
| `backend/youtube/client.py` | Minor fix for YouTube search error handling. |
| `frontend/src/api/interactiveLesson.ts` | API client for the interactive lesson loop (`startInteractiveLesson`, `tickInteractiveLesson`). |
| `frontend/src/pages/InteractiveLessonPage.tsx` | Frontend for the interactive lesson flow — transcript display, widget rendering (MCQ / flashcards / free-response / video), stage-aware UI. |
| `frontend/src/pages/RoadmapPage.tsx` | Uses `/roadmap/generate/{student_id}` instead of the old static endpoint. |
| `frontend/src/pages/HomePage.tsx` | Minor cleanup. |

**Deleted files** (do not try to restore them — logic was merged into other modules):
- `backend/adaptive_session.py`
- `backend/lesson_loop.py`
- `backend/personas.py`

---

## 3. How the SRS Works

### Algorithm — SM-2

`backend/srs.py` is the canonical SRS module. It implements SuperMemo SM-2:

- **Score** (0–5): `PASSING_SCORE = 3`. Below 3 resets repetitions to 0 and schedules review for tomorrow.
- **Ease factor**: starts at 2.5. Adjusted up or down based on score. Floor is 1.3. A low ease factor (< 1.8) means the student is struggling with this concept.
- **Interval**: 1 day → 6 days → `previous_interval × ease_factor` (exponential growth on each successive pass).

### Data flow

```
Student answers a question
         │
         ▼
POST /lesson/score
  - LLM grades the response (0–5)
  - calls upsert_srs_record()
      - fetches previous srs_records row (if any)
      - runs run_sm2(score, previous)
      - writes ease_factor, interval_days, repetitions,
        next_review_at, last_gaps, last_strengths back to Supabase
  - if score >= PASSING_SCORE:
      - calls advance_roadmap_progress() (marks lesson complete in llm_profile)
      - calls set_roadmap_position() (advances flat index for roadmap UI)
```

### How it feeds back into lesson generation

When `GET /lesson/{id}` or `POST /lesson/interactive/start` is called, `load_lesson_sources()` in `lesson_generator.py` does:

1. Looks up the student's `srs_records` row for this `lesson_id`.
2. Calls `_build_srs_context()` which converts the SRS record into a natural-language directive:
   - `ease_factor < 1.8` or `score < 3` → **"Remediate — use simpler language, more concrete examples, rebuild from first principles."**
   - `ease_factor >= 2.8` and `score >= 4` → **"Go deeper, introduce nuance, test edge cases."**
   - Otherwise → **"Reinforce core concepts, address gaps."**
3. If `last_gaps` or `last_strengths` are recorded, those are appended verbatim to the directive.
4. This context block is injected into the LLM system prompt under `PRIOR PERFORMANCE ON THIS LESSON`.

The static lesson endpoint (`GET /lesson/{id}`) also bypasses the disk cache when SRS history exists — it always regenerates a fresh adapted lesson.

---

## 4. How the Interactive Lesson Loop Works

`backend/dynamic_lesson.py` owns the entire stateful session lifecycle. Sessions are stored in-memory in `_SESSIONS` (a dict, max 200 entries, LRU-pruned). They are persisted to `lesson_sessions` in Supabase when the session reaches `complete`.

### Stage machine

Each session moves through a fixed list of stages:

```
after_overview_confirm
  step0_content_llm       ← LLM generates concept segment
  reflect_step0_user      ← student reflects (free text)
  widget_step0_user       ← interactive activity (MCQ / flashcard / etc.)
  confirm_step0_user      ← checkpoint: ready to continue?
  step1_content_llm
  reflect_step1_user
  widget_step1_user
  confirm_step1_user
  step2_content_llm
  reflect_step2_user
  widget_step2_user
  confirm_step2_user
  closing_llm
  complete
```

**LLM stages** (`*_llm`) run automatically without user input. **User stages** (`*_user`) block until the frontend calls `POST /lesson/interactive/tick`.

### Starting a session — `POST /lesson/interactive/start`

```json
{ "lesson_id": "lesson_abc", "persona": "charles", "course": null }
```

- Calls `load_lesson_sources()` to get Pinecone chunks, YouTube videos, and the SRS record.
- If an SRS record exists (student has done this lesson before), immediately generates a **prior performance recap** that names the student's last score, specific gaps, and what they did well.
- Generates the lesson overview.
- Returns `session_id`, `stage`, `transcript`, `pending_widget`, `awaiting` ("confirm" | "text" | "widget" | "none").

### Advancing — `POST /lesson/interactive/tick`

```json
{
  "session_id": "...",
  "message": "ok got it",       // text from learner
  "action": null,               // "confirm_yes" | "confirm_not_yet" (optional shortcut)
  "widget_result": null         // submit MCQ/flashcard result when at a widget stage
}
```

The session handles:
- **Checkpoint confirm stages**: LLM classifies intent ("continue", "need_help", "request_activity", "exit", "unknown"). If the student asks for help, it runs a clarification LLM call without advancing. If they want another activity (e.g., "give me a flashcard"), it generates one on the spot.
- **Reflect stages**: runs `_run_engage_llm()` which reacts to the student's reflection and generates an interactive activity. If the reflection is fewer than 40 words, it forces a free-response fallback question.
- **Widget stages**: accepts the `widget_result` JSON (e.g., `{"selected_index": 2, "correct": true}`), logs it to `activity_history`, then advances.
- **Exit intent**: at any user stage, if the student says "I'm done", "exit", etc., a graceful summary is generated and the session closes immediately.

### Session performance scoring

At the closing stage, `_session_performance_summary()` tallies all widget results:
- MCQ: correct/incorrect based on `selected_index` vs `correct_index`.
- Flashcards / free_response / video: counted as "engaged" (not incorrect) if not skipped.
- **Verdict**: `strong` (≥ 75% correct), `mixed` (≥ 40%), `repeat_recommended` (< 40% or all skipped).

The closing LLM message is explicitly told to be honest about the verdict — "repeat_recommended" sessions tell the student directly they should redo the lesson.

### Context-aware Pinecone retrieval

Instead of passing all chunks to every LLM call, `_pick_context_chunks()` scores each Pinecone entry by token overlap with a `focus_query` built from the current stage (lesson title + concept names for overview, step type + concepts for each segment, reflection text for engage). This keeps prompts focused and under the `MAX_SOURCE_CHARS = 14,000` limit.

---

## 5. API Endpoints Added / Changed

| Method | Path | Description |
|---|---|---|
| `POST` | `/lesson/interactive/start` | Start an interactive session. Body: `{lesson_id, persona, course}` |
| `POST` | `/lesson/interactive/tick` | Advance session. Body: `{session_id, message?, action?, widget_result?}` |
| `GET` | `/lesson/interactive/session/{session_id}` | Get current session state |
| `POST` | `/lesson/interactive/widget` | Imperatively enqueue a widget (for testing) |
| `POST` | `/lesson/score` | Grade a student response (0–5 via LLM), write SRS record, advance roadmap if passed |
| `GET` | `/srs/due` | Due SRS records for a student (`?persona=charles` or `?student_id=...`) |
| `GET` | `/srs/due/{student_id}` | Upcoming reviews in next 7 days |
| `GET` | `/lesson_history/{student_id}` | List completed sessions (no transcript). `?concept_id=` filter supported |
| `GET` | `/lesson_session/{session_id}` | Full session record including transcript |
| `GET` | `/roadmap_position/{student_id}` | Current flat roadmap index |
| `GET` | `/roadmap/generate/{student_id}` | Lesson roadmap with per-concept state (active/completed/locked) |
| `GET` | `/roadmap/{student_id}` | Alias for above |
| `POST` | `/roadmap/{student_id}/rebuild` | Force a fresh roadmap rebuild |
| `GET` | `/student/{student_id}` | Raw student profile |
| `GET` | `/student/{student_id}/courses` | Enrolled courses for a student |
| `GET` | `/lesson/{lesson_id}` | **Changed**: bypasses cache when SRS history exists |

---

## 6. Key Bugs Fixed

### SRS not persisting after lesson completion
The original `lesson_loop.py` called `upsert_srs_record` but was passing `node_id` to a function that expected `concept_id` as the primary key for upserts. The unique constraint `(student_id, concept_id)` was never matching, so every call was inserting a new row instead of updating. Fixed in `srs.py` by normalizing `concept_id = concept_id or node_id` before the upsert and setting both `concept_id` and `node_id` in the row.

### `interval` column name conflict
PostgreSQL reserves `interval` as a keyword. The original migration created the column named `interval` which caused silent failures when PostgREST validated the payload. Renamed to `interval_days` throughout.

### One PGRST204 error at a time
PostgREST reports only the first unknown column per request. Early testing showed the error appearing to "move" — fix `last_reviewed_at`, next request fails on `course`, etc. The `ensure_srs_records_schema.sql` migration adds all columns at once and is idempotent.

### Lesson cache bypass not working
The `/lesson/{id}` endpoint was returning the cached lesson even for students with SRS history (which would mean the adaptive content was never shown). Fixed by calling `_student_has_srs_history()` before returning the cache — if it returns `True`, the lesson is always regenerated fresh.

### Pinecone namespace misses
`lesson_generator.py` was trying a single hardcoded namespace and returning empty chunks on any miss, causing the LLM to get no source material. Fixed with `_candidate_namespaces()` which builds a priority-ordered list: env override → course mapping → `lecture_ids` from the lesson node → chunk ID prefix extraction → default namespace. It tries each until it gets results.

### `adaptive_session.py` / `lesson_loop.py` file conflict
Both files were partially overlapping with `dynamic_lesson.py`. Keeping all three caused import confusion. `adaptive_session.py` and `lesson_loop.py` were deleted; all logic now lives in `dynamic_lesson.py`.

---

## 7. Next Steps — Quality Student Responses

The next feature is ensuring students can't game the system with lazy or copy-pasted answers. Here is where to make those changes:

### Where responses are evaluated

All student responses flow through `_score_lesson_response()` in `backend/server.py` (lines 659–714). This is the function that calls Bedrock and returns a 0–5 score, explanation, strengths list, and gaps list. This is the right place to add quality checks.

The LLM system prompt for scoring is the string literal at lines 660–679:
```python
system_prompt = """You score learner knowledge-check responses for a spaced repetition system.
...
0 = blank, irrelevant, or no evidence of understanding.
...
Only give 3 or higher when the learner demonstrates the central concept."""
```

### Detecting copy-paste / lazy responses

**Option A — Add a pre-check before the LLM call.** In `score_lesson_response()` (around line 739), before calling `_score_lesson_response()`, run a heuristic check.


**Option B — Add instructions to the scoring LLM prompt.** Extend the `system_prompt` in `_score_lesson_response()` to include:

```
If the learner response appears to be copied verbatim or near-verbatim from the reference answer,
or is a single-word/single-phrase response with no explanation, score it 1 or lower regardless of correctness.
A response demonstrates understanding only when explained in the learner's own words with reasoning.
```

### Making the LLM repeat questions for lazy answers

In `_run_engage_llm()` in `dynamic_lesson.py` (around line 761), the engage prompt already has a fallback that forces a `free_response` when the reflection is under 40 words:

```python
# Fallback: if the LLM chose none but the reflection is brief, force a free_response check.
if itype == "none" and len(reflection.split()) < 40:
    ...
    itype = "free_response"
    payload = {"question": fallback_q}
```

To make this more aggressive:
1. Increase the word threshold (e.g., `< 60`).
2. Add a check for low-effort phrases: `"i don't know"`, `"idk"`, `"not sure"` — these should trigger the tutor to re-ask with a scaffold rather than moving on.
3. In the engage system prompt (around line 768), add an instruction: **"If the learner's reflection is a single sentence or shows no engagement with the material (e.g., 'idk', 'not sure', one-word answers), do NOT accept it. Instead, ask them to try again with a specific prompt — name one idea from the segment and ask them to explain it."**

### Where the reflect stage processes input

The reflect stage is handled in `tick_session()` in `dynamic_lesson.py` around line 1391:

```python
elif stage.startswith("reflect_"):
    if not text_msg:
        raise ValueError("Reflection text is required for this stage.")
    step_i = _current_step_index(stage)
    _append_user(session, text_msg)
    session["cursor"] += 1
    engage = _run_engage_llm(session, step_i, text_msg)
```

Before the `session["cursor"] += 1` line is a natural place to intercept lazy responses and either reject the reflection or flag it for `_run_engage_llm` to handle differently.

### Free-response scoring in the interactive loop

The interactive loop currently does not call `/lesson/score` — it uses `_session_performance_summary()` which only tracks MCQ correctness (widget results). Free-response reflections are counted as "engaged" even if the content is weak. To close this gap, you could call `_score_lesson_response()` on the reflection text at the reflect stage and use that score to influence the engage LLM's directive.
