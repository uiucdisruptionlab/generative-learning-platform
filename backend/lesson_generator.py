from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

from youtube.client import search_videos

_BACKEND_DIR = Path(__file__).resolve().parent
_sc_path = _BACKEND_DIR / "supabase" / "supabase_client.py"
_spec = importlib.util.spec_from_file_location("glp_supabase_client", _sc_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load supabase client from {_sc_path}")
_glp_sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_glp_sc)
get_student_profile = _glp_sc.get_student_profile
get_supabase_client = _glp_sc.get_supabase_client

COURSE_NAMESPACES: dict[str, str] = {
    "accounting": "15.501_Transcripts",
    "python": "6.0001_Transcripts",
    "financing": "11.437_Transcripts",
    "BIS512": "BIS512",
}


def _normalize_profile_to_persona(profile: dict[str, Any], *, course_fallback: str | None) -> dict[str, Any]:
    llm_profile = profile.get("llm_profile") or {}
    if not isinstance(llm_profile, dict):
        llm_profile = {}

    preferred_formats = profile.get("preferred_formats") or []
    if not isinstance(preferred_formats, list):
        preferred_formats = [str(preferred_formats)]

    interests = profile.get("interests") or []
    if not isinstance(interests, list):
        interests = [str(interests)]

    goals = profile.get("learning_goals") or {}
    if not isinstance(goals, dict):
        goals = {"raw": str(goals)}

    # Resolve course from student_courses table; fall back to course_override if provided.
    course = course_fallback or ""
    student_id = str(profile.get("id") or "")
    if not course and student_id:
        try:
            supabase = get_supabase_client()
            sc_resp = supabase.table("student_courses").select("course_id").eq("student_id", student_id).limit(1).execute()
            sc_rows = sc_resp.data or []
            if sc_rows:
                course = str(sc_rows[0]["course_id"])
        except Exception:
            pass
    if not course:
        course = "accounting"

    learning_style = (
        str(llm_profile.get("learning_style_summary") or "").strip()
        or ", ".join(str(x) for x in preferred_formats if str(x).strip())
        or "guided explanations and practice questions"
    )

    return {
        "student_id": str(profile.get("id") or ""),
        "name": str(profile.get("name") or "Learner"),
        "major": str(profile.get("major_or_field") or "General Studies"),
        "course": course,
        "familiarity": str(llm_profile.get("subject_confidence") or "unknown"),
        "learning_style": learning_style,
        "hours_per_week": profile.get("weekly_hours"),
        "notes": str(llm_profile.get("notes") or ""),
        "interests": [str(x) for x in interests if str(x).strip()],
        "learning_goals": goals,
        "preferred_formats": [str(x) for x in preferred_formats if str(x).strip()],
    }


def _wants_videos(persona: dict[str, Any]) -> bool:
    return any(
        "video" in str(item).strip().lower()
        or "youtube" in str(item).strip().lower()
        for item in (persona.get("preferred_formats") or [])
    )


def resolve_student_id(persona_id: str) -> str:
    return _resolve_student_id(persona_id)


def _resolve_student_id(persona_id: str) -> str:
    p = (persona_id or "").strip()
    if not p:
        raise ValueError("persona is required")
    # Accept explicit UUID directly.
    if re.fullmatch(r"[0-9a-fA-F-]{36}", p):
        return p.lower()
    # Look up by name in Supabase students table.
    try:
        supabase = get_supabase_client()
        resp = supabase.table("students").select("id").ilike("name", p).limit(1).execute()
        rows = resp.data or []
        if rows:
            return str(rows[0]["id"])
    except Exception as exc:
        raise ValueError(f"Failed to resolve student '{persona_id}': {exc}") from exc
    raise ValueError(f"No student found with name '{persona_id}'. Pass a name matching the students table or a UUID directly.")


def _load_persona_from_supabase(persona_id: str, *, course_override: str | None) -> dict[str, Any]:
    student_id = _resolve_student_id(persona_id)
    supabase = get_supabase_client()
    profile = get_student_profile(student_id, client=supabase)
    if not profile:
        raise RuntimeError(
            f"No student profile found in Supabase for student_id={student_id!r}. "
            "Run backend/supabase/seed_students.sql (includes Charles) and retry."
        )
    return _normalize_profile_to_persona(profile, course_fallback=course_override)


