import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_URI      = os.getenv("NEO4J_URI")
_USERNAME = os.getenv("NEO4J_USERNAME")
_PASSWORD = os.getenv("NEO4J_PASSWORD")
_DATABASE = os.getenv("NEO4J_DATABASE")

_VALID_REL_TYPES = {"PREREQUISITE_OF", "RELATED_TO", "PART_OF"}


def _driver():
    return GraphDatabase.driver(_URI, auth=(_USERNAME, _PASSWORD))


def get_all_concepts() -> list[str]:
    with _driver() as driver:
        records, _, _ = driver.execute_query(
            "MATCH (c:Concept) RETURN c.name AS name",
            database_=_DATABASE,
        )
    return [r["name"] for r in records]


def create_chunk(id: str, source: str, order: int) -> None:
    with _driver() as driver:
        driver.execute_query(
            "MERGE (ch:Chunk {id: $id}) SET ch.source = $source, ch.order = $order",
            id=id, source=source, order=order,
            database_=_DATABASE,
        )


def create_concept(name: str, description: str) -> None:
    with _driver() as driver:
        driver.execute_query(
            "MERGE (c:Concept {name: $name}) SET c.description = $description",
            name=name, description=description,
            database_=_DATABASE,
        )


def create_relationship(from_concept: str, to_concept: str, type: str) -> None:
    if type not in _VALID_REL_TYPES:
        raise ValueError(f"Relationship type must be one of {_VALID_REL_TYPES}, got '{type}'")

    query = (
        f"MATCH (a:Concept {{name: $from_concept}}) "
        f"MATCH (b:Concept {{name: $to_concept}}) "
        f"MERGE (a)-[:{type}]->(b)"
    )
    with _driver() as driver:
        driver.execute_query(
            query,
            from_concept=from_concept, to_concept=to_concept,
            database_=_DATABASE,
        )


def link_chunk_to_concept(chunk_id: str, concept_name: str) -> None:
    with _driver() as driver:
        driver.execute_query(
            """
            MATCH (ch:Chunk {id: $chunk_id})
            MATCH (c:Concept {name: $concept_name})
            MERGE (ch)-[:CONTAINS]->(c)
            """,
            chunk_id=chunk_id, concept_name=concept_name,
            database_=_DATABASE,
        )
