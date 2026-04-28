import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graphdb.toposort import topo_sort_concept_nodes
from srs import PASSING_SCORE, run_sm2


class AdaptiveSessionUnitTests(unittest.TestCase):
    def test_topo_sort_orders_prerequisites_first(self) -> None:
        concepts = [
            {"id": "loops", "name": "Loops"},
            {"id": "variables", "name": "Variables"},
            {"id": "functions", "name": "Functions"},
        ]
        relationships = [
            {"from_id": "variables", "to_id": "loops", "type": "PREREQUISITE_OF"},
            {"from_id": "loops", "to_id": "functions", "type": "PREREQUISITE_OF"},
        ]

        ordered = [concept["id"] for concept in topo_sort_concept_nodes(concepts, relationships)]

        self.assertLess(ordered.index("variables"), ordered.index("loops"))
        self.assertLess(ordered.index("loops"), ordered.index("functions"))

    def test_topo_sort_keeps_cyclic_nodes(self) -> None:
        concepts = [{"id": "a"}, {"id": "b"}]
        relationships = [
            {"from_id": "a", "to_id": "b", "type": "PREREQUISITE_OF"},
            {"from_id": "b", "to_id": "a", "type": "PREREQUISITE_OF"},
        ]

        ordered = [concept["id"] for concept in topo_sort_concept_nodes(concepts, relationships)]

        self.assertEqual(set(ordered), {"a", "b"})

    def test_sm2_uses_architecture_passing_score(self) -> None:
        self.assertEqual(PASSING_SCORE, 3)
        failed = run_sm2(2, {"interval_days": 6, "repetitions": 2})
        passed = run_sm2(3, {"interval_days": 0, "repetitions": 0})

        self.assertEqual(failed["interval_days"], 1)
        self.assertEqual(failed["repetitions"], 0)
        self.assertEqual(passed["repetitions"], 1)


if __name__ == "__main__":
    unittest.main()
