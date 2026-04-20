import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from supabaseDB.supabase_client import (
    DEMO_STUDENT_ALICE_ID,
    get_supabase_client,
    get_lessons_for_student,
    get_cached_roadmap,
)
from cacheing.redis_client import (
    get_redis_client,
    get_student,
    get_mode,
    get_node_id,
    get_chunks,
    get_block_index,
    get_messages,
    get_attempt_count,
    delete_session,
)
from session_loader import start_session

STUDENT_ID = DEMO_STUDENT_ALICE_ID
COURSE = "accounting"
NAMESPACE = "15.501_Transcripts"
MODE = "new_lesson"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


passes = 0
failures = 0


def record(label: str, condition: bool, detail: str = "") -> None:
    global passes, failures
    ok = check(label, condition, detail)
    if ok:
        passes += 1
    else:
        failures += 1


# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

section("Pre-flight checks")

try:
    get_redis_client().ping()
    print("  Redis: connected")
except Exception as e:
    print(f"  Redis: FAILED — {e}")
    sys.exit(1)

try:
    sb = get_supabase_client()
    print("  Supabase: connected")
except Exception as e:
    print(f"  Supabase: FAILED — {e}")
    sys.exit(1)

# Clear any stale state so we exercise the full build path
print(f"\n  Clearing stale cache for student {STUDENT_ID}...")
sb.table("roadmap_cache").delete().eq("student_id", STUDENT_ID).execute()
sb.table("lessons").delete().eq("student_id", STUDENT_ID).execute()
delete_session(STUDENT_ID)
print("  Cleared.")

# ---------------------------------------------------------------------------
# Run start_session
# ---------------------------------------------------------------------------

section("Running start_session")
print(f"  student_id : {STUDENT_ID}")
print(f"  course     : {COURSE}")
print(f"  namespace  : {NAMESPACE}")
print(f"  mode       : {MODE}\n")

try:
    result = start_session(STUDENT_ID, MODE, COURSE, NAMESPACE)
    print("  start_session completed.")
except Exception as e:
    print(f"  start_session FAILED: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Validate return value
# ---------------------------------------------------------------------------

section("Validating return value")

record("result has node_id", bool(result.get("node_id")))
record("result has chunks", isinstance(result.get("chunks"), list))
record("result mode correct", result.get("mode") == MODE)
record("result has student", bool(result.get("student")))
record("student has name", bool((result.get("student") or {}).get("name")))

print(f"\n  node_id : {result.get('node_id')}")
print(f"  chunks  : {len(result.get('chunks', []))} returned")
print(f"  student : {(result.get('student') or {}).get('name')!r}")

# ---------------------------------------------------------------------------
# Validate Supabase — lessons table
# ---------------------------------------------------------------------------

section("Supabase — lessons table")

lessons = get_lessons_for_student(STUDENT_ID, client=sb)
record("lessons rows created", len(lessons) > 0, f"got {len(lessons)}")
if lessons:
    first = lessons[0]
    print(f"\n  Total lessons: {len(lessons)}")
    print(f"  First lesson:")
    print(f"    lesson_id  : {first.get('lesson_id')}")
    print(f"    title      : {first.get('title')!r}")
    print(f"    chunk_ids  : {len(first.get('chunk_ids') or [])} chunks")
    print(f"    concepts   : {len(first.get('concepts') or [])} concepts")
    print(f"    prereqs    : {first.get('prerequisites')}")
    record("first lesson has title", bool(first.get("title")))
    record("first lesson has chunk_ids", bool(first.get("chunk_ids")))
    record("first lesson has concepts", bool(first.get("concepts")))

# ---------------------------------------------------------------------------
# Validate Supabase — roadmap_cache table
# ---------------------------------------------------------------------------

section("Supabase — roadmap_cache table")

cached = get_cached_roadmap(STUDENT_ID, client=sb)
record("roadmap_cache row created", cached is not None)
if cached:
    record("roadmap is a list of UUIDs", isinstance(cached, list) and all(isinstance(x, str) for x in cached),
           f"got {type(cached)}")
    record("roadmap length matches lessons", len(cached) == len(lessons),
           f"cache={len(cached)}, lessons={len(lessons)}")
    print(f"\n  Cached roadmap: {len(cached)} entries")
    print(f"  First UUID: {cached[0]}")

# ---------------------------------------------------------------------------
# Validate Redis
# ---------------------------------------------------------------------------

section("Redis — session keys")

redis_student = get_student(STUDENT_ID)
redis_mode = get_mode(STUDENT_ID)
redis_node_id = get_node_id(STUDENT_ID)
redis_chunks = get_chunks(STUDENT_ID)
redis_block_index = get_block_index(STUDENT_ID)
redis_messages = get_messages(STUDENT_ID)
redis_attempt_count = get_attempt_count(STUDENT_ID)

record("student written to Redis", redis_student is not None)
record("mode written to Redis", redis_mode == MODE)
record("node_id written to Redis", redis_node_id == result.get("node_id"))
record("chunks written to Redis", isinstance(redis_chunks, list))
record("block_index initialised to 0", redis_block_index == 0)
record("messages initialised to []", redis_messages == [])
record("attempt_count initialised to 0", redis_attempt_count == 0)

print(f"\n  Redis student name : {(redis_student or {}).get('name')!r}")
print(f"  Redis mode         : {redis_mode!r}")
print(f"  Redis node_id      : {redis_node_id!r}")
print(f"  Redis chunks       : {len(redis_chunks or [])} chunks")
print(f"  Redis block_index  : {redis_block_index}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

section("Summary")
print(f"  {passes} passed, {failures} failed")
if failures:
    print("  Some checks failed — review output above.")
else:
    print("  All checks passed.")

sys.exit(0 if failures == 0 else 1)
