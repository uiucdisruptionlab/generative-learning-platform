# Backend codebase profile

A file-by-file map of `backend/`, grouped by responsibility. Files are ordered by importance within each section. Overlap and legacy code is flagged at the bottom.

## Top-level entry points

| File | LOC | What it does |
|---|---|---|
| `server.py` | 1326 | **The FastAPI app.** All HTTP endpoints live here — `/student/*`, `/courses`, `/roadmap/*`, `/srs/due/*`, `/session/*` (adaptive lesson loop), `/lesson/interactive/*` (walkthrough), `/lesson/{id}` and `/chat/stream` (onboarding). Also owns the legacy on-disk `roadmap_cache_*.json` reader and the new Supabase-backed lesson roadmap cache. Run with `uvicorn server:app --reload --port 8000`. |
| `main.py` | 140 | **Document ingestion CLI** (not an API). Glues PDF → text → chunks → embeddings → Pinecone, with optional concept extraction → Neo4j. Run from CLI to seed a course. Toggle `ENABLE_GRAPH_INGESTION` / `GRAPH_ONLY` via env. |
| `searcher.py` | 25 | One-off Pinecone query smoke test. Hard-codes `"What is the representation space?"`. Useful for dev, not used at runtime. |

## Adaptive lesson loop (the live web flow)

| File | LOC | What it does |
|---|---|---|
| `adaptive_session.py` | 626 | **The concept-level adaptive loop.** `start_session` looks up the student's enrolled course in Supabase, pulls the cached lecture-grouped roadmap (so concept order matches the roadmap UI), determines the next active concept (overdue SRS first, else next in `node_ids`), and sets up an in-memory `SESSION_STORE` entry. `generate_block` produces Bedrock-driven video/flashcard/MCQ blocks. `lesson_message` / `classify_intent` route learner replies (question vs attempt). `complete_lesson` advances `roadmap_position` and writes SRS. `_resolve_video_block` is what calls YouTube to get a real `url` / `title` / `thumbnail` for each video block. |
| `srs.py` | 321 | **Spaced repetition (SM-2) + roadmap cursor.** `run_sm2(score, prev)` implements the SuperMemo-2 algorithm. `get_srs_record` / `upsert_srs_record` / `get_due_srs_records` / `get_upcoming_srs_records` talk to the `srs_records` table. `get_roadmap_position` / `set_roadmap_position` / `advance_roadmap_index` / `advance_roadmap_progress` manage `(student_id, course_id) → current_index` in `roadmap_position`. |
| `test_adaptive_session_units.py` | 50 | Unit tests for `topo_sort_concept_nodes` and `run_sm2` (no DB / network needed). |

## Interactive lesson walkthrough (the other web flow)

| File | LOC | What it does |
|---|---|---|
| `dynamic_lesson.py` | 1337 | **Step-by-step walkthrough engine** for `/lesson/interactive/*`. Stateful per-session conversation: overview → step content → engage (reflection) → checkpoint → closing. Generates LLM payloads with structured UI widgets (videos, MCQs, flashcards, free-response). Uses `lesson_generator.load_lesson_sources` for Pinecone chunks + YouTube videos. No SRS; pure conversational progression. |
| `lesson_generator.py` | 524 | **Static lesson generator** (the older `/lesson/{lesson_id}` endpoint). Loads chunks from Pinecone, fetches YouTube videos, builds a one-shot LLM prompt, and returns a fully-formed lesson dict. Output is cached on disk under `backend/lesson_cache/`. `load_lesson_sources` is reused by `dynamic_lesson.py`. |
| `lesson_loop.py` | 598 | **Legacy CLI loop** — terminal-first, runs through `ordered_concepts`, scores knowledge checks, writes SRS. Not used by the web app. The header docstring explicitly says: prefer `dynamic_lesson.py` for the web flow. |

## Roadmap building (Neo4j → ordered lessons)

