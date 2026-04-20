"""
test_session.py — Integration test for redis_client.py against the live Upstash instance.

Uses mock/dummy data only. Does not import session_loader, Neo4j, or Pinecone.

Run from the backend/ directory:
    python cacheing/test_session.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import redis_client as rc

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

STUDENT_ID = "test-session-student-001"

MOCK_STUDENT = {
    "id": STUDENT_ID,
    "name": "Alice Test",
    "llm_profile": {"tone": "encouraging", "verbosity": "concise"},
    "preferred_formats": ["video", "flashcard"],
    "learning_goals": {"target": "understand income statements", "timeline": "2 weeks"},
    "extra_field": "should be ignored by write_student",
}

MOCK_MODE = "new_lesson"
MOCK_NODE_ID = "lesson_042"
MOCK_CHUNKS = [
    {"index": 0, "text": "Revenue is income from normal business operations."},
    {"index": 1, "text": "Expenses are costs incurred to generate revenue."},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

passes: list[str] = []
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        passes.append(label)
        print(f"  PASS  {label}")
    else:
        failures.append(label)
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_setters_and_getters() -> None:
    print("\n--- Write all keys ---")
    rc.write_student(STUDENT_ID, MOCK_STUDENT)
    rc.write_mode(STUDENT_ID, MOCK_MODE)
    rc.write_node_id(STUDENT_ID, MOCK_NODE_ID)
    rc.write_chunks(STUDENT_ID, MOCK_CHUNKS)
    rc.write_block_index(STUDENT_ID, 0)
    rc._init_messages(STUDENT_ID)
    rc._init_attempt_count(STUDENT_ID)
    print("  Written.")

    print("\n--- Read all keys ---")

    student = rc.get_student(STUDENT_ID)
    print(f"  student:       {student}")
    check("student fields stored", student is not None)
    check("student extra field excluded", student is not None and "extra_field" not in student,
          f"got keys: {list(student or {})}")
    check("student name correct", student is not None and student.get("name") == "Alice Test")
    check("student llm_profile correct", student is not None and student.get("llm_profile") == MOCK_STUDENT["llm_profile"])

    mode = rc.get_mode(STUDENT_ID)
    print(f"  mode:          {mode!r}")
    check("mode correct", mode == MOCK_MODE)

    node_id = rc.get_node_id(STUDENT_ID)
    print(f"  node_id:       {node_id!r}")
    check("node_id correct", node_id == MOCK_NODE_ID)

    chunks = rc.get_chunks(STUDENT_ID)
    print(f"  chunks:        {chunks}")
    check("chunks correct", chunks == MOCK_CHUNKS)

    block_index = rc.get_block_index(STUDENT_ID)
    print(f"  block_index:   {block_index}")
    check("block_index is 0", block_index == 0)

    messages = rc.get_messages(STUDENT_ID)
    print(f"  messages:      {messages}")
    check("messages initialised to []", messages == [])

    attempt_count = rc.get_attempt_count(STUDENT_ID)
    print(f"  attempt_count: {attempt_count}")
    check("attempt_count initialised to 0", attempt_count == 0)


def test_append_message() -> None:
    print("\n--- append_message ---")
    rc.append_message(STUDENT_ID, "user", "What is revenue?")
    rc.append_message(STUDENT_ID, "assistant", "Revenue is income from normal business operations.")
    messages = rc.get_messages(STUDENT_ID)
    print(f"  messages: {messages}")
    check("two messages appended", len(messages) == 2,
          f"got {len(messages)} message(s)")
    check("first message role", messages[0]["role"] == "user")
    check("first message content", messages[0]["content"] == "What is revenue?")
    check("second message role", messages[1]["role"] == "assistant")


def test_increments() -> None:
    print("\n--- increment_attempt_count ---")
    v1 = rc.increment_attempt_count(STUDENT_ID)
    v2 = rc.increment_attempt_count(STUDENT_ID)
    print(f"  attempt_count after 2 increments: {v2}")
    check("attempt_count increments correctly", v1 == 1 and v2 == 2,
          f"got v1={v1}, v2={v2}")

    print("\n--- increment_block_index ---")
    b1 = rc.increment_block_index(STUDENT_ID)
    b2 = rc.increment_block_index(STUDENT_ID)
    print(f"  block_index after 2 increments: {b2}")
    check("block_index increments correctly", b1 == 1 and b2 == 2,
          f"got b1={b1}, b2={b2}")


def test_delete_session() -> None:
    print("\n--- delete_session ---")
    rc.delete_session(STUDENT_ID)
    print("  Deleted.")

    node_id_after = rc.get_node_id(STUDENT_ID)
    print(f"  node_id after delete: {node_id_after!r}")
    check("node_id gone after delete", node_id_after is None)

    student_after = rc.get_student(STUDENT_ID)
    check("student gone after delete", student_after is None)

    messages_after = rc.get_messages(STUDENT_ID)
    check("messages return [] after delete", messages_after == [])

    attempt_after = rc.get_attempt_count(STUDENT_ID)
    check("attempt_count returns 0 after delete", attempt_after == 0)


def test_invalid_mode() -> None:
    print("\n--- write_mode with invalid value ---")
    try:
        rc.write_mode(STUDENT_ID, "invalid_mode")
        check("invalid mode raises ValueError", False, "no exception raised")
    except ValueError as e:
        print(f"  ValueError raised as expected: {e}")
        check("invalid mode raises ValueError", True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Connecting to Redis...")
    try:
        rc.get_redis_client().ping()
        print("Connected.\n")
    except Exception as e:
        print(f"Could not connect to Redis: {e}")
        sys.exit(1)

    # Clean up any leftover keys from a previous run
    rc.delete_session(STUDENT_ID)

    test_setters_and_getters()
    test_append_message()
    test_increments()
    test_delete_session()
    test_invalid_mode()

    print(f"\n{'='*40}")
    print(f"Results: {len(passes)} passed, {len(failures)} failed")
    if failures:
        print(f"Failed:  {', '.join(failures)}")
    else:
        print("All tests passed.")
    print('='*40)

    sys.exit(0 if not failures else 1)
