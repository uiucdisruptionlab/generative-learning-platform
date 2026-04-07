"""
Graph-only test for lesson grouping and ordering.
Run from backend/:
    python -m graphdb.test_roadmap_builder
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graphdb.roadmap_builder import build_roadmap_from_graph_data


FAKE_GRAPH = {
    "concepts": [
        {"name": "Variables", "description": "Named storage for values"},
        {"name": "Expressions", "description": "Combinations of values and operators"},
        {"name": "Conditionals", "description": "Branching logic"},
        {"name": "Loops", "description": "Repeated execution"},
        {"name": "Functions", "description": "Reusable blocks of code"},
        {"name": "Function Parameters", "description": "Inputs passed into functions"},
    ],
    "relationships": [
        {"from": "Variables", "to": "Expressions", "type": "RELATED_TO"},
        {"from": "Conditionals", "to": "Expressions", "type": "RELATED_TO"},
        {"from": "Function Parameters", "to": "Functions", "type": "PART_OF"},
        {"from": "Variables", "to": "Conditionals", "type": "PREREQUISITE_OF"},
        {"from": "Conditionals", "to": "Loops", "type": "PREREQUISITE_OF"},
        {"from": "Loops", "to": "Functions", "type": "PREREQUISITE_OF"},
    ],
    "chunk_links": [
        {"chunk_id": "chunk_001", "lecture_id": "lec_01", "course_id": "CS101", "chunk_order": 1, "concept_name": "Variables"},
        {"chunk_id": "chunk_001", "lecture_id": "lec_01", "course_id": "CS101", "chunk_order": 1, "concept_name": "Expressions"},
        {"chunk_id": "chunk_002", "lecture_id": "lec_01", "course_id": "CS101", "chunk_order": 2, "concept_name": "Conditionals"},
        {"chunk_id": "chunk_003", "lecture_id": "lec_02", "course_id": "CS101", "chunk_order": 3, "concept_name": "Loops"},
        {"chunk_id": "chunk_004", "lecture_id": "lec_03", "course_id": "CS101", "chunk_order": 4, "concept_name": "Functions"},
        {"chunk_id": "chunk_004", "lecture_id": "lec_03", "course_id": "CS101", "chunk_order": 4, "concept_name": "Function Parameters"},
    ],
}


def main() -> None:
    roadmap = build_roadmap_from_graph_data(FAKE_GRAPH, course="CS101")
    print(json.dumps(roadmap, indent=2))


if __name__ == "__main__":
    main()
