from __future__ import annotations

import json
import os
import re
import time
import uuid
from difflib import SequenceMatcher
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

MODEL_ID = os.getenv("BEDROCK_MODEL_ID",
                     "anthropic.claude-3-haiku-20240307-v1:0")
FAST_MODEL_ID = os.getenv("BEDROCK_FAST_MODEL_ID", MODEL_ID)
AWS_REGION = os.getenv("AWS_REGION", os.getenv(
    "AWS_DEFAULT_REGION", "us-east-1"))

BLOCKS_PER_CONCEPT = 3
# One block per concept in this order — avoids three MCQs when preferred_formats is empty.
_BLOCK_TYPE_CYCLE: tuple[Literal["video", "flashcard", "mcq"], ...] = (
    "video",
    "flashcard",
    "mcq",
)
SESSION_STORE: dict[str, dict[str, Any]] = {}
_SESSION_MAX = 200

Intent = Literal["question", "attempt", "done"]

# Knowledge check: flag answers that are mostly a contiguous copy of lesson + generated blocks
_MIN_ANSWER_LEN_PASTE_CHECK = 22
_MIN_CONTIGUOUS_MATCH = 48
_MIN_MATCH_FRACTION = 0.52

_PASTE_NUDGE = (
    "That answer looks very close to the wording from the lesson or activities. "
    "In your own words, try again: explain the idea, apply it to a short example, "
    "or say what would be different if a key part changed. "
    "A one-line quote is fine, but the rest should be you."
)


def _prune_sessions() -> None:
    if len(SESSION_STORE) <= _SESSION_MAX:
        return
    oldest = sorted(SESSION_STORE.items(),
                    key=lambda item: item[1].get("created_at", 0))
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
        raise ValueError(
            f"Model returned malformed JSON: {text[:500]}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON was not an object")
    return parsed


def _resolve_video_block(search_query: str, why: str) -> dict[str, Any]:
    """Resolve a YouTube search query into a concrete video for the frontend.

    The frontend needs `url`, `title`, `channel`, and `thumbnail` to render an
    embedded player. If YOUTUBE_API_KEY is missing or the search fails, those
    fields are returned empty and the UI will fall back to a text prompt.
    """
    base = {
        "search_query": search_query,
        "search_query_used": search_query,
        "why": why,
        "url": "",
        "title": "",
        "channel": "",
        "thumbnail": "",
    }
    try:
        from youtube.client import search_videos

        results = search_videos(search_query, max_results=1)
    except Exception as exc:
        print(f"[adaptive_session] YouTube lookup failed: {exc}")
        return base

    if not results:
        return base

    top = results[0]
    base.update(
        {
            "url": str(top.get("url") or ""),
            "title": str(top.get("title") or ""),
            "channel": str(top.get("channel") or ""),
            "thumbnail": str(top.get("thumbnail") or ""),
        }
    )
    return base


def _normalize_block_content(
    block_type: Literal["video", "flashcard", "mcq"],
    content: dict[str, Any],
    *,
    session: dict[str, Any],
) -> dict[str, Any]:
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))
    if block_type == "video":
        search_query = str(content.get("search_query")
                           or f"{concept_name} tutorial")
        why = str(content.get("why")
                  or f"This video search can help reinforce {concept_name}.")
        return _resolve_video_block(search_query, why)
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
        search_query = f"{concept_name} tutorial"
        why = cleaned[:
                      240] or f"This search should help reinforce {concept_name}."
        return _resolve_video_block(search_query, why)
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
    text = "\n\n".join(str(chunk.get("text") or "").strip()
                       for chunk in chunks if chunk.get("text"))
    return text or "No source excerpts were found for this concept."


def _block_snapshot_for_prompt(block_type: str, content: dict[str, Any]) -> str:
    """Compact text so the model can avoid repeating the same teaching angle."""
    max_len = 700
    if block_type == "video":
        s = (
            f"[Video] search_query={content.get('search_query', '')!r}; "
            f"why={content.get('why', '')}"
        )
    elif block_type == "flashcard":
        s = f"[Flashcard] front: {content.get('front', '')}\nback: {content.get('back', '')}"
    else:
        opts = content.get("options")
        opts_txt = ""
        if isinstance(opts, list):
            opts_txt = "; ".join(str(o) for o in opts[:4])
        s = (
            f"[MCQ] question: {content.get('question', '')}\n"
            f"options: {opts_txt}\ncorrect: {content.get('correct', '')}; "
            f"explanation: {content.get('explanation', '')}"
        )
    s = s.strip()
    if len(s) > max_len:
        return s[:max_len] + "…"
    return s


