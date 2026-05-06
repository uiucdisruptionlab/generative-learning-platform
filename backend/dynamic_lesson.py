"""
Interactive lesson walkthrough: reuses Pinecone + YouTube (via lesson_generator.load_lesson_sources),
generates content step-by-step with Bedrock, and returns structured UI blocks (MCQ, flashcards, etc.).
SRS context (ease_factor, last_score) is injected into every LLM prompt so the tutor adapts difficulty
and emphasis to the student's prior performance. Progression is via conversational checkpoints.
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
_LESSON_CACHE_DIR = Path(__file__).resolve().parent / "lesson_cache"


def _merge_videos_from_lesson_cache(
    sources: dict[str, Any],
    lesson_id: str,
    persona: dict[str, Any],
    course: str | None,
) -> str | None:
    """
    If YouTube returned nothing, reuse `videos` from a previously generated lesson JSON
    (classic /lesson cache) so interactive mode still shows links when offline or unconfigured.
    """
    if sources.get("videos") or not _wants_videos(persona):
        return None
    persona_id = persona.get("student_id") or persona.get("id") or ""
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
        if not isinstance(detail, str) or not detail:
            detail = None
    return {"source": src, "detail": detail}


def _wants_videos(persona: dict[str, Any]) -> bool:
    return any(
        "video" in str(item).strip().lower()
        or "youtube" in str(item).strip().lower()
        for item in (persona.get("preferred_formats") or [])
    )


_FORMAT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "videos": ("video", "videos", "youtube", "clip", "clips", "watching"),
    "flashcards": ("flashcard", "flashcards", "flash card", "flash cards", "cards"),
    "reading": ("reading", "readings", "text", "article", "articles"),
    "MCQs": ("mcq", "mcqs", "multiple choice", "quiz question", "quiz questions"),
    "worked examples": ("worked example", "worked examples"),
    "practice questions": ("practice question", "practice questions", "practice problems", "problems"),
    "AI interaction": ("ai interaction", "chat", "conversation", "talking it through"),
}

_NEGATIVE_PREF_RE = re.compile(
    r"\b("
    r"don'?t|do not|doesn'?t|does not|not|no|never|stop|avoid|remove|disable|"
    r"hate|dislike|isn'?t|is not|aren'?t|are not|doesn'?t work|not working|isn'?t working"
    r")\b",
    re.IGNORECASE,
)
_POSITIVE_PREF_RE = re.compile(
    r"\b("
    r"like|prefer|want|use|include|add|more|love|helpful|works|working|rather|instead"
    r")\b",
    re.IGNORECASE,
)


def _format_from_text(text: str) -> set[str]:
    lowered = text.lower()
    matched: set[str] = set()
    for canonical, keywords in _FORMAT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matched.add(canonical)
    return matched


def _infer_profile_format_updates(text: str) -> dict[str, set[str]]:
    add: set[str] = set()
    remove: set[str] = set()
    rather_match = re.search(r"\brather\b(?P<before>.+?)\bthan\b(?P<after>.+)$", text, flags=re.IGNORECASE)
    if rather_match:
        add.update(_format_from_text(rather_match.group("before")))
        remove.update(_format_from_text(rather_match.group("after")))
        text = text[: rather_match.start()]

    replacement_match = re.search(r"\b(instead of|rather than)\b(.+)$", text, flags=re.IGNORECASE)
    if replacement_match:
        remove.update(_format_from_text(replacement_match.group(2)))
        text = text[: replacement_match.start()]

    clauses = re.split(r"[,.;!?]|\bbut\b|\band\b", text, flags=re.IGNORECASE)

    for clause in clauses:
        formats = _format_from_text(clause)
        if not formats:
            continue
        if re.search(r"\b(don'?t|do not)\s+understand\b", clause, flags=re.IGNORECASE):
            continue
        if _NEGATIVE_PREF_RE.search(clause):
            remove.update(formats)
        elif _POSITIVE_PREF_RE.search(clause):
            add.update(formats)

    add -= remove
    return {"add": add, "remove": remove}


def _preferred_formats_after_update(
    current_formats: list[Any],
    *,
    add: set[str],
    remove: set[str],
) -> list[str]:
    remove_keywords = tuple(
        keyword
        for canonical in remove
        for keyword in _FORMAT_KEYWORDS.get(canonical, (canonical,))
    )
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in current_formats:
        text = str(raw).strip()
        lowered = text.lower()
        if not text:
            continue
        if remove_keywords and any(keyword in lowered for keyword in remove_keywords):
            continue
        if lowered not in seen:
            cleaned.append(text)
            seen.add(lowered)

    for fmt in add:
        key = fmt.lower()
        if key not in seen:
            cleaned.append(fmt)
            seen.add(key)
    return cleaned


def _clear_lesson_cache_for_persona(student_id: str, persona: dict[str, Any]) -> None:
    if not _LESSON_CACHE_DIR.exists():
        return
    keys = {student_id.lower()}
    persona_id = str(persona.get("id") or persona.get("student_id") or "").strip().lower()
    name = str(persona.get("name") or "").strip().lower()
    if persona_id:
        keys.add(persona_id)
    if name:
        keys.add(name)
    for child in _LESSON_CACHE_DIR.iterdir():
        if not child.is_dir():
            continue
        folder = child.name.lower()
        if not any(folder == key or folder.startswith(f"{key}_") for key in keys if key):
            continue
        for cache_file in child.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError as exc:
                print(f"[dynamic_lesson] failed to remove stale lesson cache {cache_file}: {exc}")


def _learning_style_from_formats(formats: list[str], confidence: str | None) -> str:
    if not formats:
        return "Prefers guided explanations and targeted practice questions."
    if len(formats) == 1:
        format_phrase = formats[0]
    else:
        format_phrase = f"{', '.join(formats[:-1])} and {formats[-1]}"
    confidence_text = str(confidence or "").strip()
    suffix = f"; current confidence is {confidence_text}" if confidence_text else ""
    return f"Prefers learning through {format_phrase}{suffix}."


def _activity_types_for_formats(formats: set[str]) -> set[str]:
    out: set[str] = set()
    if "videos" in formats:
        out.add("video")
    if "flashcards" in formats:
        out.add("flashcards")
    if "MCQs" in formats:
        out.add("mcq")
    if "practice questions" in formats or "worked examples" in formats:
        out.add("free_response")
    return out


def _apply_profile_updates_from_message(session: dict[str, Any], text: str) -> dict[str, Any] | None:
    updates = _infer_profile_format_updates(text)
    add = updates["add"]
    remove = updates["remove"]
    if not add and not remove:
        return None

    persona = session["sources"].get("persona") or {}
    student_id = str(persona.get("student_id") or "").strip()
    current_formats = persona.get("preferred_formats") or []
    if not isinstance(current_formats, list):
        current_formats = [current_formats]

    next_formats = _preferred_formats_after_update(current_formats, add=add, remove=remove)
    if [str(x) for x in current_formats] == next_formats:
        return None

    confidence = str(persona.get("familiarity") or "").strip()
    next_style = _learning_style_from_formats(next_formats, confidence)

    if student_id:
        try:
            from supabase_local import get_student_profile, get_supabase_client

            supabase = get_supabase_client()
            current_profile = get_student_profile(student_id, client=supabase) or {}
            llm_profile = current_profile.get("llm_profile")
            if not isinstance(llm_profile, dict):
                llm_profile = {}
            llm_profile = {**llm_profile, "learning_style_summary": next_style}
            supabase.table("students").update(
                {
                    "preferred_formats": next_formats,
                    "llm_profile": llm_profile,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            ).eq("id", student_id).execute()
            _clear_lesson_cache_for_persona(student_id, {**persona, **current_profile})
        except Exception as exc:
            print(f"[dynamic_lesson] profile preference update failed: {exc}")
            return None

    persona["preferred_formats"] = next_formats
    persona["learning_style"] = next_style
    session["sources"]["persona"] = persona

    if "videos" in remove:
        session["sources"]["videos"] = []
        session["video_status"] = {
            "source": "none",
            "detail": "Videos were turned off after your learner-profile update.",
        }

    summary_bits: list[str] = []
    if remove:
        summary_bits.append("removed " + ", ".join(sorted(remove)))
    if add:
        summary_bits.append("added " + ", ".join(sorted(add)))
    return {
        "preferred_formats": next_formats,
        "added_formats": sorted(add),
        "removed_formats": sorted(remove),
        "removed_activity_types": _activity_types_for_formats(remove),
        "message": "Got it - I updated your learner profile and will keep that preference in mind for this lesson: "
        + "; ".join(summary_bits)
        + ".",
    }


def _handle_profile_update_turn(session: dict[str, Any], text: str) -> bool:
    profile_update = _apply_profile_updates_from_message(session, text)
    if not profile_update:
        return False
    _append_user(session, text)
    _append_assistant(
        session,
        str(profile_update["message"]),
        meta={
            "kind": "profile_update",
            "preferred_formats": profile_update["preferred_formats"],
            "added_formats": profile_update["added_formats"],
            "removed_formats": profile_update["removed_formats"],
        },
    )
    pending = session.get("pending_widget")
    removed_activity_types = profile_update.get("removed_activity_types") or set()
    if isinstance(pending, dict) and pending.get("type") in removed_activity_types:
        session["pending_widget"] = None
    return True

STEP_TYPES: list[tuple[str, str]] = [
    ("concept", "Introduce core definitions and intuition. Stay grounded in the source material."),
    ("example", "Work a concrete example tied to the excerpts. No invented course policies."),
    ("summary", "Recap what matters and how it connects to the lesson title."),
]

# Natural-language intent hints for checkpoint handling.
_EXIT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(i\s*(am|'?m)\s*done)\b",
        r"\b(done for now)\b",
        r"\b(let'?s stop)\b",
        r"\b(stop (the )?lesson)\b",
        r"\b(exit|quit|end)\b",
        r"\b(that'?s all)\b",
        r"\b(no more)\b",
        r"\b(i have to go)\b",
        r"\bwe('?re| are) done\b",
    ]
]

_CONTINUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(continue|go on|move on|next)\b",
        r"\b(i'?m ready)\b",
        r"\b(yes|yep|yeah)\b",
        r"\b(let'?s go)\b",
        r"\b(ok|okay|got it|makes sense)\b",
    ]
]

CheckpointIntent = Literal["continue", "need_help", "request_activity", "exit", "unknown"]


def _requested_activity_type(text: str) -> Literal["mcq", "flashcards", "free_response", "video"] | None:
    t = (text or "").lower()
    if not t.strip():
        return None
    if any(k in t for k in ("flashcard", "flash card", "cards", "card")):
        return "flashcards"
    if any(k in t for k in ("mcq", "multiple choice", "quiz question", "quiz me")):
        return "mcq"
    if any(k in t for k in ("video", "youtube", "clip", "watch")):
        return "video"
    if any(k in t for k in ("open question", "free response", "short answer")):
        return "free_response"
    return None


def _classify_checkpoint_intent_llm(
    session: dict[str, Any],
    *,
    stage: str,
    learner_message: str,
) -> tuple[CheckpointIntent, Literal["mcq", "flashcards", "free_response", "video"] | None]:
    """
    Use the model to classify natural-language checkpoint intent.
    This avoids brittle keyword-only routing (e.g. "ok" should usually mean continue).
    """
    lesson = session["sources"]["lesson"]
    last_block = session.get("last_step_block") or {}
    last_activity = session.get("last_activity")
    dialogue = _recent_transcript_for_context(session, max_chars=1600)

    system = """You classify learner intent at a lesson checkpoint.
