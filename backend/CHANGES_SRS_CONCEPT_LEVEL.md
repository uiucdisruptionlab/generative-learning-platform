# Backend/Frontend Changes — Concept-Level SRS

## Session Date: 2026-05-02

### Summary
This session replaced the legacy lesson-level SRS system with a concept-level one, added a lesson gate, and added a review session mode that surfaces overdue concepts before a lesson starts.

---

## 1. Database migration

**`backend/supabase/migrations/add_lesson_id_to_srs_records.sql`** (new)

Adds `lesson_id text` to `srs_records` and an index on `(student_id, lesson_id)`. This enables the gate check: `avg(score) WHERE lesson_id = previous_lesson_id`.

Run this in the Supabase SQL editor before deploying the backend changes:
```sql
ALTER TABLE public.srs_records ADD COLUMN IF NOT EXISTS lesson_id text;
CREATE INDEX IF NOT EXISTS idx_srs_records_student_lesson ON public.srs_records (student_id, lesson_id);
```

---

## 2. `backend/srs.py`

**`upsert_srs_record`**: added optional `lesson_id: str | None = None` parameter. When provided, it is stored in the `srs_records` row. The unique constraint remains `(student_id, concept_id)`.

---

## 3. `backend/dynamic_lesson.py`

### New helper functions (added before `_append_assistant`)

| Function | Purpose |
|---|---|
| `_concept_ids_for_step(concepts, step_index)` | Returns Neo4j concept UUIDs assigned to step `i` (same bucketing as the chunk selector) |
| `_score_free_response_llm(question, ref, response)` | Scores a free-response text 0–5 via a compact LLM call |
| `_score_widget_result(widget_type, payload, result)` | Maps a widget submission to a 0–5 SRS quality score (MCQ: 4/2, free_response: LLM, flashcards/video: 3, skipped: 0, dont_know: 1) |
| `_write_srs_for_concepts(session, concept_ids, score, lesson_id=None)` | Upserts SRS records per concept ID; non-fatal on error |
| `_get_lesson_avg_score(student_id, lesson_id, client)` | Queries `avg(score)` from `srs_records` for one lesson |
| `_check_lesson_gate(student_id, lesson_id, roadmap, client)` | Returns gate block info if prev-lesson avg < 3.0, else None |
| `_load_lesson_roadmap_for_student(student_id)` | Reads `roadmap_cache` from Supabase for a student |
| `_build_concept_map(roadmap)` | Builds `concept_id → {name, description}` from all lessons |
| `_run_review_recap_llm(session, concept_index)` | LLM generates a recap + widget (mcq or free_response) for one overdue concept |

### Modified functions

**`_stage_index(name, stages=None)`**: now accepts an optional `stages` list so both lesson and review sessions can use it.

**`_awaiting_for_stage(stage)`**: added `review_widget_\d+_user` → `"widget"`.

**`_response(session)`**: uses `session["stages"]` instead of global `STAGES`; adds `session_type`, `gated_info`, and `review_count` fields to the response.

**`_auto_run_llm_stages(session)`**: uses `session["stages"]`; handles `review_recap_{i}_llm` stages (runs LLM, sets `pending_widget`, advances cursor).

**`start_session(lesson_id, persona_id, course)`**: major changes:
1. Loads the roadmap and checks the lesson gate. If blocked, returns a `session_type = "gated"` response immediately (no session created, no Bedrock call).
2. Checks for overdue SRS concepts (same course). If any exist, builds a `session_type = "review"` session with dynamic stages `[review_recap_0_llm, review_widget_0_user, review_recap_1_llm, review_widget_1_user, ..., complete]`, runs the first LLM stage, and returns.
3. For a normal lesson session, stores `session["stages"] = list(STAGES)` and `session["session_type"] = "lesson"`. Gate/review checks are wrapped in try/except — failures fall through to the lesson.

**`tick_session(session_id, ...)`**: 
- Uses `session["stages"]` instead of global `STAGES` throughout.
- Added `review_widget_\d+_user` handler: submits the widget, computes SRS score, writes SRS for the reviewed concept (with its original `lesson_id`), advances cursor.
- Lesson `widget_step{i}_user` handler: after storing the activity entry, calls `_score_widget_result` + `_write_srs_for_concepts` for the concepts in that step.

**`_maybe_save_session(session)`**: uses `session["stages"]`.

**`_save_session_to_db(session)`**: 
- Removed the legacy SRS `attempts` increment (SRS is now written per-concept inline in `tick_session`).
- Stores `mode = session["session_type"]` in `lesson_sessions`.
- Stores `scored_concept_ids` in `metadata`.

---

## 4. `backend/server.py`

**Removed:**
- `LessonScoreRequest` Pydantic model
- `_score_lesson_response()` function
- `POST /lesson/score` endpoint (and all its SRS write / roadmap_position advance logic)

SRS scoring is now done inline inside `tick_session` in `dynamic_lesson.py` when a widget is submitted.

---

## 5. `frontend/src/api/interactiveLesson.ts`

**Removed:** `scoreLesson()` function.

**Added to `InteractiveSessionState`:**
```typescript
session_type?: 'lesson' | 'review' | 'gated'
gated_info?: GatedInfo | null
review_count?: number | null
```

**New type:**
```typescript
type GatedInfo = {
  blocked: boolean
  blocking_lesson_id: string
  avg_score: number
  threshold: number
}
```

---

## 6. `frontend/src/pages/InteractiveLessonPage.tsx`

**Removed:** `fireScore` callback and all three call sites (MCQ `onSubmit`, free_response `onSubmit`, free_response `dont_know`).

**Added:**

- **Review banner** (top of lesson content): shown when `session_type === "review"` with count of overdue concepts.

- **Review complete UI** (in the `awaiting === "none"` section): when `session_type === "review"` shows "Reviews cleared! Continue to lesson →" button that calls `handleRestart` (which calls `startInteractiveLesson` again — if overdue are cleared, this time returns a lesson session).

- **Gated UI** (always rendered when `session_type === "gated"`): shows the avg score and threshold, with a link back to the roadmap.

---

## How the flow works end-to-end

```
Student clicks lesson →
  start_session called →
    gate check: prev_lesson avg < 3.0? → return session_type="gated" (no session)
    overdue check: any due SRS for this course? → return session_type="review" session
    otherwise → return session_type="lesson" session

Review session progresses:
  review_recap_i_llm auto-runs → recap message + pending_widget set
  review_widget_i_user → student submits widget → SRS written for concept (keyed by concept_id, lesson_id)
  ...repeat for all overdue concepts...
  complete → frontend shows "Reviews cleared, continue to lesson" button
  Student clicks → start_session called again → this time no overdue → lesson starts

Lesson session progresses:
  widget_step{i}_user submitted → score computed → SRS written for concepts in that step
  ...lesson finishes...

Gate: next lesson's start_session checks avg(srs_records.score WHERE lesson_id = this_lesson)
  < 3.0 → gated → student must repeat
  >= 3.0 → lesson unlocked
```

---

## Files changed

| File | Change |
|---|---|
| `backend/supabase/migrations/add_lesson_id_to_srs_records.sql` | Created — run in Supabase |
| `backend/srs.py` | Added `lesson_id` param to `upsert_srs_record` |
| `backend/dynamic_lesson.py` | Major additions: concept SRS, review sessions, gate check |
| `backend/server.py` | Removed `/lesson/score` endpoint |
| `frontend/src/api/interactiveLesson.ts` | Removed `scoreLesson`, added `session_type` types |
| `frontend/src/pages/InteractiveLessonPage.tsx` | Removed `fireScore`, added review/gated UI |