def _blocks_delivered_detail(session: dict[str, Any]) -> str:
    snapshots = session.get("block_snapshots") or []
    if snapshots:
        lines = [f"{i + 1}. {snap}" for i, snap in enumerate(snapshots)]
        return "\n".join(lines)
    blocks = session.get("blocks_delivered") or []
    if not blocks:
        return "No content has been delivered yet."
    labels = {
        "video": "A video recommendation",
        "flashcard": "A flashcard on key terms",
        "mcq": "A multiple choice question",
    }
    return "\n".join(f"- {labels.get(block, block)}" for block in blocks)


def _next_block_type(session: dict[str, Any]) -> Literal["video", "flashcard", "mcq"]:
    idx = int(session.get("block_index") or 0)
    return _BLOCK_TYPE_CYCLE[idx % len(_BLOCK_TYPE_CYCLE)]


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

You have already delivered the following content for this concept (exact prior outputs — do not repeat the same terms, questions, or teaching angle):
---
{_blocks_delivered_detail(session)}
---
Do NOT repeat or paraphrase the same core fact, definition, or question as above. Each new block must add a distinct angle (e.g. different sub-idea, term, or assessment focus).

{task}""".strip()


def _block_task(session: dict[str, Any], block_type: str) -> str:
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))
    confidence = _profile_value(
        session["student"], "subject_confidence", "unknown")
    if block_type == "video":
        return f"""Suggest a YouTube search query for a video that would help a {confidence}
student understand {concept_name}.
Format as JSON only, no other text:
{{
  "search_query": "specific search string",
  "why": "one sentence explaining why this suits this specific student"
}}"""
    if block_type == "flashcard":
        return f"""Generate a flashcard for an important term or idea in {concept_name} that is not already covered in the prior blocks listed above (different term or angle).
Format as JSON only, no other text:
{{
  "front": "term or short question",
  "back": "definition or answer written for a {confidence} student"
}}"""
    return f"""Generate a multiple choice question testing understanding of {concept_name}.
Ground the question in the source material above. Ask about a different detail or inference than any prior block; do not ask a generic or duplicate question.
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
        raise ValueError(
            f"No course enrollment found for student '{student_id}'")
    course_id = str(sc_rows[0]["course_id"])

    # Step 5: pull the cached lecture-grouped lesson roadmap so the lesson loop
    # walks concepts in the same order the student-facing roadmap renders them.
    # Falls back to the raw topo sort if the cache hasn't been built yet.
    concepts: list[dict] = []
    node_ids: list[str] = []
    concept_to_lesson: dict[str, str] = {}
    try:
        from server import _get_or_build_lesson_roadmap

        roadmap = _get_or_build_lesson_roadmap(student_id, course_id)
        for lesson in roadmap.get("lessons") or []:
            lesson_id = str(lesson.get("lesson_id") or "")
            for c in lesson.get("concepts") or []:
                cid = str(c.get("id") or "")
                if not cid:
                    continue
                concepts.append({
                    "id": cid,
                    "name": c.get("name") or cid,
                    "description": c.get("description") or "",
                })
                node_ids.append(cid)
                if lesson_id:
                    concept_to_lesson[cid] = lesson_id
    except Exception as exc:
        print(f"[adaptive_session] lesson roadmap unavailable for {course_id!r}: {exc}; falling back to raw topo sort")

    if not node_ids:
        concepts = get_concept_roadmap_scoped(course_id)
        node_ids = [str(concept["id"]) for concept in concepts]
    if not node_ids:
        raise RuntimeError(
            f"No concepts found in Neo4j for course '{course_id}'")

    # Step 6: roadmap_position scoped to (student_id, course_id)
    position = get_roadmap_position(
        student_id, course_id=course_id, client=supabase)
    current_index = min(
        max(0, int(position.get("current_index") or 0)), len(node_ids) - 1)

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
        "block_snapshots": [],
        "knowledge_opened": False,
        "current_index": current_index,
        "concept_to_lesson": concept_to_lesson,
        "lesson_id": concept_to_lesson.get(node_id, ""),
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
    trigger = {"role": "user",
               "content": f"Generate a {block_type} for this concept."}
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
        parsed = _fallback_block_content(
            block_type, response_text, session=session)
    session["messages"].append(trigger)
    session["messages"].append({"role": "assistant", "content": response_text})
    session["blocks_delivered"].append(block_type)
    session.setdefault("block_snapshots", []).append(
        _block_snapshot_for_prompt(block_type, parsed)
    )
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


