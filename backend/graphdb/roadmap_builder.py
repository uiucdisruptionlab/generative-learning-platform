from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Any


def _canonicalize_name(name: str) -> str:
    return " ".join(name.lower().strip().split())


def _build_undirected_neighbors(relationships: list[dict[str, str]]) -> dict[str, set[str]]:
    neighbors: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        rel_type = rel["type"]
        if rel_type not in {"PART_OF", "RELATED_TO"}:
            continue

        a = rel["from"]
        b = rel["to"]
        if a == b:
            continue

        neighbors[a].add(b)
        neighbors[b].add(a)
    return neighbors


def _connected_components(nodes: set[str], neighbors: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []

    for node in sorted(nodes):
        if node in visited:
            continue

        queue = deque([node])
        visited.add(node)
        component: list[str] = []

        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(neighbors.get(current, set())):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)

        components.append(sorted(component))

    return components


def _select_lesson_title(component: list[str], concept_chunk_orders: dict[str, list[int]]) -> str:
    ranked = sorted(
        component,
        key=lambda name: (
            min(concept_chunk_orders.get(name, [10**9])),
            len(name),
            name.lower(),
        ),
    )
    return ranked[0]


def _topological_sort(
    node_ids: list[str],
    adjacency: dict[str, set[str]],
    lesson_order_hint: dict[str, float],
    lesson_titles: dict[str, str],
) -> list[str]:
    indegree = {node_id: 0 for node_id in node_ids}
    for source, targets in adjacency.items():
        for target in targets:
            indegree[target] += 1

    ready = [
        node_id
        for node_id in node_ids
        if indegree[node_id] == 0
    ]
    ready.sort(key=lambda node_id: (lesson_order_hint[node_id], lesson_titles[node_id].lower(), node_id))

    ordered: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for target in sorted(adjacency.get(current, set())):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort(key=lambda node_id: (lesson_order_hint[node_id], lesson_titles[node_id].lower(), node_id))

    if len(ordered) == len(node_ids):
        return ordered

    remaining = [node_id for node_id in node_ids if node_id not in ordered]
    remaining.sort(key=lambda node_id: (lesson_order_hint[node_id], lesson_titles[node_id].lower(), node_id))
    return ordered + remaining


