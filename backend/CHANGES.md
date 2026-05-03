# Backend Changes — Session Log

## 2026-05-02

### Summary
This session focused on auditing and fixing data consistency between Neo4j and Pinecone, cleaning up the Neo4j graph, and removing the legacy roadmap system from the server.

---

### 1. New audit scripts

#### `audit_pinecone_neo4j.py`
Compares chunk IDs stored as nodes in Neo4j against vectors in Pinecone, per course namespace. Reports mismatches grouped by namespace and broken down by lecture.

- Queries Neo4j for all chunks reachable via `(Course)-[:HAS_LECTURE]->(:Lecture)-[:HAS_CHUNK]->(Chunk)`
- Maps Neo4j course IDs to the correct Pinecone course-level namespace (`COURSE_NAMESPACE_MAP`)
- Batch-fetches from Pinecone (200 IDs per request) and reports missing vectors
- Outputs a per-namespace summary table and a flat list of incomplete lectures with chunk counts

Pinecone namespaces covered:
| Namespace | Course |
|---|---|
| `15.501_Transcripts` | Accounting (ALec* chunks) |
| `6.0001_Transcripts` | Python (PLec* chunks) |
| `BIS512` | BIS512 |
| `11.437_Transcripts` | Financing |

#### `audit_neo4j.py`
Audits Neo4j for nodes that don't belong to the three valid courses, and for orphaned nodes (not connected to their expected parent).

Checks:
- Invalid Course nodes (ID not in known set)
- Invalid Lecture nodes (ID doesn't start with `ALec`, `PLec`, or `BIS512`)
- Invalid Chunk nodes (same prefix check)
- Orphaned Chunks (no parent Lecture)
- Orphaned Lectures (no parent Course)
- Orphaned Concepts (no parent Chunk via `CONTAINS`)

---

### 2. Pinecone re-ingestion

Audit found **330 chunk IDs** present in Neo4j but missing from Pinecone across the accounting and Python namespaces. The missing chunks were traced to specific lectures that had been graph-ingested but never fully upserted to Pinecone.

Missing lectures re-ingested:

**Accounting (`15.501_Transcripts`)**
`ALec1`, `ALec3`, `ALec4`, `ALec5`, `ALec8`, `ALec13`, `ALec15`, `ALec18`, `ALec19`

**Python (`6.0001_Transcripts`)**
`PLec1`, `PLec6`, `PLec7`, `PLec8`, `PLec11`, `PLec12`

PDFs were copied to `backend/missing_files/accounting/` and `backend/missing_files/python/` and the ingestion pipeline in `main.py` was run against each folder.

After re-ingestion, 3 chunks remained missing because the Unstructured + LangChain chunker is non-deterministic and no longer produces those specific chunk indices from the source PDFs. These orphan nodes were deleted directly from Neo4j:

```cypher
MATCH (ch:Chunk) WHERE ch.id IN ['ALec1_p11_c2', 'ALec3_p29_c1', 'ALec5_p12_c2'] DETACH DELETE ch
```

Final state after all fixes: **all Neo4j chunks have vectors in Pinecone**.

---

### 3. Neo4j graph cleanup

The audit found invalid and orphaned nodes from a finance course (`FLec*`) that was ingested into Neo4j as bare Chunk nodes, without being linked to a Lecture or Course node. These were out of scope.

Deleted:
- **193 FLec Chunk nodes** (invalid prefix, all orphaned — no parent Lecture)
- **467 orphaned Concept nodes** (no parent Chunk via `CONTAINS`)

```cypher
-- Delete FLec chunks and their concept edges
MATCH (ch:Chunk) WHERE ch.id STARTS WITH 'FLec' DETACH DELETE ch

-- Delete any DL nodes
MATCH (n) WHERE any(label IN labels(n) WHERE label STARTS WITH 'DL') DETACH DELETE n

-- Delete concepts with no parent chunk
MATCH (c:Concept) WHERE NOT (c)<-[:CONTAINS]-(:Chunk) DELETE c
```

Final Neo4j audit: all clean — 0 invalid nodes, 0 orphaned nodes.

---

### 4. Deleted stale roadmap cache files

Two on-disk JSON files were deleted:
- `backend/roadmap_cache_accounting.json`
- `backend/roadmap_cache_python.json`

Both only contained `ALecFinal` data (from the initial ingestion). They will now be rebuilt correctly from the full Neo4j graph on next request via the new Supabase-backed lesson roadmap system.

---

### 5. Removed legacy roadmap system from `server.py`

Two roadmap systems existed in `server.py`. The **old system** used local JSON files cached on disk, keyed per course. The **new system** uses Supabase (`roadmap_cache` table), is keyed per student, and calls `build_course_lesson_roadmap()` which returns lecture-grouped lessons.

The new system is what the frontend calls (`/roadmap/{student_id}`). The old system's endpoints (`GET /roadmap`, `POST /roadmap/rebuild`) were no longer reachable from the frontend.

**Removed from `server.py`:**

| What | Notes |
|---|---|
| `ROADMAP_CACHE_DIR`, `COURSE_KEY_MAP` constants | Mapped course names to local JSON filenames |
| `_course_cache_path()` | Resolved the JSON path per course |
| `_load_roadmap_cache()` | Read the JSON file |
| `_save_roadmap_cache()` | Wrote the JSON file |
| `_node_ids_from_cached_roadmap()` | Extracted lesson IDs from the old cache |
| `_build_and_cache()` | Called old `build_roadmap()` and wrote to disk |
| `GET /roadmap` endpoint | Served the old course-level roadmap |
| `POST /roadmap/rebuild` endpoint | Force-rebuilt the old roadmap |
| Enrichment block in `_generate_and_cache_lesson()` | Read old cache to backfill `concepts`, `chunk_ids`, `lecture_ids`, `prerequisites` onto generated lessons |
| Fallback block in `_lesson_context_for_scoring()` | Read old cache to find lesson context when scoring a student response |

**Kept (the new system):**

| What | Notes |
|---|---|
| `_load_lesson_roadmap_cache()` | Reads from Supabase `roadmap_cache` table |
| `_save_lesson_roadmap_cache()` | Writes to Supabase `roadmap_cache` table |
| `_get_or_build_lesson_roadmap()` | Cache-or-build entry point |
| `GET /roadmap/{student_id}` | Serves the student-level lesson roadmap |
| `POST /roadmap/{student_id}/rebuild` | Force-rebuilds the student roadmap |
| `GET /roadmap/generate/{student_id}` | Alias for roadmap generation |

---

### Files changed

| File | Change |
|---|---|
| `audit_pinecone_neo4j.py` | Created |
| `audit_neo4j.py` | Created |
| `missing_files/accounting/` | Created — contains PDFs for re-ingestion |
| `missing_files/python/` | Created — contains PDFs for re-ingestion |
| `roadmap_cache_accounting.json` | Deleted |
| `roadmap_cache_python.json` | Deleted |
| `server.py` | Removed old roadmap system (see above) |
