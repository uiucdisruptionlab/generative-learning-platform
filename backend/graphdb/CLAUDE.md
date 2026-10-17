# Knowledge Graph and Roadmaps

Neo4j holds the course graph (`Course`, `Lecture`, `Chunk`, `Concept`) and this folder turns it into lesson roadmaps. `README.md` documents the data model.

- Every Cypher query lives in `neo4j_client.py`. Application code calls its functions instead of opening its own driver sessions.
- All writes use `MERGE`, so re-ingesting a document is safe. Keep new writes idempotent.
- `setup_schema.py` has already been run against the live database. Run it only against a brand-new instance.
- Roadmap ordering reads page and chunk position out of chunk ids shaped `..._p<page>_c<chunk>`. Changing the id format in ingestion silently breaks lesson ordering.
- LLM refinement of a roadmap is off unless `ENABLE_ROADMAP_REFINEMENT=true`; the graph-only roadmap has to be usable on its own.
