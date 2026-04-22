"""
Interactive lesson walkthrough: reuses Pinecone + YouTube (via lesson_generator.load_lesson_sources),
generates content step-by-step with Bedrock, and returns structured UI blocks (MCQ, flashcards, etc.).
No SRS — progression is conversational checkpoints only.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from bedrock.client import create_bedrock_runtime_client
from lesson_generator import load_lesson_sources

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

# How much lecture text to pass into each LLM call (characters).
MAX_SOURCE_CHARS = 14_000

# In-memory sessions (dev / single-node). Replace with Redis if you scale horizontally.
_SESSIONS: dict[str, dict[str, Any]] = {}
_SESSION_MAX = 200

# Same layout as server.py lesson cache (GET /lesson writes here).
_LESSON_CACHE_DIR = Path(__file__).resolve().parent / "lesson_cache"


def _merge_videos_from_lesson_cache(
    sources: dict[str, Any],
    lesson_id: str,
    persona_id: str,
    course: str | None,
) -> str | None:
    """
    If YouTube returned nothing, reuse `videos` from a previously generated lesson JSON
    (classic /lesson cache) so interactive mode still shows links when offline or unconfigured.
    """
    if sources.get("videos"):
        return None
    folder = f"{persona_id}_{course}" if course else persona_id
    path = _LESSON_CACHE_DIR / folder / f"{lesson_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    vids = data.get("videos")
    if not isinstance(vids, list) or not vids:
        return None
    sources["videos"] = vids
    return (
        "Using videos from a saved generated lesson on disk. "
        "Open the classic lesson view once with a working YOUTUBE_API_KEY to refresh this list."
    )


def _video_status(
    sources: dict[str, Any],
    had_youtube_results: bool,
    cache_note: str | None,
) -> dict[str, Any]:
    has_v = bool(sources.get("videos"))
    if has_v:
        src = "youtube" if had_youtube_results else "lesson_cache"
        detail = cache_note if src == "lesson_cache" else None
    else:
        src = "none"
        detail = sources.get("video_search_error")
        if isinstance(detail, str) and detail:
            pass
        else:
            detail = (
                "No videos to show. Set YOUTUBE_API_KEY in backend/.env, restart the server, "
                "or open the classic lesson once to build cache."
            )
    return {"source": src, "detail": detail}

STEP_TYPES: list[tuple[str, str]] = [
    ("concept", "Introduce core definitions and intuition. Stay grounded in the source material."),
    ("example", "Work a concrete example tied to the excerpts. No invented course policies."),
    ("summary", "Recap what matters and how it connects to the lesson title."),
]

# One user turn after overview, then per teaching step: teach (LLM) → reflect → optional widget → confirm.
# "Engage" (follow-up + widget choice) runs inline when the learner submits their reflection.
STAGES: list[str] = ["after_overview_confirm"] + sum(
    [
        [
            f"step{i}_content_llm",
            f"reflect_step{i}_user",
            f"widget_step{i}_user",
            f"confirm_step{i}_user",
        ]
        for i in range(len(STEP_TYPES))
    ],
    [],
) + ["closing_llm", "complete"]


def _stage_index(name: str) -> int:
    return STAGES.index(name)


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        out = json.loads(text)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Model returned no JSON object: {text[:400]}")
    raw = match.group(0)
    try:
        out = json.loads(raw)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass

    def _escape_string(m: re.Match[str]) -> str:
        inner = m.group(1)
        inner = inner.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        inner = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", inner)
        return f'"{inner}"'

    cleaned = re.sub(r'"((?:[^"\\]|\\.)*)"', _escape_string, raw, flags=re.DOTALL)
    return json.loads(cleaned)


def _call_converse(system: str, user: str, *, temperature: float = 0.35, max_tokens: int = 4096) -> str:
    client = create_bedrock_runtime_client(region=AWS_REGION)
    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"type": "text", "text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return "".join(
        block["text"] for block in response["output"]["message"]["content"] if "text" in block
    ).strip()


# When excerpts are missing, older prompts caused the model to tell learners to "install Pinecone" — forbid that.
_LLM_NEVER_INFRA = (
    "If SOURCE EXCERPTS below is empty or says no excerpts were attached, teach from CONCEPTS and the lesson title only. "
    "Never tell the learner to install Python packages, Pinecone, or other tools. Never blame missing infrastructure."
)


def _bundle_sources(chunks: list[str]) -> str:
    if not chunks:
        return (
            "[No lecture transcript excerpts are attached to this session — teach from CONCEPTS and title. "
            "Do not mention installing software or Pinecone.]"
        )
    joined = "\n\n---\n\n".join(chunks)
    if len(joined) > MAX_SOURCE_CHARS:
        joined = joined[:MAX_SOURCE_CHARS] + "\n\n[…truncated…]"
    return joined


_CONTEXT_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "with",
        "by",
        "from",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "we",
        "you",
        "they",
        "their",
        "not",
        "no",
        "so",
        "if",
        "then",
        "than",
        "into",
        "our",
        "out",
        "up",
        "all",
        "can",
        "will",
        "has",
        "have",
        "about",
        "what",
        "when",
        "where",
        "which",
        "who",
        "how",
    }
)


def _tokens(s: str) -> set[str]:
    return {
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", s)
        if w.lower() not in _CONTEXT_STOP
    }


def _relevance_score(focus_query: str, chunk_text: str) -> float:
    q = _tokens(focus_query)
    c = _tokens(chunk_text)
    if not q or not c:
        return 0.0
    inter = len(q & c)
    return float(inter) / (len(q) ** 0.5 + 0.25)


def _pick_context_chunks(
    chunk_entries: list[dict[str, Any]],
    *,
    focus_query: str,
    max_segments: int = 5,
    max_chars: int = MAX_SOURCE_CHARS,
) -> list[str]:
    """Rank Pinecone excerpts by token overlap with the current focus (no extra embeddings API)."""
    if not chunk_entries:
        return []
    scored: list[tuple[float, str]] = []
    for ent in chunk_entries:
        text = str(ent.get("text") or "")
        if not text.strip():
            continue
        scored.append((_relevance_score(focus_query, text), text))
    scored.sort(key=lambda x: -x[0])
    out: list[str] = []
    total = 0
    for score, text in scored:
        if score <= 0 and out:
            break
        if len(out) >= max_segments:
            break
        if total + len(text) > max_chars and out:
            break
        out.append(text)
        total += len(text)
    if not out and scored:
        out.append(scored[0][1][:max_chars])
    return out


def _recent_transcript_for_context(session: dict[str, Any], *, max_chars: int = 2800) -> str:
    """Latest learner + tutor turns (newest last), skipping system placeholders."""
    formatted: list[str] = []
    for entry in session.get("transcript") or []:
        role = entry.get("role")
        content = str(entry.get("content") or "").strip()
        if not content:
            continue
        if content.startswith("[Learner: ready to continue]"):
            continue
        if content.startswith("[Completed activity:"):
            continue
        prefix = "Learner" if role == "user" else "Tutor"
        formatted.append(f"{prefix}: {content[:900]}")
    # Keep the tail so "what we just went over" is the most recent dialogue.
    out: list[str] = []
    n = 0
    for line in reversed(formatted):
        if n + len(line) > max_chars and out:
            break
        out.append(line)
        n += len(line) + 1
    return "\n".join(reversed(out))


def _contextual_source_chunks(
    session: dict[str, Any],
    *,
    kind: str,
    step_index: int | None = None,
    reflection: str | None = None,
) -> list[str]:
    sources = session["sources"]
    entries = sources.get("chunk_entries") or []
    fallback = sources.get("chunks") or []
    if not entries:
        return list(fallback)

    lesson = sources.get("lesson") or {}
    title = str(lesson.get("title") or "")
    concepts = lesson.get("concepts") or []

    if kind == "overview":
        cnames = " ".join(c.get("name", "") for c in concepts[:6])
        focus = f"{title} introduction overview {cnames}"
        return _pick_context_chunks(entries, focus_query=focus)

    if kind == "step" and step_index is not None:
        stype, hint = STEP_TYPES[step_index]
        prior = session.get("step_summaries") or []
        prior_txt = " ".join(p.get("excerpt", "") for p in prior[-3:])
        cnames = [c.get("name", "") for c in concepts if isinstance(c, dict)]
        bucket: list[str] = []
        if cnames:
            n = len(cnames)
            k = len(STEP_TYPES)
            span = max(1, (n + k - 1) // k)
            bucket = cnames[step_index * span : (step_index + 1) * span] or [cnames[step_index % n]]
        dialogue = _recent_transcript_for_context(session)
        focus = (
            f"{stype} {hint} {title} {' '.join(bucket)} {prior_txt} {dialogue}"
        )
        return _pick_context_chunks(entries, focus_query=focus)

    if kind == "engage":
        lb = session.get("last_step_block") or {}
        prior_txt = " ".join(
            p.get("excerpt", "") for p in (session.get("step_summaries") or [])[-2:]
        )
        dialogue = _recent_transcript_for_context(session)
        focus = (
            f"{title} {lb.get('title', '')} {str(lb.get('content', ''))[:1800]} "
            f"{reflection or ''} {prior_txt} {dialogue}"
        )
        return _pick_context_chunks(entries, focus_query=focus, max_segments=4)

    if kind == "closing":
        sums = session.get("step_summaries") or []
        sum_txt = " ".join(s.get("excerpt", "") for s in sums)
        dialogue = _recent_transcript_for_context(session, max_chars=2000)
        focus = f"{title} recap summary {sum_txt} {dialogue}"
        return _pick_context_chunks(entries, focus_query=focus)

    return _pick_context_chunks(entries, focus_query=title)


def _video_search_context(session: dict[str, Any], reflection: str) -> str:
    lesson = session["sources"]["lesson"]
    lb = session.get("last_step_block") or {}
    tail = " ".join(p.get("excerpt", "") for p in (session.get("step_summaries") or [])[-2:])
    parts = [
        str(lesson.get("title") or ""),
        str(lb.get("title") or ""),
        str(lb.get("content") or "")[:700],
        reflection,
        tail,
    ]
    return " ".join(p for p in parts if p).strip()


def _public_chunks_status(sources: dict[str, Any]) -> dict[str, Any]:
    meta = sources.get("chunks_meta") or {}
    out: dict[str, Any] = {
        "status": meta.get("status"),
        "detail": meta.get("detail"),
        "requested_ids": int(meta.get("requested_ids") or 0),
        "loaded_segments": int(meta.get("loaded_segments") or 0),
        "namespace": meta.get("namespace"),
        "index": meta.get("index"),
    }
    if meta.get("missing_or_empty_ids_sample"):
        out["missing_ids_sample"] = meta["missing_or_empty_ids_sample"]
    if meta.get("namespaces_tried"):
        out["namespaces_tried"] = meta["namespaces_tried"]
    return out


def _normalize_videos(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for v in videos:
        out.append(
            {
                "title": v.get("title", ""),
                "url": v.get("url", ""),
                "channel": v.get("channel", ""),
                "thumbnail": v.get("thumbnail", ""),
                "reason": v.get("reason") or "Matched your lesson topic on YouTube.",
            }
        )
    return out


def _persona_block(persona: dict[str, Any]) -> str:
    return json.dumps(
        {
            "name": persona.get("name"),
            "major": persona.get("major"),
            "familiarity": persona.get("familiarity"),
            "learning_style": persona.get("learning_style"),
            "hours_per_week": persona.get("hours_per_week"),
            "notes": persona.get("notes"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _prune_sessions() -> None:
    if len(_SESSIONS) <= _SESSION_MAX:
        return
    # Drop oldest by created_at
    items = sorted(_SESSIONS.items(), key=lambda kv: kv[1].get("created_at", 0))
    for sid, _ in items[: max(0, len(_SESSIONS) - _SESSION_MAX + 20)]:
        _SESSIONS.pop(sid, None)


def _current_step_index(stage: str) -> int | None:
    m = re.match(r"(?:step|reflect_step|widget_step|confirm_step)(\d)_", stage)
    if not m:
        return None
    return int(m.group(1))


def _run_overview_llm(session: dict[str, Any]) -> str:
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    chunks = _contextual_source_chunks(session, kind="overview")
    videos = session["sources"]["videos"]
    system = f"""You are an expert tutor. Return valid JSON only. No markdown fences.

