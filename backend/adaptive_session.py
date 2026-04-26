from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any, Literal

from bedrock.client import create_bedrock_runtime_client
from graphdb.neo4j_client import get_chunks_for_concept, get_concept_roadmap_scoped
from srs import (
    PASSING_SCORE,
    advance_roadmap_index,
    get_due_srs_records,
    get_roadmap_position,
    upsert_srs_record,
)
from supabase_local import get_student_profile, get_supabase_client

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
FAST_MODEL_ID = os.getenv("BEDROCK_FAST_MODEL_ID", MODEL_ID)
AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

BLOCKS_PER_CONCEPT = 3
SESSION_STORE: dict[str, dict[str, Any]] = {}
_SESSION_MAX = 200

Intent = Literal["question", "attempt", "done"]


def _prune_sessions() -> None:
    if len(SESSION_STORE) <= _SESSION_MAX:
        return
    oldest = sorted(SESSION_STORE.items(), key=lambda item: item[1].get("created_at", 0))
    for session_id, _ in oldest[: max(0, len(SESSION_STORE) - _SESSION_MAX + 20)]:
        SESSION_STORE.pop(session_id, None)


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Model returned no JSON object: {text[:300]}")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned malformed JSON: {text[:500]}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON was not an object")
    return parsed


def _normalize_block_content(
    block_type: Literal["video", "flashcard", "mcq"],
    content: dict[str, Any],
    *,
    session: dict[str, Any],
) -> dict[str, Any]:
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))
    if block_type == "video":
        return {
            "search_query": str(content.get("search_query") or f"{concept_name} tutorial"),
            "why": str(content.get("why") or f"This video search can help reinforce {concept_name}."),
        }
    if block_type == "flashcard":
        return {
            "front": str(content.get("front") or concept_name),
            "back": str(content.get("back") or content.get("answer") or "Review the source material for the key definition."),
        }

    options = content.get("options")
    if not isinstance(options, list) or len(options) < 2:
        options = [
            "A. The idea described in the source material",
            "B. An unrelated detail",
            "C. A term not covered here",
            "D. None of the above",
        ]
    options = [str(option) for option in options[:4]]
    while len(options) < 4:
        options.append(f"{chr(65 + len(options))}. Review option")

    correct = str(content.get("correct") or "A").strip().upper()
    if correct and correct[0] in {"A", "B", "C", "D"}:
        correct = correct[0]
    else:
        correct = "A"

    return {
        "question": str(content.get("question") or f"Which statement best matches {concept_name}?"),
        "options": options,
        "correct": correct,
        "explanation": str(content.get("explanation") or "This answer is grounded in the source material for the concept."),
    }


def _fallback_block_content(
    block_type: Literal["video", "flashcard", "mcq"],
    response_text: str,
    *,
    session: dict[str, Any],
) -> dict[str, Any]:
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))
    cleaned = response_text.strip()
    if block_type == "video":
        return {
            "search_query": f"{concept_name} tutorial",
            "why": cleaned[:240] or f"This search should help reinforce {concept_name}.",
        }
    if block_type == "flashcard":
        return {
            "front": concept_name,
            "back": cleaned[:500] or "Review the source material for this concept.",
        }
    return {
        "question": f"Which statement best matches {concept_name}?",
        "options": [
            "A. The explanation is grounded in the source material",
            "B. The concept is unrelated to this lesson",
            "C. The concept should be skipped",
            "D. The source material is unnecessary",
        ],
        "correct": "A",
        "explanation": cleaned[:500] or "The correct answer should align with the provided source material.",
    }


def _bedrock_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {"role": message["role"], "content": [{"text": message["content"]}]}
        for message in messages
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]


def _call_converse(
    system: str,
    messages: list[dict[str, str]],
    *,
    model_id: str = MODEL_ID,
    temperature: float = 0.35,
    max_tokens: int = 1024,
) -> str:
    client = create_bedrock_runtime_client(region=AWS_REGION)
    response = client.converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=_bedrock_messages(messages),
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return "".join(
        block["text"]
        for block in response["output"]["message"]["content"]
        if "text" in block
    ).strip()


def _student_value(student: dict[str, Any], key: str, default: str = "") -> str:
    value = student.get(key)
    return str(value if value is not None else default)


def _goal_value(student: dict[str, Any], key: str, default: str = "") -> str:
    goals = student.get("learning_goals") or {}
    if not isinstance(goals, dict):
        return default
    return str(goals.get(key) or default)