| File | LOC | What it does |
|---|---|---|
| `graphdb/roadmap_builder.py` | 819 | **Two roadmap construction paths**: (a) `build_roadmap_from_graph_data` — the older path that takes raw `concepts + relationships`, runs connected-components / topo sort / dedup / merging, and optionally hands the result to the LLM refiner; (b) `build_course_lesson_roadmap(course_id)` — the **new** path: pulls lecture-grouped concepts, builds lesson candidates (one-per-lecture for multi-lecture courses, chunk-grouped for single-lecture), refines via LLM, and re-attaches Neo4j concept IDs by name. |
| `graphdb/roadmap_refiner.py` | 262 | **The LLM refiner.** Takes a draft roadmap, calls Claude Haiku with a strict system prompt to merge / clean / rename lessons. Includes a robust `_parse_llm_json` with a `_salvage_truncated_lessons_json` fallback that recovers from mid-response token-limit truncation. `MAX_LESSONS_FOR_REFINEMENT = 12`. |
| `graphdb/toposort.py` | 46 | Pure-Python Kahn topo sort over Concept nodes using PREREQUISITE_OF edges. Cycle-tolerant (appends remaining nodes if not fully drained). |

## Graph DB (Neo4j)

| File | LOC | What it does |
|---|---|---|
| `graphdb/neo4j_client.py` | 522 | **Every Cypher query.** Connection (`_driver`), reads (`get_concept_roadmap_scoped`, `get_lecture_grouped_concepts`, `get_chunks_for_concept`, `get_courses`, `get_concepts_by_lecture`, etc.), writes (`create_course`, `create_lecture`, `create_chunk`, `create_concept`, `create_relationship`, `link_*`). |
| `graphdb/graph_ingestion.py` | 126 | `ingest(chunk, extracted)` — the orchestrator called from `main.py` per-chunk: ensures the Chunk node, derives course / lecture, MERGEs concepts and relationships, and links chunk → concept via CONTAINS edges. |
| `graphdb/setup_schema.py` | 36 | **Already-run** one-time script to create uniqueness constraints on `Concept.name` and `Chunk.id`. |
| `graphdb/test_graph.py` | 126 | E2E test: ingests a fake React-Hooks chunk, verifies the resulting graph. |
| `graphdb/test_roadmap_builder.py` | 50 | Unit test for `build_roadmap_from_graph_data` with a fake CS graph. |
| `graphdb/README.md` | — | Human docs for the graph layer (data model, integration point). |
| `concept_extractor.py` | 282 | **Bedrock concept extraction.** Given one chunk, asks Claude Haiku for `{concepts[], relationships[]}` JSON. Used by `main.py` during ingestion. Validates relationship types against `{PREREQUISITE_OF, RELATED_TO, PART_OF}`. |

## Vector DB (Pinecone)

| File | LOC | What it does |
|---|---|---|
| `pc_client/client.py` | 89 | `PineconeClient` wrapper: batch upsert, fetch_by_id, query, namespace handling. |
| `pc_client/models/chunks.py` | 64 | Two dataclasses: `ChunkMetadata` (offering_id, source_type, topic, text, chunk_number) and `CourseChunk` (id, values, metadata) with validation + `to_pinecone_record()`. |
| `pc_client/test_pinecone.py` | 56 | Smoke test for upsert / fetch / query on a `test_namespace`. |

## Document ingestion (PDFs → chunks)

| File | LOC | What it does |
|---|---|---|
| `unstructured/pdf_text_extractor.py` | 53 | `PDFTextExtractor.extract_texts(pdf_path)` — calls Unstructured's hosted partition API with the VLM strategy (gpt-4o backend) to pull text + metadata from PDFs. |
| `unstructured/text_chunker.py` | 40 | `TextChunker` — wraps LangChain's `RecursiveCharacterTextSplitter` (default 500 / 100 chars). |
| `unstructured/test.py` | 29 | Standalone harness for the extractor + chunker. |
| `bedrock/embedder.py` | 46 | `BedrockEmbedder` — wraps Titan v2 (text) and Titan Image v1. |