def build_roadmap_from_graph_data(graph_data: dict[str, Any], course: str = "generated_course") -> dict[str, Any]:
    concepts = graph_data.get("concepts", [])
    relationships = graph_data.get("relationships", [])
    chunk_links = graph_data.get("chunk_links", [])

    concept_names = {concept["name"] for concept in concepts}
    concept_descriptions = {concept["name"]: concept.get("description", "") for concept in concepts}

    concept_chunk_orders: dict[str, list[int]] = defaultdict(list)
    concept_chunk_ids: dict[str, set[str]] = defaultdict(set)
    for link in chunk_links:
        concept_name = link["concept_name"]
        chunk_id = link["chunk_id"]
        chunk_order = int(link.get("chunk_order") or 0)
        concept_chunk_orders[concept_name].append(chunk_order)
        concept_chunk_ids[concept_name].add(chunk_id)

    canonical_groups: dict[str, list[str]] = defaultdict(list)
    for concept_name in concept_names:
        canonical_groups[_canonicalize_name(concept_name)].append(concept_name)

    canonical_representatives: dict[str, str] = {}
    alias_to_canonical: dict[str, str] = {}
    for _, names in canonical_groups.items():
        representative = sorted(
            names,
            key=lambda name: (
                min(concept_chunk_orders.get(name, [10**9])),
                len(name),
                name.lower(),
            ),
        )[0]
        canonical_representatives[representative] = representative
        for name in names:
            alias_to_canonical[name] = representative

    canonical_concepts = set(alias_to_canonical.values())
    canonical_descriptions = {
        canonical: concept_descriptions.get(canonical, "")
        for canonical in canonical_concepts
    }
    canonical_chunk_orders: dict[str, list[int]] = defaultdict(list)
    canonical_chunk_ids: dict[str, set[str]] = defaultdict(set)
    for original, canonical in alias_to_canonical.items():
        canonical_chunk_orders[canonical].extend(concept_chunk_orders.get(original, []))
        canonical_chunk_ids[canonical].update(concept_chunk_ids.get(original, set()))

    canonical_relationships: list[dict[str, str]] = []
    seen_relationships: set[tuple[str, str, str]] = set()
    for rel in relationships:
        from_name = alias_to_canonical.get(rel["from"])
        to_name = alias_to_canonical.get(rel["to"])
        rel_type = rel["type"]
        if not from_name or not to_name or from_name == to_name:
            continue
        key = (from_name, to_name, rel_type)
        if key in seen_relationships:
            continue
        seen_relationships.add(key)
        canonical_relationships.append(
            {
                "from": from_name,
                "to": to_name,
                "type": rel_type,
            }
        )

    neighbors = _build_undirected_neighbors(canonical_relationships)
    components = _connected_components(canonical_concepts, neighbors)

    concept_to_lesson: dict[str, str] = {}
    lessons: list[dict[str, Any]] = []
    lesson_order_hint: dict[str, float] = {}
    lesson_titles: dict[str, str] = {}

    for index, component in enumerate(components, start=1):
        lesson_id = f"lesson_{index:03d}"
        title = _select_lesson_title(component, canonical_chunk_orders)
        chunk_orders = [
            order
            for concept_name in component
            for order in canonical_chunk_orders.get(concept_name, [])
            if order > 0
        ]
        average_chunk_order = sum(chunk_orders) / len(chunk_orders) if chunk_orders else float(index)
        chunk_ids = sorted({
            chunk_id
            for concept_name in component
            for chunk_id in canonical_chunk_ids.get(concept_name, set())
        })

        lessons.append(
            {
                "lesson_id": lesson_id,
                "title": title,
                "concepts": [
                    {
                        "name": concept_name,
                        "description": canonical_descriptions.get(concept_name, ""),
                    }
                    for concept_name in component
                ],
                "chunk_ids": chunk_ids,
                "prerequisites": [],
            }
        )

        for concept_name in component:
            concept_to_lesson[concept_name] = lesson_id
        lesson_order_hint[lesson_id] = average_chunk_order
        lesson_titles[lesson_id] = title

    lesson_edges: dict[str, set[str]] = defaultdict(set)
    for rel in canonical_relationships:
        if rel["type"] != "PREREQUISITE_OF":
            continue
        source_lesson = concept_to_lesson.get(rel["from"])
        target_lesson = concept_to_lesson.get(rel["to"])
        if not source_lesson or not target_lesson or source_lesson == target_lesson:
            continue
        lesson_edges[source_lesson].add(target_lesson)

    ordered_ids = _topological_sort(
        [lesson["lesson_id"] for lesson in lessons],
        lesson_edges,
        lesson_order_hint,
        lesson_titles,
    )

    lesson_by_id = {lesson["lesson_id"]: lesson for lesson in lessons}
    ordered_lessons: list[dict[str, Any]] = []
    for lesson_id in ordered_ids:
        lesson = lesson_by_id[lesson_id]
        lesson["prerequisites"] = sorted(
            source
            for source, targets in lesson_edges.items()
            if lesson_id in targets
        )
        ordered_lessons.append(lesson)

    return {
        "course": course,
        "lesson_count": len(ordered_lessons),
        "lessons": ordered_lessons,
    }


def build_roadmap(course: str = "generated_course") -> dict[str, Any]:
    from graphdb.neo4j_client import get_concept_graph

    return build_roadmap_from_graph_data(get_concept_graph(), course=course)


def build_roadmap_for_lecture(lecture_id: str, course: str = "generated_course") -> dict[str, Any]:
    from graphdb.neo4j_client import get_concept_graph_by_lecture

    graph_data = get_concept_graph_by_lecture(lecture_id)
    roadmap = build_roadmap_from_graph_data(graph_data, course=course)
    roadmap["lecture_id"] = lecture_id
    return roadmap


if __name__ == "__main__":
    print(json.dumps(build_roadmap(), indent=2))