Schema:
{{"assistant_message": "string"}}

{_LLM_NEVER_INFRA}

Write a warm 2–4 sentence overview of the lesson: why it matters and what you will explore together.
Use ideas supported by the source excerpts when present; otherwise use the listed concepts. Do not invent policies."""
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}

LEARNER: {_persona_block(persona)}

SOURCE EXCERPTS (ranked for lesson intro from Pinecone — not the full course dump):
{_bundle_sources(chunks)}

RELATED VIDEOS (titles only): {", ".join(v.get("title", "") for v in videos)}

Return the JSON object now."""
    raw = _call_converse(system, user, temperature=0.25)
    data = _parse_json_object(raw)
    return str(data.get("assistant_message") or "").strip() or raw[:2000]


def _run_step_content_llm(session: dict[str, Any], step_index: int) -> dict[str, Any]:
    step_type, hint = STEP_TYPES[step_index]
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    chunks = _contextual_source_chunks(session, kind="step", step_index=step_index)
    prior = session.get("step_summaries", [])
    dialogue = _recent_transcript_for_context(session)
    system = f"""You are an expert tutor. Return valid JSON only. No markdown fences.

Schema:
{{
  "title": "string (short step title)",
  "step_type": "{step_type}",
  "content": "string (rich explanation; <= 180 words; use plain text or light markdown)"
}}

{_LLM_NEVER_INFRA}

This segment is the "{step_type}" portion: {hint}
Stay faithful to the excerpts when present; otherwise ground content in CONCEPTS. Do not invent facts."""
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}