def _profile_value(student: dict[str, Any], key: str, default: str = "") -> str:
    profile = student.get("llm_profile") or {}
    if not isinstance(profile, dict):
        return default
    return str(profile.get(key) or default)


def _concept_for(session: dict[str, Any], node_id: str) -> dict[str, Any]:
    for concept in session.get("concepts", []):
        if concept.get("id") == node_id:
            return concept
    return {"id": node_id, "name": node_id, "description": ""}


def _source_text(chunks: list[dict[str, Any]]) -> str:
    text = "\n\n".join(str(chunk.get("text") or "").strip() for chunk in chunks if chunk.get("text"))
    return text or "No source excerpts were found for this concept."


def _blocks_delivered_text(blocks: list[str]) -> str:
    if not blocks:
        return "No content has been delivered yet."
    labels = {
        "video": "A video recommendation",
        "flashcard": "A flashcard on key terms",
        "mcq": "A multiple choice question",
    }
    return "\n".join(f"- {labels.get(block, block)}" for block in blocks)


def _normalize_block_type(raw: str) -> Literal["video", "flashcard", "mcq"]:
    text = raw.lower()
    if "video" in text:
        return "video"
    if "flash" in text or "card" in text:
        return "flashcard"
    return "mcq"


def _next_block_type(session: dict[str, Any]) -> Literal["video", "flashcard", "mcq"]:
    formats = session["student"].get("preferred_formats") or []
    idx = int(session.get("block_index") or 0)
    if idx < len(formats):
        return _normalize_block_type(str(formats[idx]))
    return "mcq"


def _system_prompt(session: dict[str, Any], task: str) -> str:
    student = session["student"]
    concept = _concept_for(session, session["node_id"])
    confidence = _profile_value(student, "subject_confidence", "unknown")
    return f"""You are tutoring a student with the following profile:
- Name: {_student_value(student, "name", "Learner")}
- Background: {_profile_value(student, "learning_style_summary", "Not specified")}
- Confidence level: {confidence}
- Learning goals: {_goal_value(student, "primary_focus", "Not specified")}
- Additional notes: {_profile_value(student, "notes", "Not specified")}

Tailor your language, examples, and depth specifically to this student.
A beginner student needs simple language, relatable analogies, and step-by-step explanation.
A comfortable or very familiar student can handle technical depth and precise terminology.
Do not re-introduce yourself. Do not re-explain things already covered in the conversation.

You are teaching the following concept: {concept.get("name") or concept.get("id")}
Concept description: {concept.get("description") or "No description provided."}
Here is the source material for this concept:
---
{_source_text(session.get("chunks", []))}
---
Stay grounded in this material. Do not invent facts not present above.
All questions and explanations must reference this specific material.

You have already delivered the following content blocks for this concept:
{_blocks_delivered_text(session.get("blocks_delivered", []))}

Do NOT repeat or regenerate any of the above. Move forward.

{task}""".strip()


def _block_task(session: dict[str, Any], block_type: str) -> str:
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))
    confidence = _profile_value(session["student"], "subject_confidence", "unknown")
    if block_type == "video":
        return f"""Suggest a YouTube search query for a video that would help a {confidence}
student understand {concept_name}.
Format as JSON only, no other text:
{{
  "search_query": "specific search string",
  "why": "one sentence explaining why this suits this specific student"
}}"""
    if block_type == "flashcard":
        return f"""Generate a flashcard for the most important term or idea in {concept_name} not yet covered above.
Format as JSON only, no other text:
{{
  "front": "term or short question",
  "back": "definition or answer written for a {confidence} student"
}}"""
    return f"""Generate a multiple choice question testing understanding of {concept_name}.
Ground the question in the source material above. Do not ask a generic question about the topic.
Format as JSON only, no other text:
{{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct": "A",
  "explanation": "why this is correct, with reference to the source material"
}}"""


def _public_session(session: dict[str, Any]) -> dict[str, Any]:
    concept = _concept_for(session, session["node_id"])
    return {
        "session_id": session["session_id"],
        "student_id": session["student"]["id"],
        "course_id": session.get("course_id", session.get("course", "")),
        "mode": session["mode"],
        "node_id": session["node_id"],
        "concept": concept,
        "block_index": session["block_index"],
        "blocks_per_concept": BLOCKS_PER_CONCEPT,
        "attempt_count": session["attempt_count"],
        "transcript": list(session.get("transcript", [])),
        "progress": {
            "current_index": session.get("current_index", 0),
            "total": len(session.get("node_ids", [])),
        },
    }


