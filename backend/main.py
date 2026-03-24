import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from unstructured.pdf_text_extractor import PDFTextExtractor
from unstructured.text_chunker import TextChunker
from bedrock.embedder import BedrockEmbedder
from pc_client.client import PineconeClient
from pc_client.models.chunks import ChunkMetadata


def process_pdf(pdf_path: str, pinecone_index: str, pinecone_api_key: str, unstructured_api_key: str):
    """
    Orchestrates the full pipeline: extract -> chunk -> embed -> upsert
    """
  
    extractor = PDFTextExtractor(unstructured_api_key)
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)
    embedder = BedrockEmbedder()
    pinecone_client = PineconeClient(
        api_key=pinecone_api_key,
        index_name=pinecone_index
    )

    texts = extractor.extract_texts(pdf_path)
    print(f"Extracted {len(texts)} text elements")

    chunks = chunker.chunk_texts(texts)
    print(f"Created {len(chunks)} chunks")

    records = []
    offering_id = os.path.splitext(os.path.basename(pdf_path))[0]
    for chunk in chunks:
        vec = embedder.embed_data(chunk['chunk'])
        chunk_index = chunk['metadata'].get('chunk_index', 0)
        chunk_id = f"{offering_id}_p{chunk['metadata'].get('page_number', 1)}_c{chunk_index}"
        metadata = ChunkMetadata(
            offering_id=offering_id,
            source_type="textbook",
            topic=offering_id,
            text=chunk['chunk'],
            chunk_number=chunk_index + 1,
        )
        record = pinecone_client.create_record(
            id=chunk_id,
            embeddings=vec,
            metadata=metadata,
        )
        records.append(record)

    if records:
        pinecone_client.upsert(records)
        print(f"Upserted {len(records)} records to Pinecone")
    else:
        print("No records to upsert")


if __name__ == "__main__":
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(_script_dir, "unstructured", "input_files", "canvas_api_sow.pdf")
    pinecone_index = os.getenv("PINECONE_INDEX")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")

    if not pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY environment variable is required.")
    if not unstructured_api_key:
        raise RuntimeError("UNSTRUCTURED_API_KEY environment variable is required.")

    process_pdf(pdf_path, pinecone_index, pinecone_api_key, unstructured_api_key)