LEARNER: {_persona_block(persona)}

ALREADY COVERED (summaries of prior segments):
{json.dumps(prior, ensure_ascii=False)}

RECENT CONVERSATION (what you and the learner have already said in this session):
{dialogue if dialogue.strip() else "[Session just started — no prior turns.]"}

SOURCE EXCERPTS (selected for this segment + recent context, not the whole course at once):
{_bundle_sources(chunks)}

Write segment {step_index + 1}/{len(STEP_TYPES)} now. Return JSON only."""
    raw = _call_converse(system, user, temperature=0.35)
    data = _parse_json_object(raw)
    title = str(data.get("title") or f"{step_type.title()}").strip()
    content = str(data.get("content") or "").strip()
    session.setdefault("step_summaries", []).append(
        {"step_index": step_index, "step_type": step_type, "title": title, "excerpt": content[:400]}
    )
    return {"title": title, "step_type": step_type, "content": content}


def _resolve_video_widget_payload(
    raw: dict[str, Any],
    lesson: dict[str, Any],
    *,
    context_focus: str | None = None,
) -> dict[str, Any]:
    """
    Build a single video card for the UI. Prefer an explicit YouTube URL from the model; otherwise
    search YouTube Data API (same as lesson_generator).
    """
    from youtube.client import search_videos

    url_in = str(raw.get("url") or "").strip()
    if url_in and ("youtube.com/" in url_in or "youtu.be/" in url_in):
        return {
            "title": str(raw.get("title") or "Suggested video"),
            "url": url_in,
            "channel": str(raw.get("channel") or ""),
            "thumbnail": str(raw.get("thumbnail") or ""),
            "reason": str(raw.get("reason") or raw.get("caption") or "Video you asked for."),
            "source": "model_url",
        }

    q = str(raw.get("search_query") or raw.get("query") or "").strip()
    if not q:
        q = (context_focus or "").strip()
    if not q:
        q = f"{lesson.get('title', '')} {' '.join(c.get('name', '') for c in (lesson.get('concepts') or [])[:3])}".strip()

    results: list[dict[str, Any]] = []
    try:
        results = search_videos(q, max_results=1)
    except Exception as exc:
        print(f"[dynamic_lesson] YouTube search for video widget failed: {exc}")

    if not results:
        return {
            "title": "",
            "url": "",
            "channel": "",
            "thumbnail": "",
            "reason": str(
                raw.get("caption")
                or "Could not load a video (check YOUTUBE_API_KEY and try again)."
            ),
            "source": "search_failed",
            "search_query_attempted": q,
        }

    v = results[0]
    return {
        "title": v.get("title", ""),
        "url": v.get("url", ""),
        "channel": v.get("channel", ""),
        "thumbnail": v.get("thumbnail", ""),
        "reason": str(raw.get("caption") or raw.get("reason") or f"Suggested for: {q}")[:400],
        "source": "youtube_search",
        "search_query_used": q,
    }


def _run_engage_llm(session: dict[str, Any], step_index: int, reflection: str) -> dict[str, Any]:
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    last_block = session.get("last_step_block") or {}
    engage_chunks = _contextual_source_chunks(session, kind="engage", reflection=reflection)
    dialogue = _recent_transcript_for_context(session)
    system = """You are an expert tutor. Return valid JSON only. No markdown fences.

