"""
Audit Neo4j for nodes that don't belong to the 3 valid courses:
  - accounting  (ALec* chunks, course IDs: ALecFinal, ALec, accounting)
  - python      (PLec* chunks, course IDs: python, PLec)
  - BIS512      (BIS512* chunks)

Run from the repo root:
    python backend/audit_neo4j.py
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

RESET  = "\033[0m"; BOLD = "\033[1m"; RED = "\033[31m"
GREEN  = "\033[32m"; YELLOW = "\033[33m"; CYAN = "\033[36m"; DIM = "\033[2m"

def _h(t):    return f"{BOLD}{t}{RESET}"
def _ok(t):   return f"{GREEN}{t}{RESET}"
def _warn(t): return f"{YELLOW}{t}{RESET}"
def _err(t):  return f"{RED}{t}{RESET}"
def _dim(t):  return f"{DIM}{t}{RESET}"

# ── Valid ID prefixes ─────────────────────────────────────────────────────────
VALID_COURSE_IDS  = {"ALecFinal", "ALec", "accounting", "15.501", "python", "6.0001", "PLec", "BIS512"}
VALID_LECTURE_PREFIXES = ("ALec", "PLec", "BIS512")
VALID_CHUNK_PREFIXES   = ("ALec", "PLec", "BIS512")


def is_valid_course(course_id: str) -> bool:
    cid = (course_id or "").strip()
    if cid in VALID_COURSE_IDS:
        return True
    for prefix in ("ALec", "PLec", "BIS512", "accounting", "python"):
        if cid.startswith(prefix):
            return True
    return False


def is_valid_lecture(lecture_id: str) -> bool:
    lid = (lecture_id or "").strip()
    return any(lid.startswith(p) for p in VALID_LECTURE_PREFIXES)


def is_valid_chunk(chunk_id: str) -> bool:
    cid = (chunk_id or "").strip()
    return any(cid.startswith(p) for p in VALID_CHUNK_PREFIXES)


def connect():
    uri      = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE")
    if not all([uri, username, password]):
        sys.exit(_err("NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD missing from .env"))
    try:
        from neo4j import GraphDatabase
    except ImportError:
        sys.exit(_err("neo4j package not installed."))
    print(f"{CYAN}[Neo4j]{RESET} Connecting to {uri} ...")
    return GraphDatabase.driver(uri, auth=(username, password)), database


def main():
    driver, database = connect()

    with driver:
        # ── Courses ───────────────────────────────────────────────────────────
        courses, _, _ = driver.execute_query(
            "MATCH (co:Course) RETURN co.id AS id ORDER BY id",
            database_=database,
        )
        # ── Lectures ──────────────────────────────────────────────────────────
        lectures, _, _ = driver.execute_query(
            "MATCH (le:Lecture) RETURN le.id AS id, coalesce(le.course_id,'') AS course_id ORDER BY id",
            database_=database,
        )
        # ── Chunks ────────────────────────────────────────────────────────────
        chunks, _, _ = driver.execute_query(
            "MATCH (ch:Chunk) RETURN ch.id AS id, coalesce(ch.source,'') AS source ORDER BY id",
            database_=database,
        )
        # ── Orphaned concepts (not connected to any Chunk) ────────────────────
        orphan_concepts, _, _ = driver.execute_query(
            """
            MATCH (c:Concept)
            WHERE NOT (c)<-[:CONTAINS]-(:Chunk)
            RETURN c.name AS name ORDER BY name
            """,
            database_=database,
        )
        # ── Chunks not connected to any Lecture ───────────────────────────────
        orphan_chunks, _, _ = driver.execute_query(
            """
            MATCH (ch:Chunk)
            WHERE NOT (:Lecture)-[:HAS_CHUNK]->(ch)
            RETURN ch.id AS id ORDER BY id
            """,
            database_=database,
        )
        # ── Lectures not connected to any Course ──────────────────────────────
        orphan_lectures, _, _ = driver.execute_query(
            """
            MATCH (le:Lecture)
            WHERE NOT (:Course)-[:HAS_LECTURE]->(le)
            RETURN le.id AS id ORDER BY id
            """,
            database_=database,
        )

    # ── Classify ─────────────────────────────────────────────────────────────
    invalid_courses  = [r["id"] for r in courses  if not is_valid_course(str(r["id"] or ""))]
    invalid_lectures = [r["id"] for r in lectures if not is_valid_lecture(str(r["id"] or ""))]
    invalid_chunks   = [r["id"] for r in chunks   if not is_valid_chunk(str(r["id"] or ""))]
    orphan_concept_names = [r["name"] for r in orphan_concepts]
    orphan_chunk_ids     = [r["id"]   for r in orphan_chunks]
    orphan_lecture_ids   = [r["id"]   for r in orphan_lectures]

    total_courses  = len(courses)
    total_lectures = len(lectures)
    total_chunks   = len(chunks)

    # ── Report ───────────────────────────────────────────────────────────────
    print(f"\n{'='*66}")
    print(f"{_h('NEO4J AUDIT  —  invalid / orphaned nodes')}")
    print(f"{'='*66}\n")

    # Courses
    print(f"{_h('COURSES')}  ({total_courses} total)")
    if invalid_courses:
        for cid in invalid_courses:
            print(f"  {_err('XX')} {cid}")
    else:
        print(f"  {_ok('OK')} all {total_courses} course(s) are valid")
    print()

    # Lectures
    print(f"{_h('LECTURES')}  ({total_lectures} total)")
    if invalid_lectures:
        for lid in invalid_lectures:
            print(f"  {_err('XX')} {lid}")
    else:
        print(f"  {_ok('OK')} all {total_lectures} lecture(s) are valid")
    print()

    # Chunks
    print(f"{_h('CHUNKS')}  ({total_chunks} total)")
    if invalid_chunks:
        sample = invalid_chunks[:10]
        more   = len(invalid_chunks) - len(sample)
        for cid in sample:
            print(f"  {_err('XX')} {cid}")
        if more:
            print(f"  {_dim(f'... +{more} more')}")
    else:
        print(f"  {_ok('OK')} all {total_chunks} chunk(s) are valid")
    print()

    # Orphaned chunks (not linked to a lecture)
    print(f"{_h('ORPHANED CHUNKS')} (no parent Lecture node)  ({len(orphan_chunk_ids)} found)")
    if orphan_chunk_ids:
        sample = orphan_chunk_ids[:10]
        more   = len(orphan_chunk_ids) - len(sample)
        for cid in sample:
            print(f"  {_warn('??')} {cid}")
        if more:
            print(f"  {_dim(f'... +{more} more')}")
    else:
        print(f"  {_ok('OK')} none")
    print()

    # Orphaned lectures (not linked to a course)
    print(f"{_h('ORPHANED LECTURES')} (no parent Course node)  ({len(orphan_lecture_ids)} found)")
    if orphan_lecture_ids:
        for lid in orphan_lecture_ids:
            print(f"  {_warn('??')} {lid}")
    else:
        print(f"  {_ok('OK')} none")
    print()

    # Orphaned concepts
    print(f"{_h('ORPHANED CONCEPTS')} (no parent Chunk node)  ({len(orphan_concept_names)} found)")
    if orphan_concept_names:
        sample = orphan_concept_names[:10]
        more   = len(orphan_concept_names) - len(sample)
        for name in sample:
            print(f"  {_warn('??')} {name}")
        if more:
            print(f"  {_dim(f'... +{more} more')}")
    else:
        print(f"  {_ok('OK')} none")
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    total_issues = (len(invalid_courses) + len(invalid_lectures) + len(invalid_chunks)
                    + len(orphan_chunk_ids) + len(orphan_lecture_ids) + len(orphan_concept_names))
    print(f"{'='*66}")
    print(f"{_h('SUMMARY')}")
    print(f"{'='*66}")
    rows = [
        ("Invalid courses",   len(invalid_courses)),
        ("Invalid lectures",  len(invalid_lectures)),
        ("Invalid chunks",    len(invalid_chunks)),
        ("Orphaned chunks",   len(orphan_chunk_ids)),
        ("Orphaned lectures", len(orphan_lecture_ids)),
        ("Orphaned concepts", len(orphan_concept_names)),
    ]
    for label, count in rows:
        marker = _ok("0") if count == 0 else _err(str(count))
        pad = 5 + (len(marker) - len(str(count)))
        print(f"  {label:<22}  {marker:>{pad}}")
    print(f"  {'-'*30}")
    total_marker = _ok("All clean") if total_issues == 0 else _warn(f"{total_issues} issue(s) found")
    print(f"  {total_marker}\n")


if __name__ == "__main__":
    main()