def _norm_for_overlap(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _knowledge_check_corpus(session: dict[str, Any]) -> str:
    """Text we treat as the lesson: chunks + all generated block snapshots / block transcript."""
    parts: list[str] = [str(_source_text(session.get("chunks", [])) or "")]
    for snap in session.get("block_snapshots", []):
        if isinstance(snap, str) and snap.strip():
            parts.append(snap)
    for entry in session.get("transcript", []):
        meta = entry.get("meta") or {}
        if not isinstance(meta, dict) or meta.get("kind") != "block":
            continue
        bt = meta.get("block_type")
        cont = meta.get("content")
        if isinstance(cont, dict) and isinstance(bt, str):
            parts.append(_transcript_text(bt, cont))
        else:
            parts.append(str(entry.get("content") or ""))
    return _norm_for_overlap(" ".join(parts))


def _suspected_paste_of_lesson(answer: str, session: dict[str, Any]) -> bool:
    """Heuristic: long contiguous match between answer and lesson+blocks text."""
    a = _norm_for_overlap(answer)
    if len(a) < _MIN_ANSWER_LEN_PASTE_CHECK:
        return False
    c = _knowledge_check_corpus(session)
    if len(c) < 20:
        return False
    c_cap = c if len(c) <= 120_000 else c[:120_000]
    if len(a) >= 20 and a in c_cap:
        return True
    m = SequenceMatcher(
        None,
        a,
        c_cap,
        autojunk=False,
    ).find_longest_match(0, len(a), 0, len(c_cap))
    need = max(
        _MIN_CONTIGUOUS_MATCH,
        int(_MIN_MATCH_FRACTION * len(a)),
    )
    return m.size >= need


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
    # type: ignore[return-value]
    return raw if raw in {"question", "attempt", "done"} else "attempt"


def lesson_message(session_id: str, message: str | None = None) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError(session_id)
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))

    if not message or not message.strip():
        task = f"""All content blocks for this concept have been delivered.
Ask ONE open-ended question to check understanding of {concept_name}.
The question must be specific to the source material.
Do NOT ask for a rote definition, a list of terms, or anything the student could answer by copying a single paragraph from the lesson.
Prefer: a short what-if, a compare/contrast, an application to a new situation, or "what would go wrong if…" — so they must paraphrase or reason, not paste.
Do not use MCQ/flashcard format. Keep the question concise (2–4 sentences max)."""
        trigger = {"role": "user", "content": "Start the knowledge check."}
        reply = _call_converse(_system_prompt(
            session, task), session["messages"] + [trigger], max_tokens=500)
        session["messages"].append(trigger)
        session["messages"].append({"role": "assistant", "content": reply})
        session["transcript"].append(
            {"role": "assistant", "content": reply, "meta": {"kind": "knowledge_check"}})
        session["knowledge_opened"] = True
        return {"action": "knowledge_check", "reply": reply, **_public_session(session)}

    user_text = message.strip()
    session["messages"].append({"role": "user", "content": user_text})
    session["transcript"].append(
        {"role": "user", "content": user_text, "meta": {}})
    intent = classify_intent(user_text, concept_name)
    if intent == "done":
        return {"action": "complete", "intent": intent, **_public_session(session)}

    if intent == "question":
        task = """The student has a question. Answer it clearly and concisely using the source material.
Do not re-explain the entire concept. Address only what they asked.
After answering, prompt them to continue with the knowledge check."""
    else:
        if _suspected_paste_of_lesson(user_text, session):
            reply = _PASTE_NUDGE
            session["messages"].append(
                {"role": "assistant", "content": reply})
            session["transcript"].append(
                {
                    "role": "assistant",
                    "content": reply,
                    "meta": {
                        "kind": "knowledge_check",
                        "intent": intent,
                        "paste_nudge": True,
                    },
                }
            )
            return {"action": "reply", "intent": intent, "reply": reply, **_public_session(session)}

        session["attempt_count"] += 1
        task = """The student has attempted to answer your question. Their response is in the conversation above.
Evaluate their understanding specifically against the source material.
If their answer is mostly copied from the lesson text without added reasoning, say so gently and ask them to restate in their own words or use a small new example.
Tell them clearly what they got right and what they missed or got wrong.
If they have shown sufficient understanding, confirm it and ask them to type "done" to move on.
If they have not, ask a targeted follow-up that requires application (not a definition they can paste).
Do not repeat content already covered. Build on what they said."""
        if session["attempt_count"] >= 3:
            task += "\nIf they still have not shown mastery, suggest revisiting the most relevant prerequisite and do not advance."

    reply = _call_converse(_system_prompt(session, task),
                           session["messages"], max_tokens=800)
    session["messages"].append({"role": "assistant", "content": reply})
    session["transcript"].append({"role": "assistant", "content": reply, "meta": {
                                 "kind": "knowledge_check", "intent": intent}})
    return {"action": "reply", "intent": intent, "reply": reply, **_public_session(session)}