Return JSON only.
Schema:
{
  "intent": "continue" | "need_help" | "request_activity" | "exit" | "unknown",
  "activity_type": "mcq" | "flashcards" | "free_response" | "video" | null
}

Rules:
- "continue": learner is ready to move on (examples: "ok", "okay", "got it", "next", "continue", "sounds good", "makes sense").
- "need_help": learner asks for clarification, repeat, or has a question.
- "request_activity": learner explicitly asks for another activity (mcq/flashcard/video/free response).
- "exit": learner wants to stop/end for now.
- "unknown": unclear.
- Set activity_type only when intent=request_activity."""
    user = f"""STAGE: {stage}
LESSON_TITLE: {lesson.get("title")}
LAST_SEGMENT_TITLE: {last_block.get("title")}
LAST_ACTIVITY_RESULT: {json.dumps(last_activity, ensure_ascii=False)}
RECENT_CONVERSATION: {dialogue if dialogue.strip() else "[n/a]"}
LEARNER_MESSAGE: {learner_message}
Return JSON only."""
    try:
        raw = _call_converse(system, user, temperature=0, max_tokens=220)
        parsed = _parse_json_object(raw)
        intent_raw = str(parsed.get("intent") or "unknown").lower()
        intent: CheckpointIntent
        if intent_raw in {"continue", "need_help", "request_activity", "exit", "unknown"}:
            intent = intent_raw  # type: ignore[assignment]
        else:
            intent = "unknown"

        at_raw = parsed.get("activity_type")
        activity_type: Literal["mcq", "flashcards", "free_response", "video"] | None = None
        if isinstance(at_raw, str):
            at = at_raw.lower().strip()
            if at in {"mcq", "flashcards", "free_response", "video"}:
                activity_type = at  # type: ignore[assignment]

        return intent, activity_type
    except Exception:
        return "unknown", None

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


def _stage_index(name: str, stages: list[str] | None = None) -> int:
    return (stages or STAGES).index(name)


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
    concepts = lesson.get("concepts") or []
    concept_names = " ".join(c.get("name", "") for c in concepts[:3] if isinstance(c, dict))
    block_title = str(lb.get("title") or "").strip()
    lesson_title = str(lesson.get("title") or "").strip()
    topic = block_title or lesson_title
    return f"{topic} {concept_names}".strip()


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
            "preferred_formats": persona.get("preferred_formats"),
            "interests": persona.get("interests"),
            "learning_goals": persona.get("learning_goals"),
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


def _run_prior_performance_llm(session: dict[str, Any]) -> str:
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    srs_record = session["sources"].get("srs_record") or {}
    attempts = int(srs_record.get("attempts") or 0)
    last_score = float(srs_record.get("last_score") or srs_record.get("score") or 0)
    gaps = str(srs_record.get("last_gaps") or "").strip()
    strengths = str(srs_record.get("last_strengths") or "").strip()

    # attempts = number of completed sessions so far; this session is attempts+1
    upcoming = attempts + 1
    ordinal = {2: "second", 3: "third", 4: "fourth"}.get(upcoming) or f"{upcoming}th"
    system = """You are a supportive AI tutor opening a repeat lesson session. Return JSON only: {"assistant_message": "string"}

Write a brief (3-5 sentences), warm but honest message that:
1. Acknowledges this is a repeat attempt (mention which attempt if > 1st).
2. Is direct about what was challenging last time — use GAPS if provided, otherwise reference the score honestly.
3. Briefly notes what went well (use STRENGTHS if provided).
4. Sets a focused tone: "today we'll specifically work on [weak areas]" — be concrete.
Do NOT re-teach content yet. Keep it conversational, not clinical. No bullet points."""
    user = f"""LESSON: {lesson.get("title")}
LEARNER: {_persona_block(persona)}
ATTEMPT NUMBER: {ordinal} attempt
LAST SCORE: {last_score:.0f}/5
GAPS FROM LAST ATTEMPT: {gaps or "not recorded"}
STRENGTHS FROM LAST ATTEMPT: {strengths or "not recorded"}

