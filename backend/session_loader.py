"""
session_loader.py — Bootstraps a student learning session.

Resolves the active roadmap node from cache (or builds it from Neo4j on a
miss), fetches chunk text from Pinecone, then writes all session state to
Redis ready for the lesson generator.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

load_dotenv(_BACKEND / ".env")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_roadmap_entries(student_id: str, course: str) -> list[str]:
    """
    Build the roadmap from Neo4j, upsert each lesson to Supabase, and return
    an ordered list of lesson UUIDs.

    TODO: Confirm whether per-student roadmap nodes will eventually live
          directly in Neo4j (e.g. a :RoadmapNode label per student). If so,
          replace build_roadmap() with a targeted Cypher query.
    """
    from graphdb.roadmap_builder import build_roadmap
    from supabaseDB.supabase_client import upsert_lesson

    roadmap = build_roadmap(course=course)
    lesson_uuids: list[str] = []
    for lesson in roadmap["lessons"]:
        uuid = upsert_lesson(student_id, lesson)
        lesson_uuids.append(uuid)
    return lesson_uuids


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_roadmap(student_id: str, course: str) -> str:
    """
    Return the active lesson UUID for a student.

    Checks Supabase roadmap_cache first. On a miss, builds the roadmap from
    Neo4j, persists lessons to the lessons table and the ordered UUID list to
    roadmap_cache, then returns the UUID at the student's current position
    (defaults to index 0 when no position row exists yet).

    Args:
        student_id: The student's UUID.
        course: Course name used to filter the Neo4j graph (e.g. "accounting").

    Returns:
        UUID string of the active lesson row in the lessons table.

    Raises:
        ValueError: If no roadmap entries could be found or built.
    """
    from supabaseDB.supabase_client import get_cached_roadmap, save_roadmap_cache, get_roadmap_position

    lesson_uuids = get_cached_roadmap(student_id)
    if lesson_uuids is None:
        lesson_uuids = _build_roadmap_entries(student_id, course)
        if not lesson_uuids:
            raise ValueError(f"No roadmap entries found for student {student_id!r}")
        save_roadmap_cache(student_id, lesson_uuids)

    current_index = get_roadmap_position(student_id) or 0
    return lesson_uuids[min(current_index, len(lesson_uuids) - 1)]


def fetch_chunks(lesson_uuid: str, namespace: str) -> list[dict[str, Any]]:
    """
    Fetch chunk text from Pinecone for the given lesson.

    Looks up chunk_ids from the lessons table, then fetches text from Pinecone.

    Args:
        lesson_uuid: UUID of the lesson row in the lessons table.
        namespace: Pinecone namespace for the course (e.g. "15.501_Transcripts").

    Returns:
        List of {index: int, text: str} dicts in chunk order.
        Chunks missing from Pinecone are skipped.

    Raises:
        ValueError: If the lesson UUID is not found in Supabase.
    """
    from pinecone import Pinecone
    from supabaseDB.supabase_client import get_lesson

    lesson = get_lesson(lesson_uuid)
    if lesson is None:
        raise ValueError(f"Lesson {lesson_uuid!r} not found in Supabase.")

    chunk_ids: list[str] = lesson.get("chunk_ids") or []
    if not chunk_ids:
        return []

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX"))
    fetch_response = index.fetch(ids=chunk_ids, namespace=namespace)
    vectors = fetch_response.get("vectors") or fetch_response.vectors or {}

    chunks: list[dict[str, Any]] = []
    for i, chunk_id in enumerate(chunk_ids):
        vector = vectors.get(chunk_id)
        if vector is None:
            continue
        metadata = vector.get("metadata") or {}
        chunks.append({"index": i, "text": metadata.get("text", "")})

    return chunks


def start_session(student_id: str, mode: str, course: str, namespace: str) -> dict[str, Any]:
    """
    Orchestrate session initialisation for a student.

    Steps (in order):
      1. Fetch the student profile from Supabase.
      2. Resolve the active lesson UUID (roadmap_cache → Neo4j/lessons fallback).
      3. Fetch chunk text from Pinecone via the lessons table.
      4. Write student subset, mode, node_id, and chunks to Redis.
      5. Initialise block_index to 0, messages to [], attempt_count to 0.

    Args:
        student_id: The student's UUID.
        mode: Session mode — one of 'new_lesson', 'review', or 'retry'.
        course: Course name used to filter the Neo4j graph (e.g. "accounting").
        namespace: Pinecone namespace for the course (e.g. "15.501_Transcripts").

    Returns:
        Dict with keys: student, node_id, chunks, mode.

    NOTE: get_or_create_student() looks up students by *name*, not by ID, so it
          cannot be called with only a UUID. This function uses get_student_profile()
          instead. Pre-register the student via get_or_create_student() before
          starting a session; if the student row is absent a ValueError is raised.
    """
    from supabaseDB.supabase_client import get_student_profile
    from cacheing.redis_client import (
        write_student,
        write_mode,
        write_node_id,
        write_chunks,
        write_block_index,
        _init_messages,
        _init_attempt_count,
    )

    # 1. Student profile
    profile = get_student_profile(student_id)
    if profile is None:
        raise ValueError(
            f"Student {student_id!r} not found in Supabase. "
            "Register the student first via get_or_create_student()."
        )

    # 2. Active lesson UUID
    node_id = resolve_roadmap(student_id, course)

    # 3. Chunk text from Pinecone via lessons table
    chunks = fetch_chunks(node_id, namespace)

    # 4 & 5. Write session state to Redis
    write_student(student_id, profile)
    write_mode(student_id, mode)
    write_node_id(student_id, node_id)
    write_chunks(student_id, chunks)
    write_block_index(student_id, 0)
    _init_messages(student_id)
    _init_attempt_count(student_id)

    return {
        "student": {k: profile.get(k) for k in ("id", "name", "llm_profile", "preferred_formats", "learning_goals")},
        "node_id": node_id,
        "chunks": chunks,
        "mode": mode,
    }
