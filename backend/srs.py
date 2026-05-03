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


def _srs_identity_filter(query: Any, concept_id: str) -> Any:
    """Prefer the current unique key while keeping legacy node_id rows readable."""
    return query.or_(f"concept_id.eq.{concept_id},node_id.eq.{concept_id}")


def get_roadmap_position(
    student_id: str,
    *,
    course_id: str = "",
    client: Client,
) -> dict[str, Any]:
    query = (
        client.table("roadmap_position")
        .select("*")
        .eq("student_id", student_id)
    )
    if course_id:
        query = query.eq("course_id", course_id)
    response = query.limit(1).execute()
    rows = response.data or []
    if rows:
        return rows[0]

    insert_row: dict[str, Any] = {"student_id": student_id, "current_index": 0}
    if course_id:
        insert_row["course_id"] = course_id
    conflict_cols = "student_id,course_id" if course_id else "student_id"
    # Use upsert so concurrent requests don't race to INSERT the same row.
    # On conflict keep the existing current_index intact (update nothing).
    upserted = (
        client.table("roadmap_position")
        .upsert(insert_row, on_conflict=conflict_cols, ignore_duplicates=True)
        .execute()
    )
    data = upserted.data or []
    if data:
        return data[0]
    # ON CONFLICT DO NOTHING returns empty data — re-fetch the existing row.
    refetch = (
        client.table("roadmap_position")
        .select("*")
        .eq("student_id", student_id)
    )
    if course_id:
        refetch = refetch.eq("course_id", course_id)
    refetch_rows = (refetch.limit(1).execute().data or [])
    if refetch_rows:
        return refetch_rows[0]
    raise RuntimeError("get_roadmap_position: no row returned from Supabase")


def set_roadmap_position(
    student_id: str,
    current_index: int,
    *,
    course_id: str = "",
    client: Client,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "student_id": student_id,
        "current_index": max(0, int(current_index)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if course_id:
        row["course_id"] = course_id
    on_conflict = "student_id,course_id" if course_id else "student_id"
    response = (
        client.table("roadmap_position")
        .upsert(row, on_conflict=on_conflict)
        .execute()
    )
    data = response.data or []
    if not data:
        raise RuntimeError("set_roadmap_position: no row returned from Supabase")
    return data[0]


def upsert_srs_record(
    *,
    student_id: str,
    concept_id: str | None = None,
    node_id: str | None = None,
    course: str | None,
    lesson_id: str | None = None,
    score: int | float,
    metadata: dict[str, Any] | None,
    client: Client,
) -> dict[str, Any]:
    concept_id = concept_id or node_id
    if not concept_id:
        raise ValueError("concept_id is required")

    previous = get_srs_record(student_id, concept_id, client=client)
    schedule = run_sm2(score, previous)
    reviewed_at = schedule["last_reviewed_at"]

    # Merge last_gaps / last_strengths from incoming metadata with any prior record so
    # _build_srs_context can tailor the next session to specific weak areas.
    meta = metadata or {}
    gaps = meta.get("gaps") or []
    strengths = meta.get("strengths") or []

    row: dict[str, Any] = {
        "student_id": student_id,
        "concept_id": concept_id,
        "node_id": concept_id,
        "score": schedule["quality"],
        "ease_factor": schedule["ease_factor"],
        "interval_days": schedule["interval_days"],
        "repetitions": schedule["repetitions"],
        "next_review_at": schedule["next_review_at"],
    }
    if lesson_id:
        row["lesson_id"] = lesson_id
    # Columns added via migration — included in primary attempt, dropped in fallback if schema is older.
    extended: dict[str, Any] = {
        "last_reviewed_at": reviewed_at,
        "course": course or "",
    }
    if gaps:
        extended["last_gaps"] = gaps if isinstance(gaps, str) else "; ".join(str(g) for g in gaps)
    if strengths:
        extended["last_strengths"] = strengths if isinstance(strengths, str) else "; ".join(str(s) for s in strengths)

    full_row = {k: v for k, v in {**row, **extended}.items() if v is not None and v != ""}

    try:
        response = (
            client.table("srs_records")
            .upsert(full_row, on_conflict="student_id,concept_id")
            .execute()
        )
    except Exception:  # pylint: disable=broad-exception-caught
        # Retry with only the base columns that exist in all schema versions.
        response = (
            client.table("srs_records")
            .upsert({k: v for k, v in row.items() if v is not None}, on_conflict="student_id,concept_id")
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


def get_upcoming_srs_records(
    student_id: str,
    *,
    days: int = 7,
    client: Client,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=max(0, int(days)))
    response = (
        client.table("srs_records")
        .select("*")
        .eq("student_id", student_id)
        .gte("next_review_at", now.isoformat())
        .lte("next_review_at", end.isoformat())
        .order("next_review_at")
        .execute()
    )
    return list(response.data or [])


def advance_roadmap_index(
    *,
    student_id: str,
    node_ids: list[str],
    current_node_id: str,
    course_id: str = "",
    client: Client,
) -> dict[str, Any]:
    position = get_roadmap_position(student_id, course_id=course_id, client=client)
    current_index = int(position.get("current_index") or 0)
    if current_index < len(node_ids) and node_ids[current_index] == current_node_id:
        next_index = current_index + 1
    else:
        try:
            next_index = node_ids.index(current_node_id) + 1
        except ValueError:
            next_index = current_index

    updated = set_roadmap_position(student_id, next_index, course_id=course_id, client=client)
    return {
        "current_index": updated.get("current_index", next_index),
        "complete": next_index >= len(node_ids),
        "total": len(node_ids),
    }


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
