from __future__ import annotations

import asyncio
import json
import os
import re
import sys
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
            return cached
    from graphdb.roadmap_builder import build_course_lesson_roadmap

    fresh = build_course_lesson_roadmap(course_id, refine_with_llm=True)
    if fresh.get("lessons"):
        _save_lesson_roadmap_cache(student_id, fresh)
    return fresh
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
                "concepts": ec,
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
