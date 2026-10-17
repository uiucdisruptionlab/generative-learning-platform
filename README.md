# Generative Learning Platform

An AI-powered educational platform that ingests course documents, builds vector search over them, and constructs a knowledge graph of the concepts they contain.

## Repository structure

```
generative-learning-platform/
├── backend/                  # Python ingestion pipeline and graph layer
│   ├── server.py             # FastAPI app
│   ├── ingestion/ingest_course.py  # Ingestion entry point
│   ├── pdf_ingest/           # PDF extraction and text chunking
│   ├── llm/                  # LLM and embedding client (Bedrock or OpenAI)
│   ├── pc_client/            # Pinecone client and data models
│   └── graphdb/              # Neo4j knowledge graph layer
└── frontend/                 # React frontend
```

## Ingestion pipeline

The pipeline lives in `backend/` and runs top to bottom for each document:

```
PDF file
  │
  ▼
PDFTextExtractor          (pdf_ingest/)
  Calls the Unstructured API with a VLM strategy (GPT-4o).
  Splits the document per page and returns a list of
  { text, metadata } dicts.
  │
  ▼
TextChunker               (pdf_ingest/)
  Uses LangChain's RecursiveCharacterTextSplitter.
  Produces overlapping chunks of ~500 characters,
  adding chunk_index and page_number to each chunk's metadata.
  │
  ▼
Embedder                  (llm/)
  Calls AWS Bedrock (amazon.titan-embed-text-v2:0).
  Returns a 1536-dimensional float vector for each chunk.
  │
  ▼
PineconeClient.create_record()   (pc_client/)
  Packages the chunk text, embedding vector, and metadata
  into a CourseChunk object.
  │
  ├──▶ graph_ingestion.ingest()  (graphdb/)       ← knowledge graph layer
  │      Writes Chunk and Concept nodes to Neo4j.
  │      See backend/graphdb/README.md for details.
  │
  ▼
PineconeClient.upsert()
  Batch-upserts CourseChunk records to Pinecone (50 at a time)
  under the configured index and namespace.
```

### Key data types

**`ChunkMetadata`** — attached to every chunk:
- `offering_id` — document/course identifier
- `source_type` — e.g. `"textbook"`, `"slides"`
- `topic` — used for retrieval biasing
- `text` — the raw chunk text
- `chunk_number` — position within the document

**`CourseChunk`** — the unit passed between pipeline stages:
- `id` — unique string, format `{offering_id}_p{page}_c{chunk_index}`
- `values` — embedding vector (`list[float]`)
- `metadata` — `ChunkMetadata` instance

### Running the pipeline

**Prerequisites:** fill in `backend/.env`:
```
PINECONE_API_KEY=...
PINECONE_INDEX=...
UNSTRUCTURED_API_KEY=...
AWS_REGION=us-east-1
NEO4J_URI=...
NEO4J_USERNAME=...
NEO4J_PASSWORD=...
NEO4J_DATABASE=...
```

**Ingest a folder of course PDFs:**
```bash
cd backend
python -m ingestion.ingest_course --course-id BIS512 --namespace BIS512 --folder sample_data/BIS512 --enable-graph-ingestion
```

Run `python -m ingestion.ingest_course --help` for the other options.

## Knowledge graph

See [`backend/graphdb/README.md`](backend/graphdb/README.md) for the Neo4j layer — data model, setup steps, and how to run the end-to-end test.
