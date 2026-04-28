from __future__ import annotations

import json
import os
import re
from typing import Any

from bedrock.client import create_bedrock_runtime_client

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-haiku-20240307-v1:0",
)

SYSTEM_PROMPT = """
You refine a draft learning roadmap into a stronger lesson sequence.

Return JSON only. No markdown. No prose outside JSON.

Input:
- A draft roadmap with lessons, concepts, chunk_ids, lecture_ids, and prerequisite IDs.

Output schema:
{
  "course": "string",
  "lesson_count": 0,
  "lessons": [
    {
      "lesson_id": "string",
      "title": "string",
      "summary": "string",
      "concepts": [
        {
          "name": "string",
          "description": "string"
        }
      ],
      "chunk_ids": ["string"],
      "lecture_ids": ["string"],
      "prerequisites": ["string"]
    }
  ]
}

Rules:
- Return fewer, stronger lessons. Prefer roughly 6-12 lessons for a lecture-sized roadmap unless the draft is extremely small.
- Aggressively remove administrative, metadata, or low-value content such as slide credits, logos, professor names, page labels, agenda items, exam logistics, assignment labels, one-off jokes, image credits, or stray examples that are not core course concepts.
- Remove trivial or overly narrow lessons that are really just syntax fragments, tiny facts, or one-off examples. Merge them into broader teachable units when possible.
- Merge repetitive or overlapping lessons when appropriate.
- Rewrite vague lesson titles into concrete, human-readable teaching units. Avoid titles like abbreviations, generic words, or weak labels such as "Pitfalls", "Approach", "Agenda", or isolated acronyms unless they are truly standard and self-explanatory in the field.
- Prefer broader lesson-sized units over concept-sized units. A lesson should feel like something a student would realistically expect to study in a course roadmap.
- Keep the lesson ordering logically teachable.
- Push final review, wrap-up, exam, or summary material toward the end of the roadmap, or remove it if it is mostly administrative.
- When chunk_ids indicate one lesson comes from much later source pages than another, prefer the earlier source material first unless prerequisites strongly require otherwise.
- Preserve prerequisite IDs when they still make sense after merging, but simplify noisy prerequisite structure when needed for clarity.
- Keep each lesson focused on meaningful concepts.
- Do not invent concepts not present in the draft roadmap.
- Keep summaries short and useful.
""".strip()


def _extract_text_from_converse_response(response: dict[str, Any]) -> str:
    return "".join(
        block["text"]
        for block in response["output"]["message"]["content"]
        if "text" in block
    ).strip()


