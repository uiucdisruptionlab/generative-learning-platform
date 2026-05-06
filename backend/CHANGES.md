# Backend Change Log

---

## Current System State (as of 2026-05-03)

### Architecture overview

The backend is a FastAPI server (`server.py`) that connects to:
- **Supabase** — student profiles, roadmap cache, SRS records, lesson session history, roadmap position
- **Neo4j** — concept graph (concepts, relationships, lectures, courses)
- **Pinecone** — lecture transcript chunk vectors
- **AWS Bedrock** — Claude Haiku for all LLM calls (content generation, widget generation, scoring)
- **YouTube Data API** — video suggestions (only for students who prefer video format)

### How a lesson session works

```
Student opens lesson →
  start_session() called →
    Gate check: prev lesson avg concept score < 3.0? → return session_type="gated"
    Overdue SRS check: any due concepts for this course? → return session_type="review"
    Otherwise → return session_type="lesson"

Lesson session:
  overview_llm → after_overview_confirm →
  [for each step: step_content_llm → reflect_stepN_user → widget_stepN_user → confirm_stepN_user] →
  complete

Review session:
  [for each overdue concept: review_recap_i_llm → review_widget_i_user] →
  complete → frontend shows "Reviews cleared, continue to lesson" button →
  start_session called again → (if no more overdue) → lesson session starts

Widget scoring → SRS write:
  MCQ correct → score 4, MCQ wrong → score 2
  free_response → LLM scores 0–5
  flashcards / video → score 3 (engagement)
  skipped → score 0, dont_know → score 1
  Score written per concept (not per lesson) to srs_records
  Widget question stored as last_gaps (wrong) or last_strengths (correct)

Repeat lesson:
  load_lesson_sources batch-queries srs_records for all lesson concepts →
  builds composite PRIOR PERFORMANCE context with weak/strong concept list →
  injected into every LLM prompt → tutor adapts difficulty and targets gaps
```

### Roadmap & caching

- **`roadmap_cache` (Supabase)** — one row per student, stores the full lesson roadmap. Built by `build_course_lesson_roadmap()` (Neo4j graph fetch + Bedrock LLM refinement). Expensive to build; persists until `POST /roadmap/{student_id}/rebuild` is called.
- **`COURSE_NEO4J_IDS` (roadmap_builder.py)** — maps semantic course names (`"accounting"`) to Neo4j Course node IDs (`"ALecFinal"`). `student_courses.course_id` uses semantic names everywhere; the bridge to Neo4j only happens inside `build_course_lesson_roadmap`.
- **`COURSE_NAMESPACES` (lesson_generator.py)** — maps semantic course names to Pinecone namespaces.
- **`_SESSIONS` (dynamic_lesson.py)** — in-memory dict of active sessions, capped at 200 (LRU prune). Non-persistent across restarts.

### SRS system

- SM-2 algorithm in `srs.py`. Records keyed by `(student_id, concept_id)`.
- `lesson_id` column on `srs_records` enables the gate: `avg(score) WHERE lesson_id = prev_lesson`.
- Gate threshold: 3.0. If prev lesson avg < 3.0, the next lesson is blocked.
- Overdue check: `next_review_at <= now`. Fires before every lesson start.
- `last_gaps` / `last_strengths` on each record: populated from the widget question text after each attempt. Used to personalize the repeat lesson experience.

### Video preference gating

YouTube search (at lesson load time and for video widgets) only runs if `"videos"` is in the student's `preferred_formats`. Students without a video preference see no video cards and no error message — absence of videos is treated as intentional.

---

## Session Log

---

### 2026-05-02 — Data integrity, graph cleanup, legacy roadmap removal

#### 1. New audit scripts

**`audit_pinecone_neo4j.py`** — compares chunk IDs in Neo4j against vectors in Pinecone per course namespace. Reports missing vectors grouped by namespace and lecture.

**`audit_neo4j.py`** — audits Neo4j for nodes with invalid prefixes, orphaned chunks/lectures/concepts (disconnected from expected parents), and invalid Course nodes.

#### 2. Pinecone re-ingestion

Audit found **330 chunk IDs** in Neo4j with no corresponding Pinecone vector. Missing chunks were traced to lectures that had been graph-ingested but never upserted to Pinecone.

Re-ingested lectures:
- **Accounting (`15.501_Transcripts`):** `ALec1`, `ALec3`, `ALec4`, `ALec5`, `ALec8`, `ALec13`, `ALec15`, `ALec18`, `ALec19`
- **Python (`6.0001_Transcripts`):** `PLec1`, `PLec6`, `PLec7`, `PLec8`, `PLec11`, `PLec12`

3 chunks remained missing due to chunker non-determinism; deleted from Neo4j directly:
```cypher
MATCH (ch:Chunk) WHERE ch.id IN ['ALec1_p11_c2', 'ALec3_p29_c1', 'ALec5_p12_c2'] DETACH DELETE ch
```

Final state: all Neo4j chunks have vectors in Pinecone.

