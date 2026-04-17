from __future__ import annotations

PERSONAS: dict[str, dict] = {
    "alice": {
        "student_id": "a0000001-0000-4000-8000-000000000001",
        "name": "Alice",
        "major": "Finance and Data Science",
        "course": "python",
        "familiarity": "beginner",
        "learning_style": "videos and hands-on problems",
        "hours_per_week": 5,
        "notes": (
            "Alice is not very familiar with coding. Prefer simple language, "
            "relatable analogies, and hands-on examples. Avoid heavy jargon. "
            "Keep explanations approachable and build intuition before diving into details."
        ),
    },
    "bob": {
        "student_id": "b0000002-0000-4000-8000-000000000002",
        "name": "Bob",
        "major": "Business",
        "course": "financing",
        "familiarity": "high",
        "learning_style": "reading and interacting with AI, lots of real-world examples",
        "hours_per_week": 2,
        "notes": (
            "Bob is already very familiar with the topic. Skip basic definitions and "
            "go straight to nuance, edge cases, and real-world business applications. "
            "Use dense, example-rich content. He has limited time so keep it efficient."
        ),
    },
    "charles": {
        "student_id": "c0000003-0000-4000-8000-000000000003",
        "name": "Charles",
        "major": "Accounting",
        "course": "accounting",
        "familiarity": "intermediate",
        "learning_style": "flashcard reviews and questions to test knowledge",
        "hours_per_week": 10,
        "notes": (
            "Charles wants to be tested frequently. Emphasize knowledge checks, "
            "key term definitions, and structured review. He can handle more depth "
            "and appreciates thorough explanations followed by questions."
        ),
    },
}


def get_persona(persona_id: str) -> dict:
    persona = PERSONAS.get(persona_id.lower())
    if not persona:
        raise ValueError(f"Unknown persona '{persona_id}'. Choose from: {list(PERSONAS.keys())}")
    return persona