Schema:
{
  "assistant_message": "string (brief reaction to what the learner said; encourage; clarify if needed)",
  "interaction": {
    "type": "none" | "mcq" | "flashcards" | "free_response" | "video",
    "payload": {}
  }
}

interaction.payload rules:
- type "none": payload {}.
- type "mcq": payload {"question": "...", "options": ["four strings"], "correct_index": 0-3, "explanation": "..."}.
- type "flashcards": payload {"concepts": [{"name": "...", "description": "..."}], "cards": optional [{"front": "...", "back": "..."}] } — if cards omitted, UI uses concepts as front/back.
- type "free_response": payload {"question": "..."}.
- type "video": payload {"search_query": "string (optional — specific keywords; backend also uses lecture context)", "caption": "string (one line why this helps)", "url": "optional full https://www.youtube.com/watch?v=... if you know a specific video" }.

IMPORTANT: If the learner asks to watch a video, see a clip, or wants something explained on YouTube, use type "video".
Ground your search_query in what you just taught and what they asked — do not use generic course titles alone.
The backend will run a real YouTube search merged with session context (or open your url). Do not invent watch URLs unless you are certain they exist.

SOURCE EXCERPTS below are retrieved for THIS moment (last segment + their message). Use them to stay on-topic.

Pick mcq or flashcards when a quick check helps; use video when they want audiovisual material; use free_response for open reflection; use none if the learner already showed strong understanding."""
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}
LEARNER: {_persona_block(persona)}

LAST TEACHING SEGMENT TITLE: {last_block.get("title")}
LAST TEACHING SEGMENT (excerpt): {(last_block.get("content") or "")[:1200]}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[No prior dialogue.]"}

SOURCE EXCERPTS (ranked for this checkpoint — tie your response to these ideas when relevant):
{_bundle_sources(engage_chunks)}

LEARNER REFLECTION / QUESTION:
{reflection}

Return JSON only."""
    raw = _call_converse(system, user, temperature=0.4)
    data = _parse_json_object(raw)
    msg = str(data.get("assistant_message") or "").strip()
    inter = data.get("interaction")
    if not isinstance(inter, dict):
        inter = {"type": "none", "payload": {}}
    itype = str(inter.get("type") or "none").lower()
    if itype not in ("none", "mcq", "flashcards", "free_response", "video"):
        itype = "none"
    payload = inter.get("payload") if isinstance(inter.get("payload"), dict) else {}
    if itype == "video":
        vctx = _video_search_context(session, reflection)
        payload = _resolve_video_widget_payload(payload, lesson, context_focus=vctx)
    return {"assistant_message": msg, "interaction": {"type": itype, "payload": payload}}


