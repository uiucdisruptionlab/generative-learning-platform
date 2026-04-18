"""
Supabase read/write for GLP — students, content_items, recommendations, content_interactions,
roadmap_cache, roadmap_position, srs_records.
No LLM, Neo4j, or LangChain code here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# Repo root: .../generative-learning-platform (this file is backend/supabase/...)
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# Matches seed_students.sql — use for local demo after seeding.
DEMO_STUDENT_ALICE_ID = "a0000001-0000-4000-8000-000000000001"


def _env_strip(name: str) -> str:
    raw = os.environ.get(name, "") or ""
    return raw.strip().strip('"\'' "\u201c\u201d\u2018\u2019")


def get_supabase_client() -> Client:
    url = _env_strip("SUPABASE_URL")
    key = _env_strip("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Set SUPABASE_URL and SUPABASE_KEY in .env (straight double quotes)."
        )
    return create_client(url, key)


def get_student_profile(
    student_id: str,
    *,
    client: Optional[Client] = None,
) -> Optional[dict[str, Any]]:
    """Return one student row (all columns) or None if not found."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("students")
        .select("*")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def get_student(
    student_id: str,
    *,
    client: Optional[Client] = None,
) -> Optional[dict[str, Any]]:
    """Alias for get_student_profile. Return one student row (all columns) or None if not found."""
    return get_student_profile(student_id, client=client)


def create_student(
    student_data: dict[str, Any],
    *,
    client: Optional[Client] = None,
) -> dict[str, Any]:
    """
    Create a new student record. Required: name.

    Accepted keys: name, academic_level, major_or_field, learning_goals (dict → jsonb),
    interests (list), weekly_hours (int), preferred_formats (list), llm_profile (dict → jsonb).
    Returns the complete student record including id, created_at, and updated_at.
    """
    if not student_data.get("name"):
        raise ValueError("student_data must include non-empty 'name'")

    # Prepare the row data, filtering out None values
    row = {
        "name": str(student_data["name"]),
        "academic_level": student_data.get("academic_level"),
        "major_or_field": student_data.get("major_or_field"),
        "learning_goals": student_data.get("learning_goals"),
        "interests": student_data.get("interests"),
        "weekly_hours": student_data.get("weekly_hours"),
        "preferred_formats": student_data.get("preferred_formats"),
        "llm_profile": student_data.get("llm_profile"),
    }
    # Drop keys that are None so defaults / DB nulls stay clean
    row = {k: v for k, v in row.items() if v is not None}

    supabase = client or get_supabase_client()
    response = supabase.table("students").insert(row).execute()
    data = response.data or []
    if not data:
        raise RuntimeError("create_student: no row returned from Supabase")
    return data[0]


def get_or_create_student(
    student_data: dict[str, Any],
    *,
    client: Optional[Client] = None,
) -> tuple[dict[str, Any], bool]:
    """
    Get existing student by name, or create new one if not found.
    Returns (student_dict, created_bool) where created_bool is True if student was created.
    """
    if not student_data.get("name"):
        raise ValueError("student_data must include non-empty 'name'")

    name = student_data["name"]
    supabase = client or get_supabase_client()

    # Try to find existing student by name
    response = (
        supabase.table("students")
        .select("*")
        .eq("name", name)
        .limit(1)
        .execute()
    )
    rows = response.data or []

    if rows:
        # Student exists
        return rows[0], False
    else:
        # Create new student
        student = create_student(student_data, client=client)
        return student, True


def insert_content_item(
    lesson: dict[str, Any],
    *,
    client: Optional[Client] = None,
) -> str:
    """
    Insert a lesson-like dict into content_items. Required: title.

    Accepted keys: title, summary, content_type, difficulty, url, topics (list or dict → jsonb).
    Returns the new content item UUID string.
    """
    if not lesson.get("title"):
        raise ValueError("lesson must include non-empty 'title'")

    topics = lesson.get("topics")
    if topics is not None and not isinstance(topics, (list, dict)):
        topics = [topics]

    row = {
        "title": str(lesson["title"]),
        "summary": lesson.get("summary"),
        "content_type": lesson.get("content_type"),
        "difficulty": lesson.get("difficulty"),
        "url": lesson.get("url"),
        "topics": topics,
    }
    # Drop keys that are None so defaults / DB nulls stay clean
    row = {k: v for k, v in row.items() if v is not None}

    supabase = client or get_supabase_client()
    response = supabase.table("content_items").insert(row).execute()
    data = response.data or []
    if not data:
        raise RuntimeError("insert_content_item: no row returned from Supabase")
    return str(data[0]["id"])


def insert_recommendation(
    student_id: str,
    content_id: str,
    score: float,
    explanation: str,
    *,
    client: Optional[Client] = None,
) -> dict[str, Any]:
    """Insert one recommendation row; channel and status are fixed for the knowledge graph."""
    supabase = client or get_supabase_client()
    row = {
        "student_id": student_id,
        "content_id": content_id,
        "channel": "knowledge_graph",
        "score": float(score),
        "explanation": explanation or "",
        "status": "pending",
    }
    response = supabase.table("recommendations").insert(row).execute()
    data = response.data or []
    if not data:
        raise RuntimeError("insert_recommendation: no row returned from Supabase")
    return data[0]


def insert_content_interaction(
    student_id: str,
    content_id: str,
    interaction_type: str,
    *,
    client: Optional[Client] = None,
) -> dict[str, Any]:
    """Log a student action on a content item."""
    supabase = client or get_supabase_client()
    row = {
        "student_id": student_id,
        "content_id": content_id,
        "interaction_type": interaction_type,
    }
    response = supabase.table("content_interactions").insert(row).execute()
    data = response.data or []
    if not data:
        raise RuntimeError("insert_content_interaction: no row returned from Supabase")
    return data[0]


