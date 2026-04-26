from __future__ import annotations

from collections import defaultdict, deque


def _node_id(record: dict) -> str:
    return str(record.get("id") or record.get("name") or "")


def topo_sort_concept_nodes(
    concepts: list[dict],
    relationships: list[dict],
) -> list[dict]:
    """Kahn topo sort over Concept nodes using PREREQUISITE_OF edges."""
    by_id: dict[str, dict] = {}
    for concept in concepts:
        node_id = _node_id(concept)
        if node_id:
            by_id[node_id] = {**concept, "id": node_id}

    indegree = {node_id: 0 for node_id in by_id}
    outgoing: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        if rel.get("type") != "PREREQUISITE_OF":
            continue
        source = str(rel.get("from_id") or rel.get("from") or "")
        target = str(rel.get("to_id") or rel.get("to") or "")
        if source in by_id and target in by_id and target not in outgoing[source]:
            outgoing[source].add(target)
            indegree[target] += 1

    queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while queue:
        node_id = queue.popleft()
        ordered.append(node_id)
        for target in sorted(outgoing[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if len(ordered) < len(by_id):
        seen = set(ordered)
        ordered.extend(sorted(node_id for node_id in by_id if node_id not in seen))

    return [by_id[node_id] for node_id in ordered]
