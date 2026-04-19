"""
Terminal-first lesson loop: ordered concepts → personalized Bedrock blocks → knowledge checks.

Runs after the knowledge graph. No streaming, Redis, LangChain, or tool calls (v1).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
# Match backend/server.py
load_dotenv(dotenv_path=_BACKEND_DIR / ".env")
sys.path.insert(0, str(_BACKEND_DIR))

from bedrock.client import BearerTokenBedrockClient, create_bedrock_runtime_client

# Load GLP supabase_client by file path — avoids shadowing the `supabase` PyPI package.
_sc_path = _BACKEND_DIR / "supabase" / "supabase_client.py"
_spec = importlib.util.spec_from_file_location("glp_supabase_client", _sc_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load supabase client from {_sc_path}")
_glp_sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_glp_sc)
get_student_profile = _glp_sc.get_student_profile
get_supabase_client = _glp_sc.get_supabase_client

from srs import PASSING_SCORE, upsert_srs_record

# Default matches backend/server.py (Haiku). Override with BEDROCK_MODEL_ID.
DEFAULT_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

JSON_SYSTEM_RULES = """You MUST respond with exactly one JSON object and nothing else.
No markdown fences, no preamble, no trailing commentary.
Schema:
{
  "explanation": "string",
  "example": "string",
  "knowledge_check": {
    "question": "string",
    "type": "free_response"
  }
}

JSON string rules (critical): every value is a JSON string. Inside a string you may use literal newlines,
but any double-quote character inside the string MUST be written as backslash-doublequote (\\").
In Python code samples, prefer single-quoted strings (e.g. input('x')) to avoid escaping quotes.
"""


def build_prompt(
    concept: dict[str, Any],
    student_profile: dict[str, Any],
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for Bedrock."""
    system_prompt = (
        "You are an expert tutor for a generative learning platform. "
        "Personalize explanations to the learner. "
        + JSON_SYSTEM_RULES
    )

    prereq = concept.get("prerequisites") or []
    if not isinstance(prereq, list):
        prereq = [prereq]

    user_payload = {
        "learner": {
            "academic_level": student_profile.get("academic_level"),
            "preferred_formats": student_profile.get("preferred_formats"),
            "llm_profile": student_profile.get("llm_profile"),
        },
        "concept": {
            "name": concept.get("concept"),
            "difficulty": concept.get("difficulty"),
            "order": concept.get("order"),
            "prerequisite_names": prereq,
        },
        "task": (
            "Write one teaching block for this concept only. "
            "Assume the learner has seen the prerequisite concepts by name; "
            "do not re-teach them in depth, but connect briefly where helpful."
        ),
    }
    user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)
    return system_prompt, user_prompt


