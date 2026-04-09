# GraphDB — Knowledge Graph Layer

This module builds a Neo4j knowledge graph on top of the document ingestion pipeline. For every chunk that passes through the pipeline, structured concept nodes and their relationships are written to Neo4j AuraDB in addition to the Pinecone vector upsert.

## What it does

After a chunk is embedded and before it is upserted to Pinecone, the concept extraction layer produces a structured JSON payload describing the concepts found in that chunk and how they relate. This module takes that payload and writes it to Neo4j.

The result is a graph where:
- **Chunk nodes** represent individual document segments, linked to the source document and their position within it
- **Concept nodes** represent educational concepts extracted from the content
- **Edges between concepts** capture how they relate to each other (prerequisite, part-of, or general association)
- **CONTAINS edges** connect each Chunk to every Concept it mentions, allowing you to traverse from a concept back to the source material

## Data model

```
(Chunk)-[:CONTAINS]->(Concept)
(Concept)-[:PREREQUISITE_OF]->(Concept)
(Concept)-[:PART_OF]->(Concept)
(Concept)-[:RELATED_TO]->(Concept)
```

Node properties:

| Node | Properties |
|------|-----------|
| `Chunk` | `id` (unique), `source` (offering/document ID), `order` (chunk number) |
| `Concept` | `name` (unique), `description` |

All writes use `MERGE`, so re-running the pipeline on the same document is safe — no duplicate nodes or edges are created.

## Files

| File | Purpose |
|------|---------|
| `neo4j_client.py` | Low-level Neo4j connection and Cypher operations |
| `graph_ingestion.py` | `ingest(chunk, extracted)` — orchestrates a full write for one chunk |
| `setup_schema.py` | One-time script to create uniqueness constraints — **already run, do not run again** |
| `test_graph.py` | End-to-end test with fake data and a live verification query |
| `main.py` | Scratch file used during initial Neo4j connection setup |

## Setup

**1. Add credentials to `backend/.env`:**
```
NEO4J_URI=neo4j+ssc://<your-instance>.databases.neo4j.io
NEO4J_USERNAME=<username>
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=<database-name>
```

**2. Schema setup — ALREADY DONE, DO NOT RUN AGAIN:**

> `setup_schema.py` has already been run against the AuraDB instance. The uniqueness constraints on `Concept.name` and `Chunk.id` are live in the database. Running it again is harmless but unnecessary. Only run it if you are pointing the credentials at a brand new database instance.

**3. Run the test to verify the connection and writes:**
```bash
python -m graphdb.test_graph
```

The test creates a fake chunk about React Hooks, runs it through `ingest()`, then queries Neo4j directly to confirm the nodes and edges are present.

## Integration point

In `main.py` (the ingestion pipeline), call `ingest()` after `create_record()` and before the Pinecone upsert:

```python
from graphdb.graph_ingestion import ingest

record = pinecone_client.create_record(id=chunk_id, embeddings=vec, metadata=metadata)
ingest(record, extracted_concepts_dict)  # write to Neo4j
records.append(record)
```

The `extracted_concepts_dict` is expected in this format:

```json
{
    "chunk_id": "lec01_p1_c0",
    "concepts": [
        { "name": "Backpropagation", "description": "Algorithm for computing gradients in neural networks" }
    ],
    "relationships": [
        { "from": "Backpropagation", "to": "Gradient Descent", "type": "PREREQUISITE_OF" }
    ]
}
```

Valid relationship types: `PREREQUISITE_OF`, `RELATED_TO`, `PART_OF`.