def _run_closing_llm(session: dict[str, Any]) -> str:
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    summaries = session.get("step_summaries", [])
    closing_chunks = _contextual_source_chunks(session, kind="closing")
    dialogue = _recent_transcript_for_context(session, max_chars=2200)
    system = """You are an expert tutor. Return JSON only: {"assistant_message": "string"}
Congratulate the learner, recap 3 bullets max, suggest one concrete next action (e.g. try a problem, rewatch a clip)."""
    user = f"""LESSON: {lesson.get("title")}
LEARNER: {_persona_block(persona)}
SEGMENT SUMMARIES: {json.dumps(summaries, ensure_ascii=False)}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[n/a]"}

SOURCE EXCERPTS (selected for wrap-up):
{_bundle_sources(closing_chunks)}
Return JSON only."""
    raw = _call_converse(system, user, temperature=0.3)
    data = _parse_json_object(raw)
    return str(data.get("assistant_message") or "").strip()


def _run_checkpoint_help_llm(
    session: dict[str, Any],
    *,
    stage: str,
    learner_message: str,
) -> str:
    """
    Conversational helper used when the learner clicks "not quite yet" at a checkpoint.
    It acknowledges what they asked, gives a concise clarification, and keeps the learner
    on the same checkpoint instead of jumping to the next teaching block.
    """
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    last_block = session.get("last_step_block") or {}
    dialogue = _recent_transcript_for_context(session, max_chars=2200)

    step_i = _current_step_index(stage)
    if step_i is not None:
        chunks = _contextual_source_chunks(
            session,
            kind="engage",
            step_index=step_i,
            reflection=learner_message,
        )
    else:
        chunks = _contextual_source_chunks(session, kind="overview")

    system = """You are a supportive AI tutor. Return valid JSON only. No markdown fences.

Schema:
{"assistant_message":"string"}

Behavior requirements:
- Start by acknowledging the learner's request in plain language (e.g., "Sure, let's go over that again.").
- Then clarify the key idea briefly (2-4 short sentences).
- Do NOT output a brand-new lesson block with headings.
- End with one gentle checkpoint question like "Does this make more sense?".
- Keep tone conversational and encouraging."""
    user = f"""LESSON: {lesson.get("title")}
LEARNER: {_persona_block(persona)}

LAST TEACHING SEGMENT TITLE: {last_block.get("title")}
LAST TEACHING SEGMENT (excerpt): {(last_block.get("content") or "")[:1200]}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[n/a]"}

SOURCE EXCERPTS (selected for this clarification):
{_bundle_sources(chunks)}

LEARNER MESSAGE AT CHECKPOINT:
{learner_message}

Return JSON only."""
    raw = _call_converse(system, user, temperature=0.35, max_tokens=700)
    data = _parse_json_object(raw)
    out = str(data.get("assistant_message") or "").strip()
    if out:
        return out
    return (
        "Sure, let's go over that again. Here's the main idea in simpler terms: "
        "focus on the key relationship we just covered and how it applies in the example. "
        "Does this make more sense?"
    )