#### 3. Neo4j graph cleanup

Deleted invalid/orphaned nodes from a finance course (`FLec*`) that was partially ingested:
- **193 FLec Chunk nodes** (invalid prefix, orphaned)
- **467 orphaned Concept nodes** (no parent Chunk via `CONTAINS`)

```cypher
MATCH (ch:Chunk) WHERE ch.id STARTS WITH 'FLec' DETACH DELETE ch
MATCH (n) WHERE any(label IN labels(n) WHERE label STARTS WITH 'DL') DETACH DELETE n
MATCH (c:Concept) WHERE NOT (c)<-[:CONTAINS]-(:Chunk) DELETE c
```

Final audit: 0 invalid nodes, 0 orphaned nodes.

#### 4. Deleted stale roadmap cache files

`backend/roadmap_cache_accounting.json` and `backend/roadmap_cache_python.json` deleted. Both contained only `ALecFinal` data from initial ingestion. Replaced by the Supabase-backed per-student roadmap.

#### 5. Removed legacy roadmap system from `server.py`

Two roadmap systems coexisted. The old system used local JSON files keyed per course; the new system uses Supabase `roadmap_cache` keyed per student and calls `build_course_lesson_roadmap()`. Removed the old system entirely.

Removed: `ROADMAP_CACHE_DIR`, `COURSE_KEY_MAP`, `_course_cache_path()`, `_load_roadmap_cache()`, `_save_roadmap_cache()`, `_node_ids_from_cached_roadmap()`, `_build_and_cache()`, `GET /roadmap`, `POST /roadmap/rebuild`, enrichment and fallback blocks that read the old cache.

Kept: `_load_lesson_roadmap_cache()`, `_save_lesson_roadmap_cache()`, `_get_or_build_lesson_roadmap()`, `GET /roadmap/{student_id}`, `POST /roadmap/{student_id}/rebuild`, `GET /roadmap/generate/{student_id}`.

---

### 2026-05-02 — Concept-level SRS, review sessions, lesson gate

#### Supabase migration

**`backend/supabase/migrations/add_lesson_id_to_srs_records.sql`** — run in Supabase SQL editor before deploying:
```sql
ALTER TABLE public.srs_records ADD COLUMN IF NOT EXISTS lesson_id text;
CREATE INDEX IF NOT EXISTS idx_srs_records_student_lesson ON public.srs_records (student_id, lesson_id);
```

#### `backend/srs.py`

Added optional `lesson_id: str | None = None` to `upsert_srs_record`. When provided, stored in the row. Enables `_get_lesson_avg_score` to compute avg by lesson for the gate check.

#### `backend/dynamic_lesson.py`

New helper functions:

| Function | Purpose |
|---|---|
| `_concept_ids_for_step(concepts, step_index)` | Returns concept IDs assigned to step N (same bucket logic as chunk selector) |
| `_score_free_response_llm(question, ref, response)` | Scores free-response 0–5 via LLM |
| `_score_widget_result(widget_type, payload, result)` | Maps widget submission to 0–5 SRS score |
| `_derive_srs_metadata(activity, score)` | Extracts `gaps`/`strengths` from widget payload for storage on SRS record |
| `_write_srs_for_concepts(session, concept_ids, score, *, lesson_id, activity)` | Upserts SRS records per concept; derives and stores gap metadata |
| `_get_lesson_avg_score(student_id, lesson_id, client)` | Queries avg SRS score for a lesson |
| `_check_lesson_gate(student_id, lesson_id, roadmap, client)` | Returns gate block dict if prev-lesson avg < 3.0, else None |
| `_load_lesson_roadmap_for_student(student_id)` | Reads `roadmap_cache` from Supabase |
| `_build_concept_map(roadmap)` | Builds `concept_id → {name, description}` across all lessons |
| `_run_review_recap_llm(session, concept_index)` | LLM generates recap + widget for one overdue concept |

Modified `start_session`: gate check → gated response; overdue check → review session with dynamic stages; normal lesson → `session["stages"] = list(STAGES)`, `session["session_type"] = "lesson"`.

Modified `tick_session`: `review_widget_\d+_user` handler writes SRS for the reviewed concept; `widget_step{i}_user` handler writes SRS for the concepts in that step.

Modified `_save_session_to_db`: removed legacy SRS `attempts` increment; stores `mode = session_type`; stores `scored_concept_ids` in metadata.

#### `backend/server.py`

Removed `LessonScoreRequest`, `_score_lesson_response()`, and `POST /lesson/score`. SRS scoring is now inline in `tick_session`.

#### `frontend/src/api/interactiveLesson.ts`

Removed `scoreLesson()`. Added `GatedInfo` type and `session_type`, `gated_info`, `review_count` to `InteractiveSessionState`.

#### `frontend/src/pages/InteractiveLessonPage.tsx`

Removed `fireScore` callback and all call sites. Added:
- Review banner when `session_type === "review"`
- Gated lock UI when `session_type === "gated"`
- Review completion button ("Reviews cleared! Continue to lesson →") that calls `handleRestart`

