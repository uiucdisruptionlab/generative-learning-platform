from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3

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
- Merge repetitive or overlapping lessons when appropriate.
- Remove weak or trivial lessons if they do not add real learning value.
- Keep the lesson ordering logically teachable.
- Preserve prerequisite IDs when they still make sense after merging.
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


def _parse_llm_json(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {raw_text}")

    candidate = match.group(0)
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
    return json.loads(cleaned)


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


def refine_roadmap_with_llm(roadmap: dict[str, Any]) -> dict[str, Any]:
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[
            {
                "role": "user",
                "content": [{"text": json.dumps(roadmap, ensure_ascii=False, indent=2)}],
            }
        ],
        inferenceConfig={"maxTokens": 1600, "temperature": 0},
    )
    raw_text = _extract_text_from_converse_response(response)
    refined = _parse_llm_json(raw_text)
    return _normalize_refined_roadmap(refined, fallback=roadmap)