## Bedrock client (LLM access)

| File | LOC | What it does |
|---|---|---|
| `bedrock/client.py` | 111 | `create_bedrock_runtime_client()` returns either boto3's `bedrock-runtime` client (if `AWS_ACCESS_KEY_ID` / `SECRET` are set) or a `BearerTokenBedrockClient` shim that hits the Bedrock REST API directly with `AWS_BEARER_TOKEN_BEDROCK`. The shim implements `invoke_model`, `converse`, and `invoke_model_with_response_stream`. |

## Supabase (Postgres)

| File | What it does |
|---|---|
| `supabase/supabase_client.py` | The actual client module. `get_supabase_client()`, `get_student_profile()`, plus older helpers for `content_items`, `recommendations`, `content_interactions`, `srs_records`. Loads `.env` from repo root then `backend/.env` (override). |
| `supabase_local.py` | Tiny shim that imports `supabase/supabase_client.py` by file path so callers don't shadow the `supabase` PyPI package. Re-exports `get_supabase_client` and `get_student_profile`. |
| `supabase/seed_students.sql` | INSERT statements for the three demo personas (Alice / Bob / Charles). |
| `supabase/seed_students_srs.sql` | Demo SRS rows. |
| `supabase/migrations/ensure_adaptive_lesson_schema.sql` | Creates `roadmap_position` + extends `srs_records` with `concept_id`, `node_id`, `attempts`, etc. |
| `supabase/migrations/create_srs_records.sql` | Original `srs_records` table. |
| `supabase/migrations/ensure_srs_records_schema.sql` | Idempotent schema-fix-up for `srs_records`. |
| `supabase/migrations/patch_srs_records_add_concept_id.sql` | Adds `concept_id` to `srs_records`. |
| `supabase/migrations/patch_srs_rename_interval_to_interval_days.sql` | Renames `interval` → `interval_days` in `srs_records`. |
| `supabase/migrations/add_student_courses_and_course_id_to_roadmap.sql` | Creates `student_courses`, adds `course_id` to `roadmap_position`'s primary key. |
| `supabase/migrations/use_roadmap_cache_for_lesson_roadmap.sql` | Alters `roadmap_cache.roadmap` from `jsonb[]` → `jsonb`, adds `UNIQUE (student_id)`, wipes stale rows. |

## External APIs

| File | LOC | What it does |
|---|---|---|
| `youtube/client.py` | 71 | `search_videos(query, max_results)` — calls YouTube Data API v3, returns `[{video_id, title, channel, description, url, thumbnail}]`. Reads `YOUTUBE_API_KEY` lazily so dotenv loads first. Returns `[]` and logs if missing. |

## Misc

| File | LOC | What it does |
|---|---|---|
| `personas.py` | 53 | **In-memory** persona dict (Alice / Bob / Charles + IDs / learning style / notes). Used by older lesson generator paths. The web flow now reads personas from Supabase `students`, but this file is still imported by `lesson_generator.py`. |
| `requirements.txt` | — | Python dependencies. |
| `ingestion_pipeline.txt` | 13 | Plaintext ascii diagram of the ingestion flow. |
| `roadmap_cache_accounting.json` / `roadmap_cache_python.json` | — | **Legacy** on-disk cache for the older `/roadmap?course=` endpoint (different shape from the new lesson roadmap). Not currently consumed by the live web flow but `server.py:_load_roadmap_cache` still reads them if the route is hit. Safe to delete if no caller is using `/roadmap?course=…`. |
| `lesson_cache/` | — | On-disk cache for the older `/lesson/{id}` endpoint (one JSON per persona / lesson). Currently only contains `charles_accounting/lesson_001.json`. |