Return JSON only."""
    try:
        raw = _call_converse(system, user, temperature=0.4, max_tokens=400)
        data = _parse_json_object(raw)
        out = str(data.get("assistant_message") or "").strip()
        if out:
            return out
    except Exception:
        pass
    gap_note = f" Last time, we noticed some gaps around: {gaps}." if gaps else ""
    return (
        f"Welcome back — this is your {ordinal} attempt at this lesson.{gap_note} "
        "Today's session has been adapted to focus on those areas. Let's work through it together."
    )


def _allowed_activity_types(persona: dict[str, Any]) -> set[str]:
    preferred = {
        str(item).strip().lower()
        for item in (persona.get("preferred_formats") or [])
        if str(item).strip()
    }
    allowed = {"mcq", "free_response"}
    if any("flash" in item or "card" in item for item in preferred):
        allowed.add("flashcards")
    if any("video" in item or "youtube" in item for item in preferred):
        allowed.add("video")
    return allowed


def _coerce_allowed_activity_type(
    itype: str,
    persona: dict[str, Any],
    *,
    requested_by_learner: bool = False,
) -> str:
    if itype in {"none", "mcq", "free_response"}:
        return itype
    allowed = _allowed_activity_types(persona)
    if requested_by_learner and itype == "video":
        return itype
    if itype in allowed:
        return itype
    return "mcq"


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
Use ideas supported by the source excerpts when present; otherwise use the listed concepts. Do not invent policies.
Personalize examples and framing to the learner's interests/goals in LEARNER when relevant.
When PRIOR PERFORMANCE is present, follow its assessment directive exactly — adjust difficulty, emphasize weak areas, and do not re-explain strong areas at length."""
    srs_context = session["sources"].get("srs_context", "")
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}

LEARNER: {_persona_block(persona)}
{f"PRIOR PERFORMANCE: {srs_context}" if srs_context else ""}
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
Stay faithful to the excerpts when present; otherwise ground content in CONCEPTS. Do not invent facts.
Explicitly tailor examples to LEARNER interests/goals whenever possible.
When PRIOR PERFORMANCE is present, follow its assessment directive exactly — adjust difficulty, emphasize weak areas, and do not re-explain strong areas at length."""
    srs_context = session["sources"].get("srs_context", "")
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}

LEARNER: {_persona_block(persona)}
{f"PRIOR PERFORMANCE: {srs_context}" if srs_context else ""}
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
    persona: dict[str, Any],
    *,
    context_focus: str | None = None,
) -> dict[str, Any]:
    """
    Build a single video card for the UI. Prefer an explicit YouTube URL from the model; otherwise
    search YouTube Data API (same as lesson_generator).
    """
    from youtube.client import search_videos

    def _video_score(focus: str, item: dict[str, Any]) -> float:
        corpus = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("description") or ""),
                str(item.get("channel") or ""),
            ]
        )
        return _relevance_score(focus, corpus)

    url_in = str(raw.get("url") or "").strip()
    q = str(raw.get("search_query") or raw.get("query") or "").strip()
    if not q:
        # context_focus is already a tight "block title + concept names" string
        q = (context_focus or "").strip()
    if not q:
        concepts_short = " ".join(c.get("name", "") for c in (lesson.get("concepts") or [])[:3] if isinstance(c, dict))
        q = f"{lesson.get('title', '')} {concepts_short}".strip()
    # Keep the query concise — YouTube ranks best on 5-10 keyword queries
    q = " ".join(q.split()[:10])

    results: list[dict[str, Any]] = []
    if _wants_videos(persona):
        try:
            results = search_videos(q, max_results=5)
        except Exception as exc:
            print(f"[dynamic_lesson] YouTube search for video widget failed: {exc}")
    else:
        print(f"[dynamic_lesson] Skipping YouTube search: videos not in learner's preferred formats.")

    if results:
        results = sorted(results, key=lambda v: _video_score(q, v), reverse=True)
        v = results[0]
        return {
            "title": v.get("title", ""),
            "url": v.get("url", ""),
            "channel": v.get("channel", ""),
            "thumbnail": v.get("thumbnail", ""),
            "reason": str(raw.get("reason") or raw.get("caption") or f"Suggested for: {q}")[:400],
            "source": "youtube_search",
            "search_query_used": q,
        }

    # Fallback only when search returns nothing: allow direct model URL if present.
    if url_in and ("youtube.com/" in url_in or "youtu.be/" in url_in):
        return {
            "title": str(raw.get("title") or "Suggested video"),
            "url": url_in,
            "channel": str(raw.get("channel") or ""),
            "thumbnail": str(raw.get("thumbnail") or ""),
            "reason": str(raw.get("reason") or raw.get("caption") or "Video recommendation."),
            "source": "model_url_fallback",
            "search_query_attempted": q,
        }

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

    return {
        "title": "",
        "url": "",
        "channel": "",
        "thumbnail": "",
        "reason": str(raw.get("caption") or "Could not load a relevant video."),
        "source": "search_failed",
        "search_query_attempted": q,
    }


def _run_engage_llm(session: dict[str, Any], step_index: int, reflection: str) -> dict[str, Any]:
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    last_block = session.get("last_step_block") or {}
    last_activity = session.get("last_activity")
    allowed_activities = sorted(_allowed_activity_types(persona))
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
- type "free_response": payload {"question": "...", "reference_answer": "... (2-3 sentence model answer the student can compare against)"}.
- type "video": payload {"search_query": "string (optional — specific keywords; backend also uses lecture context)", "reason": "string (one line why this helps)", "url": "optional full https://www.youtube.com/watch?v=... if you know a specific video" }.

IMPORTANT: If the learner asks to watch a video, see a clip, or wants something explained on YouTube, use type "video".
Ground your search_query in what you just taught and what they asked — do not use generic course titles alone.
The backend will run a real YouTube search merged with session context (or open your url). Do not invent watch URLs unless you are certain they exist.

Grounding rule:
- Only say "correct"/"incorrect" if LAST_ACTIVITY_RESULT explicitly contains correctness evidence.
- If evidence is missing, avoid certainty and ask a clarifying question.

SOURCE EXCERPTS below are retrieved for THIS moment (last segment + their message). Use them to stay on-topic.

Activity selection — DEFAULT TO GENERATING AN ACTIVITY at every checkpoint:
- mcq: use for quick factual checks; prefer this as the default when unsure.
- flashcards: use ONLY when the learner's preferred_formats includes flashcards/cards.
- free_response: use when an open-ended explanation would deepen understanding.
- video: use only when the learner explicitly asks to watch a clip or wants audiovisual explanation.
- none: ONLY if the learner's reflection is already a detailed, multi-sentence explanation covering ALL the key points from the segment — a brief acknowledgement or single sentence is NOT enough to skip the activity. If in doubt, default to mcq.
Keep assistant wording and examples aligned with LEARNER interests/goals; avoid generic examples when profile gives specifics."""
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}
LEARNER: {_persona_block(persona)}
ALLOWED_ACTIVITY_TYPES: {json.dumps(allowed_activities, ensure_ascii=False)}

LAST TEACHING SEGMENT TITLE: {last_block.get("title")}
LAST TEACHING SEGMENT (excerpt): {(last_block.get("content") or "")[:1200]}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[No prior dialogue.]"}

SOURCE EXCERPTS (ranked for this checkpoint — tie your response to these ideas when relevant):
{_bundle_sources(engage_chunks)}

