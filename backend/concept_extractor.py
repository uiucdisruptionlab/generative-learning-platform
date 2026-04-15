import json
import os
import re
from typing import Any

from bedrock.client import create_bedrock_runtime_client
from pipeline_log import plog

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-haiku-20240307-v1:0",
)

SYSTEM_PROMPT = """
You extract graph-ready concepts from a single chunk of educational content.

Return JSON only. No markdown. No prose outside JSON.

Output schema:
{
  "chunk_id": "string",
  "concepts": [
    {
      "name": "string",
      "description": "string"
    }
  ],
  "relationships": [
    {
      "from": "string",
      "to": "string",
      "type": "PART_OF | PREREQUISITE_OF | RELATED_TO"
    }
  ]
}

Rules:
- Extract only meaningful teachable concepts, topics, or subtopics.
- Prefer concise canonical concept names.
- "PART_OF" means a narrower concept belongs under a broader one.
- "PREREQUISITE_OF" means concept A should generally be learned before concept B.
- If the chunk implies "PREREQUISITE", convert it to "PREREQUISITE_OF".
- Use "RELATED_TO" only when useful and neither PART_OF nor PREREQUISITE_OF fits.
- Only include relationships between concepts that appear in the concepts list.
- Do not invent concepts not supported by the chunk.
- Keep descriptions short and clear.
- Avoid duplicates.
""".strip()

ALLOWED_RELATIONSHIP_TYPES = {"PART_OF", "PREREQUISITE_OF", "RELATED_TO", "PREREQUISITE"}