def _vector_metadata(vector: Any) -> dict[str, Any]:
    """Handle dict-like and object-like Pinecone vector responses."""
    if isinstance(vector, dict):
        md = vector.get("metadata")
        return md if isinstance(md, dict) else {}
    md = getattr(vector, "metadata", None)
    if isinstance(md, dict):
        return md
    if md is not None and hasattr(md, "__dict__"):
        return dict(vars(md))
    return {}


def _extract_chunk_text(metadata: dict[str, Any]) -> str:
    """
    Normalize common metadata keys used for chunk body text.
    Some old ingestions used keys other than `text`.
    """
    for key in ("text", "chunk", "content", "page_content", "body"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _candidate_namespaces(
    *,
    course: str,
    lesson: dict[str, Any],
    chunk_ids: list[str],
) -> list[str]:
    """Try likely namespace values in priority order."""
    out: list[str] = []

    env_ns = (os.getenv("PINECONE_NAMESPACE") or "").strip()
    if env_ns:
        out.append(env_ns)

    mapped = COURSE_NAMESPACES.get(course, "")
    if mapped:
        out.append(mapped)

    lecture_ids = lesson.get("lecture_ids") or []
    for lec in lecture_ids:
        s = str(lec or "").strip()
        if s:
            out.append(s)

    for cid in chunk_ids:
        m = re.match(r"^(.*)_p\d+_c\d+$", str(cid))
        if m:
            pref = m.group(1).strip()
            if pref:
                out.append(pref)

    # Sometimes data lands in the default namespace.
    out.append("")

    deduped: list[str] = []
    seen: set[str] = set()
    for ns in out:
        if ns in seen:
            continue
        seen.add(ns)
        deduped.append(ns)
    return deduped


def _fetch_chunks_from_pinecone(
    chunk_ids: list[str],
    namespace: str,
) -> tuple[list[str], dict[str, Any], list[dict[str, Any]]]:
    """
    Fetch raw text from Pinecone by chunk ID.

    Returns (texts, meta) where meta explains empty results (import, env, wrong namespace, etc.).
    """
    display_ns = namespace if namespace != "" else "__default__"
    meta: dict[str, Any] = {
        "requested_ids": len(chunk_ids),
        "namespace": display_ns,
        "index": os.getenv("PINECONE_INDEX") or "",
        "loaded_segments": 0,
        "status": "ok",
        "detail": None,
    }

    if not chunk_ids:
        meta["status"] = "no_chunk_ids"
        meta["detail"] = "This lesson has no chunk_ids in the roadmap."
        return [], meta, []

    try:
        from pinecone import Pinecone
    except ImportError as exc:
        meta["status"] = "import_error"
        meta["detail"] = (
            "The `pinecone` package is not importable in the Python process running the API "
            f"({exc!r}). Install into that same environment: `pip install pinecone` and restart uvicorn."
        )
        print(f"[lesson_generator] {meta['detail']}")
        return [], meta, []

    api_key = os.getenv("PINECONE_API_KEY", "").strip()
    index_name = os.getenv("PINECONE_INDEX", "").strip()
    if not api_key or not index_name:
        meta["status"] = "env_incomplete"
        meta["detail"] = "Set PINECONE_API_KEY and PINECONE_INDEX in backend/.env (same env as uvicorn)."
        print("[lesson_generator] PINECONE_API_KEY or PINECONE_INDEX unset; skipping chunk fetch.")
        return [], meta, []

    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        response = index.fetch(ids=chunk_ids, namespace=namespace)
        vectors = response.get("vectors", {}) if isinstance(response, dict) else getattr(response, "vectors", {})
        if vectors is None:
            vectors = {}

        texts: list[str] = []
        entries: list[dict[str, Any]] = []
        missing: list[str] = []
        for chunk_id in chunk_ids:
            vector = vectors.get(chunk_id)
            if not vector:
                missing.append(chunk_id)
                continue
            metadata = _vector_metadata(vector)
            text = _extract_chunk_text(metadata)
            if text:
                texts.append(text)
                entries.append({"id": chunk_id, "text": text, "metadata": metadata})
            else:
                missing.append(chunk_id)

        meta["loaded_segments"] = len(texts)
        if not texts:
            meta["status"] = "no_vectors_or_text"
            meta["detail"] = (
                "Pinecone fetch returned no text for these chunk_ids in this namespace. "
                f"Namespace used: {display_ns!r}. "
                "Confirm vectors exist, text-bearing metadata exists, and the namespace matches your index "
                "(set PINECONE_NAMESPACE in .env to override defaults)."
            )
            if missing:
                meta["missing_or_empty_ids_sample"] = missing[:5]
        elif missing:
            meta["status"] = "partial"
            meta["detail"] = f"Some chunk_ids had no vector or empty text (e.g. {missing[:3]})."
        return texts, meta, entries
    except Exception as exc:
        meta["status"] = "fetch_error"
        meta["detail"] = str(exc)
        print(f"[lesson_generator] Pinecone fetch failed: {exc}")
        return [], meta, []



def _build_composite_srs_context(
    records: list[dict[str, Any]],
    name_map: dict[str, str],
) -> tuple[dict[str, Any], str]:
    """Build an srs_context string and a synthetic srs_record from multiple concept records.

    Returns (synthetic_record, context_string). The synthetic record keeps
    _run_prior_performance_llm working without changes.
    """
    if not records:
        return {}, ""

    avg_score = sum(float(r.get("score") or 0) for r in records) / len(records)
    min_ease = min(float(r.get("ease_factor") or 2.5) for r in records)
    max_reps = max(int(r.get("repetitions") or 0) for r in records)

    if min_ease < 1.8 or avg_score < 3:
        assessment = "struggling"
        directive = (
            "Remediate — use simpler language, more concrete examples, and rebuild from "
            "first principles. Do not assume prior understanding carries over."
        )
    elif min_ease >= 2.8 and avg_score >= 4:
        assessment = "strong"
        directive = (
            "Student has a strong grasp. Go deeper, introduce nuance, and include a more "
            "challenging question that tests edge cases."
        )
    else:
        assessment = "progressing"
        directive = (
            "Student is making steady progress. Reinforce core concepts and address any "
            "gaps with targeted examples."
        )

    lines = [
        "PRIOR PERFORMANCE ON THIS LESSON:",
        f"- Attempts: {max_reps}",
        f"- Average concept score: {avg_score:.1f}/5",
        f"- Assessment: {assessment}",
        f"→ {directive}",
    ]

    weak_lines: list[str] = []
    strong_lines: list[str] = []
    all_gaps: list[str] = []
    all_strengths: list[str] = []
    for r in sorted(records, key=lambda x: float(x.get("score") or 0)):
        cid = str(r.get("concept_id") or "")
        cname = name_map.get(cid) or cid[:16]
        score = float(r.get("score") or 0)
        gaps = str(r.get("last_gaps") or "").strip()
        strengths = str(r.get("last_strengths") or "").strip()
        if score < 3:
            weak_lines.append(f"  • {cname}" + (f": {gaps}" if gaps else ""))
            if gaps:
                all_gaps.append(f"{cname}: {gaps}")
        elif score >= 4:
            strong_lines.append(f"  • {cname}" + (f": {strengths}" if strengths else ""))
            if strengths:
                all_strengths.append(f"{cname}: {strengths}")

    if weak_lines:
        lines.append(
            "WEAK AREAS (re-explain with fresh examples; design activities that target these):\n"
            + "\n".join(weak_lines)
        )
    if strong_lines:
        lines.append(
            "STRONG AREAS (acknowledge briefly; push to deeper applications):\n"
            + "\n".join(strong_lines)
        )

    synthetic_record = {
        "score": round(avg_score, 1),
        "ease_factor": round(min_ease, 4),
        "repetitions": max_reps,
        "last_gaps": "; ".join(all_gaps),
        "last_strengths": "; ".join(all_strengths),
    }
    return synthetic_record, "\n".join(lines)


def _build_prompt(lesson: dict[str, Any], chunks: list[str], persona: dict, videos: list[dict], srs_context: str = "") -> str:
    concepts_text = "\n".join(
        f"- {c['name']}: {c.get('description', '')}" for c in lesson.get("concepts", [])
    )
    chunks_text = (
        "\n\n---\n\n".join(chunks)
        if chunks
        else "[No lecture excerpts loaded — use CONCEPTS only. Do not tell the learner to install software.]"
    )
    videos_text = json.dumps(videos, indent=2) if videos else "[]"

    srs_section = f"\n\n{srs_context}" if srs_context else ""

    return f"""
LESSON TO GENERATE:
Lesson ID: {lesson['lesson_id']}
Title: {lesson['title']}

CONCEPTS COVERED:
{concepts_text}

LEARNER PROFILE:
Name: {persona['name']}
Major: {persona['major']}
Familiarity with topic: {persona['familiarity']}
Learning style: {persona['learning_style']}
Hours available per week: {persona['hours_per_week']}
Preferred formats: {json.dumps(persona.get('preferred_formats', []), ensure_ascii=False)}
Interests: {json.dumps(persona.get('interests', []), ensure_ascii=False)}
Learning goals: {json.dumps(persona.get('learning_goals', {}), ensure_ascii=False)}
Additional notes: {persona['notes']}{srs_section}

SOURCE MATERIAL (raw lecture chunks):
{chunks_text}

AVAILABLE YOUTUBE VIDEOS:
{videos_text}

Personalization requirement:
- Keep tutor narration in the learner's language preference (if specified elsewhere), but make
  examples, scenarios, and analogies explicitly relevant to the learner's interests/goals above.
- Respect Preferred formats when choosing activities and supporting media. Avoid formats the learner
  removed from their profile unless they explicitly ask for them later.

Generate a personalized lesson following the output schema exactly.
""".strip()


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from model response: {raw[:200]}")


def load_lesson_sources(lesson_id: str, persona_id: str, course_override: str | None = None) -> dict[str, Any]:
    """
    Load all sources needed for an interactive lesson session: persona, roadmap lesson,
    Pinecone chunks, YouTube videos, and SRS context. Used by dynamic_lesson.py.
    """
    persona = _load_persona_from_supabase(persona_id, course_override=course_override)
    course = course_override or persona.get("course", "accounting")
    student_id = persona.get("student_id", "")

    # Prefer the student's Supabase roadmap (built by build_course_lesson_roadmap)
    # since that is the authoritative source the roadmap page uses.
    lesson = None
    if student_id:
        try:
            supabase = get_supabase_client()
            resp = supabase.table("roadmap_cache").select("roadmap").eq("student_id", student_id).limit(1).execute()
            rows = resp.data or []
            if rows:
                roadmap = rows[0].get("roadmap")
                if isinstance(roadmap, str):
                    roadmap = json.loads(roadmap)
                if isinstance(roadmap, dict):
                    for l in roadmap.get("lessons", []):
                        if l.get("lesson_id") == lesson_id:
                            lesson = l
                            break
        except Exception as exc:
            print(f"[lesson_generator] Supabase roadmap lookup failed: {exc}")

    if lesson is None:
        raise ValueError(
            f"Lesson '{lesson_id}' not found in roadmap for student '{student_id}'. "
            "Rebuild the roadmap first via POST /roadmap/{student_id}/rebuild."
        )

    srs_record: dict[str, Any] | None = None
    srs_context = ""
    if student_id:
        try:
            concept_ids = [str(c.get("id") or "") for c in lesson.get("concepts") or [] if c.get("id")]
            name_map = {str(c.get("id") or ""): str(c.get("name") or "") for c in lesson.get("concepts") or []}
            if concept_ids:
                supabase_srs = get_supabase_client()
                resp = (
                    supabase_srs.table("srs_records")
                    .select("*")
                    .eq("student_id", student_id)
                    .in_("concept_id", concept_ids)
                    .execute()
                )
                concept_records = [r for r in (resp.data or []) if r.get("repetitions")]
                if concept_records:
                    srs_record, srs_context = _build_composite_srs_context(concept_records, name_map)
        except Exception as exc:
            print(f"[lesson_generator] SRS lookup skipped: {exc}")

    chunk_ids = lesson.get("chunk_ids", [])
    if chunk_ids:
        namespaces = _candidate_namespaces(course=course, lesson=lesson, chunk_ids=chunk_ids)
        best_chunks: list[str] = []
        best_entries: list[dict[str, Any]] = []
        best_meta: dict[str, Any] | None = None
        tried: list[str] = []

        for ns in namespaces:
            texts, meta, entries = _fetch_chunks_from_pinecone(chunk_ids, ns)
            tried.append(meta.get("namespace") or (ns if ns else "__default__"))
            if (
                best_meta is None
                or len(texts) > len(best_chunks)
                or (
                    len(texts) == len(best_chunks)
                    and best_meta.get("status") == "no_vectors_or_text"
                    and meta.get("status") != "no_vectors_or_text"
                )
            ):
                best_chunks, best_entries, best_meta = texts, entries, meta

            if len(texts) == len(chunk_ids):
                break

            if meta.get("status") in {"import_error", "env_incomplete", "fetch_error"}:
                break

        chunks = best_chunks
        chunk_entries = best_entries
        chunks_meta = best_meta or {
            "status": "fetch_error",
            "detail": "Unknown Pinecone error.",
            "requested_ids": len(chunk_ids),
            "namespace": namespaces[0] if namespaces else "__default__",
            "index": os.getenv("PINECONE_INDEX") or "",
            "loaded_segments": 0,
        }
        chunks_meta["namespaces_tried"] = tried
        if not chunks and chunks_meta.get("status") == "no_vectors_or_text":
            chunks_meta["detail"] = (
                str(chunks_meta.get("detail") or "")
                + f" Namespaces tried: {', '.join(tried) or '(none)'}."
            )
    else:
        chunks = []
        chunk_entries = []
        chunks_meta = {
            "status": "no_chunk_ids",
            "detail": "This lesson has no chunk_ids in the roadmap (nothing to fetch from Pinecone).",
            "requested_ids": 0,
            "namespace": "__default__",
            "index": os.getenv("PINECONE_INDEX") or "",
            "loaded_segments": 0,
            "namespaces_tried": [],
        }

    _sq_parts = f"{lesson['title']} {' '.join(c['name'] for c in lesson.get('concepts', [])[:3])}"
    search_query = " ".join(_sq_parts.split()[:10])
    video_search_error: str | None = None
    videos = []
    if _wants_videos(persona):
        try:
            videos = search_videos(search_query, max_results=3)
        except Exception as e:
            print(f"[lesson_generator] YouTube search failed: {e}")
            videos = []
            video_search_error = str(e)

        if not videos and not video_search_error:
            if not os.getenv("YOUTUBE_API_KEY", "").strip():
                video_search_error = (
                    "YOUTUBE_API_KEY is not set. Add it to backend/.env and restart the API server."
                )
    else:
        # Do not treat the absence of a video preference as an error.
        video_search_error = None

    return {
        "lesson": lesson,
        "persona": persona,
        "course": course,
        "chunks": chunks,
        "chunk_entries": chunk_entries,
        "chunks_meta": chunks_meta,
        "videos": videos,
        "video_search_error": video_search_error,
        "srs_record": srs_record,
        "srs_context": srs_context,
    }


def generate_lesson(lesson_id: str, persona_id: str, course_override: str | None = None) -> dict[str, Any]:
    bundle = load_lesson_sources(lesson_id, persona_id, course_override)
    lesson = bundle["lesson"]
    chunks = bundle["chunks"]
    persona = bundle["persona"]
    videos = bundle["videos"]
    srs_context = bundle.get("srs_context", "")

    prompt = _build_prompt(lesson, chunks, persona, videos, srs_context)

    client = create_bedrock_runtime_client(region=AWS_REGION)
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.3},
    )

    raw_text = "".join(
        block["text"]
        for block in response["output"]["message"]["content"]
        if "text" in block
    ).strip()

    return _parse_json(raw_text)