LAST_ACTIVITY_RESULT (may be null):
{json.dumps(last_activity, ensure_ascii=False)}

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
    itype = _coerce_allowed_activity_type(itype, persona)
    payload = inter.get("payload") if isinstance(inter.get("payload"), dict) else {}

    # Fallback: if the LLM chose none but the reflection is brief, force a free_response check.
    if itype == "none" and len(reflection.split()) < 40:
        last_block = session.get("last_step_block") or {}
        concepts = lesson.get("concepts") or []
        concept_names = ", ".join(c.get("name", "") for c in concepts[:3] if isinstance(c, dict))
        fallback_q = (
            f"In your own words, what is the most important idea from "
            f'"{last_block.get("title") or lesson.get("title")}"'
            + (f" as it relates to {concept_names}?" if concept_names else "?")
        )
        itype = "free_response"
        payload = {
            "question": fallback_q,
            "reference_answer": _fallback_free_response_answer(session, fallback_q),
        }

    if itype == "free_response" and not payload.get("reference_answer"):
        payload["reference_answer"] = _fallback_free_response_answer(
            session,
            str(payload.get("question") or ""),
        )

    if itype == "video":
        vctx = _video_search_context(session, reflection)
        payload = _resolve_video_widget_payload(payload, lesson, persona, context_focus=vctx)
    return {"assistant_message": msg, "interaction": {"type": itype, "payload": payload}}


def _fallback_free_response_answer(session: dict[str, Any], question: str) -> str:
    lesson = session["sources"]["lesson"]
    last_block = session.get("last_step_block") or {}
    concepts = lesson.get("concepts") or []
    concept_names = ", ".join(
        str(c.get("name") or "")
        for c in concepts[:3]
        if isinstance(c, dict) and c.get("name")
    )
    focus = str(last_block.get("title") or lesson.get("title") or "this lesson").strip()
    content = " ".join(str(last_block.get("content") or "").split())
    if len(content) > 260:
        content = content[:260].rsplit(" ", 1)[0] + "..."
    answer = f"A strong answer should explain the main idea from {focus}"
    if concept_names:
        answer += f" and connect it to {concept_names}"
    answer += "."
    if content:
        answer += f" In this checkpoint, that means using the lesson explanation: {content}"
    if question:
        answer += " Then restate it in your own words rather than copying the wording exactly."
    return answer


def _session_performance_summary(session: dict[str, Any]) -> dict[str, Any]:
    """
    Summarise all widget results into a simple performance verdict.
    Returns a dict passed verbatim into the closing LLM prompt.
    """
    history: list[dict[str, Any]] = session.get("activity_history") or []
    if not history:
        return {"verdict": "no_activities", "detail": "No interactive activities were completed."}

    total = len(history)
    correct = 0
    incorrect = 0
    skipped = 0

    for act in history:
        result = act.get("result") or {}
        atype = str(act.get("type") or "")
        if result.get("skipped"):
            skipped += 1
        elif atype == "mcq":
            if result.get("correct") is True or result.get("selected_index") == (act.get("payload") or {}).get("correct_index"):
                correct += 1
            else:
                incorrect += 1
        elif atype == "free_response":
            text = str(result.get("text") or "").strip()
            if result.get("dont_know") or len(text.split()) < 6:
                incorrect += 1
            else:
                correct += 1
        else:
            # flashcards and video count as engaged if not skipped.
            correct += 1

    engaged = total - skipped
    if engaged == 0:
        verdict = "repeat_recommended"
    elif correct / max(engaged, 1) >= 0.75:
        verdict = "strong"
    elif correct / max(engaged, 1) >= 0.4:
        verdict = "mixed"
    else:
        verdict = "repeat_recommended"

    return {
        "verdict": verdict,
        "total_activities": total,
        "correct_or_engaged": correct,
        "incorrect": incorrect,
        "skipped": skipped,
    }


def _run_closing_llm(session: dict[str, Any]) -> str:
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    summaries = session.get("step_summaries", [])
    perf = _session_performance_summary(session)
    closing_chunks = _contextual_source_chunks(session, kind="closing")
    dialogue = _recent_transcript_for_context(session, max_chars=2200)
    system = """You are an expert tutor. Return JSON only: {"assistant_message": "string"}

Structure your closing message in three parts:
1. Congratulate the learner and recap 2-3 key points from the lesson (bullets are fine).
2. A direct, warm assessment of their session performance based on SESSION_PERFORMANCE verdict. Do NOT state a numeric score, but be clear and honest:
   - "strong": tell them their understanding was solid and they're ready to move on.
   - "mixed": name the specific area(s) that still need work and tell them directly it's worth revisiting before moving forward.
   - "repeat_recommended": be explicit — tell them the session showed some gaps that need attention, and that they should repeat this lesson. Do not soften this to the point of obscuring the message. Still be warm, but be clear.
   - "no_activities": note they moved through without engaging the checks, and encourage them to try the activities on the next pass.
3. One concrete next action."""
    user = f"""LESSON: {lesson.get("title")}
LEARNER: {_persona_block(persona)}
SEGMENT SUMMARIES: {json.dumps(summaries, ensure_ascii=False)}

SESSION_PERFORMANCE:
{json.dumps(perf, ensure_ascii=False)}

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
    last_activity = session.get("last_activity")
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
- Keep tone conversational and encouraging.
- IMPORTANT: Only claim an answer is "correct" or "incorrect" if LAST_ACTIVITY_RESULT has explicit evidence.
  Otherwise, avoid certainty and ask a clarifying question.
- Use LEARNER interests/goals to anchor explanations when you re-explain."""
    user = f"""LESSON: {lesson.get("title")}
LEARNER: {_persona_block(persona)}

LAST TEACHING SEGMENT TITLE: {last_block.get("title")}
LAST TEACHING SEGMENT (excerpt): {(last_block.get("content") or "")[:1200]}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[n/a]"}

SOURCE EXCERPTS (selected for this clarification):
{_bundle_sources(chunks)}

LAST_ACTIVITY_RESULT (may be null):
{json.dumps(last_activity, ensure_ascii=False)}

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


def _is_exit_intent(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return any(p.search(t) for p in _EXIT_PATTERNS)


def _is_continue_intent(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return any(p.search(t) for p in _CONTINUE_PATTERNS)


def _run_exit_summary_llm(session: dict[str, Any], learner_message: str) -> str:
    """
    Summarize progress and end warmly when learner opts out mid-lesson.
    """
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    summaries = session.get("step_summaries", [])
    chunks = _contextual_source_chunks(session, kind="closing")
    dialogue = _recent_transcript_for_context(session, max_chars=2200)

    system = """You are a supportive AI tutor. Return valid JSON only.
Schema: {"assistant_message":"string"}

The learner explicitly wants to stop now.
- Acknowledge their message in one short sentence.
- Give a compact recap (2-4 bullets or sentences) of what was covered so far.
- End with a warm goodbye and invite them to return later.
- Do not ask them to continue right now."""
    user = f"""LESSON: {lesson.get("title")}
LEARNER: {_persona_block(persona)}
LEARNER EXIT MESSAGE: {learner_message}

COMPLETED SEGMENTS SO FAR:
{json.dumps(summaries, ensure_ascii=False)}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[n/a]"}

SOURCE EXCERPTS (for accurate recap):
{_bundle_sources(chunks)}

