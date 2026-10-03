# Pinecone Client

`PineconeClient` wraps the Pinecone index for ingestion (`ingest_course.py`). Lesson retrieval in `lesson_generator.py` fetches from Pinecone directly. One Pinecone namespace holds one course offering, and `COURSE_NAMESPACES` in `lesson_generator.py` maps course names to namespaces.

`models/chunks.py` defines the record written at ingestion. The chunk text is stored in the vector's metadata and lessons are built from that metadata, so a record without `text` produces a lesson with no source material. `source_type` is restricted to `slides`, `notes`, `assignments` or `textbook`.

Chunk ids are shared with Neo4j `Chunk` nodes. Keep them identical in both stores.
