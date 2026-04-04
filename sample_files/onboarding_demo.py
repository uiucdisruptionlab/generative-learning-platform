from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    import boto3
except ImportError:
    boto3 = None

MODEL_ID = os.getenv("BEDROCK_MODEL_ID",
                     "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_REGION", os.getenv(
    "AWS_DEFAULT_REGION", "us-east-1"))

TERMINATION_PATTERNS = [
    r"\bno\b.*\b(that'?s|thats|it|all|enough|good)\b",
    r"\bthat'?s all\b",
    r"\bthat'?s it\b",
    r"\bnothing else\b",
    r"\bnope\b",
    r"\ball good\b",
    r"\bwe'?re good\b",
    r"\bfor now\b",
    r"\bdone\b",
]

REQUIRED_FIELDS = [
    "name",
    "major",
    "career_goals",
    "career_clarity",
    "subject_confidence",
    "learning_style_summary",
]

JSON_ONLY_SYSTEM_PROMPT = """You are an onboarding assistant for a Generative Learning Platform.
Your job is to learn about a student through a short, natural open-ended conversation — both
their background and how they learn — then reflect that back in a clear summary.

You will be given:
1. The user's current structured profile.
2. The conversation history.
3. The user's latest message.

You MUST return valid JSON only. No markdown. No prose outside JSON.

Your goals:
- Ask exactly one natural, concise follow-up question at a time.
- Do not ask for information already known.
- Personalize lightly based on what the user already said.
- Extract structured updates from the latest user message.
- Decide whether the user seems finished, especially if they say things like
  'no, that's all', 'that's it for now', 'nothing else', 'we are good', etc.
- If the user seems finished AND the required fields are already collected, then your assistant_reply
  should be a brief closing message rather than another question.
- if the user seems finished but the required fields are not collected, keep prompting for the answers until 
actually finished.

The JSON schema you must return is:
{
  "assistant_reply": "string",
  "extracted_updates": {
    "name": "string or null",
    "major": "string or null",
    "minor": "string or null",
    "career_goals": "string or null",
    "career_clarity": "very_clear | somewhat_clear | exploring | unsure | null",
    "subject_confidence": "totally_new | beginner | somewhat_familiar | comfortable | advanced | null",
    "learning_style_summary": "string or null",
    "interests": ["string", "..."] or null,
    "notes": "string or null"
  },
  "user_seems_finished": true,
  "missing_fields": ["field_name", "..."]
}

"""


@dataclass
class LLMResult:
    assistant_reply: str
    extracted_updates: Dict[str, Any]
    user_seems_finished: bool
    missing_fields: List[str]


class BedrockChatClient:
    def __init__(self, model_id: str = MODEL_ID, region_name: str = AWS_REGION):
        if boto3 is None:
            raise RuntimeError(
                "boto3 is not installed. Run: pip install boto3")
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region_name)

    def send(
        self,
        profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        user_message: str,
    ) -> LLMResult:
        prompt_payload = {
            "profile": profile,
            "conversation_history": conversation_history,
            "latest_user_message": user_message,
            "required_fields": REQUIRED_FIELDS,
        }

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 700,
            "temperature": 0,
            "system": JSON_ONLY_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(prompt_payload, ensure_ascii=False, indent=2),
                        }
                    ],
                }
            ],
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        raw = response["body"].read().decode("utf-8")
        parsed = json.loads(raw)
        text = "".join(
            block.get("text", "")
            for block in parsed.get("content", [])
            if block.get("type") == "text"
        ).strip()

        llm_json = self._parse_json(text)
        return self._normalize(llm_json, profile, user_message)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise ValueError(f"Model did not return valid JSON: {text}")
            return json.loads(match.group(0))

    def _normalize(
        self,
        llm_json: Dict[str, Any],
        profile: Dict[str, Any],
        user_message: str,
    ) -> LLMResult:
        extracted_updates = llm_json.get("extracted_updates") or {}
        missing_fields = llm_json.get("missing_fields") or compute_missing_fields(
            profile, extracted_updates
        )
        user_seems_finished = bool(llm_json.get("user_seems_finished")) or looks_like_done(
            user_message
        )
        assistant_reply = str(
            llm_json.get("assistant_reply") or "Could you tell me a bit more?"
        ).strip()

        return LLMResult(
            assistant_reply=assistant_reply,
            extracted_updates=normalized_updates(extracted_updates),
            user_seems_finished=user_seems_finished,
            missing_fields=missing_fields,
        )


def normalized_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "name": None,
        "major": None,
        "minor": None,
        "career_goals": None,
        "career_clarity": None,
        "subject_confidence": None,
        "learning_style_summary": None,
        "interests": None,
        "notes": None,
    }
    for key, value in updates.items():
        if key in base:
            base[key] = value
    return base


def looks_like_done(text: str) -> bool:
    lower = text.lower().strip()
    return any(re.search(pattern, lower) for pattern in TERMINATION_PATTERNS)


def merge_profile(profile: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(profile))
    for key, value in normalized_updates(updates).items():
        if value in (None, "", []):
            continue
        if key == "interests":
            current = merged.get("interests") or []
            merged["interests"] = list(dict.fromkeys(current + value))
        elif key == "notes":
            if merged.get("notes"):
                merged["notes"] = f"{merged['notes']} | {value}"
            else:
                merged["notes"] = value
        else:
            merged[key] = value
    return merged


def compute_missing_fields(
    profile: Dict[str, Any],
    pending_updates: Optional[Dict[str, Any]] = None,
) -> List[str]:
    merged = merge_profile(profile, pending_updates or {})
    return [field for field in REQUIRED_FIELDS if not merged.get(field)]


def initial_profile() -> Dict[str, Any]:
    return {
        "name": None,
        "major": None,
        "minor": None,
        "career_goals": None,
        "career_clarity": None,
        "subject_confidence": None,
        "learning_style_summary": None,
        "interests": [],
        "notes": None,
    }


def print_profile(profile: Dict[str, Any]) -> None:
    print("\n=== FINAL ONBOARDING PROFILE ===")
    print(json.dumps(profile, indent=2, ensure_ascii=False))


def run_chat() -> None:
    print("\n=== Generative Learning Platform Onboarding ===\n")

    profile = initial_profile()
    history: List[Dict[str, str]] = []
    llm = BedrockChatClient()

    opening = "Hi! Before we get started, what name would you like me to use?"
    print(f"Assistant: {opening}")
    history.append({"role": "assistant", "content": opening})

    while True:
        user_message = input("You: ").strip()
        if not user_message:
            print("Assistant: Go ahead, I'm listening.")
            continue

        history.append({"role": "user", "content": user_message})

        result = llm.send(
            profile=profile,
            conversation_history=history,
            user_message=user_message,
        )

        profile = merge_profile(profile, result.extracted_updates)
        missing = compute_missing_fields(profile)

        if result.user_seems_finished and not missing:
            closing = result.assistant_reply.strip() or "Perfect — I have everything I need."
            print(f"Assistant: {closing}")
            history.append({"role": "assistant", "content": closing})
            break

        print(f"Assistant: {result.assistant_reply}")
        history.append(
            {"role": "assistant", "content": result.assistant_reply})

    print_profile(profile)


if __name__ == "__main__":
    try:
        run_chat()
    except Exception as exc:
        print(f"\n[Fatal error: {exc}]", file=sys.stderr)
        sys.exit(1)