Return JSON only."""
    try:
        raw = _call_converse(system, user, temperature=0.3, max_tokens=700)
        data = _parse_json_object(raw)
        out = str(data.get("assistant_message") or "").strip()
        if out:
            return out
    except Exception:
        pass
    return (
        "Absolutely — we can stop here. Quick recap: we covered the core concept, "
        "walked through an example, and checked your understanding with interactive prompts. "
        "Great work today, and feel free to come back anytime to continue."
    )


def _run_forced_activity_llm(
    session: dict[str, Any],
    *,
    step_index: int,
    learner_message: str,
    activity_type: Literal["mcq", "flashcards", "free_response", "video"],
) -> tuple[str, dict[str, Any]]:
    """
    Generate a requested activity from a confirm checkpoint, e.g.:
    "give me another flashcard" right after prior activity.
    """
    lesson = session["sources"]["lesson"]
    persona = session["sources"]["persona"]
    activity_type = _coerce_allowed_activity_type(
        activity_type,
        persona,
        requested_by_learner=_requested_activity_type(learner_message) == activity_type,
    )  # type: ignore[assignment]
    last_block = session.get("last_step_block") or {}
    dialogue = _recent_transcript_for_context(session, max_chars=2200)
    chunks = _contextual_source_chunks(
        session, kind="engage", step_index=step_index, reflection=learner_message
    )

    payload_schema = {
        "mcq": '{"question":"string","options":["4 strings"],"correct_index":0,"explanation":"string"}',
        "flashcards": '{"concepts":[{"name":"string","description":"string"}],"cards":[{"front":"string","back":"string"}]}',
        "free_response": '{"question":"string","reference_answer":"string (2-3 sentence model answer)"}',
        "video": '{"search_query":"string","reason":"string (one line why this helps)","url":"optional YouTube URL"}',
    }[activity_type]

    system = f"""You are an expert tutor. Return valid JSON only.
Schema:
{{
  "assistant_message": "string (brief acknowledgment in conversational tone)",
  "payload": {payload_schema}
}}

The learner explicitly requested an additional activity of type "{activity_type}".
Generate one high-quality activity grounded in recent lesson context."""
    user = f"""LESSON: {lesson.get("title")}
CONCEPTS: {json.dumps(lesson.get("concepts", []), ensure_ascii=False)}
LEARNER: {_persona_block(persona)}

LAST TEACHING SEGMENT TITLE: {last_block.get("title")}
LAST TEACHING SEGMENT (excerpt): {(last_block.get("content") or "")[:1200]}

RECENT CONVERSATION:
{dialogue if dialogue.strip() else "[n/a]"}

SOURCE EXCERPTS (selected for this follow-up activity):
{_bundle_sources(chunks)}

LEARNER REQUEST:
{learner_message}

Return JSON only."""
    raw = _call_converse(system, user, temperature=0.35, max_tokens=1000)
    data = _parse_json_object(raw)
    msg = str(data.get("assistant_message") or "").strip() or "Sure — here is another quick check."
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}

    if activity_type == "mcq":
        options = payload.get("options")
        if not isinstance(options, list) or len(options) < 2:
            options = ["Option A", "Option B", "Option C", "Option D"]
        payload = {
            "question": str(payload.get("question") or "Quick check: which option best matches the core idea?"),
            "options": [str(o) for o in options][:4],
            "correct_index": int(payload.get("correct_index") or 0),
            "explanation": str(payload.get("explanation") or "This checks the main concept from the prior step."),
        }
    elif activity_type == "flashcards":
        payload = {
            "concepts": payload.get("concepts") if isinstance(payload.get("concepts"), list) else [],
            "cards": payload.get("cards") if isinstance(payload.get("cards"), list) else [],
        }
    elif activity_type == "free_response":
        question = str(payload.get("question") or "In your own words, what was the key idea?")
        payload = {
            "question": question,
            "reference_answer": str(
                payload.get("reference_answer")
                or _fallback_free_response_answer(session, question)
            ),
        }
    else:  # video
        vctx = _video_search_context(session, learner_message)
        payload = _resolve_video_widget_payload(payload, lesson, persona, context_focus=vctx)

    return msg, payload


def _concept_ids_for_step(concepts: list[dict[str, Any]], step_index: int) -> list[str]:
    """Return Neo4j concept IDs assigned to the given step_index (0-based)."""
    n = len(concepts)
    k = len(STEP_TYPES)
    span = max(1, (n + k - 1) // k)
    start = step_index * span
    end = (step_index + 1) * span
    bucket = [c for c in concepts[start:end] if isinstance(c, dict)] or (
        [concepts[step_index % n]] if concepts else []
    )
    return [str(c.get("id") or "") for c in bucket if c.get("id")]


def _score_free_response_llm(question: str, reference_answer: str, learner_response: str) -> int:
    """Score a free-response answer 0–5 via a compact LLM call."""
    system = (
        "You score a learner's response for spaced repetition. Return JSON only: {\"score\": 0}. "
        "0=blank/irrelevant. 1=tiny fragment. 2=partial, misses core. 3=understands core with gaps. "
        "4=correct with minor omissions. 5=complete and precise."
    )
    payload = json.dumps({
        "question": question,
        "reference_answer": reference_answer,
        "learner_response": learner_response,
    })
    try:
        raw = _call_converse(system, payload, temperature=0, max_tokens=80)
        data = _parse_json_object(raw)
        return max(0, min(5, int(round(float(data.get("score", 2))))))
    except Exception:
        return 2


def _score_widget_result(widget_type: str, payload: dict[str, Any], result: dict[str, Any]) -> int:
    """Map a widget submission to a 0–5 SRS quality score."""
    if result.get("skipped"):
        return 0
    if result.get("dont_know"):
        return 1
    if widget_type == "mcq":
        correct_index = payload.get("correct_index", 0)
        selected_index = result.get("selected_index")
        if selected_index is None:
            return 0
        return 4 if selected_index == correct_index else 2
    if widget_type == "free_response":
        text = str(result.get("text") or "").strip()
        if not text:
            return 1
        return _score_free_response_llm(
            str(payload.get("question") or ""),
            str(payload.get("reference_answer") or ""),
            text,
        )
    if widget_type in ("flashcards", "video"):
        return 3
    return 2


def _derive_srs_metadata(activity: dict[str, Any], score: int) -> dict[str, Any] | None:
    """Extract gaps/strengths from a widget result to store on the SRS record."""
    wtype = str(activity.get("type") or "")
    if wtype not in ("mcq", "free_response"):
        return None
    question = str((activity.get("payload") or {}).get("question") or "").strip()
    if not question:
        return None
    if score >= 4:
        return {"gaps": [], "strengths": [question]}
    if score <= 2:
        return {"gaps": [question], "strengths": []}
    return None


def _write_srs_for_concepts(
    session: dict[str, Any],
    concept_ids: list[str],
    score: int,
    *,
    lesson_id: str | None = None,
    activity: dict[str, Any] | None = None,
) -> None:
    """Write per-concept SRS records. Non-fatal on any error."""
    from srs import upsert_srs_record
    from supabase_local import get_supabase_client

    persona = session["sources"].get("persona") or {}
    student_id = str(persona.get("student_id") or "")
    course = str(session.get("course") or persona.get("course") or "")
    effective_lesson_id = lesson_id or str(session.get("lesson_id") or "")

    if not student_id:
        return
    # Build a quick id→name lookup from session data for logging
    _name_map: dict[str, str] = {}
    for _c in ((session.get("sources") or {}).get("lesson") or {}).get("concepts") or []:
        _name_map[str(_c.get("id") or "")] = str(_c.get("name") or "")
    for _rc in session.get("review_concepts") or []:
        _name_map[str(_rc.get("concept_id") or "")] = str(_rc.get("concept_name") or "")
    meta = _derive_srs_metadata(activity, score) if activity else None
    try:
        client = get_supabase_client()
        for cid in concept_ids:
            if not cid:
                continue
            upsert_srs_record(
                student_id=student_id,
                concept_id=cid,
                course=course,
                lesson_id=effective_lesson_id,
                score=score,
                metadata=meta,
                client=client,
            )
            session.setdefault("scored_concept_ids", set()).add(cid)
            _cname = _name_map.get(cid) or cid[:12]
            print(f"[SRS] ✓ wrote  {_cname!r}  score={score}/5  lesson={effective_lesson_id}")
    except Exception as exc:
        print(f"[dynamic_lesson] SRS write failed (non-fatal): {exc}")


def _get_lesson_avg_score(student_id: str, lesson_id: str, client: Any) -> float | None:
    """Return the average SRS score across all concepts in a lesson, or None if no records."""
    try:
        resp = (
            client.table("srs_records")
            .select("score")
            .eq("student_id", student_id)
            .eq("lesson_id", lesson_id)
            .not_.is_("score", "null")
            .execute()
        )
        scores = [r["score"] for r in (resp.data or []) if r.get("score") is not None]
        return sum(scores) / len(scores) if scores else None
    except Exception as exc:
        print(f"[dynamic_lesson] gate score query failed: {exc}")
        return None


def _check_lesson_gate(
    student_id: str,
    lesson_id: str,
    roadmap: dict[str, Any],
    client: Any,
) -> dict[str, Any] | None:
    """Return gate block info if the student hasn't cleared the previous lesson, else None."""
    GATE_THRESHOLD = 3.0
    lessons = roadmap.get("lessons") or []
    lesson_ids = [str(lsn.get("lesson_id") or "") for lsn in lessons]
    if lesson_id not in lesson_ids:
        return None
    idx = lesson_ids.index(lesson_id)
    if idx == 0:
        return None
    prev_lesson_id = lesson_ids[idx - 1]
    avg_score = _get_lesson_avg_score(student_id, prev_lesson_id, client)
    if avg_score is None:
        print(f"[SRS] gate  lesson={lesson_id}  prev={prev_lesson_id}  no records → passed")
        return None
    if avg_score >= GATE_THRESHOLD:
        print(f"[SRS] gate  lesson={lesson_id}  prev={prev_lesson_id}  avg={avg_score:.2f} ≥ {GATE_THRESHOLD} → passed")
        return None
    print(f"[SRS] gate  lesson={lesson_id}  prev={prev_lesson_id}  avg={avg_score:.2f} < {GATE_THRESHOLD} → BLOCKED")
    return {
        "blocked": True,
        "blocking_lesson_id": prev_lesson_id,
        "avg_score": round(avg_score, 2),
        "threshold": GATE_THRESHOLD,
    }


