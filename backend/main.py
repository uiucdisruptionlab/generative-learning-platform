import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from unstructured.pdf_text_extractor import PDFTextExtractor
from unstructured.text_chunker import TextChunker
from bedrock.embedder import BedrockEmbedder
from concept_extractor import extract_concepts_from_chunk
from graphdb.graph_ingestion import ingest as ingest_graph
from pc_client.client import PineconeClient
from pc_client.models.chunks import ChunkMetadata, CourseChunk


def process_pdf(
    pdf_path: str,
    pinecone_index: str,
    pinecone_api_key: str,
    unstructured_api_key: str,
    enable_graph_ingestion: bool = False,
    graph_only: bool = False,
    namespace: str = "DL_Transcripts",
):
    """
    Orchestrates the full pipeline: extract -> chunk -> embed -> upsert.

    When enable_graph_ingestion is True, each chunk is also passed through the
    Bedrock concept extractor and written to Neo4j.

    When graph_only is True, skips embedding and Pinecone upsert entirely —
    useful when chunks are already in Pinecone and you only need the Neo4j graph.
    """

    extractor = PDFTextExtractor(unstructured_api_key)
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)

    texts = extractor.extract_texts(pdf_path)
    print(f"Extracted {len(texts)} text elements")

    chunks = chunker.chunk_texts(texts)
    print(f"Created {len(chunks)} chunks")

    offering_id = os.path.splitext(os.path.basename(pdf_path))[0]

    if not graph_only:
        embedder = BedrockEmbedder()
        pinecone_client = PineconeClient(
            api_key=pinecone_api_key,
            index_name=pinecone_index,
            namespace=namespace,
        )

    records = []
    for chunk in chunks:
        chunk_text = chunk["chunk"]
        chunk_index = chunk["metadata"].get("chunk_index", 0)
        chunk_id = f"{offering_id}_p{chunk['metadata'].get('page_number', 1)}_c{chunk_index}"
        metadata = ChunkMetadata(
            offering_id=offering_id,
            source_type="textbook",
            topic=offering_id,
            text=chunk_text,
            chunk_number=chunk_index + 1,
        )
        course_chunk = CourseChunk(id=chunk_id, values=[] if graph_only else embedder.embed_data(chunk_text), metadata=metadata)

        if not graph_only:
            records.append(course_chunk.to_pinecone_record())

        if enable_graph_ingestion:
            try:
                extracted = extract_concepts_from_chunk(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "metadata": chunk.get("metadata", {}),
                    }
                )
                ingest_graph(course_chunk, extracted)
            except Exception as exc:
                print(f"[graph] Skipping chunk {chunk_id}: {exc}")

    if not graph_only:
        if records:
            pinecone_client.upsert(records)
            print(f"Upserted {len(records)} records to Pinecone")
        else:
            print("No records to upsert")


def process_folder(folder_path, pinecone_index, pinecone_api_key, unstructured_api_key):
    if not os.path.exists(folder_path):
        raise RuntimeError(f"Folder does not exist: {folder_path}")

    files = os.listdir(folder_path)

    pdf_files = [f for f in files if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("No PDF files found in folder.")
        return

    print(f"Found {len(pdf_files)} PDF(s). Processing...\n")

    for file_name in pdf_files:
        pdf_path = os.path.join(folder_path, file_name)

        try:
            print(f"Processing: {file_name}")
            process_pdf(pdf_path, pinecone_index, pinecone_api_key, unstructured_api_key)
            print(f"Finished: {file_name}\n")
        except Exception as e:
            print(f"Error processing {file_name}: {e}\n")


if __name__ == "__main__":
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    pinecone_index = os.getenv("PINECONE_INDEX")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")
    enable_graph_ingestion = os.getenv("ENABLE_GRAPH_INGESTION", "false").lower() == "true"
    graph_only = os.getenv("GRAPH_ONLY", "false").lower() == "true"

    if not unstructured_api_key:
        raise RuntimeError("UNSTRUCTURED_API_KEY environment variable is required.")
    if not graph_only and not pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY environment variable is required.")

    # --- Configure which file/folder to process ---
    file_path = os.path.join(_script_dir, "sample_data", "accounting", "ALecFinal.pdf")

    process_pdf(
        file_path,
        pinecone_index,
        pinecone_api_key,
        unstructured_api_key,
        enable_graph_ingestion=enable_graph_ingestion,
        graph_only=graph_only,
    )