def get_recommendations(
    student_id: str,
    *,
    client: Optional[Client] = None,
) -> list[dict[str, Any]]:
    """All recommendations for a student with nested content_items, highest score first."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("recommendations")
        .select("*, content_items(*)")
        .eq("student_id", student_id)
        .order("score", desc=True)
        .execute()
    )
    return list(response.data or [])


def clear_recommendations(
    student_id: str,
    *,
    client: Optional[Client] = None,
) -> None:
    """Delete every recommendation row for this student (test resets)."""
    supabase = client or get_supabase_client()
    supabase.table("recommendations").delete().eq("student_id", student_id).execute()


def get_cached_roadmap(
    student_id: str,
    node_ids: list[str],
    *,
    client: Optional[Client] = None,
) -> Optional[dict[str, Any]]:
    """Return cached roadmap row if student_id and node_ids match exactly, or None if not found."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("roadmap_cache")
        .select("*")
        .eq("student_id", student_id)
        .eq("node_ids", node_ids)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def save_roadmap_cache(
    student_id: str,
    node_ids: list[str],
    *,
    client: Optional[Client] = None,
) -> str:
    """Insert a new roadmap cache entry for a student. Returns the new row's UUID."""
    supabase = client or get_supabase_client()
    row = {"student_id": student_id, "node_ids": node_ids}
    response = supabase.table("roadmap_cache").insert(row).execute()
    data = response.data or []
    if not data:
        raise RuntimeError("save_roadmap_cache: no row returned from Supabase")
    return str(data[0]["id"])


def get_roadmap_position(
    student_id: str,
    *,
    client: Optional[Client] = None,
) -> Optional[int]:
    """Return the current_index for a student's roadmap position, or None if not found."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("roadmap_position")
        .select("current_index")
        .eq("student_id", student_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0]["current_index"] if rows else None


def update_roadmap_position(
    student_id: str,
    current_index: int,
    *,
    client: Optional[Client] = None,
) -> dict[str, Any]:
    """Update or create the current_index for a student's roadmap position. Returns the updated row."""
    supabase = client or get_supabase_client()
    
    # First try to update existing position
    response = (
        supabase.table("roadmap_position")
        .update({"current_index": current_index})
        .eq("student_id", student_id)
        .execute()
    )
    
    if response.data:
        # Update succeeded
        return response.data[0]
    else:
        # No existing position, create new one
        row = {"student_id": student_id, "current_index": current_index}
        response = supabase.table("roadmap_position").insert(row).execute()
        data = response.data or []
        if not data:
            raise RuntimeError("update_roadmap_position: no row returned from Supabase")
        return data[0]


def get_due_reviews(
    *,
    client: Optional[Client] = None,
) -> list[dict[str, Any]]:
    """Get all SRS records that are due for review, ordered by most overdue first."""
    supabase = client or get_supabase_client()
    response = (
        supabase.table("srs_records")
        .select("*")
        .lte("next_review_at", "now()")  # next_review_at <= current time
        .order("next_review_at", desc=False)  # oldest (most overdue) first
        .execute()
    )
    return list(response.data or [])


def upsert_srs_record(
    node_id: str,
    ease_factor: float,
    interval_days: int,
    next_review_at: str,  # ISO timestamp string
    last_reviewed_at: Optional[str] = None,  # ISO timestamp string
    *,
    client: Optional[Client] = None,
) -> dict[str, Any]:
    """
    Insert or update an SRS record for a node.
    If record exists for node_id, updates it; otherwise creates new record.
    Returns the upserted record.
    """
    row = {
        "node_id": node_id,
        "ease_factor": float(ease_factor),
        "interval_days": int(interval_days),
        "next_review_at": next_review_at,
    }
    if last_reviewed_at is not None:
        row["last_reviewed_at"] = last_reviewed_at

    supabase = client or get_supabase_client()
    response = supabase.table("srs_records").upsert(row).execute()
    data = response.data or []
    if not data:
        raise RuntimeError("upsert_srs_record: no row returned from Supabase")
    return data[0]


if __name__ == "__main__":
    sb = get_supabase_client()
    alice = DEMO_STUDENT_ALICE_ID

    profile = get_student_profile(alice, client=sb)
    if not profile:
        print(
            "Alice not found. Run backend/seed_students.sql in Supabase, then retry.\n"
        )
        raise SystemExit(1)

    print("Alice profile (excerpt):")
    print(f"  name={profile.get('name')!r}, major={profile.get('major_or_field')!r}")
    print(f"  preferred_formats={profile.get('preferred_formats')}")
    print(f"  llm_profile keys: {list((profile.get('llm_profile') or {}).keys())}\n")

    mock_lesson = {
        "title": "Demo: Variables and assignment (Python)",
        "summary": "Short lesson on names, binding, and basic types for beginners.",
        "content_type": "lesson",
        "difficulty": "beginner",
        "url": "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/",
        "topics": ["python", "variables", "assignment"],
    }

    clear_recommendations(alice, client=sb)
    new_id = insert_content_item(mock_lesson, client=sb)
    print(f"Inserted content_item id={new_id}")

    insert_recommendation(
        alice,
        new_id,
        score=0.92,
        explanation="Start here — foundational syntax before control flow.",
        client=sb,
    )
    insert_content_interaction(
        alice,
        new_id,
        interaction_type="demo_script_insert",
        client=sb,
    )

    recs = get_recommendations(alice, client=sb)
    print(f"\nRecommendations for Alice ({len(recs)}):")
    for r in recs:
        item = r.get("content_items") or {}
        title = item.get("title", "?") if isinstance(item, dict) else "?"
        print(
            f"  score={r.get('score')} | {title!r} | {r.get('explanation', '')[:60]}..."
        )
