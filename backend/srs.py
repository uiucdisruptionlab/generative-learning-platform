from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
PASSING_SCORE = 3


def clamp_quality(score: int | float) -> int:
    return max(0, min(5, int(round(score))))


def run_sm2(score: int | float, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the next SM-2 scheduling state for a 0-5 quality score."""
    quality = clamp_quality(score)
    previous = previous or {}

    old_repetitions = int(previous.get("repetitions") or 0)
    old_interval = int(
        previous.get("interval_days") or previous.get("interval") or 0
    )
    old_ease = float(previous.get("ease_factor") or DEFAULT_EASE_FACTOR)

    ease_factor = old_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease_factor = max(MIN_EASE_FACTOR, ease_factor)

    if quality < PASSING_SCORE:
        repetitions = 0
        interval_days = 1
    else:
        repetitions = old_repetitions + 1
        if repetitions == 1:
            interval_days = 1
        elif repetitions == 2:
            interval_days = 6
        else:
            interval_days = max(1, round(max(old_interval, 1) * ease_factor))

    reviewed_at = datetime.now(timezone.utc)
    next_review_at = reviewed_at + timedelta(days=interval_days)

    return {
        "quality": quality,
        "ease_factor": round(ease_factor, 4),
        "interval_days": interval_days,
        "repetitions": repetitions,
        "last_reviewed_at": reviewed_at.isoformat(),
        "next_review_at": next_review_at.isoformat(),
        "next_review_date": next_review_at.date().isoformat(),
    }


def get_srs_record(
    student_id: str,
    concept_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    response = (
        client.table("srs_records")
        .select("*")
        .eq("student_id", student_id)
        .eq("concept_id", concept_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def upsert_srs_record(
    *,
    student_id: str,
    concept_id: str | None = None,
    node_id: str | None = None,
    course: str | None,
    score: int | float,
    metadata: dict[str, Any] | None,
    client: Client,
) -> dict[str, Any]:
    concept_id = concept_id or node_id
    if not concept_id:
        raise ValueError("concept_id is required")

    previous = get_srs_record(student_id, concept_id, client=client)
    schedule = run_sm2(score, previous)

    row = {
        "student_id": student_id,
        "concept_id": concept_id,
        "node_id": concept_id,
        "score": schedule["quality"],
        "ease_factor": schedule["ease_factor"],
        "interval_days": schedule["interval_days"],
        "repetitions": schedule["repetitions"],
        "next_review_at": schedule["next_review_at"],
    }
    row = {key: value for key, value in row.items() if value is not None}

    response = (
        client.table("srs_records")
        .upsert(row, on_conflict="student_id,concept_id")
        .execute()
    )
    data = response.data or []
    if not data:
        raise RuntimeError("upsert_srs_record: no row returned from Supabase")
    return data[0]


def get_due_srs_records(
    student_id: str,
    *,
    client: Client,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    response = (
        client.table("srs_records")
        .select("*")
        .eq("student_id", student_id)
        .lte("next_review_at", now.isoformat())
        .order("next_review_at")
        .execute()
    )
    return list(response.data or [])


def advance_roadmap_progress(
    *,
    student_id: str,
    course: str,
    lesson_id: str,
    client: Client,
) -> dict[str, Any]:
    response = (
        client.table("students")
        .select("llm_profile")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        raise ValueError(f"Student '{student_id}' not found")

    llm_profile = rows[0].get("llm_profile") or {}
    if not isinstance(llm_profile, dict):
        llm_profile = {}

    all_progress = llm_profile.get("roadmap_progress") or {}
    if not isinstance(all_progress, dict):
        all_progress = {}

    course_progress = all_progress.get(course) or {}
    if not isinstance(course_progress, dict):
        course_progress = {}

    completed = course_progress.get("completed_lessons") or []
    if not isinstance(completed, list):
        completed = []
    if lesson_id not in completed:
        completed.append(lesson_id)

    course_progress["completed_lessons"] = completed
    course_progress["current_lesson_id"] = lesson_id
    course_progress["updated_at"] = datetime.now(timezone.utc).isoformat()
    all_progress[course] = course_progress
    llm_profile["roadmap_progress"] = all_progress

    update = client.table("students").update({"llm_profile": llm_profile}).eq("id", student_id).execute()
    data = update.data or []
    if not data:
        raise RuntimeError("advance_roadmap_progress: no row returned from Supabase")
    return course_progress
