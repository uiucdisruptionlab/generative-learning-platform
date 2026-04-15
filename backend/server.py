from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bedrock.client import create_bedrock_runtime_client
from pipeline_log import plog

_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir.parent / ".env")
load_dotenv(_backend_dir / ".env", override=True)
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
        inner = inner.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        # Remove any remaining non-printable control chars
        inner = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", inner)
        return f'"{inner}"'

    cleaned = re.sub(r'"((?:[^"\\]|\\.)*)"', _escape_string, raw, flags=re.DOTALL)
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

ROADMAP_CACHE_DIR = Path(__file__).parent

COURSE_KEY_MAP: dict[str, str] = {
    "ALecFinal": "accounting",
    "accounting": "accounting",
    "python": "python",
    "financing": "financing",
}


def _course_cache_path(course: str) -> Path:
    key = COURSE_KEY_MAP.get(course, course)
    return ROADMAP_CACHE_DIR / f"roadmap_cache_{key}.json"


def _load_roadmap_cache(course: str) -> dict | None:
    path = _course_cache_path(course)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_roadmap_cache(course: str, data: dict) -> None:
    _course_cache_path(course).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_and_cache(course: str, lecture_id: str | None) -> dict:
    from graphdb.roadmap_builder import build_roadmap, build_roadmap_for_lecture
    if lecture_id:
        data = build_roadmap_for_lecture(lecture_id, course=course, refine_with_llm=True)
    else:
        data = build_roadmap(course=course, refine_with_llm=True)
    _save_roadmap_cache(course, data)
    return data


@app.get("/roadmap")
def get_roadmap(
    course: str = Query(default="accounting"),
    lecture_id: str | None = Query(default=None),
):
    cached = _load_roadmap_cache(course)
    if cached:
        return cached
    try:
        return _build_and_cache(course, lecture_id)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/roadmap/rebuild")
def rebuild_roadmap(
    course: str = Query(default="accounting"),
    lecture_id: str | None = Query(default=None),
):
    try:
        return _build_and_cache(course, lecture_id)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


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
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _generate_and_cache_lesson(lesson_id: str, persona_id: str, course: str | None = None) -> dict:
    from lesson_generator import generate_lesson
    data = generate_lesson(lesson_id=lesson_id, persona_id=persona_id, course_override=course)
    _save_lesson_cache(persona_id, lesson_id, data, course)
    return data


@app.get("/lesson/{lesson_id}")
def get_lesson(lesson_id: str, persona: str = Query(default="charles"), course: str | None = Query(default=None)):
    cached = _load_lesson_cache(persona, lesson_id, course)
    if cached:
        return cached
    try:
        return _generate_and_cache_lesson(lesson_id, persona, course)
    except Exception as exc:
        import traceback
        traceback.print_exc()
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


def _pipeline_max_chunks() -> int | None:
    """
    Cap how many chunks get Bedrock + Neo4j graph ingestion per PDF.
    Each chunk is one Bedrock call; large PDFs can produce hundreds of chunks (30+ min).
    Set PIPELINE_MAX_CHUNKS empty, 'none', or 'unlimited' for no cap (not recommended for demos).
    """
    raw = os.getenv("PIPELINE_MAX_CHUNKS", "40").strip()
    if not raw or raw.lower() in ("none", "unlimited"):
        return None
    try:
        n = int(raw)
    except ValueError:
        return 40
    if n < 1:
        return None
    return n


def _sanitize_pdf_stem(filename: str) -> str:
    """Safe basename stem for temp files and Neo4j lecture id (matches main.process_pdf offering_id)."""
    name = Path(filename or "document").name
    stem = Path(name).stem
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", stem).strip("._-")
    return stem[:120] if stem else "document"


