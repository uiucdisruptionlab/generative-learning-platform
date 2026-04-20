import json
import os
from pathlib import Path

import redis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SESSION_TTL = 7200  # 2 hours

_VALID_MODES = {"new_lesson", "review", "retry"}

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Returns a reusable Redis connection. Initializes once and reuses the same instance."""
    global _client
    if _client is None:
        url = os.getenv("REDIS_URL")
        if not url:
            raise EnvironmentError("REDIS_URL is not set in the environment")
        _client = redis.from_url(url, decode_responses=True)
    return _client


# ---------------------------------------------------------------------------
# session:{id}:student
# ---------------------------------------------------------------------------

_STUDENT_FIELDS = ("id", "name", "llm_profile", "preferred_formats", "learning_goals")


def write_student(student_id: str, student: dict) -> None:
    """Write the student profile subset to Redis.

    Stores only: id, name, llm_profile, preferred_formats, learning_goals.

    Args:
        student_id: The student's UUID (used as the session key).
        student: Full or partial student dict; extra fields are ignored.
    """
    payload = {k: student[k] for k in _STUDENT_FIELDS if k in student}
    get_redis_client().set(f"session:{student_id}:student", json.dumps(payload), ex=SESSION_TTL)


def get_student(student_id: str) -> dict | None:
    """Return the cached student profile subset, or None if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    raw = get_redis_client().get(f"session:{student_id}:student")
    return json.loads(raw) if raw is not None else None


# ---------------------------------------------------------------------------
# session:{id}:mode
# ---------------------------------------------------------------------------

def write_mode(student_id: str, mode: str) -> None:
    """Write the session mode. Valid values: new_lesson, review, retry.

    Args:
        student_id: The student's UUID.
        mode: One of 'new_lesson', 'review', or 'retry'.

    Raises:
        ValueError: If mode is not a recognised value.
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"mode must be one of {_VALID_MODES}, got {mode!r}")
    get_redis_client().set(f"session:{student_id}:mode", mode, ex=SESSION_TTL)


def get_mode(student_id: str) -> str | None:
    """Return the session mode string, or None if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    return get_redis_client().get(f"session:{student_id}:mode")


# ---------------------------------------------------------------------------
# session:{id}:node_id
# ---------------------------------------------------------------------------

def write_node_id(student_id: str, node_id: str) -> None:
    """Write the active roadmap node ID.

    Args:
        student_id: The student's UUID.
        node_id: The active Neo4j concept/node identifier.
    """
    get_redis_client().set(f"session:{student_id}:node_id", node_id, ex=SESSION_TTL)


def get_node_id(student_id: str) -> str | None:
    """Return the active roadmap node ID, or None if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    return get_redis_client().get(f"session:{student_id}:node_id")


# ---------------------------------------------------------------------------
# session:{id}:chunks
# ---------------------------------------------------------------------------

def write_chunks(student_id: str, chunks: list[dict]) -> None:
    """Write the ordered content chunks list.

    Each chunk must have: index (int), text (str).

    Args:
        student_id: The student's UUID.
        chunks: Ordered list of {index, text} dicts.
    """
    get_redis_client().set(f"session:{student_id}:chunks", json.dumps(chunks), ex=SESSION_TTL)


def get_chunks(student_id: str) -> list[dict] | None:
    """Return the content chunks list, or None if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    raw = get_redis_client().get(f"session:{student_id}:chunks")
    return json.loads(raw) if raw is not None else None


# ---------------------------------------------------------------------------
# session:{id}:block_index
# ---------------------------------------------------------------------------

def write_block_index(student_id: str, index: int) -> None:
    """Write the active block index.

    Args:
        student_id: The student's UUID.
        index: Block position within the current concept.
    """
    get_redis_client().set(f"session:{student_id}:block_index", index, ex=SESSION_TTL)


def get_block_index(student_id: str) -> int | None:
    """Return the active block index, or None if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    raw = get_redis_client().get(f"session:{student_id}:block_index")
    return int(raw) if raw is not None else None


def increment_block_index(student_id: str) -> int:
    """Atomically increment block_index by 1 and refresh the TTL.

    Args:
        student_id: The student's UUID.

    Returns:
        The new block_index value.
    """
    r = get_redis_client()
    key = f"session:{student_id}:block_index"
    new_val = r.incr(key)
    r.expire(key, SESSION_TTL)
    return new_val


# ---------------------------------------------------------------------------
# session:{id}:messages
# ---------------------------------------------------------------------------

def get_messages(student_id: str) -> list[dict]:
    """Return the full conversation history. Returns [] if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    raw = get_redis_client().get(f"session:{student_id}:messages")
    return json.loads(raw) if raw is not None else []


def append_message(student_id: str, role: str, content: str) -> None:
    """Append one message to the conversation history and refresh the TTL.

    This is the only intended write path for messages after session start.

    Args:
        student_id: The student's UUID.
        role: Message role, e.g. 'user' or 'assistant'.
        content: Message text.
    """
    r = get_redis_client()
    key = f"session:{student_id}:messages"
    raw = r.get(key)
    messages = json.loads(raw) if raw is not None else []
    messages.append({"role": role, "content": content})
    r.set(key, json.dumps(messages), ex=SESSION_TTL)


def _init_messages(student_id: str) -> None:
    """Initialise messages to an empty list at session start."""
    get_redis_client().set(f"session:{student_id}:messages", json.dumps([]), ex=SESSION_TTL)


# ---------------------------------------------------------------------------
# session:{id}:attempt_count
# ---------------------------------------------------------------------------

def get_attempt_count(student_id: str) -> int:
    """Return the attempt count, or 0 if missing/expired.

    Args:
        student_id: The student's UUID.
    """
    raw = get_redis_client().get(f"session:{student_id}:attempt_count")
    return int(raw) if raw is not None else 0


def increment_attempt_count(student_id: str) -> int:
    """Atomically increment attempt_count by 1 and refresh the TTL.

    If the returned value reaches 3, the caller should surface a
    prerequisite suggestion to the student.

    Args:
        student_id: The student's UUID.

    Returns:
        The new attempt_count value.
    """
    r = get_redis_client()
    key = f"session:{student_id}:attempt_count"
    new_val = r.incr(key)
    r.expire(key, SESSION_TTL)
    return new_val


def _init_attempt_count(student_id: str) -> None:
    """Initialise attempt_count to 0 at session start."""
    get_redis_client().set(f"session:{student_id}:attempt_count", 0, ex=SESSION_TTL)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def delete_session(student_id: str) -> None:
    """Delete all session keys for a student.

    Args:
        student_id: The student's UUID.
    """
    r = get_redis_client()
    prefix = f"session:{student_id}"
    r.delete(
        f"{prefix}:student",
        f"{prefix}:mode",
        f"{prefix}:node_id",
        f"{prefix}:chunks",
        f"{prefix}:block_index",
        f"{prefix}:messages",
        f"{prefix}:attempt_count",
    )
