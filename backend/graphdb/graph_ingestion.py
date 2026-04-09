import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pc_client.models.chunks import CourseChunk
from graphdb.neo4j_client import (
    create_course,
    get_all_concepts,
    create_lecture,
    create_chunk,
    create_concept,
    create_relationship,
    link_course_to_lecture,
    link_lecture_to_chunk,
    link_chunk_to_concept,
)


def _derive_course_id(chunk: CourseChunk) -> str:
    course_id = getattr(chunk.metadata, "course_id", None)
    if course_id:
        return str(course_id)

    offering_id = chunk.metadata.offering_id
    if "_" in offering_id:
        return offering_id.split("_", 1)[0]

    letters = "".join(ch for ch in offering_id if ch.isalpha())
    return letters or offering_id


def ingest(chunk: CourseChunk, extracted: dict) -> None:
    """
    Write extracted concepts and relationships to Neo4j.

    Parameters
    ----------
    chunk     : CourseChunk — the source chunk from the ingestion pipeline
    extracted : dict with keys:
                  "chunk_id"      : str
                  "concepts"      : list of {"name": str, "description": str}
                  "relationships" : list of {"from": str, "to": str, "type": str}
    """
    print(f"\n{'='*60}")
    print(f"[graph_ingestion] Processing chunk: {chunk.id}")
    print(f"{'='*60}")

  
    # 1. Fetch existing concepts so we can detect reuse vs. new creation  
    existing = set(get_all_concepts())
    print(f"[neo4j] Found {len(existing)} existing concept(s) in graph")
    if existing:
        print(f"         {sorted(existing)}")

    # 2. Ensure the Chunk node exists                                      
    create_chunk(
        id=chunk.id,
        source=chunk.metadata.offering_id,
        order=chunk.metadata.chunk_number,
    )
    print(f"[neo4j] Chunk node merged: {chunk.id}")

    course_id = _derive_course_id(chunk)
    lecture_id = chunk.metadata.offering_id
    create_course(course_id)
    create_lecture(lecture_id, course_id=course_id, title=chunk.metadata.topic)
    link_course_to_lecture(course_id, lecture_id)
    link_lecture_to_chunk(lecture_id, chunk.id)
    print(f"[neo4j] Course/Lecture structure merged: {course_id} -> {lecture_id} -> {chunk.id}")


    # 3. Create concepts (reuse existing ones where name matches)         
    created_concepts = []
    reused_concepts  = []

    for concept in extracted.get("concepts", []):
        name        = concept["name"]
        description = concept["description"]

        if name in existing:
            reused_concepts.append(name)
            print(f"[neo4j] Concept reused:  '{name}'")
        else:
            create_concept(name, description)
            existing.add(name)          # keep local set in sync
            created_concepts.append(name)
            print(f"[neo4j] Concept created: '{name}'  —  {description}")


    # 4. Create relationships between concepts                            
    relationships_written = []

    for rel in extracted.get("relationships", []):
        from_name = rel["from"]
        to_name   = rel["to"]
        rel_type  = rel["type"]

        if from_name not in existing:
            print(f"[neo4j] WARNING: skipping relationship — source concept '{from_name}' not in graph")
            continue
        if to_name not in existing:
            print(f"[neo4j] WARNING: skipping relationship — target concept '{to_name}' not in graph")
            continue

        create_relationship(from_name, to_name, rel_type)
        relationships_written.append((from_name, rel_type, to_name))
        print(f"[neo4j] Relationship merged: ({from_name})-[:{rel_type}]->({to_name})")

  
    # 5. Link every concept to the chunk via CONTAINS edge               
    all_concept_names = [c["name"] for c in extracted.get("concepts", [])]
    for name in all_concept_names:
        link_chunk_to_concept(chunk.id, name)
        print(f"[neo4j] Linked chunk '{chunk.id}' -[:CONTAINS]-> '{name}'")

  
    # 6. Summary                                                          
    print(f"\n[summary] Chunk          : {chunk.id}")
    print(f"[summary] Concepts created: {len(created_concepts)}  {created_concepts}")
    print(f"[summary] Concepts reused : {len(reused_concepts)}  {reused_concepts}")
    print(f"[summary] Relationships   : {len(relationships_written)}")
    for r in relationships_written:
        print(f"           ({r[0]})-[:{r[1]}]->({r[2]})")
    print(f"[summary] CONTAINS edges  : {len(all_concept_names)}")
    print(f"{'='*60}\n")