def _extract_text_from_converse_response(response: dict[str, Any]) -> str:
    content_blocks = response["output"]["message"]["content"]
    text_parts: list[str] = []

    for block in content_blocks:
        if "text" in block:
            text_parts.append(block["text"])

    return "".join(text_parts).strip()


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
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Bedrock occasionally emits unescaped quotes inside string values.
    # Fall back to extracting the fields we care about instead of failing the chunk.
    chunk_match = re.search(r'"chunk_id"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
    chunk_id = chunk_match.group(1) if chunk_match else ""

    concepts: list[dict[str, str]] = []
    for concept_match in re.finditer(
        r'\{\s*"name"\s*:\s*"(?P<name>(?:[^"\\]|\\.)*)"\s*,\s*"description"\s*:\s*"(?P<description>.*?)"\s*\}',
        cleaned,
        flags=re.DOTALL,
    ):
        concepts.append(
            {
                "name": concept_match.group("name"),
                "description": concept_match.group("description").replace('\\"', '"').strip(),
            }
        )

    relationships: list[dict[str, str]] = []
    for rel_match in re.finditer(
        r'\{\s*"from"\s*:\s*"(?P<from>(?:[^"\\]|\\.)*)"\s*,\s*"to"\s*:\s*"(?P<to>(?:[^"\\]|\\.)*)"\s*,\s*"type"\s*:\s*"(?P<type>(?:[^"\\]|\\.)*)"\s*\}',
        cleaned,
        flags=re.DOTALL,
    ):
        relationships.append(
            {
                "from": rel_match.group("from"),
                "to": rel_match.group("to"),
                "type": rel_match.group("type"),
            }
        )

    if concepts or relationships or chunk_id:
        return {
            "chunk_id": chunk_id,
            "concepts": concepts,
            "relationships": relationships,
        }

    raise ValueError(f"Unable to parse model response as graph JSON: {raw_text}")


def _coerce_chunk(chunk: Any, default_chunk_id: str | None = None) -> dict[str, Any]:
    if isinstance(chunk, str):
        return {
            "chunk_id": default_chunk_id or "chunk_001",
            "text": chunk,
            "metadata": {},
        }

    if isinstance(chunk, dict):
        chunk_id = chunk.get("chunk_id") or chunk.get("id") or default_chunk_id or "chunk_001"
        text = chunk.get("text") or chunk.get("page_content") or chunk.get("content") or ""
        metadata = chunk.get("metadata") or {}
        return {
            "chunk_id": str(chunk_id),
            "text": str(text),
            "metadata": metadata,
        }

    page_content = getattr(chunk, "page_content", None)
    metadata = getattr(chunk, "metadata", {}) or {}
    chunk_id = metadata.get("chunk_id") or metadata.get("id") or default_chunk_id or "chunk_001"

    return {
        "chunk_id": str(chunk_id),
        "text": str(page_content or ""),
        "metadata": metadata,
    }


def _normalize_result(data: dict[str, Any], fallback_chunk_id: str) -> dict[str, Any]:
    chunk_id = str(data.get("chunk_id") or fallback_chunk_id)
    concepts = data.get("concepts") or []
    relationships = data.get("relationships") or []

    seen_concepts: set[str] = set()
    normalized_concepts: list[dict[str, str]] = []

    for concept in concepts:
        name = str(concept.get("name", "")).strip()
        description = str(concept.get("description", "")).strip()

        if not name:
            continue

        key = name.lower()
        if key in seen_concepts:
            continue

        seen_concepts.add(key)
        normalized_concepts.append(
            {
                "name": name,
                "description": description or f"Concept extracted from chunk {chunk_id}",
            }
        )

    valid_names = {c["name"].lower(): c["name"] for c in normalized_concepts}
    seen_relationships: set[tuple[str, str, str]] = set()
    normalized_relationships: list[dict[str, str]] = []

    for rel in relationships:
        from_name = str(rel.get("from", "")).strip()
        to_name = str(rel.get("to", "")).strip()
        rel_type = str(rel.get("type", "")).strip().upper()

        if rel_type == "PREREQUISITE":
            rel_type = "PREREQUISITE_OF"

        if not from_name or not to_name or rel_type not in ALLOWED_RELATIONSHIP_TYPES:
            continue

        from_original = valid_names.get(from_name.lower())
        to_original = valid_names.get(to_name.lower())

        if not from_original or not to_original or from_original == to_original:
            continue

        key = (from_original.lower(), to_original.lower(), rel_type)
        if key in seen_relationships:
            continue

        seen_relationships.add(key)
        normalized_relationships.append(
            {
                "from": from_original,
                "to": to_original,
                "type": rel_type,
            }
        )

    return {
        "chunk_id": chunk_id,
        "concepts": normalized_concepts,
        "relationships": normalized_relationships,
    }


def extract_concepts_from_chunk(chunk: Any) -> dict[str, Any]:
    chunk_obj = _coerce_chunk(chunk)
    chunk_id = chunk_obj["chunk_id"]
    chunk_text = chunk_obj["text"]
    metadata = chunk_obj["metadata"]

    if not chunk_text.strip():
        raise ValueError("Chunk text is empty.")

    user_payload = {
        "chunk_id": chunk_id,
        "chunk_text": chunk_text,
        "metadata": metadata,
    }

    plog("bedrock", f"converse START chunk_id={chunk_id} model={BEDROCK_MODEL_ID} text_len={len(chunk_text)}")
    client = create_bedrock_runtime_client(region=AWS_REGION)
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": json.dumps(user_payload, ensure_ascii=False, indent=2),
                    }
                ],
            }
        ],
        inferenceConfig={
            "maxTokens": 900,
            "temperature": 0,
        },
    )

    raw_text = _extract_text_from_converse_response(response)
    plog("bedrock", f"converse response received chunk_id={chunk_id} raw_len={len(raw_text)}")
    parsed = _parse_llm_json(raw_text)
    out = _normalize_result(parsed, fallback_chunk_id=chunk_id)
    plog(
        "bedrock",
        f"converse DONE chunk_id={chunk_id} concepts={len(out.get('concepts', []))} rels={len(out.get('relationships', []))}",
    )
    return out


def extract_concepts_from_chunks(chunks: list[Any]) -> list[dict[str, Any]]:
    results = []

    for idx, chunk in enumerate(chunks, start=1):
        default_chunk_id = f"chunk_{idx:03d}"
        coerced = _coerce_chunk(chunk, default_chunk_id=default_chunk_id)
        results.append(extract_concepts_from_chunk(coerced))

    return results
