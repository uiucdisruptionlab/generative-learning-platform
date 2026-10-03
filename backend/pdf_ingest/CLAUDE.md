# PDF Extraction and Chunking

First stage of ingestion: a PDF goes to Unstructured's hosted partition API (VLM strategy), and the returned text is split into overlapping chunks. Extraction needs `UNSTRUCTURED_API_KEY` and network access.

`smoke_extract.py` is a hand-run harness that calls the live API and writes to `output_files/`, which is git-ignored.

Chunk size and overlap decide how much text each Pinecone vector and Neo4j `Chunk` carries. Changing them means re-ingesting a course, not just redeploying.
