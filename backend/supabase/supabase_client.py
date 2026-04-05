"""
Supabase read/write for GLP — students, content_items, recommendations, content_interactions.
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
