from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bedrock.client import create_bedrock_runtime_client

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent))

MODEL_ID = os.getenv("BEDROCK_MODEL_ID",
                     "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_REGION", os.getenv(
    "AWS_DEFAULT_REGION", "us-east-1"))

OPENING_MESSAGE = "Hi! Before we get started, what name would you like me to use?"

TERMINATION_PATTERNS = [
    r"\bno\b.*\b(that'?s|thats|it|all|enough|good)\b",
    r"\bthat'?s all\b",
    r"\bthat'?s it\b",
    r"\bnothing else\b",
    r"\bnope\b",
    r"\ball good\b",
    r"\bwe'?re good\b",
    r"\bfor now\b",
    r"\bdone\b",
]

REQUIRED_FIELDS = [
    "name",
    "major",
    "academic_level",
    "career_goals",
    "career_clarity",
    "subject_confidence",
    "learning_style_summary",
    "weekly_hours",
    "preferred_formats",
]

JSON_ONLY_SYSTEM_PROMPT = """You are an onboarding assistant for a Generative Learning Platform.
Your job is to learn about a student through a short, natural conversation and collect the
information needed to personalise their learning experience.

You will be given:
1. The user's current structured profile.
2. The conversation history.
3. The user's latest message.

You MUST return valid JSON only. No markdown. No prose outside JSON.

Your goals:
- Ask exactly one natural, concise question at a time.
- Do not ask for information already known.
- Personalize lightly based on what the user already said.
- Extract structured updates from the latest user message.
- Decide whether the user seems finished, especially if they say things like
  'no, that\'s all', 'that\'s it for now', 'nothing else', 'we are good', etc.
- If the user seems finished AND all required fields are collected, write a warm closing message.
- If required fields are missing, keep asking politely until finished.

Information to collect — weave naturally into conversation, combine when it makes sense:
1. name — what to call them.
2. major and academic_level — e.g. "What are you studying, and what year are you in?"
3. career_goals + career_clarity — what they want to do and how sure they are.
4. subject_confidence — prior experience with this subject.
5. Learning style (2–3 open-ended questions, e.g. "How do you usually tackle something new?",
   "What helps things click for you?") → summarise as learning_style_summary, a 1–2 sentence
   plain-English reflection grounded in their own words.
6. weekly_hours + preferred_formats — e.g. "How many hours a week can you dedicate, and how do
   you prefer to learn — videos, reading, hands-on practice, case studies?"

Valid career_clarity values: very_clear | somewhat_clear | exploring | unsure
Valid subject_confidence values: totally_new | beginner | somewhat_familiar | comfortable | advanced

The JSON schema you must return is:
{
  "assistant_reply": "string",
  "extracted_updates": {
    "name": "string or null",
    "major": "string or null",
    "minor": "string or null",
    "academic_level": "string or null  (e.g. Freshman, Sophomore, Junior, Senior, Graduate)",
    "career_goals": "string or null",
    "career_clarity": "very_clear | somewhat_clear | exploring | unsure | null",
    "subject_confidence": "totally_new | beginner | somewhat_familiar | comfortable | advanced | null",
    "learning_style_summary": "string or null",
    "weekly_hours": "number or null",
    "preferred_formats": ["string", "..."] or null,
    "interests": ["string", "..."] or null,
    "notes": "string or null"
  },
  "user_seems_finished": boolean,
  "missing_fields": ["field_name", "..."]
}
"""

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="GLP Onboarding API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    profile: Dict[str, Any]


class ChatResponse(BaseModel):
    message: str
    profile: Dict[str, Any]
    done: bool


class StudentUpdateRequest(BaseModel):
    name: str | None = None
    academic_level: str | None = None
    major_or_field: str | None = None
    learning_goals: Dict[str, Any] | None = None
    interests: List[str] | None = None
    weekly_hours: float | int | None = None
    preferred_formats: List[str] | None = None
    llm_profile: Dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Core logic (mirror of onboarding_demo.py)
# ---------------------------------------------------------------------------

def looks_like_done(text: str) -> bool:
    lower = text.lower().strip()
    return any(re.search(p, lower) for p in TERMINATION_PATTERNS)


def normalized_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "name": None,
        "major": None,
        "minor": None,
        "academic_level": None,
        "career_goals": None,
        "career_clarity": None,
        "subject_confidence": None,
        "learning_style_summary": None,
        "weekly_hours": None,
        "preferred_formats": None,
        "interests": None,
        "notes": None,
    }
    for key, value in updates.items():
        if key in base:
            base[key] = value
    return base