def _persist_lesson_session(
    session: dict[str, Any],
    *,
    score: int,
    passed: bool,
    client: Any,
) -> None:
    """Upsert a row into `lesson_sessions` so the transcript survives session teardown.

    Silent on failure — if the migration hasn't been applied or RLS blocks the write,
    we log and move on rather than failing the lesson completion endpoint.
    """
    try:
        concept = _concept_for(session, session["node_id"])
        row = {
            "session_id": session["session_id"],
            "student_id": session["student"]["id"],
            "course_id": session.get("course_id") or session.get("course") or "",
            "lesson_id": session.get("lesson_id") or "",
            "concept_id": session["node_id"],
            "concept_name": str(concept.get("name") or concept.get("id") or ""),
            "mode": session.get("mode"),
            "score": score,
            "passed": passed,
            "transcript": session.get("transcript", []),
            "metadata": {
                "attempt_count": session.get("attempt_count", 0),
                "blocks_delivered": session.get("blocks_delivered", []),
            },
            "started_at": _isoformat(session.get("created_at")),
        }
        client.table("lesson_sessions").upsert(row, on_conflict="session_id").execute()
    except Exception as exc:
        print(
            f"[adaptive_session] failed to persist lesson_sessions row for "
            f"session={session.get('session_id')!r}: {exc}"
        )


def _isoformat(epoch_seconds: float | None) -> str | None:
    if not epoch_seconds:
        return None
    try:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc).isoformat()
    except Exception:
        return None


def complete_lesson(session_id: str) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError(session_id)
    concept = _concept_for(session, session["node_id"])
    concept_name = str(concept.get("name") or concept.get("id"))
    system = """You are an automated grader. You receive a transcript of a tutoring conversation and produce a score.
You are NOT addressing the student. You are NOT continuing the conversation. Do not greet, acknowledge, or explain.
Score the student's demonstrated understanding of the concept from 0 to 5 based ONLY on what the student wrote:
0-2: Does not understand the concept
3: Basic understanding, some gaps remain
4: Solid understanding, minor gaps
5: Strong understanding, could explain it to someone else
If the student's substantive answers are largely copied verbatim from the source material or prior tutor lines (no added reasoning, example, or paraphrase), cap the score at 2.
Return ONE JSON object and nothing else. Schema: {"score": <integer 0-5>}"""
    transcript_lines = [
        f"{m.get('role', '?')}: {m.get('content', '')}"
        for m in session.get("messages", [])
        if m.get("role") in {"user", "assistant"} and m.get("content")
    ]
    transcript = "\n".join(transcript_lines) or "(no conversation recorded)"
    grading_prompt = (
        f"Concept: {concept_name}\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Return the score JSON now."
    )
    raw = _call_converse(
        system,
        [{"role": "user", "content": grading_prompt}],
        model_id=FAST_MODEL_ID,
        temperature=0,
        max_tokens=64,
    )
    try:
        score = max(0, min(5, int(_parse_json_object(raw).get("score", 0))))
    except (ValueError, TypeError):
        # Fall back to scanning for a 0-5 digit instead of 500-ing the lesson.
        digit_match = re.search(r"\b([0-5])\b", raw)
        score = int(digit_match.group(1)) if digit_match else 0
        print(
            f"[adaptive_session] complete_lesson scoring fell back to regex; "
            f"score={score}, raw={raw!r}"
        )
    supabase = get_supabase_client()
    srs_record = upsert_srs_record(
        student_id=session["student"]["id"],
        node_id=session["node_id"],
        course=session.get("course"),
        score=score,
        metadata={"session_id": session_id},
        client=supabase,
    )

    passed = score >= PASSING_SCORE
    _persist_lesson_session(session, score=score, passed=passed, client=supabase)

    if passed:
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
    session["block_snapshots"] = []
    return {"action": "retry", "score": score, "srs_record": srs_record, **_public_session(session)}