def _unescape_json_string_body(s: str) -> str:
    """Decode JSON escapes inside a string body (no surrounding quotes)."""
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n in '"\\':
                out.append(n)
                i += 2
                continue
            if n == "n":
                out.append("\n")
                i += 2
                continue
            if n == "r":
                out.append("\r")
                i += 2
                continue
            if n == "t":
                out.append("\t")
                i += 2
                continue
            if n == "u" and i + 5 < len(s):
                try:
                    out.append(chr(int(s[i + 2 : i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
        out.append(s[i])
        i += 1
    return "".join(out)


def _fallback_parse_teaching_json(text: str) -> dict[str, Any]:
    """
    Recover teaching block JSON when standard parse fails (e.g. unescaped " inside
    "example" from Python code like input("x")). Slices string fields using key boundaries.
    """
    exp_m = re.search(r'"explanation"\s*:\s*"', text)
    ex_m = re.search(r'"example"\s*:\s*"', text)
    kc_m = re.search(r'"knowledge_check"\s*:\s*\{', text)
    if not exp_m or not ex_m or not kc_m:
        raise ValueError("fallback: missing explanation, example, or knowledge_check")

    exp_start = exp_m.end()
    exp_end_rel = re.search(r'"\s*,\s*"example"', text[exp_start:])
    if not exp_end_rel:
        raise ValueError("fallback: could not close explanation string")
    explanation = _unescape_json_string_body(text[exp_start : exp_start + exp_end_rel.start()])

    ex_start = ex_m.end()
    ex_end_rel = re.search(r'"\s*,\s*"knowledge_check"', text[ex_start:])
    if not ex_end_rel:
        raise ValueError("fallback: could not close example string")
    example = _unescape_json_string_body(text[ex_start : ex_start + ex_end_rel.start()])

    brace_open = kc_m.end() - 1
    dec = json.JSONDecoder()
    kc_obj, _ = dec.raw_decode(text, brace_open)
    if not isinstance(kc_obj, dict):
        raise ValueError("fallback: knowledge_check must be an object")

    return {
        "explanation": explanation,
        "example": example,
        "knowledge_check": kc_obj,
    }


def _parse_model_json_object(text: str) -> dict[str, Any]:
    """
    Parse a single JSON object from model text. Tolerates literal newlines / control
    chars inside string values (same idea as server._parse_llm_json).
    """
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Model returned no JSON object: {text[:500]}...")
    raw = match.group(0)

    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    def _escape_string(m: re.Match[str]) -> str:
        inner = m.group(1)
        inner = inner.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        inner = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", inner)
        return f'"{inner}"'

    try:
        fixed = re.sub(r'"((?:[^"\\]|\\.)*)"', _escape_string, raw, flags=re.DOTALL)
        obj = json.loads(fixed)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    try:
        return _fallback_parse_teaching_json(text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not parse model JSON: {exc}") from exc


def _strip_markdown_fences(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _anthropic_response_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in payload.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts).strip()


def _invoke_model_body(body: dict[str, Any]) -> dict[str, Any]:
    client = create_bedrock_runtime_client(region=AWS_REGION)
    if isinstance(client, BearerTokenBedrockClient):
        wrapped = client.invoke_model(modelId=MODEL_ID, body=body)
        return json.loads(wrapped["body"].read())

    resp = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    raw = resp["body"].read()
    if isinstance(raw, bytes):
        return json.loads(raw.decode("utf-8"))
    return json.loads(raw)


def _call_bedrock_json(system: str, user: str, *, temperature: float = 0.3) -> dict[str, Any]:
    """Invoke Bedrock (non-streaming), return one parsed JSON object."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": temperature,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": user}],
            }
        ],
    }
    payload = _invoke_model_body(body)
    raw_text = _anthropic_response_text(payload)
    cleaned = _strip_markdown_fences(raw_text)
    try:
        parsed = _parse_model_json_object(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        print("--- Raw model output (parse failed) ---")
        print(raw_text)
        raise RuntimeError(
            "Bedrock returned JSON we could not parse (after fence strip + newline repair); "
            "see raw text above."
        ) from exc
    if not isinstance(parsed, dict):
        print("--- Raw model output (not a JSON object) ---")
        print(raw_text)
        raise RuntimeError("Bedrock JSON root must be an object.")
    return parsed


def call_bedrock(system: str, user: str) -> dict[str, Any]:
    """Invoke Bedrock (non-streaming), return normalized content block dict."""
    return _normalize_block(_call_bedrock_json(system, user))


def _normalize_block(raw: dict[str, Any]) -> dict[str, Any]:
    kc = raw.get("knowledge_check")
    if not isinstance(kc, dict):
        kc = {}
    return {
        "explanation": str(raw.get("explanation") or ""),
        "example": str(raw.get("example") or ""),
        "knowledge_check": {
            "question": str(
                kc.get("question") or "In one or two sentences, what is the main idea?"
            ),
            "type": str(kc.get("type") or "free_response"),
        },
    }


SCORING_SYSTEM_PROMPT = """You score free-response knowledge checks for a spaced repetition system.
Return exactly one JSON object and nothing else.
Schema:
{
  "score": 0,
  "explanation": "string"
}

Scoring rubric:
0 = blank, irrelevant, or no evidence of understanding.
1 = tiny fragment of relevant recall but mostly incorrect.
2 = partially relevant but misses the core idea or has major errors.
3 = basically understands the core idea with some gaps.
4 = correct and clear with minor omissions.
5 = complete, precise, and well explained.

Only score 3 or higher when the learner demonstrates the central concept."""


def score_knowledge_check(
    concept: dict[str, Any],
    block: dict[str, Any],
    learner_answer: str,
) -> dict[str, Any]:
    payload = {
        "concept": {
            "id": concept_id_for_srs(concept),
            "name": concept.get("concept"),
            "difficulty": concept.get("difficulty"),
            "prerequisites": concept.get("prerequisites") or [],
        },
        "teaching_block": {
            "explanation": block.get("explanation"),
            "example": block.get("example"),
        },
        "knowledge_check": block.get("knowledge_check") or {},
        "learner_answer": learner_answer,
    }
    parsed = _call_bedrock_json(
        SCORING_SYSTEM_PROMPT,
        json.dumps(payload, ensure_ascii=False, indent=2),
        temperature=0,
    )
    try:
        score = max(0, min(5, int(round(float(parsed.get("score", 0))))))
    except (TypeError, ValueError):
        score = 0
    return {
        "score": score,
        "explanation": str(parsed.get("explanation") or "").strip(),
    }


def concept_id_for_srs(concept: dict[str, Any]) -> str:
    raw_id = (
        concept.get("concept_id")
        or concept.get("id")
        or concept.get("node_id")
        or concept.get("concept")
    )
    if not raw_id:
        raise ValueError(f"Concept is missing an id/name for SRS: {concept}")
    return str(raw_id)


def run_lesson_loop(student_id: str, ordered_concepts: list[dict[str, Any]]) -> None:
    """
    Load profile once, then for each concept: Bedrock block → print → input() pause.
    Production roadmaps often use ~6 concepts; demos may use fewer.
    """
    profile = get_student_profile(student_id)
    if profile is None:
        raise RuntimeError(
            f"No student profile for id={student_id!r}. "
            "Seed students in Supabase (e.g. Alice) before running the lesson loop."
        )

    supabase = get_supabase_client()
    concepts = sorted(
        ordered_concepts,
        key=lambda c: (c.get("order") is None, c.get("order") or 0),
    )

    for i, concept in enumerate(concepts, start=1):
        name = concept.get("concept", "(unnamed concept)")
        print(f"\n{'=' * 60}\nConcept {i}/{len(concepts)}: {name}\n{'=' * 60}")

        system_p, user_p = build_prompt(concept, profile)
        block = call_bedrock(system_p, user_p)

        print("\n--- Explanation ---\n")
        print(block["explanation"])
        print("\n--- Example ---\n")
        print(block["example"])
        print("\n--- Knowledge check ---\n")
        print(block["knowledge_check"]["question"])
        print(f"(type: {block['knowledge_check']['type']})\n")

        learner_answer = input("Your answer: ").strip()
        if not learner_answer:
            learner_answer = "(blank)"

        scoring = score_knowledge_check(concept, block, learner_answer)
        srs_record = upsert_srs_record(
            student_id=student_id,
            concept_id=concept_id_for_srs(concept),
            course=None,
            score=scoring["score"],
            metadata={
                "knowledge_check": block.get("knowledge_check"),
                "learner_answer": learner_answer,
                "scoring_explanation": scoring["explanation"],
            },
            client=supabase,
        )

        outcome = "passed" if scoring["score"] >= PASSING_SCORE else "needs review"
        print(
            f"\nScore: {scoring['score']}/5 ({outcome})\n"
            f"Why: {scoring['explanation'] or 'No explanation returned.'}\n"
            f"Next review: {srs_record.get('next_review_at')}\n"
        )

    print(f"\nDone — completed {len(concepts)} concept(s) for student {student_id!r}.")


if __name__ == "__main__":
    # Production typically ~6 ordered concepts from Neo4j; three here for a quicker terminal test.
    alice = "a0000001-0000-4000-8000-000000000001"
    mock_concepts: list[dict[str, Any]] = [
        {
            "order": 1,
            "concept": "Variables",
            "difficulty": "beginner",
            "prerequisites": [],
        },
        {
            "order": 2,
            "concept": "Loops",
            "difficulty": "beginner",
            "prerequisites": ["Variables"],
        },
        {
            "order": 3,
            "concept": "Functions",
            "difficulty": "beginner",
            "prerequisites": ["Variables", "Loops"],
        },
    ]
    print(f"Model: {MODEL_ID} | Region: {AWS_REGION}")
    api = os.getenv("SUPABASE_URL", "").strip()
    if api:
        host = urlparse(api).netloc or "(parse error)"
        print(
            f"Supabase REST host: {host} "
            "(SRS column errors → run backend/supabase/migrations/ensure_srs_records_schema.sql.)"
        )
    run_lesson_loop(alice, mock_concepts)