---

### 2026-05-03 — Course ID architecture fix, repeat-lesson personalization, SRS logs, video preference gating

#### Course ID architecture fix (`backend/graphdb/roadmap_builder.py`, `backend/lesson_generator.py`)

**Problem:** `student_courses.course_id` used `"ALecFinal"` (a Neo4j ingestion artifact) as the course identifier. This leaked into Pinecone namespace lookups and failed because `COURSE_NAMESPACES` only mapped semantic names like `"accounting"`.

**Fix:**
- Added `COURSE_NEO4J_IDS: dict[str, str] = {"accounting": "ALecFinal"}` to `roadmap_builder.py`. `build_course_lesson_roadmap` resolves the semantic name to the Neo4j ID only at the point of the Neo4j query.
- Reverted the quick patch that added `"ALecFinal": "15.501_Transcripts"` to `COURSE_NAMESPACES` in `lesson_generator.py`.
- Run in Supabase: `UPDATE public.student_courses SET course_id = 'accounting' WHERE course_id = 'ALecFinal';`

Now `student_courses.course_id` is `"accounting"` everywhere, which maps correctly to both Pinecone (`COURSE_NAMESPACES`) and Neo4j (`COURSE_NEO4J_IDS`).

#### SRS console logs (`backend/dynamic_lesson.py`)

Added `[SRS]` prefixed logs so the full SRS flow is visible in the server terminal in real time:

```
[SRS] gate  lesson=lesson_002  prev=lesson_001  avg=3.80 ≥ 3.0 → passed
[SRS] review session  3 overdue concept(s): ['Revenue Recognition', ...]
[SRS] review 1/3  mcq  score=4/5  concept='Revenue Recognition'
[SRS] step 0 mcq  score=2/5  concepts=['Revenue Recognition', 'Matching Principle']
[SRS] ✓ wrote  'Revenue Recognition'  score=2/5  lesson=lesson_002
[SRS] session complete  type=lesson  lesson=lesson_002  score=3/5  verdict=mixed  activities=2/3  concepts_scored=4
```

#### Repeat-lesson personalization (`backend/lesson_generator.py`, `backend/dynamic_lesson.py`)

**Problem:** A repeated lesson was identical to the first attempt because `last_gaps`/`last_strengths` were never populated on SRS records, and the SRS lookup used `lesson_id` as the key (legacy approach) instead of concept IDs.

**Fix — gap storage:**
- Added `_derive_srs_metadata(activity, score)` to `dynamic_lesson.py`. For MCQ/free_response widgets, stores the question text as `gaps` (score ≤ 2) or `strengths` (score ≥ 4).
- `_write_srs_for_concepts` now accepts `activity` and passes derived metadata to `upsert_srs_record`, which writes `last_gaps`/`last_strengths` to the SRS record.

**Fix — context injection:**
- Replaced the legacy `get_srs_record(student_id, lesson_id)` single-record lookup in `load_lesson_sources` with a batch query: `srs_records WHERE student_id=X AND concept_id IN [lesson concepts]`.
- Added `_build_composite_srs_context(records, name_map)` which produces a structured summary with per-concept weak/strong areas, average score, and a tutor directive (remediate / progress / push deeper).
- The composite context is injected into every LLM prompt as `PRIOR PERFORMANCE` and into `_run_prior_performance_llm` (the opening message on repeat attempts).

**Result:** On the first attempt, gaps get written. On the second attempt, the tutor opens with a targeted recap of what was hard last time, and every explanation and widget in the session is adapted to those weak areas.

#### Video preference gating (merged from teammate branch)

YouTube search is now gated behind `"videos" in persona["preferred_formats"]` at two points:
- **`load_lesson_sources`** — skips the YouTube search entirely at lesson load time.
- **`_resolve_video_widget_payload`** — skips the YouTube search when generating a video widget.
- **`_merge_videos_from_lesson_cache`** — skips the lesson-cache fallback for video too.

Students without a video preference see no video cards and no error message.

Also fixed a pre-existing bug: `_normalize_profile_to_persona` was reading `preferred_formats` from the student profile but not including it in the returned persona dict — it was silently dropped. Now included.

#### Files changed this session

| File | Change |
|---|---|
| `backend/graphdb/roadmap_builder.py` | Added `COURSE_NEO4J_IDS`; resolve semantic→Neo4j ID in `build_course_lesson_roadmap` |
| `backend/lesson_generator.py` | Reverted `ALecFinal` patch; replaced single SRS lookup with batch concept query; added `_build_composite_srs_context`; video search gated by `preferred_formats`; fixed `preferred_formats` not being returned from `_normalize_profile_to_persona` |
| `backend/dynamic_lesson.py` | Added `_derive_srs_metadata`; wired `activity` metadata through `_write_srs_for_concepts`; added `[SRS]` console logs throughout; restored `_LESSON_CACHE_DIR` + `_merge_videos_from_lesson_cache` (dropped during SRS rewrite); video widget gated by `preferred_formats` |
