"""
End-to-end test for the Neo4j graph ingestion layer.
Run from backend/:
    python -m graphdb.test_graph
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from neo4j import GraphDatabase
from pc_client.models.chunks import CourseChunk, ChunkMetadata
from graphdb.graph_ingestion import ingest

# ------------------------------------------------------------------ #
# Fake data                                                           #
# ------------------------------------------------------------------ #
FAKE_CHUNK = CourseChunk(
    id="test_lec01_p1_c0",
    values=[0.0] * 1536,
    metadata=ChunkMetadata(
        offering_id="test_course",
        source_type="textbook",
        topic="React Fundamentals",
        text=(
            "React Hooks allow functional components to manage state and side effects. "
            "useState is a hook that returns a state variable and a setter function. "
            "useEffect runs after render and is used for side effects like data fetching."
        ),
        chunk_number=1,
    ),
)

FAKE_EXTRACTED = {
    "chunk_id": "test_lec01_p1_c0",
    "concepts": [
        {
            "name": "React Hooks",
            "description": "Functions that let you use state and lifecycle features in functional components",
        },
        {
            "name": "useState",
            "description": "A React Hook that adds a state variable to a functional component",
        },
        {
            "name": "useEffect",
            "description": "A React Hook for synchronising a component with an external system or side effect",
        },
        {
            "name": "Functional Component",
            "description": "A React component defined as a plain JavaScript function",
        },
    ],
    "relationships": [
        {"from": "useState",  "to": "React Hooks",         "type": "PART_OF"},
        {"from": "useEffect", "to": "React Hooks",         "type": "PART_OF"},
        {"from": "React Hooks", "to": "Functional Component", "type": "RELATED_TO"},
    ],
}


# ------------------------------------------------------------------ #
# Run ingestion                                                        #
# ------------------------------------------------------------------ #
def main():
    print("Running graph ingestion test...\n")
    ingest(FAKE_CHUNK, FAKE_EXTRACTED)

    # ------------------------------------------------------------------ #
    # Verification query                                                  #
    # ------------------------------------------------------------------ #
    uri      = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    print("Running verification queries against Neo4j...\n")

    with GraphDatabase.driver(uri, auth=(username, password)) as driver:

        # Chunk node
        records, _, _ = driver.execute_query(
            "MATCH (ch:Chunk {id: $id}) RETURN ch.id AS id, ch.source AS source, ch.order AS order",
            id=FAKE_CHUNK.id,
            database_=database,
        )
        if records:
            r = records[0]
            print(f"[verify] Chunk found     : id={r['id']}  source={r['source']}  order={r['order']}")
        else:
            print("[verify] ERROR: Chunk node not found!")

        # Concept nodes
        records, _, _ = driver.execute_query(
            """
            MATCH (ch:Chunk {id: $id})-[:CONTAINS]->(c:Concept)
            RETURN c.name AS name, c.description AS description
            """,
            id=FAKE_CHUNK.id,
            database_=database,
        )
        print(f"\n[verify] Concepts linked to chunk ({len(records)} found):")
        for r in records:
            print(f"         • {r['name']} — {r['description']}")

        # Relationships
        records, _, _ = driver.execute_query(
            """
            MATCH (a:Concept)-[r]->(b:Concept)
            WHERE a.name IN $names OR b.name IN $names
            RETURN a.name AS from, type(r) AS type, b.name AS to
            """,
            names=[c["name"] for c in FAKE_EXTRACTED["concepts"]],
            database_=database,
        )
        print(f"\n[verify] Concept relationships ({len(records)} found):")
        for r in records:
            print(f"         ({r['from']})-[:{r['type']}]->({r['to']})")

    print("\nVerification complete.")


if __name__ == "__main__":
    main()