def _run_pdf_ingest_job(pdf_path: Path, refine_with_llm: bool) -> Dict[str, Any]:
    """
    Run extract → chunk → Bedrock concept extraction → Neo4j (graph_only: no Pinecone upsert).
    Lecture id in the graph equals the PDF filename stem.
    """
    from main import process_pdf
    from graphdb.neo4j_client import get_concept_graph_by_lecture
    from graphdb.roadmap_builder import build_roadmap_for_lecture

    plog("ingest_job", f"START pdf={pdf_path.name} refine_with_llm={refine_with_llm}")

    unstructured_key = os.getenv("UNSTRUCTURED_API_KEY")
    if not unstructured_key:
        raise RuntimeError("UNSTRUCTURED_API_KEY is not set")

    plog("ingest_job", "calling main.process_pdf (Unstructured → chunks → Bedrock × N → Neo4j)…")
    ingest_stats = process_pdf(
        str(pdf_path),
        pinecone_index=os.getenv("PINECONE_INDEX", ""),
        pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
        unstructured_api_key=unstructured_key,
        enable_graph_ingestion=True,
        graph_only=True,
        max_chunks=_pipeline_max_chunks(),
    )
    plog("ingest_job", f"process_pdf finished stats={ingest_stats}")

    lecture_id = pdf_path.stem
    plog("ingest_job", f"loading Neo4j subgraph lecture_id={lecture_id}…")
    graph = get_concept_graph_by_lecture(lecture_id)
    plog("ingest_job", f"Neo4j subgraph loaded concepts={len(graph.get('concepts', []))} rels={len(graph.get('relationships', []))}")

    plog("ingest_job", "building roadmap from graph…")
    roadmap = build_roadmap_for_lecture(
        lecture_id,
        course="generated_course",
        refine_with_llm=refine_with_llm,
    )
    plog("ingest_job", f"roadmap built lesson_count={roadmap.get('lesson_count')} DONE")

    chunk_ids = {str(link.get("chunk_id")) for link in graph.get("chunk_links", []) if link.get("chunk_id")}
    return {
        "lecture_id": lecture_id,
        "source_filename": pdf_path.name,
        "chunk_count": len(chunk_ids),
        "concept_count": len(graph.get("concepts", [])),
        "relationship_count": len(graph.get("relationships", [])),
        "ingest_stats": ingest_stats,
        "graph": graph,
        "roadmap": roadmap,
    }


@app.post("/pipeline/ingest")
async def pipeline_ingest(
    file: UploadFile = File(...),
    refine: bool = Query(default=False),
) -> Dict[str, Any]:
    """
    Upload a PDF, run the same pipeline as backend/main.py (graph ingestion into Neo4j),
    then return the subgraph for that lecture plus the roadmap from graphdb/roadmap_builder.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    stem = _sanitize_pdf_stem(file.filename)
    work_dir = Path(tempfile.mkdtemp(prefix="glp_ingest_"))
    pdf_path = work_dir / f"{stem}.pdf"

    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file.")
        pdf_path.write_bytes(data)
    except HTTPException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Could not read upload: {exc}") from exc

    try:
        plog("http", f"POST /pipeline/ingest saved temp PDF bytes={pdf_path.stat().st_size} path={pdf_path}")
        result = await asyncio.to_thread(_run_pdf_ingest_job, pdf_path, refine)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return result


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
            assistant_reply, updated_profile, done = _process_llm_response(raw_text, profile, latest)
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


class LessonChatMessage(BaseModel):
    role: str
    content: str

class LessonChatRequest(BaseModel):
    lesson_id: str
    persona: str
    messages: List[LessonChatMessage]


@app.post("/lesson/chat")
async def lesson_chat(req: LessonChatRequest) -> StreamingResponse:
    cached = _load_lesson_cache(req.persona, req.lesson_id)
    lesson_context = ""
    if cached:
        title = cached.get("title", "")
        overview = cached.get("overview", "")
        concepts = ", ".join(c["name"] for c in cached.get("concepts", []) if isinstance(c, dict))
        lesson_context = f"Lesson: {title}\nOverview: {overview}\nConcepts covered: {concepts}"

    from personas import get_persona
    try:
        persona = get_persona(req.persona)
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
            {"role": m["role"], "content": [{"type": "text", "text": m["content"]}]}
            for m in messages[:-1]
        ]

        client = create_bedrock_runtime_client(region=AWS_REGION)

        try:
            response = await asyncio.to_thread(
                client.converse,
                modelId=MODEL_ID,
                system=[{"text": system_prompt}],
                messages=history_for_bedrock + [
                    {"role": "user", "content": [{"type": "text", "text": latest}]}
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