def start_session(student_id: str, course: str | None = None) -> dict[str, Any]:
    _prune_sessions()
    supabase = get_supabase_client()
    student = get_student_profile(student_id, client=supabase)
    if not student:
        raise ValueError(f"Student '{student_id}' not found")

    # Step 2: look up course from student_courses table
    sc_response = (
        supabase.table("student_courses")
        .select("course_id")
        .eq("student_id", student_id)
        .limit(1)
        .execute()
    )
    sc_rows = sc_response.data or []
    if not sc_rows:
        raise ValueError(f"No course enrollment found for student '{student_id}'")
    course_id = str(sc_rows[0]["course_id"])

    # Step 5: scoped topo sort query for this course
    concepts = get_concept_roadmap_scoped(course_id)
    node_ids = [str(concept["id"]) for concept in concepts]
    if not node_ids:
        raise RuntimeError(f"No concepts found in Neo4j for course '{course_id}'")

    # Step 6: roadmap_position scoped to (student_id, course_id)
    position = get_roadmap_position(student_id, course_id=course_id, client=supabase)
    current_index = min(max(0, int(position.get("current_index") or 0)), len(node_ids) - 1)

    # Only consider SRS reviews whose concept is in the current course's node_ids.
    # Otherwise stale rows from other courses would hijack the active concept.
    in_course = set(node_ids)
    due_reviews = [
        r for r in get_due_srs_records(student_id, client=supabase)
        if str(r.get("node_id") or r.get("concept_id") or "") in in_course
    ]
    if due_reviews:
        first_due = due_reviews[0]
        node_id = str(first_due.get("node_id") or first_due.get("concept_id"))
        mode = "review"
    else:
        node_id = node_ids[current_index]
        mode = "new_lesson"

    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "created_at": time.time(),
        "student": student,
        "course": course_id,
        "course_id": course_id,
        "concepts": concepts,
        "node_ids": node_ids,
        "node_id": node_id,
        "mode": mode,
        "chunks": get_chunks_for_concept(node_id),
        "messages": [],
        "transcript": [],
        "attempt_count": 0,
        "block_index": 0,
        "blocks_delivered": [],
        "knowledge_opened": False,
        "current_index": current_index,
    }
    SESSION_STORE[session_id] = session
    return _public_session(session)


def get_session_public(session_id: str) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError(session_id)
    return _public_session(session)


def generate_block(session_id: str) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError(session_id)
    if session["block_index"] >= BLOCKS_PER_CONCEPT:
        return {"action": "knowledge_check", **_public_session(session)}

    block_type = _next_block_type(session)
    trigger = {"role": "user", "content": f"Generate a {block_type} for this concept."}
    response_text = _call_converse(
        _system_prompt(session, _block_task(session, block_type)),
        session["messages"] + [trigger],
        max_tokens=1024,
    )
    try:
        parsed = _normalize_block_content(
            block_type,
            _parse_json_object(response_text),
            session=session,
        )
    except ValueError:
        parsed = _fallback_block_content(block_type, response_text, session=session)
    session["messages"].append(trigger)
    session["messages"].append({"role": "assistant", "content": response_text})
    session["blocks_delivered"].append(block_type)
    session["block_index"] += 1

    transcript_text = _transcript_text(block_type, parsed)
    session["transcript"].append(
        {
            "role": "assistant",
            "content": transcript_text,
            "meta": {"kind": "block", "block_type": block_type, "content": parsed},
        }
    )
    return {
        "action": "render_block",
        "type": block_type,
        "content": parsed,
        **_public_session(session),
    }


def _transcript_text(block_type: str, content: dict[str, Any]) -> str:
    if block_type == "video":
        return f"Video search: {content.get('search_query', '')}\n{content.get('why', '')}".strip()
    if block_type == "flashcard":
        return f"{content.get('front', '')}\n\n{content.get('back', '')}".strip()
    return f"{content.get('question', '')}\n\n{content.get('explanation', '')}".strip()