def _load_lesson_roadmap_for_student(student_id: str) -> dict[str, Any] | None:
    """Load the cached lesson roadmap for this student from Supabase roadmap_cache."""
    try:
        from supabase_local import get_supabase_client
        client = get_supabase_client()
        resp = (
            client.table("roadmap_cache")
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
            roadmap = json.loads(roadmap)
        if isinstance(roadmap, dict) and roadmap.get("lessons"):
            return roadmap
        return None
    except Exception as exc:
        print(f"[dynamic_lesson] roadmap load failed: {exc}")
        return None


def _build_concept_map(roadmap: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Build a concept_id → {name, description} lookup from all lessons in the roadmap."""
    result: dict[str, dict[str, str]] = {}
    for lsn in roadmap.get("lessons") or []:
        for c in lsn.get("concepts") or []:
            cid = str(c.get("id") or "")
            if cid:
                result[cid] = {
                    "name": str(c.get("name") or ""),
                    "description": str(c.get("description") or ""),
                }
    return result


def _run_review_recap_llm(
    session: dict[str, Any],
    concept_index: int,
) -> tuple[str, dict[str, Any]]:
    """Generate a short review recap and a widget (mcq or free_response) for one overdue concept."""
    review_concepts = session.get("review_concepts") or []
    if concept_index >= len(review_concepts):
        return (
            "Let's do a quick review.",
            {"type": "free_response", "payload": {"question": "What do you remember?"}},
        )
    concept = review_concepts[concept_index]
    concept_name = str(concept.get("concept_name") or concept.get("concept_id") or "")
    last_score = int(concept.get("score") or 0)
    description = str(concept.get("concept_description") or "")
    total = len(review_concepts)

    system = """You are a tutor running a spaced repetition review. Return JSON only.
Schema:
{
  "recap": "string (2-3 sentences: name the concept, hint at what was tricky, set up the question)",
  "widget": {
    "type": "mcq" | "free_response",
    "payload": {}
  }
}
For mcq payload: {"question":"string","options":["4 strings"],"correct_index":0-3,"explanation":"string"}
For free_response payload: {"question":"string","reference_answer":"string (2-3 sentence model answer)"}
Choose mcq when last_score <= 2, free_response when last_score >= 3."""

    user = json.dumps({
        "concept_name": concept_name,
        "concept_description": description,
        "last_score": last_score,
        "review_index": concept_index + 1,
        "review_total": total,
        "persona": _persona_block(session["sources"].get("persona") or {}),
    }, ensure_ascii=False)

    try:
        raw = _call_converse(system, user, temperature=0.3, max_tokens=600)
        data = _parse_json_object(raw)
        recap = str(data.get("recap") or "").strip() or f"Let's review: {concept_name}."
        widget_raw = data.get("widget") or {}
        wtype = str(widget_raw.get("type") or "mcq").lower()
        if wtype not in ("mcq", "free_response"):
            wtype = "mcq" if last_score <= 2 else "free_response"
        wpayload = widget_raw.get("payload") if isinstance(widget_raw.get("payload"), dict) else {}
        return recap, {"type": wtype, "payload": wpayload}
    except Exception:
        return (
            f"Let's quickly review: {concept_name}.",
            {"type": "free_response", "payload": {"question": f"In your own words, explain: {concept_name}."}},
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
    cache_note = _merge_videos_from_lesson_cache(sources, lesson_id, sources.get("persona") or {}, course)
    video_status = _video_status(sources, had_youtube_results, cache_note)
    persona = sources.get("persona") or {}
    student_id = str(persona.get("student_id") or "")
    effective_course = course or str(persona.get("course") or "")

    # --- Gate check + overdue review check (Supabase-dependent, non-fatal) ---
    if student_id:
        try:
            from srs import get_due_srs_records
            from supabase_local import get_supabase_client
            client = get_supabase_client()

            roadmap = _load_lesson_roadmap_for_student(student_id)
            concept_map = _build_concept_map(roadmap) if roadmap else {}

            # Gate: if previous lesson avg score < 3.0, block this lesson
            if roadmap:
                gate = _check_lesson_gate(student_id, lesson_id, roadmap, client)
                if gate:
                    lesson = sources.get("lesson") or {}
                    return {
                        "session_id": "",
                        "session_type": "gated",
                        "stage": "gated",
                        "lesson_title": str(lesson.get("title") or lesson_id),
                        "concepts": list(lesson.get("concepts") or []),
                        "videos": _normalize_videos(sources.get("videos") or []),
                        "video_status": video_status,
                        "chunks_status": _public_chunks_status(sources),
                        "transcript": [],
                        "pending_widget": None,
                        "awaiting": "none",
                        "model_id": MODEL_ID,
                        "gated_info": gate,
                        "review_count": None,
                    }

            # Review: if overdue concepts exist for this course, run review session first
            all_due = get_due_srs_records(student_id, client=client)
            overdue = [r for r in all_due if not effective_course or r.get("course") == effective_course]
            if overdue:
                review_concepts = [
                    {
                        **r,
                        "concept_name": concept_map.get(str(r.get("concept_id") or ""), {}).get("name")
                            or str(r.get("concept_id") or ""),
                        "concept_description": concept_map.get(str(r.get("concept_id") or ""), {}).get("description") or "",
                    }
                    for r in overdue
                ]
                _rc_names = [rc.get("concept_name") or str(rc.get("concept_id") or "")[:12] for rc in review_concepts]
                print(f"[SRS] review session  {len(review_concepts)} overdue concept(s): {_rc_names}")
                review_stages: list[str] = []
                for i in range(len(review_concepts)):
                    review_stages.append(f"review_recap_{i}_llm")
                    review_stages.append(f"review_widget_{i}_user")
                review_stages.append("complete")

                review_sources: dict[str, Any] = {
                    "lesson": {"title": "Concept Review", "concepts": []},
                    "videos": [],
                    "persona": persona,
                    "chunk_entries": [],
                    "chunks": [],
                    "chunks_meta": {"status": "review", "detail": None, "requested_ids": 0, "loaded_segments": 0},
                }
                session_id = str(uuid.uuid4())
                session: dict[str, Any] = {
                    "session_id": session_id,
                    "lesson_id": lesson_id,
                    "persona_id": persona_id,
                    "course": effective_course,
                    "sources": review_sources,
                    "video_status": {"source": "none", "detail": None},
                    "cursor": 0,
                    "transcript": [],
                    "step_summaries": [],
                    "last_step_block": None,
                    "last_activity": None,
                    "activity_history": [],
                    "pending_widget": None,
                    "created_at": time.time(),
                    "session_type": "review",
                    "stages": review_stages,
                    "review_concepts": review_concepts,
                    "scored_concept_ids": set(),
                }
                _auto_run_llm_stages(session)
                _SESSIONS[session_id] = session
                return _response(session)
        except Exception as exc:
            print(f"[start_session] gate/review check failed (non-fatal): {exc}")

    # --- Normal lesson session ---
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "lesson_id": lesson_id,
        "persona_id": persona_id,
        "course": effective_course,
        "sources": sources,
        "video_status": video_status,
        "cursor": 0,
        "transcript": [],
        "step_summaries": [],
        "last_step_block": None,
        "last_activity": None,
        "activity_history": [],
        "pending_widget": None,
        "created_at": time.time(),
        "session_type": "lesson",
        "stages": list(STAGES),
        "scored_concept_ids": set(),
    }
    srs_record = sources.get("srs_record")
    if srs_record:
        recap = _run_prior_performance_llm(session)
        _append_assistant(session, recap, meta={"kind": "prior_performance"})

    overview = _run_overview_llm(session)
    _append_assistant(session, overview, meta={"kind": "overview"})
    _SESSIONS[session_id] = session
    return _response(session)


def _awaiting_for_stage(stage: str) -> Literal["confirm", "text", "widget", "none"]:
    if stage in ("complete", "gated"):
        return "none"
    if stage == "after_overview_confirm":
        return "confirm"
    if re.match(r"review_widget_\d+_user", stage):
        return "widget"
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
    stages = session.get("stages") or STAGES
    stage = stages[session["cursor"]] if session["cursor"] < len(stages) else "complete"
    session_type = session.get("session_type", "lesson")
    return {
        "session_id": session["session_id"],
        "session_type": session_type,
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
        "gated_info": session.get("gated_info"),
        "review_count": len(session.get("review_concepts") or []) if session_type == "review" else None,
    }


def _auto_run_llm_stages(session: dict[str, Any]) -> None:
    """Run consecutive LLM stages until we need user input or complete."""
    stages = session.get("stages") or STAGES
    while session["cursor"] < len(stages):
        stage = stages[session["cursor"]]
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

        m = re.match(r"review_recap_(\d+)_llm", stage)
        if m:
            concept_i = int(m.group(1))
            recap_msg, widget = _run_review_recap_llm(session, concept_i)
            review_concepts = session.get("review_concepts") or []
            concept_name = ""
            if concept_i < len(review_concepts):
                concept_name = str(review_concepts[concept_i].get("concept_name") or "")
            _append_assistant(
                session, recap_msg,
                meta={"kind": "review_recap", "concept_index": concept_i, "concept_name": concept_name},
            )
            session["pending_widget"] = widget
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

    stages = session.get("stages") or STAGES
    if session["cursor"] >= len(stages) or stages[session["cursor"]] == "complete":
        return _response(session)

    stage = stages[session["cursor"]]
    text_msg = (message or "").strip()

    # Allow graceful early exit from any stage that accepts user text.
    if text_msg and _is_exit_intent(text_msg):
        _append_user(session, text_msg)
        bye = _run_exit_summary_llm(session, text_msg)
        _append_assistant(session, bye, meta={"kind": "closing", "early_exit": True})
        session["pending_widget"] = None
        session["cursor"] = _stage_index("complete", stages)
        _maybe_save_session(session)
        return _response(session)

    if text_msg and _handle_profile_update_turn(session, text_msg):
        return _response(session)

    # Optional widget was skipped by the model — don't block the learner on an empty slot.
    if stage.startswith("widget_") and session.get("pending_widget") is None:
        session["cursor"] += 1
        stage = stages[session["cursor"]] if session["cursor"] < len(stages) else "complete"

    if stage.endswith("_user"):
        if stage.startswith("confirm") or stage == "after_overview_confirm":
            handled_confirm = False
            llm_intent: CheckpointIntent = "unknown"
            llm_activity: Literal["mcq", "flashcards", "free_response", "video"] | None = None
            if text_msg:
                llm_intent, llm_activity = _classify_checkpoint_intent_llm(
                    session,
                    stage=stage,
                    learner_message=text_msg,
                )
            if text_msg and llm_intent == "exit":
                _append_user(session, text_msg)
                bye = _run_exit_summary_llm(session, text_msg)
                _append_assistant(session, bye, meta={"kind": "closing", "early_exit": True})
                session["pending_widget"] = None
                session["cursor"] = _stage_index("complete", stages)
                _maybe_save_session(session)
                handled_confirm = True

            requested = llm_activity or _requested_activity_type(text_msg)
            step_i = _current_step_index(stage)
            if (
                requested
                and step_i is not None
                and stage.startswith("confirm_step")
                and llm_intent in {"request_activity", "unknown"}
            ):
                _append_user(session, text_msg)
                msg, payload = _run_forced_activity_llm(
                    session,
                    step_index=step_i,
                    learner_message=text_msg,
                    activity_type=requested,
                )
                _append_assistant(
                    session,
                    msg,
                    meta={"kind": "engage", "step_index": step_i, "forced_activity": requested},
                )
                session["pending_widget"] = {"type": requested, "payload": payload}
                session["cursor"] = _stage_index(f"widget_step{step_i}_user", stages)
                handled_confirm = True

            if not handled_confirm and (
                action == "confirm_yes"
                or llm_intent == "continue"
                or (llm_intent == "unknown" and _is_continue_intent(text_msg))
            ):
                _append_user(session, "[Learner: ready to continue]")
                session["cursor"] += 1
                session["pending_widget"] = None
            elif not handled_confirm and (
                action == "confirm_not_yet"
                or llm_intent == "need_help"
                or (llm_intent == "unknown" and bool(text_msg))
            ):
                learner_msg = text_msg or "I need more help before moving on."
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
            elif not handled_confirm:
                raise ValueError(
                    "Send a checkpoint message (e.g. 'continue', a question, or 'I'm done')."
                )

        elif stage.startswith("reflect_"):
            if not text_msg:
                raise ValueError("Reflection text is required for this stage.")
            step_i = _current_step_index(stage)
            if step_i is None:
                raise ValueError("Invalid stage")
            _append_user(session, text_msg)
            session["cursor"] += 1

            engage = _run_engage_llm(session, step_i, text_msg)
            _append_assistant(
                session,
                engage["assistant_message"],
                meta={"kind": "engage", "step_index": step_i},
            )
            itype = engage["interaction"]["type"]
            payload = engage["interaction"]["payload"]
            if itype == "none":
                session["pending_widget"] = None
                session["cursor"] = _stage_index(f"confirm_step{step_i}_user", stages)
            else:
                session["pending_widget"] = {"type": itype, "payload": payload}
                session["cursor"] = _stage_index(f"widget_step{step_i}_user", stages)

        elif re.match(r"review_widget_\d+_user", stage):
            # Review session: submit a widget result for a specific overdue concept.
            m_rv = re.match(r"review_widget_(\d+)_user", stage)
            concept_i = int(m_rv.group(1)) if m_rv else 0
            pending_before = session.get("pending_widget")
            if pending_before is not None and widget_result is None and action != "confirm_yes":
                raise ValueError(
                    "Submit widget_result for this activity, or send action=confirm_yes to skip it."
                )
            result = widget_result or {"skipped": action == "confirm_yes"}
            summary = json.dumps(result, ensure_ascii=False)[:2000]
            _append_user(session, f"[Completed activity: {summary}]")
            if isinstance(pending_before, dict):
                activity_entry = {
                    "type": pending_before.get("type"),
                    "payload": pending_before.get("payload"),
                    "result": result,
                }
                session["last_activity"] = activity_entry
                session.setdefault("activity_history", []).append(activity_entry)
                # Write SRS for this overdue concept
                wtype = str(pending_before.get("type") or "")
                wpayload = pending_before.get("payload") or {}
                score = _score_widget_result(wtype, wpayload, result)
                review_concepts = session.get("review_concepts") or []
                if concept_i < len(review_concepts):
                    rc = review_concepts[concept_i]
                    rc_cid = str(rc.get("concept_id") or "")
                    rc_lid = str(rc.get("lesson_id") or "")
                    rc_name = rc.get("concept_name") or rc_cid[:12]
                    print(f"[SRS] review {concept_i + 1}/{len(review_concepts)}  {wtype}  score={score}/5  concept={rc_name!r}")
                    if rc_cid:
                        _write_srs_for_concepts(
                            session, [rc_cid], score, lesson_id=rc_lid,
                            activity={"type": wtype, "payload": wpayload, "result": result},
                        )
            session["pending_widget"] = None
            session["cursor"] += 1

        elif stage.startswith("widget_"):
            pending_before = session.get("pending_widget")
            if (
                session.get("pending_widget") is not None
                and widget_result is None
                and action != "confirm_yes"
            ):
                raise ValueError(
                    "Submit widget_result for this activity, or send action=confirm_yes to skip it."
                )
            result = widget_result or {"skipped": action == "confirm_yes"}
            summary = json.dumps(result, ensure_ascii=False)[:2000]
            _append_user(session, f"[Completed activity: {summary}]")
            if isinstance(pending_before, dict):
                activity_entry = {
                    "type": pending_before.get("type"),
                    "payload": pending_before.get("payload"),
                    "result": result,
                }
                session["last_activity"] = activity_entry
                session.setdefault("activity_history", []).append(activity_entry)
                # Write SRS for the concepts associated with this lesson step
                step_i = _current_step_index(stage)
                if step_i is not None:
                    wtype = str(pending_before.get("type") or "")
                    wpayload = pending_before.get("payload") or {}
                    score = _score_widget_result(wtype, wpayload, result)
                    concepts = session["sources"]["lesson"].get("concepts") or []
                    concept_ids = _concept_ids_for_step(concepts, step_i)
                    _cid_set = set(concept_ids)
                    _cnames = [str(c.get("name") or c.get("id") or "") for c in concepts if str(c.get("id") or "") in _cid_set]
                    print(f"[SRS] step {step_i} {wtype}  score={score}/5  concepts={_cnames}")
                    if concept_ids:
                        _write_srs_for_concepts(
                            session, concept_ids, score,
                            activity={"type": wtype, "payload": wpayload, "result": result},
                        )
            session["pending_widget"] = None
            session["cursor"] += 1

    _auto_run_llm_stages(session)
    _maybe_save_session(session)
    return _response(session)


def _maybe_save_session(session: dict[str, Any]) -> None:
    """Persist the session to `lesson_sessions` once when it reaches the complete stage."""
    if session.get("saved_to_db"):
        return
    stages = session.get("stages") or STAGES
    cursor = session.get("cursor", 0)
    if cursor < len(stages) and stages[cursor] != "complete":
        return
    session["saved_to_db"] = True
    try:
        _save_session_to_db(session)
    except Exception as exc:
        print(f"[dynamic_lesson] session persist failed (non-fatal): {exc}")


def _save_session_to_db(session: dict[str, Any]) -> None:
    from datetime import datetime, timezone
    from supabase_local import get_supabase_client

    sources = session["sources"]
    persona = sources.get("persona") or {}
    lesson = sources.get("lesson") or {}
    student_id = str(persona.get("student_id") or "")
    course_id = str(session.get("course") or persona.get("course") or "")
    lesson_id = str(session.get("lesson_id") or "")
    session_type = session.get("session_type") or "lesson"

    if not student_id or not lesson_id:
        return

    perf = _session_performance_summary(session)
    verdict = perf.get("verdict", "no_activities")
    correct = int(perf.get("correct_or_engaged") or 0)
    total = int(perf.get("total_activities") or 0)
    raw_score = round(5 * correct / total) if total > 0 else 0
    passed = verdict in ("strong", "mixed")

    started_ts = session.get("created_at")
    started_at = (
        datetime.fromtimestamp(started_ts, tz=timezone.utc).isoformat()
        if isinstance(started_ts, (int, float))
        else None
    )

    row = {
        "session_id": session["session_id"],
        "student_id": student_id,
        "course_id": course_id,
        "lesson_id": lesson_id,
        "concept_id": lesson_id,
        "concept_name": str(lesson.get("title") or ""),
        "mode": session_type,
        "score": raw_score,
        "passed": passed,
        "transcript": session.get("transcript") or [],
        "metadata": {
            "activity_summary": perf,
            "step_summaries": session.get("step_summaries") or [],
            "scored_concept_ids": list(session.get("scored_concept_ids") or []),
        },
        "started_at": started_at,
    }

    scored_ids = list(session.get("scored_concept_ids") or [])
    print(
        f"[SRS] session complete  type={session_type}  lesson={lesson_id}"
        f"  score={raw_score}/5  verdict={verdict}  activities={correct}/{total}"
        f"  concepts_scored={len(scored_ids)}"
    )

    client = get_supabase_client()
    client.table("lesson_sessions").upsert(row, on_conflict="session_id").execute()

    if session_type == "lesson" and passed:
        _advance_roadmap_past_lesson(student_id, lesson_id, course_id, client)


def _advance_roadmap_past_lesson(
    student_id: str,
    lesson_id: str,
    course_id: str,
    client: Any,
) -> None:
    """Advance roadmap_position to the first concept of the next lesson once a lesson is passed."""
    from srs import get_roadmap_position, set_roadmap_position

    try:
        roadmap = _load_lesson_roadmap_for_student(student_id)
        if not roadmap:
            print(f"[roadmap] no roadmap found for student={student_id}, skipping advance")
            return
        flat_idx = 0
        for lsn in roadmap.get("lessons") or []:
            concepts = lsn.get("concepts") or []
            count = len(concepts)
            if not count:
                continue
            if str(lsn.get("lesson_id") or "") == lesson_id:
                next_index = flat_idx + count
                position = get_roadmap_position(student_id, course_id=course_id, client=client)
                current_index = int(position.get("current_index") or 0)
                if next_index > current_index:
                    set_roadmap_position(student_id, next_index, course_id=course_id, client=client)
                    print(f"[roadmap] advanced  lesson={lesson_id}  index={current_index}→{next_index}")
                else:
                    print(f"[roadmap] position already past lesson={lesson_id} (current={current_index}, next={next_index}), skipping")
                return
            flat_idx += count
        print(f"[roadmap] lesson_id={lesson_id} not found in roadmap for student={student_id}")
    except Exception as exc:
        print(f"[roadmap] advance failed (non-fatal): {exc}")


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
        persona = session["sources"]["persona"]
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
        payload = _resolve_video_widget_payload(payload, lesson, persona, context_focus=vf)
    session["pending_widget"] = {"type": wtype, "payload": payload}
    if note:
        _append_assistant(session, note, meta={"kind": "widget_enqueue"})
    return _response(session)