def _salvage_truncated_lessons_json(raw: str) -> dict[str, Any] | None:
    """Best-effort recovery from JSON truncated mid-lesson.

    Claude Haiku's max output is 4096 tokens. On dense roadmaps the response
    runs over and gets cut off in the middle of a lesson, breaking strict JSON
    parsing. This walks the response, finds the last balanced lesson object
    inside the `lessons` array, and reconstructs valid JSON ending there.
    Returns None if it can't find at least one complete lesson.
    """
    start = raw.find("{")
    if start < 0:
        return None
    raw = raw[start:]

    lessons_match = re.search(r'"lessons"\s*:\s*\[', raw)
    if not lessons_match:
        return None
    array_start = lessons_match.end()

    depth = 0
    in_string = False
    escape = False
    last_complete_end = -1
    for i in range(array_start, len(raw)):
        ch = raw[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete_end = i

    if last_complete_end < 0:
        return None

    salvaged = raw[: last_complete_end + 1] + "]}"
    try:
        return json.loads(salvaged)
    except json.JSONDecodeError:
        return None


def _parse_llm_json(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw_text, flags=re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    candidate = match.group(0) if match else raw_text

    if match:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    def _escape_string(m: re.Match[str]) -> str:
        inner = m.group(1)
        inner = inner.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        inner = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", inner)
        return f'"{inner}"'

    cleaned = re.sub(r'"((?:[^"\\]|\\.)*)"', _escape_string, candidate, flags=re.DOTALL)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    cleaned_no_trailing = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned_no_trailing)
    except json.JSONDecodeError:
        pass

    salvaged = _salvage_truncated_lessons_json(raw_text)
    if salvaged is not None:
        print(f"[roadmap_refiner] Salvaged truncated response with {len(salvaged.get('lessons', []))} lessons")
        return salvaged

    raise ValueError(f"Could not parse model response as JSON. First 200 chars: {raw_text[:200]!r}")


def _normalize_refined_roadmap(refined: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    lessons = refined.get("lessons") or fallback.get("lessons", [])
    valid_ids = {lesson["lesson_id"] for lesson in lessons if lesson.get("lesson_id")}
    normalized_lessons = []
    seen_titles: set[str] = set()

    for index, lesson in enumerate(lessons, start=1):
        lesson_id = str(lesson.get("lesson_id") or f"lesson_{index:03d}")
        title = str(lesson.get("title") or f"Lesson {index}").strip()
        concepts = lesson.get("concepts") or []
        chunk_ids = sorted(set(lesson.get("chunk_ids") or []))
        lecture_ids = sorted(set(lesson.get("lecture_ids") or []))
        prerequisites = [
            prereq for prereq in lesson.get("prerequisites") or []
            if prereq in valid_ids and prereq != lesson_id
        ]
        title_key = title.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        normalized_lessons.append(
            {
                "lesson_id": lesson_id,
                "title": title,
                "summary": str(lesson.get("summary") or "").strip(),
                "concepts": [
                    {
                        "name": str(concept.get("name") or "").strip(),
                        "description": str(concept.get("description") or "").strip(),
                    }
                    for concept in concepts
                    if str(concept.get("name") or "").strip()
                ],
                "chunk_ids": chunk_ids,
                "lecture_ids": lecture_ids,
                "prerequisites": sorted(set(prerequisites)),
            }
        )

    return {
        "course": str(refined.get("course") or fallback.get("course") or "generated_course"),
        "lesson_count": len(normalized_lessons),
        "lessons": normalized_lessons,
    }


# Claude 3 Haiku's max output is 4096 tokens. Dense roadmaps with concept-rich
# lessons easily blow past that and the response gets truncated mid-lesson.
# Cap input lessons to a count Haiku can reliably finish JSON for.
MAX_LESSONS_FOR_REFINEMENT = 12


def _truncate_roadmap(roadmap: dict[str, Any]) -> dict[str, Any]:
    """Cap the number of lessons sent to the LLM to avoid token limit truncation."""
    lessons = roadmap.get("lessons", [])
    if len(lessons) <= MAX_LESSONS_FOR_REFINEMENT:
        return roadmap
    print(f"[roadmap_refiner] Truncating {len(lessons)} lessons to {MAX_LESSONS_FOR_REFINEMENT} for refinement")
    truncated_lessons = lessons[:MAX_LESSONS_FOR_REFINEMENT]
    return {**roadmap, "lessons": truncated_lessons, "lesson_count": len(truncated_lessons)}


def refine_roadmap_with_llm(roadmap: dict[str, Any]) -> dict[str, Any]:
    client = create_bedrock_runtime_client(region=AWS_REGION)
    last_error: Exception | None = None
    roadmap = _truncate_roadmap(roadmap)

    for attempt in range(2):
        try:
            response = client.converse(
                modelId=BEDROCK_MODEL_ID,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": json.dumps(roadmap, ensure_ascii=False, indent=2)}],
                    }
                ],
                inferenceConfig={"maxTokens": 4096, "temperature": 0},
            )
            raw_text = _extract_text_from_converse_response(response)
            refined = _parse_llm_json(raw_text)
            return _normalize_refined_roadmap(refined, fallback=roadmap)
        except Exception as exc:
            last_error = exc
            print(f"[roadmap_refiner] Attempt {attempt + 1} failed: {exc}")

    assert last_error is not None
    raise last_error
