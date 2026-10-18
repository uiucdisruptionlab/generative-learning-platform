# Backend

FastAPI app in `server.py`. It builds roadmaps from Neo4j, retrieves lecture chunks from Pinecone, stores students, sessions and spaced-repetition records in Supabase, and generates lessons through an LLM. `BACKEND_PROFILE.md` maps every module and endpoint.

Commands run from this directory:

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
python -m unittest test_adaptive_session_units
ruff check .
```

After a backend change, start the server and exercise the endpoint you touched.

## Conventions

- All model calls go through `create_llm_client()` from `llm/`. See `llm/CLAUDE.md` before changing how a request is built.
- Prompts live next to the code that sends them, not in a shared prompt file: `interactive_lesson.py` (interactive lesson), `lesson_generator.py` (static lesson), `server.py` (onboarding and lesson chat), `ingestion/concept_extractor.py` and `graphdb/roadmap_refiner.py` (ingestion).
- Model output is parsed as JSON and then normalized in code. Decide in code whatever the inputs fully determine (allowed activity types, widget type from a score) and leave the model the judgment.
- Import Supabase helpers from `db.supabase_client`. Do not name a local folder after an installed package (`supabase`, `unstructured`); it shadows the package on import.
- Lint with `ruff check .` (config in `pyproject.toml`). Scripts named `smoke_*.py` call live services and are run by hand.

## Ingestion

`ingestion/ingest_course.py` is the only ingestion entry point (run it as `python -m ingestion.ingest_course` from this directory). It names chunks `<course_id>_Lec<n>_p<page>_c<chunk>` and tags them `slides`.

The accounting and Python courses were ingested earlier by a script that has since been removed, which named chunks after the PDF file alone (`ALecFinal_p3_c2`) and tagged them `textbook`. Re-ingesting those courses with `ingest_course.py` therefore writes new ids beside the old ones in Pinecone and Neo4j instead of overwriting them. Clear the course's namespace and graph nodes first.
