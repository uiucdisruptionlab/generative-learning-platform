from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import boto3
except ImportError:
    boto3 = None

MODEL_ID = os.getenv("BEDROCK_MODEL_ID",
                     "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_REGION", os.getenv(
    "AWS_DEFAULT_REGION", "us-east-1"))
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

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

QUIZ_QUESTIONS = [
    {
        "id": "understanding_preference",
        "question": "When you're trying to understand something new, what helps most?",
        "options": [
            ("example_first", "Seeing a real example first"),
            ("theory_then_apply", "Understanding the theory, then applying it"),
            ("talk_it_through", "Talking it through with someone"),
            ("dive_in", "Just diving in and figuring it out"),
        ],
    },
    {
        "id": "information_preference",
        "question": "How do you prefer to take in new information?",
        "options": [
            ("visual_diagrams", "Visual diagrams and charts"),
            ("written_explanations", "Written explanations"),
            ("hands_on_practice", "Hands-on practice"),
            ("discussion_conversation", "Discussion and conversation"),
        ],
    },
    {
        "id": "problem_solving_style",
        "question": "When solving a problem, you usually:",
        "options": [
            ("break_into_steps", "Break it into smaller steps"),
            ("look_for_examples", "Look for similar examples"),
            ("try_different_approaches",
             "Try different approaches until something works"),
            ("ask_for_guidance", "Ask for guidance first"),
        ],
    },
    {
        "id": "best_learning_condition",
        "question": "You learn best when:",
        "options": [
            ("relevant_to_goals", "Content is directly relevant to your goals"),
            ("builds_from_basics", "Material builds logically from basics"),
            ("immediate_application", "You can see immediate applications"),
            ("room_to_explore", "There's room to explore and experiment"),
        ],
    },
]

REQUIRED_FIELDS = [
    "name",
    "major",
    "career_goals",
    "career_clarity",
    "subject_confidence",
]

