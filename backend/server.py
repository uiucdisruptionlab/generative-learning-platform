from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import boto3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
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

@app.get("/roadmap")
def get_roadmap():
    from graphdb.roadmap_builder import build_roadmap
    try:
        return build_roadmap(course="accounting")
    except Exception as exc:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)