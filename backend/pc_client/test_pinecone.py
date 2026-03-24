from dotenv import load_dotenv
import os

from client import PineconeClient
from models.chunks import ChunkMetadata

# --------------- Init ------------------------

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "course-library"
DEFAULT_NAMESPACE = "test_namespace"  # in the format {course_id}_{semester_code}_{section}
DIM_SIZE = 10 # this is a placeholder value for now; actual value depends on the model


def main() -> None:
    """Simple smoke-test for Pinecone CRUD operations."""

    if not PINECONE_API_KEY:
        raise RuntimeError("Missing Pinecone API Key.")

    client = PineconeClient(
        api_key=PINECONE_API_KEY,
        index_name=INDEX_NAME,
        namespace=DEFAULT_NAMESPACE,
    )

    # --- Example record ---
    test_embeddings = [0.1] * DIM_SIZE

    metadata = ChunkMetadata(
        offering_id=DEFAULT_NAMESPACE,
        source_type="slides",
        topic="example",
        text="This is a test chunk.",
        chunk_number=1,
    )

    record = client.create_record(
        id="lec03_chunk_1",
        embeddings=test_embeddings,
        metadata=metadata,
    )

    client.upsert([record])

    fetch_res = client.fetch_by_id(["lec03_chunk_1"])
    print("Fetch Response:", fetch_res)

    query_res = client.query(test_embeddings, top_k=1)
    print("Query Response:", query_res)


if __name__ == "__main__":
    main()

