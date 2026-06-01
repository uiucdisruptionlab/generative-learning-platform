from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from bedrock.embedder import BedrockEmbedder
from concept_extractor import extract_concepts_from_chunk
from graphdb.graph_ingestion import ingest as ingest_graph
from pc_client.client import PineconeClient
from pc_client.models.chunks import ChunkMetadata, CourseChunk
from unstructured.pdf_text_extractor import PDFTextExtractor
from unstructured.text_chunker import TextChunker


load_dotenv(Path(__file__).resolve().parent / ".env")


def lecture_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(?:lec|lecture)[_\-\s]*(\d+)", path.stem, flags=re.IGNORECASE)
    if match:
        return (int(match.group(1)), path.name.lower())
    return (10**9, path.name.lower())


def lecture_id_for(course_id: str, pdf_path: Path) -> str:
    match = re.search(r"(?:lec|lecture)[_\-\s]*(\d+)", pdf_path.stem, flags=re.IGNORECASE)
    if match:
        return f"{course_id}_Lec{int(match.group(1))}"
    clean = re.sub(r"[^A-Za-z0-9]+", "_", pdf_path.stem).strip("_")
    return f"{course_id}_{clean}"


def lecture_number_from_pdf(pdf_path: Path) -> int:
    match = re.search(r"(?:lec|lecture)[_\-\s]*(\d+)", pdf_path.stem, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 10**9


def ingest_pdf(
    pdf_path: Path,
    course_id: str,
    course_title: str,
    pinecone_index: str,
    pinecone_api_key: str,
    unstructured_api_key: str,
    enable_graph_ingestion: bool,
    graph_only: bool,
    namespace: str,
) -> None:
    extractor = PDFTextExtractor(unstructured_api_key)
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)
    offering_id = lecture_id_for(course_id, pdf_path)

    texts = extractor.extract_texts(str(pdf_path))
    print(f"[{offering_id}] Extracted {len(texts)} text elements")
    chunks = chunker.chunk_texts(texts)
    print(f"[{offering_id}] Created {len(chunks)} chunks")

    embedder = None if graph_only else BedrockEmbedder()
    pinecone_client = None
    if not graph_only:
        pinecone_client = PineconeClient(
            api_key=pinecone_api_key,
            index_name=pinecone_index,
            namespace=namespace,
        )

    records = []
    for chunk in chunks:
        chunk_text = chunk["chunk"]
        chunk_index = int(chunk["metadata"].get("chunk_index", 0))
        page_number = int(chunk["metadata"].get("page_number", 1))
        chunk_id = f"{offering_id}_p{page_number}_c{chunk_index}"
        metadata = ChunkMetadata(
            offering_id=offering_id,
            source_type="slides",
            topic=course_title,
            text=chunk_text,
            chunk_number=chunk_index + 1,
            course_id=course_id,
        )
        values = [] if graph_only else embedder.embed_data(chunk_text)
        course_chunk = CourseChunk(id=chunk_id, values=values, metadata=metadata)

        if not graph_only:
            records.append(course_chunk.to_pinecone_record())

        if enable_graph_ingestion:
            extracted = {
                "chunk_id": chunk_id,
                "concepts": [],
                "relationships": [],
            }
            try:
                extracted = extract_concepts_from_chunk(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "metadata": chunk.get("metadata", {}),
                    }
                )
            except Exception as exc:
                print(f"[{offering_id}] concept extraction failed for {chunk_id}: {exc}. Continuing with chunk-only graph ingest.")
            ingest_graph(course_chunk, extracted)

    if pinecone_client and records:
        pinecone_client.upsert(records)
        print(f"[{offering_id}] Upserted {len(records)} records to Pinecone namespace {namespace!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a folder of course PDFs into Pinecone and Neo4j.")
    parser.add_argument("--course-id", default="BIS512")
    parser.add_argument("--course-title", default="Financing Economic Development")
    parser.add_argument("--folder", default=str(Path(__file__).parent / "sample_data" / "BIS512"))
    parser.add_argument("--namespace", default="BIS512")
    parser.add_argument("--graph-only", action="store_true")
    parser.add_argument("--enable-graph-ingestion", action="store_true")
    parser.add_argument(
        "--min-lecture",
        type=int,
        default=1,
        help="Skip PDFs whose lecture number is below this value (ALecFinal always included when present).",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise RuntimeError(f"Folder does not exist: {folder}")

    pinecone_index = os.getenv("PINECONE_INDEX", "")
    pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
    unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY", "")
    if not unstructured_api_key:
        print("UNSTRUCTURED_API_KEY not set. Falling back to local PDF text extraction via pypdf.")
    if not args.graph_only and (not pinecone_api_key or not pinecone_index):
        raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX are required unless --graph-only is set.")

    pdfs = sorted(folder.glob("*.pdf"), key=lecture_sort_key)
    if not pdfs:
        raise RuntimeError(f"No PDFs found in {folder}")

    for pdf_path in pdfs:
        lec_num = lecture_number_from_pdf(pdf_path)
        is_final = pdf_path.stem.lower() == "alecfinal"
        if lec_num < args.min_lecture and not is_final:
            print(f"Skipping {pdf_path.name} (--min-lecture {args.min_lecture})")
            continue
        print(f"Processing {pdf_path.name}")
        ingest_pdf(
            pdf_path=pdf_path,
            course_id=args.course_id,
            course_title=args.course_title,
            pinecone_index=pinecone_index,
            pinecone_api_key=pinecone_api_key,
            unstructured_api_key=unstructured_api_key,
            enable_graph_ingestion=args.enable_graph_ingestion,
            graph_only=args.graph_only,
            namespace=args.namespace,
        )


if __name__ == "__main__":
    main()