JSON_ONLY_SYSTEM_PROMPT = """You are an onboarding assistant for a Generative Learning Platform.
Your job is to help collect student onboarding information through a short, natural conversation.

You will be given:
1. The user's current structured profile.
2. The conversation history.
3. The user's latest message.

You MUST return valid JSON only. No markdown.

Your goals:
- Ask exactly one natural, concise follow-up question at a time.
- Do not ask for information already known.
- Personalize lightly based on what the user already said.
- Extract structured updates from the latest user message.
- Decide whether the user seems finished, especially if they say things like
  'no, that's all', 'that's it for now', 'nothing else', 'we are good', etc.
- If the user seems finished AND the required fields are already collected, then your assistant_reply
  should be a brief closing message rather than another question.
- If the user seems finished but required fields are missing, politely ask for the single most important missing field.
- Prefer these fields when missing: name, major, career_goals, career_clarity, subject_confidence.

Valid career_clarity enum values:
- very_clear
- somewhat_clear
- exploring
- unsure

Valid subject_confidence enum values:
- totally_new
- beginner
- somewhat_familiar
- comfortable
- advanced

Use null for any unknown extracted field.

The JSON schema you must return is:
{
  "assistant_reply": "string",
  "extracted_updates": {
    "id": "uuid or null",
    "name": "string or null",
    "major_or_field": "string or null",
    "learning_goals": "json or null",
    "interests": jsonb or null,
    "academic_level": "string or integer or null",
    "weekly_hours": "integer or null",
    "preferred_formats": "jsonb or null",
    "llm_profile": "jsonb or null",
    "created_at": "timestamp or null",
    "updated_at": "timestamp or null"
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


class BedrockJSONChatClient:
    def __init__(self, model_id: str = MODEL_ID, region_name: str = AWS_REGION):
        self.model_id = model_id
        self.region_name = region_name
        self.client = None
        if not USE_MOCK_LLM:
            if boto3 is None:
                raise RuntimeError(
                    "boto3 is not installed. Install it or run with USE_MOCK_LLM=true."
                )
            self.client = boto3.client(
                "bedrock-runtime", region_name=region_name)

    def send(
        self,
        profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        user_message: str,
    ) -> LLMResult:
        if USE_MOCK_LLM:
            return self._mock_send(profile, conversation_history, user_message)

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

        llm_json = self._parse_json_from_text(text)
        return self._normalize_result(llm_json, profile, user_message)

    def _parse_json_from_text(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise ValueError(f"Model did not return valid JSON: {text}")
            return json.loads(match.group(0))

    def _normalize_result(
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

    def _mock_send(
        self,
        profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        user_message: str,
    ) -> LLMResult:
        del conversation_history

        updates: Dict[str, Any] = {
            "name": None,
            "major": None,
            "minor": None,
            "career_goals": None,
            "career_clarity": None,
            "subject_confidence": None,
            "interests": None,
            "notes": None,
        }

        msg = user_message.strip()
        lower = msg.lower()

        if not profile.get("name"):
            maybe_name = extract_name(msg)
            if maybe_name:
                updates["name"] = maybe_name

        if not profile.get("major"):
            maybe_major = extract_major(msg)
            if maybe_major:
                updates["major"] = maybe_major

        if not profile.get("minor"):
            minor_match = re.search(
                r"minor(?:ing)? in\s+([A-Za-z&/ ,\\-]+)", msg, flags=re.I)
            if minor_match:
                updates["minor"] = clean_fragment(minor_match.group(1))

        if not profile.get("career_goals") and any(
            phrase in lower
            for phrase in [
                "want to",
                "interested in",
                "maybe something in",
                "eventually",
                "my goal is",
                "i'd like to",
                "i want",
            ]
        ):
            updates["career_goals"] = msg

        if not profile.get("career_clarity"):
            if any(
                phrase in lower
                for phrase in ["not sure", "unsure", "figuring it out", "don't know", "dont know"]
            ):
                updates["career_clarity"] = "unsure"
            elif any(phrase in lower for phrase in ["exploring", "maybe", "considering"]):
                updates["career_clarity"] = "exploring"
            elif any(phrase in lower for phrase in ["pretty clear", "somewhat sure"]):
                updates["career_clarity"] = "somewhat_clear"
            elif any(phrase in lower for phrase in ["definitely", "very sure", "exactly"]):
                updates["career_clarity"] = "very_clear"

        if not profile.get("subject_confidence"):
            if any(phrase in lower for phrase in ["totally new", "brand new", "know nothing"]):
                updates["subject_confidence"] = "totally_new"
            elif any(phrase in lower for phrase in ["beginner", "just starting", "a little"]):
                updates["subject_confidence"] = "beginner"
            elif any(phrase in lower for phrase in ["somewhat familiar", "kind of familiar"]):
                updates["subject_confidence"] = "somewhat_familiar"
            elif any(phrase in lower for phrase in ["comfortable", "pretty comfortable"]):
                updates["subject_confidence"] = "comfortable"
            elif any(phrase in lower for phrase in ["advanced", "very experienced"]):
                updates["subject_confidence"] = "advanced"

        interests = extract_interests(msg)
        if interests:
            updates["interests"] = interests

        if not any(updates.values()) and not looks_like_done(user_message):
            updates["notes"] = msg

        merged_preview = merge_profile(profile, updates)
        missing = compute_missing_fields(merged_preview)
        finished = looks_like_done(user_message)

        if finished and not missing:
            reply = "Perfect. I have everything I need and can store your onboarding profile."
        else:
            next_field = missing[0] if missing else None
            reply = question_for_field(next_field, merged_preview)

        return LLMResult(
            assistant_reply=reply,
            extracted_updates=updates,
            user_seems_finished=finished,
            missing_fields=missing,
        )


def clean_fragment(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .,!?:;-")


def extract_name(text: str) -> Optional[str]:
    patterns = [
        r"\bmy name is\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"\bi(?:'m| am)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"\bcall me\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean_fragment(match.group(1))
    return None


def extract_interests(text: str) -> List[str]:
    matches = re.findall(
        r"(?:interested in|into|love|enjoy)\s+([A-Za-z0-9&/ ,\\-]+?)(?:[.!?]|$)",
        text,
        flags=re.I,
    )
    interests: List[str] = []
    for match in matches:
        for item in re.split(r",| and ", match):
            cleaned = clean_fragment(item)
            if cleaned:
                interests.append(cleaned)
    return list(dict.fromkeys(interests))


def extract_major(text: str) -> Optional[str]:
    patterns = [
        r"\bmajor(?:ing)? in\s+([A-Za-z&/ ,\\-]+?)(?:\s+and\s+minor(?:ing)? in\b|[.!?]|$)",
        r"\bi study\s+([A-Za-z&/ ,\\-]+?)(?:[.!?]|$)",
        r"\bstudying\s+([A-Za-z&/ ,\\-]+?)(?:[.!?]|$)",
        r"\bi(?:'m| am)\s+an?\s+([A-Za-z&/ ,\\-]+?)\s+(?:major|student)(?:[.!?]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean_fragment(match.group(1))
    return None


def normalized_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "name": None,
        "major": None,
        "minor": None,
        "career_goals": None,
        "career_clarity": None,
        "subject_confidence": None,
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


def question_for_field(field: Optional[str], profile: Dict[str, Any]) -> str:
    name = profile.get("name")
    prefix = f"{name}, " if name else ""

    if field == "name":
        return "Thanks. Before we begin, what name would you like me to use?"
    if field == "major":
        return f"{prefix}What are you majoring in right now?"
    if field == "career_goals":
        return (
            f"{prefix}What do you think you might want to do eventually, even if you're still exploring?"
        )
    if field == "career_clarity":
        return (
            f"{prefix}How clear do you feel about that path right now: very clear, somewhat clear, "
            "still exploring, or not really sure yet?"
        )
    if field == "subject_confidence":
        return (
            f"{prefix}How would you describe your current familiarity with this subject: "
            "totally new, beginner, somewhat familiar, comfortable, or advanced?"
        )
    return f"{prefix}Anything else I should know before we start?"


def render_quiz_question(question_num: int, total: int, question: Dict[str, Any]) -> str:
    lines = [f"\n{question_num} of {total}", question["question"]]
    for idx, (_, label) in enumerate(question["options"], start=1):
        lines.append(f"  {idx}. {label}")
    lines.append("> ")
    return "\n".join(lines)


def collect_learning_profile() -> Dict[str, str]:
    print("\n=== Generative Learning Platform Onboarding ===")
    print("We'll start with 4 quick preference questions.\n")

    learning_profile: Dict[str, str] = {}
    total = len(QUIZ_QUESTIONS)

    for index, question in enumerate(QUIZ_QUESTIONS, start=1):
        while True:
            raw = input(render_quiz_question(index, total, question)).strip()
            if raw.isdigit() and 1 <= int(raw) <= len(question["options"]):
                option_key, option_label = question["options"][int(raw) - 1]
                learning_profile[question["id"]] = option_key
                print(f"Selected: {option_label}\n")
                break
            print("Please enter the number of one of the options.\n")

    return learning_profile


def initial_profile(learning_profile: Dict[str, str]) -> Dict[str, Any]:
    return {
        "name": None,
        "major": None,
        "minor": None,
        "career_goals": None,
        "career_clarity": None,
        "subject_confidence": None,
        "interests": [],
        "notes": None,
        "learning_profile": learning_profile,
    }


def print_json(profile: Dict[str, Any]) -> None:
    print("\n=== FINAL ONBOARDING JSON ===")
    print(json.dumps(profile, indent=2, ensure_ascii=False))


def run_chat() -> None:
    learning_profile = collect_learning_profile()
    profile = initial_profile(learning_profile)
    history: List[Dict[str, str]] = []
    llm = BedrockJSONChatClient()

    opening = (
        "Thanks. I have a sense of how you learn. Before we begin, what name would you like me to use?"
    )
    print(f"Assistant: {opening}")
    history.append({"role": "assistant", "content": opening})

    while True:
        user_message = input("You: ").strip()
        if not user_message:
            print("Assistant: Go ahead. I'm listening.")
            continue

        history.append({"role": "user", "content": user_message})

        try:
            result = llm.send(
                profile=profile,
                conversation_history=history,
                user_message=user_message,
            )
        except Exception as exc:
            print(f"\n[Error calling model: {exc}]", file=sys.stderr)
            print("Falling back to a simple local handler.\n", file=sys.stderr)
            os.environ["USE_MOCK_LLM"] = "true"
            global USE_MOCK_LLM
            USE_MOCK_LLM = True
            llm = BedrockJSONChatClient()
            result = llm.send(
                profile=profile,
                conversation_history=history,
                user_message=user_message,
            )

        profile = merge_profile(profile, result.extracted_updates)
        missing = compute_missing_fields(profile)

        if result.user_seems_finished and not missing:
            closing = "Perfect. I have everything I need. Here's the structured profile I'd store."
            print(f"Assistant: {closing}")
            history.append({"role": "assistant", "content": closing})
            break

        assistant_reply = result.assistant_reply.strip() or question_for_field(
            missing[0] if missing else None,
            profile,
        )
        print(f"Assistant: {assistant_reply}")
        history.append({"role": "assistant", "content": assistant_reply})

    print_json(profile)


if __name__ == "__main__":
    run_chat()