def merge_profile(profile: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(profile))
    for key, value in normalized_updates(updates).items():
        if value in (None, "", []):
            continue
        if key in ("interests", "preferred_formats"):
            current = merged.get(key) or []
            merged[key] = list(dict.fromkeys(current + value))
        elif key == "notes":
            if merged.get("notes"):
                merged["notes"] = f"{merged['notes']} | {value}"
            else:
                merged["notes"] = value
        else:
            merged[key] = value
    return merged


def compute_missing_fields(
    profile: Dict[str, Any],
    pending_updates: Optional[Dict[str, Any]] = None,
) -> List[str]:
    merged = merge_profile(profile, pending_updates or {})
    return [f for f in REQUIRED_FIELDS if not merged.get(f)]


def _parse_llm_json(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM output, tolerating literal control chars inside strings."""
    text = text.strip()

    # Pass 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Pass 2: extract the first {...} block, then try again
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Model returned no JSON object: {text}")
    raw = match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Pass 3: the LLM embedded literal newlines / control chars inside string values.
    # Find every quoted string and escape any bare control characters inside it.
    def _escape_string(m: re.Match) -> str:  # type: ignore[type-arg]
        inner = m.group(1)
        inner = inner.replace("\n", "\\n").replace(
            "\r", "\\r").replace("\t", "\\t")
        # Remove any remaining non-printable control chars
        inner = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", inner)
        return f'"{inner}"'

    cleaned = re.sub(r'"((?:[^"\\]|\\.)*)"',
                     _escape_string, raw, flags=re.DOTALL)
    return json.loads(cleaned)


def _bedrock_body(profile: Dict[str, Any], history: List[Dict[str, str]], user_message: str) -> str:
    payload = {
        "profile": profile,
        "conversation_history": history,
        "latest_user_message": user_message,
        "required_fields": REQUIRED_FIELDS,
    }
    return json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 700,
        "temperature": 0,
        "system": JSON_ONLY_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
            }
        ],
    })


def call_bedrock_stream(
    profile: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
) -> str:
    """Call Bedrock with streaming and return the fully accumulated response text."""
    client = create_bedrock_runtime_client(region=AWS_REGION)
    response = client.invoke_model_with_response_stream(
        modelId=MODEL_ID,
        body=_bedrock_body(profile, history, user_message),
        contentType="application/json",
        accept="application/json",
    )
    full_text = ""
    for event in response["body"]:
        chunk = event.get("chunk")
        if not chunk:
            continue
        data = json.loads(chunk["bytes"].decode("utf-8"))
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                full_text += delta.get("text", "")
    return full_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # disable Nginx buffering
}


def _sse(data: Any) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _process_llm_response(
    raw_text: str,
    profile: Dict[str, Any],
    latest_user_message: str,
) -> tuple[str, Dict[str, Any], bool]:
    llm_json = _parse_llm_json(raw_text)
    extracted_updates = llm_json.get("extracted_updates") or {}
    user_seems_finished = bool(llm_json.get("user_seems_finished")) or looks_like_done(
        latest_user_message
    )
    assistant_reply = str(
        llm_json.get("assistant_reply") or "Could you tell me a bit more?"
    ).strip()
    updated_profile = merge_profile(profile, extracted_updates)
    missing = compute_missing_fields(updated_profile)
    done = user_seems_finished and not missing
    return assistant_reply, updated_profile, done


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Lesson roadmap cache (lecture-grouped + LLM-refined). Stored in the existing
# Supabase `roadmap_cache` table, keyed by student_id (one course per student
# is currently assumed, so per-student caching is equivalent to per-course).
# ---------------------------------------------------------------------------


def _load_lesson_roadmap_cache(student_id: str) -> dict | None:
    """Load the cached lesson roadmap for a student from `roadmap_cache`."""
    try:
        from supabase_local import get_supabase_client

        supabase = get_supabase_client()
        resp = (
            supabase.table("roadmap_cache")
            .select("roadmap")
            .eq("student_id", student_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        roadmap = rows[0].get("roadmap")
        if isinstance(roadmap, str):
            try:
                roadmap = json.loads(roadmap)
            except Exception:
                return None
        # Only treat as a valid lesson roadmap if it has the new shape.
        if isinstance(roadmap, dict) and roadmap.get("lessons"):
            return roadmap
        return None
    except Exception as exc:
        print(f"[server] failed to read roadmap_cache for student {student_id!r}: {exc}")
        return None


def _save_lesson_roadmap_cache(student_id: str, data: dict) -> None:
    """Upsert the cached lesson roadmap for a student into `roadmap_cache`."""
    try:
        from supabase_local import get_supabase_client

        supabase = get_supabase_client()
        row = {
            "student_id": student_id,
            "roadmap": data,
        }
        supabase.table("roadmap_cache").upsert(
            row, on_conflict="student_id"
        ).execute()
    except Exception as exc:
        print(f"[server] failed to write roadmap_cache for student {student_id!r}: {exc}")


def _lesson_concept_order(course_id: str) -> dict[str, tuple[int, int, str]]:
    """Best-effort source order for concepts in the lesson roadmap."""
    try:
        from graphdb.neo4j_client import get_lecture_grouped_concepts

        order: dict[str, tuple[int, int, str]] = {}
        for lecture_index, lecture in enumerate(get_lecture_grouped_concepts(course_id)):
            for concept in lecture.get("concepts") or []:
                cid = str(concept.get("id") or "")
                if not cid:
                    continue
                order.setdefault(
                    cid,
                    (
                        lecture_index,
                        int(concept.get("chunk_order") or 0),
                        str(concept.get("name") or cid).lower(),
                    ),
                )
        return order
    except Exception as exc:
        print(f"[server] failed to load concept order for course {course_id!r}: {exc}")
        return {}


def _concept_display_sort_key(
    lesson_title: str,
    concept: dict[str, Any],
    order: dict[str, tuple[int, int, str]],
) -> tuple[int, int, int, str]:
    stopwords = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "with"}

    def tokens(value: str) -> set[str]:
        words = re.sub(r"[^a-z0-9\s]", " ", value.lower()).split()
        normalized = {
            word[:-1] if len(word) > 3 and word.endswith("s") else word
            for word in words
            if word not in stopwords
        }
        return {word for word in normalized if word}

    title_tokens = tokens(lesson_title)
    concept_name = str(concept.get("name") or concept.get("id") or "")
    concept_tokens = tokens(concept_name)
    title_related = bool(title_tokens & concept_tokens)
    source_order = order.get(
        str(concept.get("id") or ""),
        (10**9, 10**9, concept_name.lower()),
    )
    return (
        0 if title_related else 1,
        int(source_order[0]),
        int(source_order[1]),
        str(source_order[2]),
    )


LATE_LESSON_KEYWORDS = {
    "administration",
    "allowed reference",
    "cheat sheet",
    "course wrap",
    "exam",
    "final",
    "practice exam",
    "review",
    "wrap up",
    "wrap-up",
}


def _lesson_source_order(
    lesson: dict[str, Any],
    concept_order: dict[str, tuple[int, int, str]],
) -> tuple[int, int, str]:
    orders = [
        concept_order[str(concept.get("id") or "")]
        for concept in lesson.get("concepts") or []
        if isinstance(concept, dict) and str(concept.get("id") or "") in concept_order
    ]
    if not orders:
        return (10**9, 10**9, str(lesson.get("title") or "").lower())
    first = min(orders)
    return (int(first[0]), int(first[1]), str(first[2]))


def _looks_like_late_lesson(lesson: dict[str, Any]) -> bool:
    text_parts = [
        str(lesson.get("title") or ""),
        str(lesson.get("summary") or ""),
    ]
    text_parts.extend(
        str(concept.get("name") or "")
        for concept in lesson.get("concepts") or []
        if isinstance(concept, dict)
    )
    haystack = " ".join(text_parts).lower()
    return any(
        re.search(rf"\b{re.escape(keyword).replace(r'\ ', r'\s+')}\b", haystack)
        for keyword in LATE_LESSON_KEYWORDS
    )


def _normalize_lesson_sequence(roadmap: dict, course_id: str) -> dict:
    lessons = [
        lesson for lesson in roadmap.get("lessons") or []
        if isinstance(lesson, dict)
    ]
    if len(lessons) <= 1:
        return roadmap

    concept_order = _lesson_concept_order(course_id)
    ordered_lessons = sorted(
        enumerate(lessons),
        key=lambda item: (
            1 if _looks_like_late_lesson(item[1]) else 0,
            *_lesson_source_order(item[1], concept_order),
            item[0],
        ),
    )
    normalized_lessons = [lesson for _, lesson in ordered_lessons]
    node_ids = [
        str(concept.get("id") or "")
        for lesson in normalized_lessons
        for concept in lesson.get("concepts") or []
        if isinstance(concept, dict) and concept.get("id")
    ]

    return {
        **roadmap,
        "lessons": normalized_lessons,
        "lesson_count": len(normalized_lessons),
        "node_ids": node_ids or list(roadmap.get("node_ids") or []),
    }


def _get_or_build_lesson_roadmap(
    student_id: str,
    course_id: str,
    force_refresh: bool = False,
) -> dict:
    """Return the cached lesson roadmap for a student, building it if missing.

    `student_id` is the cache key; `course_id` is what the builder runs against.
    Assumes one course per student.
    """
    if not force_refresh:
        cached = _load_lesson_roadmap_cache(student_id)
        if cached and cached.get("lessons") and cached.get("course_id") == course_id:
            return _normalize_lesson_sequence(cached, course_id)
    from graphdb.roadmap_builder import build_course_lesson_roadmap

    fresh = build_course_lesson_roadmap(course_id, refine_with_llm=True)
    if fresh.get("lessons"):
        _save_lesson_roadmap_cache(student_id, fresh)
    return _normalize_lesson_sequence(fresh, course_id)


LESSON_CACHE_DIR = Path(__file__).parent / "lesson_cache"


def _get_lesson_cache_path(persona_id: str, lesson_id: str, course: str | None = None) -> Path:
    folder = f"{persona_id}_{course}" if course else persona_id
    return LESSON_CACHE_DIR / folder / f"{lesson_id}.json"


def _load_lesson_cache(persona_id: str, lesson_id: str, course: str | None = None) -> dict | None:
    path = _get_lesson_cache_path(persona_id, lesson_id, course)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_lesson_cache(persona_id: str, lesson_id: str, data: dict, course: str | None = None) -> None:
    path = _get_lesson_cache_path(persona_id, lesson_id, course)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        data, indent=2, ensure_ascii=False), encoding="utf-8")


def _generate_and_cache_lesson(lesson_id: str, persona_id: str, course: str | None = None) -> dict:
    from lesson_generator import generate_lesson
    data = generate_lesson(lesson_id=lesson_id,
                           persona_id=persona_id, course_override=course)
    _save_lesson_cache(persona_id, lesson_id, data, course)
    return data


def _student_has_srs_history(persona_id: str, lesson_id: str) -> bool:
    try:
        from lesson_generator import resolve_student_id
        from srs import get_srs_record
        from supabase_local import get_supabase_client
        student_id = resolve_student_id(persona_id)
        return get_srs_record(student_id, lesson_id, client=get_supabase_client()) is not None
    except Exception as exc:
        print(f"[get_lesson] SRS history check failed: {exc}")
        return False


@app.get("/lesson/{lesson_id}")
def get_lesson(lesson_id: str, persona: str = Query(default="charles"), course: str | None = Query(default=None)):
    cached = _load_lesson_cache(persona, lesson_id, course)
    if cached and not _student_has_srs_history(persona, lesson_id):
        return cached
    try:
        return _generate_and_cache_lesson(lesson_id, persona, course)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        if cached:
            return cached
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/lesson/{lesson_id}/rebuild")
def rebuild_lesson(lesson_id: str, persona: str = Query(default="charles"), course: str | None = Query(default=None)):
    try:
        return _generate_and_cache_lesson(lesson_id, persona, course)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    messages = [m.model_dump() for m in req.messages]
    profile = req.profile
    user_messages = [m for m in messages if m["role"] == "user"]

    async def generate() -> AsyncGenerator[str, None]:
        # Opening greeting — no Bedrock call needed
        if not user_messages:
            for word in OPENING_MESSAGE.split():
                yield _sse({"type": "chunk", "text": word + " "})
                await asyncio.sleep(0.04)
            yield _sse({"type": "result", "message": OPENING_MESSAGE, "profile": profile, "done": False})
            return

        latest = user_messages[-1]["content"]
        history = messages[:-1]

        # Run the blocking Bedrock call in a thread so we don't block the event loop
        try:
            raw_text = await asyncio.to_thread(call_bedrock_stream, profile, history, latest)
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        try:
            assistant_reply, updated_profile, done = _process_llm_response(
                raw_text, profile, latest)
        except Exception as exc:
            yield _sse({"type": "error", "message": f"Parse error: {exc}"})
            return

        # Stream the reply text word-by-word
        words = assistant_reply.split()
        for i, word in enumerate(words):
            yield _sse({"type": "chunk", "text": word + (" " if i < len(words) - 1 else "")})
            await asyncio.sleep(0.03)

        # Final event carries the full profile and done flag
        yield _sse({"type": "result", "message": assistant_reply, "profile": updated_profile, "done": done})

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/srs/due")
def get_due_reviews(
    student_id: str = Query(default=""),
    persona: str = Query(default="charles"),
) -> dict[str, Any]:
    from lesson_generator import _resolve_student_id
    from srs import get_due_srs_records
    from supabase_local import get_supabase_client

    if not student_id:
        try:
            student_id = _resolve_student_id(persona)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    try:
        due = get_due_srs_records(student_id, client=get_supabase_client())
        return {"student_id": student_id, "due": due, "review_mode": bool(due)}
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/roadmap_position/{student_id}")
def get_student_roadmap_position(student_id: str) -> dict[str, Any]:
    from srs import get_roadmap_position
    from supabase_local import get_supabase_client

    try:
        supabase = get_supabase_client()
        sc_resp = (
            supabase.table("student_courses")
            .select("course_id")
            .eq("student_id", student_id)
            .limit(1)
            .execute()
        )
        sc_rows = sc_resp.data or []
        course_id = str(sc_rows[0]["course_id"]) if sc_rows else ""
        position = get_roadmap_position(student_id, course_id=course_id, client=supabase)
        return {
            "student_id": student_id,
            "course_id": course_id,
            "current_index": int(position.get("current_index") or 0),
            "updated_at": position.get("updated_at"),
        }
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/roadmap/generate/{student_id}")
def generate_student_roadmap(student_id: str) -> dict[str, Any]:
    """Lecture-grouped, LLM-refined roadmap with per-lesson and per-concept state.

    Response shape:
        {
            "student_id", "course_id", "current_index",
            "node_ids": [concept_id, ...],         # flat ordered concepts
            "lessons": [
                {
                    "lesson_id", "title", "summary", "state",
                    "concepts": [
                        {"id", "name", "description", "state"}, ...
                    ],
                },
                ...
            ],
            # `concepts` mirrors `node_ids` for legacy clients that haven't been updated yet.
            "concepts": [{"id", "name", "description", "state"}, ...],
        }
    """
    from srs import get_roadmap_position
    from supabase_local import get_supabase_client

    try:
        supabase = get_supabase_client()

        sc_resp = (
            supabase.table("student_courses")
            .select("course_id")
            .eq("student_id", student_id)
            .limit(1)
            .execute()
        )
        sc_rows = sc_resp.data or []
        if not sc_rows:
            raise HTTPException(status_code=404, detail="no course enrollment found for student")
        course_id = str(sc_rows[0]["course_id"])

        roadmap = _get_or_build_lesson_roadmap(student_id, course_id)
        lessons = roadmap.get("lessons") or []
        node_ids: list[str] = list(roadmap.get("node_ids") or [])
        concept_order = _lesson_concept_order(course_id)

        position = get_roadmap_position(student_id, course_id=course_id, client=supabase)
        current_index = int(position.get("current_index") or 0)
        if node_ids:
            current_index = max(0, min(current_index, len(node_ids) - 1))

        enriched_lessons: list[dict[str, Any]] = []
        flat_concepts: list[dict[str, Any]] = []
        flat_idx = 0
        for lesson in lessons:
            lesson_concepts = lesson.get("concepts") or []
            lesson_concept_count = len(lesson_concepts)
            if not lesson_concept_count:
                continue
            lesson_start = flat_idx
            lesson_end = flat_idx + lesson_concept_count - 1
            if current_index < lesson_start:
                lesson_state = "locked"
            elif current_index > lesson_end:
                lesson_state = "completed"
            else:
                lesson_state = "active"

            ec: list[dict[str, Any]] = []
            for c in lesson_concepts:
                if flat_idx < current_index:
                    state = "completed"
                elif flat_idx == current_index:
                    state = "active"
                else:
                    state = "locked"
                concept_dict = {
                    "id": str(c.get("id") or ""),
                    "name": c.get("name") or "",
                    "description": c.get("description") or "",
                    "state": state,
                }
                ec.append(concept_dict)
                flat_concepts.append(concept_dict)
                flat_idx += 1

            enriched_lessons.append({
                "lesson_id": str(lesson.get("lesson_id") or ""),
                "title": str(lesson.get("title") or ""),
                "summary": str(lesson.get("summary") or ""),
                "lecture_ids": list(lesson.get("lecture_ids") or []),
                "state": lesson_state,
                "concepts": sorted(
                    ec,
                    key=lambda c: _concept_display_sort_key(
                        str(lesson.get("title") or ""),
                        c,
                        concept_order,
                    ),
                ),
            })

        return {
            "student_id": student_id,
            "course_id": course_id,
            "current_index": current_index,
            "node_ids": node_ids,
            "lessons": enriched_lessons,
            "concepts": flat_concepts,
        }
    except HTTPException:
        raise
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/roadmap/{student_id}")
def get_student_roadmap(student_id: str) -> dict[str, Any]:
    return generate_student_roadmap(student_id)


@app.post("/roadmap/{student_id}/rebuild")
def rebuild_student_lesson_roadmap(student_id: str) -> dict[str, Any]:
    """Force a fresh LLM-refined lesson roadmap rebuild for the student's enrolled course."""
    from supabase_local import get_supabase_client

    try:
        supabase = get_supabase_client()
        sc_resp = (
            supabase.table("student_courses")
            .select("course_id")
            .eq("student_id", student_id)
            .limit(1)
            .execute()
        )
        sc_rows = sc_resp.data or []
        if not sc_rows:
            raise HTTPException(status_code=404, detail="no course enrollment found for student")
        course_id = str(sc_rows[0]["course_id"])
        _get_or_build_lesson_roadmap(student_id, course_id, force_refresh=True)
        return generate_student_roadmap(student_id)
    except HTTPException:
        raise
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


_LESSON_HISTORY_COLUMNS = (
    "session_id, student_id, course_id, lesson_id, concept_id, concept_name, "
    "mode, score, passed, started_at, completed_at, metadata"
)


@app.get("/lesson_history/{student_id}")
def list_lesson_history(
    student_id: str,
    concept_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List completed lesson sessions for a student, optionally filtered by concept_id.

    Returns metadata only (no transcript). Use `/lesson_session/{session_id}` for the full log.
    """
    from supabase_local import get_supabase_client

    try:
        supabase = get_supabase_client()
        query = (
            supabase.table("lesson_sessions")
            .select(_LESSON_HISTORY_COLUMNS)
            .eq("student_id", student_id)
            .order("completed_at", desc=True)
            .limit(limit)
        )
        if concept_id:
            query = query.eq("concept_id", concept_id)
        resp = query.execute()
        return {
            "student_id": student_id,
            "concept_id": concept_id,
            "sessions": list(resp.data or []),
        }
    except Exception as exc:
        msg = str(exc)
        if "lesson_sessions" in msg and ("Could not find" in msg or "PGRST205" in msg):
            return {"student_id": student_id, "concept_id": concept_id, "sessions": []}
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=msg)


@app.get("/lesson_session/{session_id}")
def get_lesson_session(session_id: str) -> dict[str, Any]:
    """Read a single completed lesson session, including the full transcript."""
    from supabase_local import get_supabase_client

    try:
        supabase = get_supabase_client()
        resp = (
            supabase.table("lesson_sessions")
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="lesson session not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc)
        if "lesson_sessions" in msg and ("Could not find" in msg or "PGRST205" in msg):
            raise HTTPException(status_code=404, detail="lesson session not found")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=msg)


@app.get("/courses")
def get_courses_endpoint() -> dict[str, Any]:
    from graphdb.neo4j_client import get_courses

    try:
        return {"courses": get_courses()}
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/student/{student_id}/courses")
def get_student_enrolled_courses(student_id: str) -> dict[str, Any]:
    """Only the Neo4j Course nodes that the student is enrolled in via student_courses."""
    from graphdb.neo4j_client import get_courses
    from supabase_local import get_supabase_client

    try:
        supabase = get_supabase_client()
        sc_resp = (
            supabase.table("student_courses")
            .select("course_id")
            .eq("student_id", student_id)
            .execute()
        )
        enrolled_ids = {str(row["course_id"]) for row in (sc_resp.data or [])}
        if not enrolled_ids:
            return {"courses": []}
        all_courses = get_courses()
        filtered = [c for c in all_courses if str(c.get("id") or "") in enrolled_ids]
        return {"courses": filtered}
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/srs/due/{student_id}")
def get_due_reviews_for_student(student_id: str) -> dict[str, Any]:
    from srs import get_upcoming_srs_records
    from supabase_local import get_supabase_client

    try:
        due = get_upcoming_srs_records(student_id, days=7, client=get_supabase_client())
        return {"student_id": student_id, "due": due, "review_mode": bool(due)}
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _clean_string_list(values: list[Any] | None) -> list[str] | None:
    if values is None:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _clean_json_object(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    cleaned: dict[str, Any] = {}
    for key, raw in value.items():
        safe_key = str(key).strip()
        if not safe_key or raw is None:
            continue
        if isinstance(raw, str):
            text = raw.strip()
            if text:
                cleaned[safe_key] = text
        elif isinstance(raw, list):
            cleaned_list = _clean_string_list(raw)
            if cleaned_list:
                cleaned[safe_key] = cleaned_list
        elif isinstance(raw, dict):
            nested = _clean_json_object(raw)
            if nested:
                cleaned[safe_key] = nested
        else:
            cleaned[safe_key] = raw
    return cleaned


def _merge_json_field(current: Any, updates: dict[str, Any] | None) -> dict[str, Any] | None:
    if updates is None:
        return None
    base = current if isinstance(current, dict) else {}
    return {**base, **updates}


def _profile_cache_keys(student_id: str, profile: dict[str, Any]) -> set[str]:
    keys = {student_id}
    name = str(profile.get("name") or "").strip().lower()
    if name:
        keys.add(name)
    # Demo persona IDs used by the frontend.
    known_ids = {
        "a0000001-0000-4000-8000-000000000001": "alice",
        "b0000002-0000-4000-8000-000000000002": "bob",
        "c0000003-0000-4000-8000-000000000003": "charles",
    }
    if student_id in known_ids:
        keys.add(known_ids[student_id])
    return keys


def _clear_lesson_cache_for_profile(student_id: str, before: dict[str, Any], after: dict[str, Any]) -> None:
    if not LESSON_CACHE_DIR.exists():
        return
    keys = _profile_cache_keys(student_id, before) | _profile_cache_keys(student_id, after)
    for child in LESSON_CACHE_DIR.iterdir():
        if not child.is_dir():
            continue
        folder = child.name.lower()
        if not any(folder == key or folder.startswith(f"{key}_") for key in keys):
            continue
        for cache_file in child.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError as exc:
                print(f"[server] failed to remove stale lesson cache {cache_file}: {exc}")


@app.get("/student/{student_id}")
def get_student(student_id: str) -> dict[str, Any]:
    from supabase_local import get_student_profile, get_supabase_client

    try:
        profile = get_student_profile(student_id, client=get_supabase_client())
        if not profile:
            raise HTTPException(status_code=404, detail="student not found")
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/student/{student_id}")
def update_student(student_id: str, req: StudentUpdateRequest) -> dict[str, Any]:
    from supabase_local import get_student_profile, get_supabase_client

    try:
        supabase = get_supabase_client()
        current = get_student_profile(student_id, client=supabase)
        if not current:
            raise HTTPException(status_code=404, detail="student not found")

        raw = req.model_dump(exclude_unset=True)
        updates: dict[str, Any] = {}

        for field in ("name", "academic_level", "major_or_field"):
            if field in raw:
                cleaned = _clean_optional_string(raw[field])
                if cleaned is not None:
                    updates[field] = cleaned

        if "weekly_hours" in raw and raw["weekly_hours"] is not None:
            updates["weekly_hours"] = max(0, int(round(float(raw["weekly_hours"]))))

        for field in ("interests", "preferred_formats"):
            if field in raw:
                cleaned_list = _clean_string_list(raw[field])
                if cleaned_list is not None:
                    updates[field] = cleaned_list

        if "learning_goals" in raw:
            cleaned_goals = _clean_json_object(raw["learning_goals"])
            merged_goals = _merge_json_field(current.get("learning_goals"), cleaned_goals)
            if merged_goals is not None:
                updates["learning_goals"] = merged_goals

        if "llm_profile" in raw:
            cleaned_llm_profile = _clean_json_object(raw["llm_profile"])
            merged_llm_profile = _merge_json_field(current.get("llm_profile"), cleaned_llm_profile)
            if merged_llm_profile is not None:
                updates["llm_profile"] = merged_llm_profile

        if not updates:
            return current

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = (
            supabase.table("students")
            .update(updates)
            .eq("id", student_id)
            .execute()
        )
        rows = response.data or []
        if rows:
            _clear_lesson_cache_for_profile(student_id, current, rows[0])
            return rows[0]
        refreshed = get_student_profile(student_id, client=supabase)
        if refreshed:
            _clear_lesson_cache_for_profile(student_id, current, refreshed)
            return refreshed
        raise HTTPException(status_code=404, detail="student not found after update")
    except HTTPException:
        raise
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/lesson/chat")
async def lesson_chat(req: LessonChatRequest) -> StreamingResponse:
    cached = _load_lesson_cache(req.persona, req.lesson_id)
    lesson_context = ""
    if cached:
        title = cached.get("title", "")
        overview = cached.get("overview", "")
        concepts = ", ".join(c["name"] for c in cached.get(
            "concepts", []) if isinstance(c, dict))
        lesson_context = f"Lesson: {title}\nOverview: {overview}\nConcepts covered: {concepts}"

    from lesson_generator import _load_persona_from_supabase
    try:
        persona = _load_persona_from_supabase(req.persona, course_override=None)
        persona_context = (
            f"Student name: {persona['name']}\n"
            f"Major: {persona['major']}\n"
            f"Familiarity: {persona['familiarity']}\n"
            f"Learning style: {persona['learning_style']}\n"
            f"Notes: {persona['notes']}"
        )
    except Exception:
        persona_context = ""

    system_prompt = f"""You are a helpful, encouraging teaching assistant guiding a student through a lesson.
Your job is to answer questions, clarify concepts, and help the student understand the material deeply.
Always relate your answers back to the lesson context. Be concise but thorough.
Adapt your tone and depth to the student's profile.

{persona_context}

{lesson_context}""".strip()

    messages = [m.model_dump() for m in req.messages]
    user_messages = [m for m in messages if m["role"] == "user"]

    async def generate() -> AsyncGenerator[str, None]:
        if not user_messages:
            greeting = "Hi! I'm your lesson assistant. Ask me anything about this lesson and I'll help you understand it."
            for word in greeting.split():
                yield _sse({"type": "chunk", "text": word + " "})
                await asyncio.sleep(0.04)
            yield _sse({"type": "done", "message": greeting})
            return

        latest = user_messages[-1]["content"]
        history_for_bedrock = [
            {"role": m["role"], "content": [
                {"type": "text", "text": m["content"]}]}
            for m in messages[:-1]
        ]

        client = create_bedrock_runtime_client(region=AWS_REGION)

        try:
            response = await asyncio.to_thread(
                client.converse,
                modelId=MODEL_ID,
                system=[{"text": system_prompt}],
                messages=history_for_bedrock + [
                    {"role": "user", "content": [
                        {"type": "text", "text": latest}]}
                ],
                inferenceConfig={"maxTokens": 1024, "temperature": 0.5},
            )
            reply = "".join(
                block["text"]
                for block in response["output"]["message"]["content"]
                if "text" in block
            ).strip()
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        for i, word in enumerate(reply.split()):
            yield _sse({"type": "chunk", "text": word + (" " if i < len(reply.split()) - 1 else "")})
            await asyncio.sleep(0.03)

        yield _sse({"type": "done", "message": reply})

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


class InteractiveLessonStartRequest(BaseModel):
    lesson_id: str
    persona: str = "charles"
    course: Optional[str] = None


class InteractiveLessonTickRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    action: Optional[str] = None
    widget_result: Optional[Dict[str, Any]] = None


class InteractiveLessonWidgetRequest(BaseModel):
    session_id: str
    widget_type: str
    payload: Dict[str, Any]
    note: Optional[str] = None


@app.post("/lesson/interactive/start")
def interactive_lesson_start(req: InteractiveLessonStartRequest) -> dict[str, Any]:
    """Walk a lesson dynamically using Pinecone + YouTube (same sources as /lesson) and Bedrock checkpoints."""
    try:
        from dynamic_lesson import start_session

        return start_session(req.lesson_id, req.persona, req.course)
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/lesson/interactive/tick")
def interactive_lesson_tick(req: InteractiveLessonTickRequest) -> dict[str, Any]:
    try:
        from dynamic_lesson import tick_session

        return tick_session(
            req.session_id,
            message=req.message,
            action=req.action,
            widget_result=req.widget_result,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/lesson/interactive/session/{session_id}")
def interactive_lesson_session(session_id: str) -> dict[str, Any]:
    try:
        from dynamic_lesson import get_session_public

        return get_session_public(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")


@app.post("/lesson/interactive/widget")
def interactive_lesson_enqueue_widget(req: InteractiveLessonWidgetRequest) -> dict[str, Any]:
    """
    Attach an MCQ / flashcard / free-response block (same shape the model returns in pending_widget).
    Lets a tool-calling layer or tests push UI without going through a reflection tick.
    """
    try:
        from dynamic_lesson import enqueue_widget

        return enqueue_widget(
            req.session_id,
            {"type": req.widget_type, "payload": req.payload},
            note=req.note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
