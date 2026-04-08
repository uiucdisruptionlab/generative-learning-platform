from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from bedrock.client import create_bedrock_runtime_client
from personas import get_persona
from youtube.client import search_videos

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

COURSE_NAMESPACES: dict[str, str] = {
    "accounting": "15.501_Transcripts",
    "python": "6.0001_Transcripts",
    "financing": "11.437_Transcripts",
}

SYSTEM_PROMPT = """
You are an expert educational content creator. Your job is to generate a personalized lesson for a student based on:
- The lesson topic and concepts
- Raw source material (lecture chunks)
- The student's learner profile
- Relevant YouTube videos

Return JSON only. No markdown. No prose outside JSON.

Output schema:
{
  "lesson_id": "string",
  "title": "string",
  "overview": "string (2-3 sentences introducing the lesson and why it matters)",
  "steps": [
    {
      "step_number": 1,
      "title": "string",
      "type": "concept" | "example" | "summary",
      "content": "string (rich explanation, tailored to the learner profile)"
    }
  ],
  "videos": [
    {
      "title": "string",
      "url": "string",
      "channel": "string",
      "thumbnail": "string",
      "reason": "string (one sentence on why this video is relevant)"
    }
  ],
  "questions": [
    {
      "type": "multiple_choice" | "fill_in_the_blank",
      "question": "string",
      "options": ["string"] (only for multiple_choice, 4 options),
      "answer": "string",
      "explanation": "string (brief explanation of why this is the correct answer)"
    }
  ]
}

Rules:
- Tailor the depth, tone, and structure of every step to the learner profile provided.
- Steps should flow logically: start with core concepts, then move to examples, then a summary.
- Aim for exactly 3 steps.
- Generate exactly 3 questions. Mix multiple choice and fill in the blank.
- Questions should test genuine understanding, not just recall.
- Use only concepts and facts present in the source material. Do not invent information.
- Keep the overview to 2 sentences max.
- Keep each step's content under 100 words.
- For fill_in_the_blank questions, use ___ to mark the blank in the question string.
- The "options" field should only appear for multiple_choice questions.
- Be concise throughout — this is a summary lesson, not a textbook.
""".strip()


def _fetch_chunks_from_pinecone(chunk_ids: list[str], namespace: str) -> list[str]:
    """Fetch raw text from Pinecone by chunk ID."""
    from pinecone import Pinecone

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX"))

    response = index.fetch(ids=chunk_ids, namespace=namespace)
    vectors = response.get("vectors", {})

    texts = []
    for chunk_id in chunk_ids:
        vector = vectors.get(chunk_id)
        if vector:
            text = vector.get("metadata", {}).get("text", "")
            if text:
                texts.append(text)

    return texts


COURSE_KEY_MAP: dict[str, str] = {
    "ALecFinal": "accounting",
    "accounting": "accounting",
    "python": "python",
    "financing": "financing",
}


def _load_roadmap_cache(course: str) -> dict[str, Any]:
    key = COURSE_KEY_MAP.get(course, course)
    cache_path = Path(__file__).parent / f"roadmap_cache_{key}.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"roadmap_cache_{key}.json not found. Hit GET /roadmap?course={course} first.")
    return json.loads(cache_path.read_text(encoding="utf-8"))


def _get_lesson_from_cache(lesson_id: str, course: str) -> dict[str, Any]:
    roadmap = _load_roadmap_cache(course)
    for lesson in roadmap.get("lessons", []):
        if lesson["lesson_id"] == lesson_id:
            return lesson
    raise ValueError(f"Lesson '{lesson_id}' not found in roadmap cache for course '{course}'.")


def _build_prompt(lesson: dict[str, Any], chunks: list[str], persona: dict, videos: list[dict]) -> str:
    concepts_text = "\n".join(
        f"- {c['name']}: {c.get('description', '')}" for c in lesson.get("concepts", [])
    )
    chunks_text = "\n\n---\n\n".join(chunks) if chunks else "No source material available."
    videos_text = json.dumps(videos, indent=2) if videos else "[]"

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
Additional notes: {persona['notes']}

SOURCE MATERIAL (raw lecture chunks):
{chunks_text}

AVAILABLE YOUTUBE VIDEOS:
{videos_text}

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


def generate_lesson(lesson_id: str, persona_id: str, course_override: str | None = None) -> dict[str, Any]:
    persona = get_persona(persona_id)
    course = course_override or persona.get("course", "accounting")
    lesson = _get_lesson_from_cache(lesson_id, course)

    chunk_ids = lesson.get("chunk_ids", [])
    namespace = COURSE_NAMESPACES.get(course, "")
    chunks = _fetch_chunks_from_pinecone(chunk_ids, namespace) if chunk_ids else []

    search_query = f"{lesson['title']} {' '.join(c['name'] for c in lesson.get('concepts', [])[:3])}"
    try:
        videos = search_videos(search_query, max_results=3)
    except Exception as e:
        print(f"[lesson_generator] YouTube search failed: {e}")
        videos = []

    prompt = _build_prompt(lesson, chunks, persona, videos)

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
