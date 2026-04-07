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

def get_lessons_by_course(course_id: str) -> list[dict]:
    with _driver() as driver:
        records, _, _ = driver.execute_query(
            """
            MATCH (l:Lesson {course_id: $course_id})
            OPTIONAL MATCH (prereq:Lesson)-[:PREREQUISITE_OF]->(l)
            RETURN l.id AS lesson_id, l.title AS title, collect(prereq.id) AS prerequisites
            ORDER BY size((()-[:PREREQUISITE_OF]->(l))) ASC
            """,
            course_id=course_id,
            database_=_DATABASE,
        )
    return [
        {
            "lesson_id": r["lesson_id"],
            "title": r["title"],
            "prerequisites": list(r["prerequisites"]),
        }
        for r in records
    ]


def create_course(course_id: str) -> None:
    with _driver() as driver:
        driver.execute_query(
            "MERGE (co:Course {id: $course_id})",
            course_id=course_id,
            database_=_DATABASE,
        )


def create_lecture(lecture_id: str, course_id: str | None = None, title: str | None = None) -> None:
    with _driver() as driver:
        driver.execute_query(
            """
            MERGE (le:Lecture {id: $lecture_id})
            SET le.course_id = COALESCE($course_id, le.course_id),
                le.title = COALESCE($title, le.title)
            """,
            lecture_id=lecture_id,
            course_id=course_id,
            title=title,
            database_=_DATABASE,
        )


def link_course_to_lecture(course_id: str, lecture_id: str) -> None:
    with _driver() as driver:
        driver.execute_query(
            """
            MATCH (co:Course {id: $course_id})
            MATCH (le:Lecture {id: $lecture_id})
            MERGE (co)-[:HAS_LECTURE]->(le)
            """,
            course_id=course_id,
            lecture_id=lecture_id,
            database_=_DATABASE,
        )


def link_lecture_to_chunk(lecture_id: str, chunk_id: str) -> None:
    with _driver() as driver:
        driver.execute_query(
            """
            MATCH (le:Lecture {id: $lecture_id})
            MATCH (ch:Chunk {id: $chunk_id})
            MERGE (le)-[:HAS_CHUNK]->(ch)
            """,
            lecture_id=lecture_id,
            chunk_id=chunk_id,
            database_=_DATABASE,
        )


def get_concepts_by_lecture(lecture_id: str) -> list[dict[str, str]]:
    with _driver() as driver:
        records, _, _ = driver.execute_query(
            """
            MATCH (le:Lecture {id: $lecture_id})-[:HAS_CHUNK]->(ch:Chunk)-[:CONTAINS]->(c:Concept)
            RETURN DISTINCT c.name AS name, c.description AS description
            """,
            lecture_id=lecture_id,
            database_=_DATABASE,
        )
    return [{"name": r["name"], "description": r["description"]} for r in records]


def get_concept_graph_by_lecture(lecture_id: str) -> dict:
    with _driver() as driver:
        concept_records, _, _ = driver.execute_query(
            """
            MATCH (le:Lecture {id: $lecture_id})-[:HAS_CHUNK]->(ch:Chunk)-[:CONTAINS]->(c:Concept)
            RETURN DISTINCT c.name AS name, c.description AS description, le.id AS lecture_id
            """,
            lecture_id=lecture_id,
            database_=_DATABASE,
        )
        relationship_records, _, _ = driver.execute_query(
            """
            MATCH (le:Lecture {id: $lecture_id})-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS]->(a:Concept)-[r]->(b:Concept)
            WHERE EXISTS {
                MATCH (:Lecture {id: $lecture_id})-[:HAS_CHUNK]->(:Chunk)-[:CONTAINS]->(b)
            }
            RETURN DISTINCT a.name AS from, type(r) AS type, b.name AS to, le.id AS lecture_id
            """,
            lecture_id=lecture_id,
            database_=_DATABASE,
        )
        chunk_records, _, _ = driver.execute_query(
            """
            MATCH (le:Lecture {id: $lecture_id})-[:HAS_CHUNK]->(ch:Chunk)-[:CONTAINS]->(c:Concept)
            RETURN ch.id AS chunk_id, le.id AS lecture_id, ch.order AS chunk_order, c.name AS concept_name
            """,
            lecture_id=lecture_id,
            database_=_DATABASE,
        )

    return {
        "lecture_id": lecture_id,
        "concepts": [record.data() for record in concept_records],
        "relationships": [record.data() for record in relationship_records],
        "chunk_links": [record.data() for record in chunk_records],
    }


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


def get_concept_graph() -> dict:
    with _driver() as driver:
        concept_records, _, _ = driver.execute_query(
            "MATCH (c:Concept) RETURN c.name AS name, c.description AS description",
            database_=_DATABASE,
        )
        relationship_records, _, _ = driver.execute_query(
            """
            MATCH (a:Concept)-[r]->(b:Concept)
            RETURN a.name AS from, type(r) AS type, b.name AS to
            """,
            database_=_DATABASE,
        )
        chunk_records, _, _ = driver.execute_query(
            """
            MATCH (ch:Chunk)-[:CONTAINS]->(c:Concept)
            OPTIONAL MATCH (le:Lecture)-[:HAS_CHUNK]->(ch)
            OPTIONAL MATCH (co:Course)-[:HAS_LECTURE]->(le)
            RETURN ch.id AS chunk_id,
                   ch.source AS chunk_source,
                   le.id AS lecture_id,
                   co.id AS course_id,
                   ch.order AS chunk_order,
                   c.name AS concept_name
            """,
            database_=_DATABASE,
        )

    return {
        "concepts": [record.data() for record in concept_records],
        "relationships": [record.data() for record in relationship_records],
        "chunk_links": [record.data() for record in chunk_records],
    }