def _append_assistant(session: dict[str, Any], text: str, *, meta: dict[str, Any] | None = None) -> None:
    session.setdefault("transcript", []).append(
        {"role": "assistant", "content": text, "meta": meta or {}}
    )


def _append_user(session: dict[str, Any], text: str) -> None:
    session.setdefault("transcript", []).append({"role": "user", "content": text, "meta": {}})


def start_session(lesson_id: str, persona_id: str, course: str | None) -> dict[str, Any]:
    _prune_sessions()
    sources = load_lesson_sources(lesson_id, persona_id, course)
    had_youtube_results = bool(sources.get("videos"))
    cache_note = _merge_videos_from_lesson_cache(sources, lesson_id, persona_id, course)
    video_status = _video_status(sources, had_youtube_results, cache_note)

    session_id = str(uuid.uuid4())
    session: dict[str, Any] = {
        "session_id": session_id,
        "lesson_id": lesson_id,
        "persona_id": persona_id,
        "course": course,
        "sources": sources,
        "video_status": video_status,
        "cursor": 0,
        "transcript": [],
        "step_summaries": [],
        "last_step_block": None,
        "pending_widget": None,
        "created_at": time.time(),
    }
    overview = _run_overview_llm(session)
    _append_assistant(session, overview, meta={"kind": "overview"})
    _SESSIONS[session_id] = session

    stage = STAGES[session["cursor"]]
    return {
        "session_id": session_id,
        "stage": stage,
        "lesson_title": sources["lesson"].get("title", ""),
        "concepts": sources["lesson"].get("concepts", []),
        "videos": _normalize_videos(sources["videos"]),
        "video_status": video_status,
        "chunks_status": _public_chunks_status(sources),
        "transcript": session["transcript"],
        "pending_widget": None,
        "awaiting": _awaiting_for_stage(stage),
        "model_id": MODEL_ID,
    }


