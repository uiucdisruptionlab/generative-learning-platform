"""
Audit: chunk IDs present in Neo4j but missing from Pinecone.
Checks vectors against the 4 course-level namespaces only.
Run from the repo root:
    python backend/audit_pinecone_neo4j.py
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# ── ANSI colours ─────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD  = "\033[1m"
RED   = "\033[31m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
CYAN  = "\033[36m"
DIM   = "\033[2m"

def _h(t):   return f"{BOLD}{t}{RESET}"
def _ok(t):  return f"{GREEN}{t}{RESET}"
def _warn(t):return f"{YELLOW}{t}{RESET}"
def _err(t): return f"{RED}{t}{RESET}"
def _dim(t): return f"{DIM}{t}{RESET}"

# ── Course → Pinecone namespace mapping ──────────────────────────────────────
# Keys are Neo4j Course.id values (or prefixes that appear in them).
# Values are the Pinecone namespace where those chunks were indexed.
COURSE_NAMESPACE_MAP: dict[str, str] = {
    # accounting course — ALec* chunk IDs
    "ALec":          "15.501_Transcripts",
    "accounting":    "15.501_Transcripts",
    "15.501":        "15.501_Transcripts",
    # python course — PLec* chunk IDs
    "PLec":          "6.0001_Transcripts",
    "python":        "6.0001_Transcripts",
    "6.0001":        "6.0001_Transcripts",
    # financing
    "financing":     "11.437_Transcripts",
    "11.437":        "11.437_Transcripts",
    # BIS512
    "BIS512":        "BIS512",
}

def resolve_namespace(course_id: str) -> str | None:
    """Map a Neo4j Course.id to its Pinecone namespace."""
    cid = (course_id or "").strip()
    # exact match first
    if cid in COURSE_NAMESPACE_MAP:
        return COURSE_NAMESPACE_MAP[cid]
    # prefix match (e.g. "ALecFinal" → "ALec")
    for prefix, ns in COURSE_NAMESPACE_MAP.items():
        if cid.startswith(prefix):
            return ns
    return None


# ── Step 1: fetch all chunk IDs from Neo4j, grouped by course ────────────────
def neo4j_chunks_by_course() -> dict[str, list[str]]:
    """Returns { neo4j_course_id: [chunk_id, ...] }"""
    uri      = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE")

    if not all([uri, username, password]):
        sys.exit(_err("NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD missing from .env"))

    try:
        from neo4j import GraphDatabase
    except ImportError:
        sys.exit(_err("neo4j package not installed. Run: pip install neo4j"))

    print(f"{CYAN}[Neo4j]{RESET} Connecting to {uri} ...")
    driver = GraphDatabase.driver(uri, auth=(username, password))

    with driver:
        records, _, _ = driver.execute_query(
            """
            MATCH (co:Course)-[:HAS_LECTURE]->(:Lecture)-[:HAS_CHUNK]->(ch:Chunk)
            RETURN co.id AS course_id, ch.id AS chunk_id
            ORDER BY course_id, chunk_id
            """,
            database_=database,
        )

    by_course: dict[str, list[str]] = defaultdict(list)
    for r in records:
        cid = str(r["course_id"] or "").strip()
        chid = str(r["chunk_id"] or "").strip()
        if cid and chid:
            by_course[cid].append(chid)

    print(f"{CYAN}[Neo4j]{RESET} Found {_h(str(sum(len(v) for v in by_course.values())))} "
          f"chunk(s) across {_h(str(len(by_course)))} course(s): "
          f"{', '.join(sorted(by_course.keys()))}")
    return dict(by_course)


# ── Step 2: batch-fetch IDs from a Pinecone namespace ────────────────────────
BATCH_SIZE = 200

def pinecone_fetch_missing(ids: list[str], namespace: str, index) -> list[str]:
    """Returns IDs that are absent from Pinecone in the given namespace."""
    missing: list[str] = []
    for i in range(0, len(ids), BATCH_SIZE):
        batch = ids[i : i + BATCH_SIZE]
        try:
            resp = index.fetch(ids=batch, namespace=namespace)
            vectors = (
                resp.get("vectors", {})
                if isinstance(resp, dict)
                else getattr(resp, "vectors", {}) or {}
            )
            for cid in batch:
                if cid not in vectors:
                    missing.append(cid)
        except Exception as exc:
            print(f"  {_err('fetch error')} batch {i//BATCH_SIZE + 1}: {exc}")
            missing.extend(batch)
    return missing


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    api_key    = os.getenv("PINECONE_API_KEY", "").strip()
    index_name = os.getenv("PINECONE_INDEX", "").strip()
    if not api_key or not index_name:
        sys.exit(_err("PINECONE_API_KEY or PINECONE_INDEX missing from .env"))

    try:
        from pinecone import Pinecone
    except ImportError:
        sys.exit(_err("pinecone package not installed. Run: pip install pinecone"))

    print(f"{CYAN}[Pinecone]{RESET} Connecting to index '{_h(index_name)}' ...\n")
    index = Pinecone(api_key=api_key).Index(index_name)

    # Neo4j data
    neo4j_data = neo4j_chunks_by_course()
    if not neo4j_data:
        print(_warn("No chunks found in Neo4j. Nothing to compare."))
        return

    # Group by Pinecone namespace (multiple Neo4j courses may share one namespace)
    ns_to_ids: dict[str, list[str]] = defaultdict(list)
    unmapped_courses: list[str] = []

    for course_id, chunk_ids in neo4j_data.items():
        ns = resolve_namespace(course_id)
        if ns:
            ns_to_ids[ns].extend(chunk_ids)
        else:
            unmapped_courses.append(course_id)
            print(_warn(f"  [warn] No Pinecone namespace mapping for Neo4j course '{course_id}' "
                        f"({len(chunk_ids)} chunks) — skipping."))

    if unmapped_courses:
        print()

    # Deduplicate IDs per namespace (shouldn't be needed, but safe)
    for ns in ns_to_ids:
        ns_to_ids[ns] = list(dict.fromkeys(ns_to_ids[ns]))

    print(f"\n{'-'*66}")
    print(f"{_h('PINECONE AUDIT  (per namespace)')}")
    print(f"{'-'*66}\n")

    report_rows: list[tuple[str, int, int]] = []
    missing_by_ns: dict[str, list[str]] = {}
    grand_total = grand_missing = 0

    for ns in sorted(ns_to_ids.keys()):
        ids   = ns_to_ids[ns]
        total = len(ids)
        grand_total += total

        print(f"  {CYAN}Namespace:{RESET} {_h(ns)}  ({total} chunk(s))")
        missing = pinecone_fetch_missing(ids, ns, index)
        missing_by_ns[ns] = missing

        found  = total - len(missing)
        pct    = (found / total * 100) if total else 0
        status = _ok("OK  all present") if not missing else _err(f"XX  {len(missing)} missing")
        print(f"    {status}   {_dim(f'{found}/{total} in Pinecone ({pct:.0f}%)')}")

        if missing:
            sample = missing[:5]
            more   = len(missing) - len(sample)
            line   = ", ".join(sample)
            if more:
                line += f"  {_dim(f'... +{more} more')}"
            print(f"    {_warn('Missing IDs (sample):')} {line}")

        grand_missing += len(missing)
        report_rows.append((ns, total, len(missing)))
        print()

    # Summary table
    col_ns = max((len(r[0]) for r in report_rows), default=9)
    col_ns = max(col_ns, 9)
    print(f"{'='*66}")
    print(f"{_h('SUMMARY')}")
    print(f"{'='*66}")
    hdr = f"  {'Namespace':<{col_ns}}  {'Total':>7}  {'Missing':>8}  {'OK%':>5}"
    print(_h(hdr))
    print(f"  {'-'*col_ns}  {'-'*7}  {'-'*8}  {'-'*5}")

    for ns, total, n_miss in report_rows:
        pct = ((total - n_miss) / total * 100) if total else 0
        mr  = str(n_miss)
        ms  = _err(mr) if n_miss else _ok(mr)
        pr  = f"{pct:.0f}%"
        ps  = _ok(pr) if pct == 100 else _warn(pr)
        mp  = 8 + (len(ms) - len(mr))
        pp  = 5 + (len(ps) - len(pr))
        print(f"  {ns:<{col_ns}}  {total:>7}  {ms:>{mp}}  {ps:>{pp}}")

    print(f"  {'-'*col_ns}  {'-'*7}  {'-'*8}  {'-'*5}")
    gp = ((grand_total - grand_missing) / grand_total * 100) if grand_total else 0
    print(f"  {'TOTAL':<{col_ns}}  {grand_total:>7}  {grand_missing:>8}  {gp:.0f}%")
    print(f"{'='*66}\n")

    if grand_missing == 0:
        print(_ok("All Neo4j chunks have vectors in Pinecone. No action needed."))
        return

    print(_warn(f"{grand_missing} chunk ID(s) are in Neo4j but have no vector in Pinecone."))

    # ── Missing lectures breakdown ────────────────────────────────────────────
    # Extract lecture prefix: "ALec13_p1_c0" -> "ALec13"
    import re

    # Build: { namespace: { lecture_id: [chunk_id, ...] } }
    missing_lectures: dict[str, dict[str, list[str]]] = {}
    for ns, ids in missing_by_ns.items():
        if not ids:
            continue
        by_lec: dict[str, list[str]] = defaultdict(list)
        for cid in ids:
            m = re.match(r"^(.+?)_p\d+", cid)
            lec = m.group(1) if m else cid
            by_lec[lec].append(cid)
        missing_lectures[ns] = dict(by_lec)

    print(f"\n{'='*66}")
    print(f"{_h('MISSING LECTURES')}")
    print(f"{'='*66}")

    for ns in sorted(missing_lectures.keys()):
        by_lec = missing_lectures[ns]
        lec_count   = len(by_lec)
        chunk_count = sum(len(v) for v in by_lec.values())
        print(f"\n  {CYAN}{ns}{RESET}  "
              f"({_err(str(lec_count))} lecture(s) incomplete, "
              f"{_err(str(chunk_count))} chunk(s) missing)\n")

        col_lec = max(len(l) for l in by_lec) + 2
        lec_hdr = f"  Lecture{' '*(col_lec-7)}  Missing chunks  Chunk IDs"
        print(f"  {_h(lec_hdr)}")
        print(f"  {'-'*(col_lec+40)}")

        for lec in sorted(by_lec.keys(), key=lambda x: (re.sub(r'\d+', '', x), int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)):
            chunks = sorted(by_lec[lec])
            count_str = _err(str(len(chunks)))
            ids_str   = ", ".join(chunks[:4])
            if len(chunks) > 4:
                ids_str += f"  {_dim(f'... +{len(chunks)-4} more')}"
            count_pad = 15 + (len(count_str) - len(str(len(chunks))))
            print(f"  {_err('XX')}  {lec:<{col_lec}}  {count_str:>{count_pad}}  {_dim(ids_str)}")

    # All-missing-lectures flat list
    all_missing_lecs: dict[str, set[str]] = defaultdict(set)
    for ns, by_lec in missing_lectures.items():
        for lec in by_lec:
            all_missing_lecs[ns].add(lec)

    print(f"\n{'='*66}")
    print(f"{_h('FLAT LIST OF INCOMPLETE LECTURES')}")
    print(f"{'='*66}")
    for ns in sorted(all_missing_lecs.keys()):
        lecs = sorted(
            all_missing_lecs[ns],
            key=lambda x: (re.sub(r'\d+', '', x), int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
        )
        print(f"\n  {CYAN}{ns}{RESET}")
        for lec in lecs:
            n = len(missing_lectures[ns][lec])
            print(f"    {_err('XX')} {lec}  {_dim(f'({n} chunk(s) missing)')}")

    print()


if __name__ == "__main__":
    main()