def classify_intent(message: str, concept_name: str) -> Intent:
    system = """Classify the student's message into exactly one of three categories:
- question: the student is asking for clarification or help understanding something
- attempt: the student is trying to answer a question or demonstrate their understanding
- done: the student is signalling they want to move on, such as done, got it, ready, or move on

Reply with only the single word: question, attempt, or done. No punctuation, no explanation."""
    raw = _call_converse(
        system,
        [{"role": "user", "content": f"Concept being taught: {concept_name}\n\nStudent message: {message}"}],
        model_id=FAST_MODEL_ID,
        temperature=0,
        max_tokens=10,
    ).strip().lower()
    return raw if raw in {"question", "attempt", "done"} else "attempt"  # type: ignore[return-value]


def lesson_message(session_id: str, message: str | None = None) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError(session_id)
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))

    if not message or not message.strip():
        task = f"""All content blocks for this concept have been delivered.
Ask the student one open-ended question to check their understanding of {concept_name}.
The question must be specific to the source material, not a generic comprehension check.
Do not ask a multiple choice question. Ask something that requires them to explain in their own words.
Keep the question concise."""
        trigger = {"role": "user", "content": "Start the knowledge check."}
        reply = _call_converse(_system_prompt(session, task), session["messages"] + [trigger], max_tokens=500)
        session["messages"].append(trigger)
        session["messages"].append({"role": "assistant", "content": reply})
        session["transcript"].append({"role": "assistant", "content": reply, "meta": {"kind": "knowledge_check"}})
        session["knowledge_opened"] = True
        return {"action": "knowledge_check", "reply": reply, **_public_session(session)}

    user_text = message.strip()
    session["messages"].append({"role": "user", "content": user_text})
    session["transcript"].append({"role": "user", "content": user_text, "meta": {}})
    intent = classify_intent(user_text, concept_name)
    if intent == "done":
        return {"action": "complete", "intent": intent, **_public_session(session)}

    if intent == "question":
        task = """The student has a question. Answer it clearly and concisely using the source material.
Do not re-explain the entire concept. Address only what they asked.
After answering, prompt them to continue with the knowledge check."""
    else:
        session["attempt_count"] += 1
        task = """The student has attempted to answer your question. Their response is in the conversation above.
Evaluate their understanding specifically against the source material.
Tell them clearly what they got right and what they missed or got wrong.
If they have shown sufficient understanding, confirm it and ask them to type "done" to move on.
If they have not, ask a targeted follow-up question to guide them toward the right understanding.
Do not repeat content already covered. Build on what they said."""
        if session["attempt_count"] >= 3:
            task += "\nIf they still have not shown mastery, suggest revisiting the most relevant prerequisite and do not advance."

    reply = _call_converse(_system_prompt(session, task), session["messages"], max_tokens=800)
    session["messages"].append({"role": "assistant", "content": reply})
    session["transcript"].append({"role": "assistant", "content": reply, "meta": {"kind": "knowledge_check", "intent": intent}})
    return {"action": "reply", "intent": intent, "reply": reply, **_public_session(session)}


def complete_lesson(session_id: str) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError(session_id)
    system = """You are evaluating a student's understanding of a concept based on a tutoring conversation.
Read the full conversation and score the student's demonstrated understanding from 0 to 5:
0-2: Does not understand the concept
3: Basic understanding, some gaps remain
4: Solid understanding, minor gaps
5: Strong understanding, could explain it to someone else
Return JSON only, no other text: {"score": N}"""
    raw = _call_converse(system, session["messages"], model_id=FAST_MODEL_ID, temperature=0, max_tokens=30)
    score = max(0, min(5, int(_parse_json_object(raw).get("score", 0))))
    supabase = get_supabase_client()
    srs_record = upsert_srs_record(
        student_id=session["student"]["id"],
        node_id=session["node_id"],
        course=session.get("course"),
        score=score,
        metadata={"session_id": session_id},
        client=supabase,
    )

    if score >= PASSING_SCORE:
        public = _public_session(session)
        progress = advance_roadmap_index(
            student_id=session["student"]["id"],
            node_ids=session["node_ids"],
            current_node_id=session["node_id"],
            course_id=session.get("course_id", ""),
            client=supabase,
        )
        SESSION_STORE.pop(session_id, None)
        return {
            "action": "complete" if progress["complete"] else "advance",
            "score": score,
            "srs_record": srs_record,
            "roadmap_progress": progress,
            **public,
        }

    session["mode"] = "retry"
    session["block_index"] = 0
    session["blocks_delivered"] = []
    return {"action": "retry", "score": score, "srs_record": srs_record, **_public_session(session)}