def _awaiting_for_stage(stage: str) -> Literal["confirm", "text", "widget", "none"]:
    if stage == "complete":
        return "none"
    # First checkpoint after the overview — name does not end in _user but still needs Yes / not yet.
    if stage == "after_overview_confirm":
        return "confirm"
    if "confirm" in stage and "user" in stage:
        return "confirm"
    if stage.startswith("reflect_"):
        return "text"
    if stage.startswith("widget_"):
        return "widget"
    return "none"


def get_session(session_id: str) -> dict[str, Any] | None:
    return _SESSIONS.get(session_id)


def get_session_public(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError(session_id)
    return _response(session)


def _public_transcript(session: dict[str, Any]) -> list[dict[str, Any]]:
    return list(session.get("transcript", []))


def _response(session: dict[str, Any]) -> dict[str, Any]:
    stage = STAGES[session["cursor"]] if session["cursor"] < len(STAGES) else "complete"
    return {
        "session_id": session["session_id"],
        "stage": stage,
        "lesson_title": session["sources"]["lesson"].get("title", ""),
        "concepts": session["sources"]["lesson"].get("concepts", []),
        "videos": _normalize_videos(session["sources"]["videos"]),
        "video_status": session.get("video_status") or {"source": "none", "detail": None},
        "chunks_status": _public_chunks_status(session["sources"]),
        "transcript": _public_transcript(session),
        "pending_widget": session.get("pending_widget"),
        "awaiting": _awaiting_for_stage(stage),
        "model_id": MODEL_ID,
    }


def _auto_run_llm_stages(session: dict[str, Any]) -> None:
    """Run consecutive LLM stages until we need user input or complete."""
    while session["cursor"] < len(STAGES):
        stage = STAGES[session["cursor"]]
        if stage == "complete":
            return
        if stage.endswith("_user"):
            return
        if stage == "closing_llm":
            text = _run_closing_llm(session)
            _append_assistant(session, text, meta={"kind": "closing"})
            session["cursor"] += 1
            continue

        m = re.match(r"step(\d)_content_llm", stage)
        if m:
            idx = int(m.group(1))
            block = _run_step_content_llm(session, idx)
            session["last_step_block"] = block
            body = f"**{block['title']}**\n\n{block['content']}"
            _append_assistant(session, body, meta={"kind": "step", "step_index": idx, **block})
            session["cursor"] += 1
            continue

        # Should not reach other _llm names without user; safety
        session["cursor"] += 1


def tick_session(
    session_id: str,
    *,
    message: str | None = None,
    action: str | None = None,
    widget_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("unknown session")

    if session["cursor"] >= len(STAGES) or STAGES[session["cursor"]] == "complete":
        return _response(session)

    stage = STAGES[session["cursor"]]

    # Optional widget was skipped by the model — don't block the learner on an empty slot.
    if stage.startswith("widget_") and session.get("pending_widget") is None:
        session["cursor"] += 1
        stage = STAGES[session["cursor"]] if session["cursor"] < len(STAGES) else "complete"

    if stage.endswith("_user"):
        if stage.startswith("confirm") or stage == "after_overview_confirm":
            if action == "confirm_yes":
                _append_user(session, "[Learner: ready to continue]")
                session["cursor"] += 1
                session["pending_widget"] = None
            elif action == "confirm_not_yet" or (message or "").strip():
                learner_msg = (message or "").strip() or "I need more help before moving on."
                _append_user(session, learner_msg)
                helper = _run_checkpoint_help_llm(
                    session,
                    stage=stage,
                    learner_message=learner_msg,
                )
                _append_assistant(
                    session,
                    helper,
                    meta={"kind": "engage", "checkpoint_help": True},
                )
                session["pending_widget"] = None
            else:
                raise ValueError("Send action=confirm_yes, or a message explaining what is unclear.")

        elif stage.startswith("reflect_"):
            if not (message or "").strip():
                raise ValueError("Reflection text is required for this stage.")
            step_i = _current_step_index(stage)
            if step_i is None:
                raise ValueError("Invalid stage")
            _append_user(session, (message or "").strip())
            session["cursor"] += 1

            engage = _run_engage_llm(session, step_i, (message or "").strip())
            _append_assistant(
                session,
                engage["assistant_message"],
                meta={"kind": "engage", "step_index": step_i},
            )
            itype = engage["interaction"]["type"]
            payload = engage["interaction"]["payload"]
            if itype == "none":
                session["pending_widget"] = None
                session["cursor"] = _stage_index(f"confirm_step{step_i}_user")
            else:
                session["pending_widget"] = {"type": itype, "payload": payload}
                session["cursor"] = _stage_index(f"widget_step{step_i}_user")

        elif stage.startswith("widget_"):
            if (
                session.get("pending_widget") is not None
                and widget_result is None
                and action != "confirm_yes"
            ):
                raise ValueError(
                    "Submit widget_result for this activity, or send action=confirm_yes to skip it."
                )
            summary = json.dumps(widget_result or {"skipped": action == "confirm_yes"}, ensure_ascii=False)[
                :2000
            ]
            _append_user(session, f"[Completed activity: {summary}]")
            session["pending_widget"] = None
            session["cursor"] += 1

    _auto_run_llm_stages(session)
    return _response(session)


def enqueue_widget(session_id: str, widget: dict[str, Any], *, note: str | None = None) -> dict[str, Any]:
    """
    Imperative API: attach a widget the same shape the model would return.
    Useful for tool-calling style integrations or tests. Does not advance the pipeline.
    """
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("unknown session")
    wtype = str(widget.get("type") or "").lower()
    if wtype not in ("mcq", "flashcards", "free_response", "video"):
        raise ValueError("type must be mcq, flashcards, free_response, or video")
    payload = widget.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if wtype == "video":
        lesson = session["sources"]["lesson"]
        last_ref = ""
        for e in reversed(session.get("transcript") or []):
            if e.get("role") != "user":
                continue
            c = str(e.get("content") or "")
            if c.startswith("[Learner:") or c.startswith("[Completed activity:"):
                continue
            last_ref = c[:800]
            break
        vf = _video_search_context(session, last_ref)
        payload = _resolve_video_widget_payload(payload, lesson, context_focus=vf)
    session["pending_widget"] = {"type": wtype, "payload": payload}
    if note:
        _append_assistant(session, note, meta={"kind": "widget_enqueue"})
    return _response(session)
