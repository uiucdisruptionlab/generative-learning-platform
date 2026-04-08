from __future__ import annotations

import json
import os
import re
from collections import defaultdict, deque
from typing import Any


STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}

COURSE_SOURCE_PREFIXES = {
    "accounting": ("ALec",),
    "finance": ("FLec",),
    "financing": ("FLec",),
    "python": ("PLec",),
    "deep_learning": ("DL_", "DLlec", "DL_lec"),
    "dl": ("DL_", "DLlec", "DL_lec"),
}

LATE_TOPIC_KEYWORDS = {
    "final",
    "review",
    "wrap up",
    "wrap-up",
    "summary",
    "exam",
    "midterm",
    "practice exam",
    "administration",
}


def _course_prefixes(course: str) -> tuple[str, ...]:
    normalized = course.strip().lower()
    return COURSE_SOURCE_PREFIXES.get(normalized, ())


def _filter_graph_data_for_course(graph_data: dict[str, Any], course: str) -> dict[str, Any]:
    if not course or course == "generated_course":
        return graph_data

    prefixes = _course_prefixes(course)
    normalized_course = course.strip().lower()

    chunk_links = graph_data.get("chunk_links", [])
    filtered_chunk_links = []
    for link in chunk_links:
        course_id = str(link.get("course_id") or "").strip().lower()
        lecture_id = str(link.get("lecture_id") or "")
        chunk_id = str(link.get("chunk_id") or "")
        chunk_source = str(link.get("chunk_source") or "")
        source_candidates = [chunk_source, lecture_id, chunk_id, course_id]

        if course_id and course_id == normalized_course:
            filtered_chunk_links.append(link)
            continue
        if any(prefix and candidate.startswith(prefix) for candidate in source_candidates for prefix in prefixes):
            filtered_chunk_links.append(link)

    if not filtered_chunk_links and not prefixes:
        return graph_data

    if not filtered_chunk_links:
        return {
            "concepts": [],
            "relationships": [],
            "chunk_links": [],
        }

    valid_concepts = {link["concept_name"] for link in filtered_chunk_links}
    filtered_relationships = [
        rel for rel in graph_data.get("relationships", [])
        if rel["from"] in valid_concepts and rel["to"] in valid_concepts
    ]
    filtered_concepts = [
        concept for concept in graph_data.get("concepts", [])
        if concept["name"] in valid_concepts
    ]

    return {
        "concepts": filtered_concepts,
        "relationships": filtered_relationships,
        "chunk_links": filtered_chunk_links,
    }


def _chunk_position_from_id(chunk_id: str) -> float | None:
    match = re.search(r"_p(?P<page>\d+)_c(?P<chunk>\d+)", chunk_id)
    if not match:
        return None
    page = int(match.group("page"))
    chunk = int(match.group("chunk"))
    return float(page) + (chunk / 1000.0)


def _looks_like_late_topic(title: str, concept_names: list[str]) -> bool:
    haystacks = [title.lower(), *[name.lower() for name in concept_names]]
    return any(keyword in haystack for haystack in haystacks for keyword in LATE_TOPIC_KEYWORDS)


def _canonicalize_name(name: str) -> str:
    lowered = name.lower().strip()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    tokens = [token for token in lowered.split() if token]
    normalized_tokens: list[str] = []
    for token in tokens:
        if len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        normalized_tokens.append(token)
    return " ".join(normalized_tokens)


def _tokenize(name: str) -> set[str]:
    return {
        token
        for token in _canonicalize_name(name).split()
        if token and token not in STOPWORDS
    }


def _name_similarity(a: str, b: str) -> float:
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def _dedupe_concept_names(concept_names: set[str], concept_chunk_orders: dict[str, list[int]]) -> dict[str, str]:
    grouped_by_canonical: dict[str, list[str]] = defaultdict(list)
    for name in concept_names:
        grouped_by_canonical[_canonicalize_name(name)].append(name)

    alias_to_canonical: dict[str, str] = {}
    canonical_names: list[str] = []

    for _, names in grouped_by_canonical.items():
        representative = sorted(
            names,
            key=lambda name: (
                min(concept_chunk_orders.get(name, [10**9])),
                len(name),
                name.lower(),
            ),
        )[0]
        for name in names:
            alias_to_canonical[name] = representative
        canonical_names.append(representative)

    for index, name in enumerate(sorted(canonical_names)):
        if name not in alias_to_canonical:
            alias_to_canonical[name] = name
        for other in canonical_names[index + 1:]:
            if other == name:
                continue
            if _name_similarity(name, other) < 0.8:
                continue
            winner = sorted(
                [name, other],
                key=lambda candidate: (
                    min(concept_chunk_orders.get(candidate, [10**9])),
                    len(candidate),
                    candidate.lower(),
                ),
            )[0]
            loser = other if winner == name else name
            for original, canonical in list(alias_to_canonical.items()):
                if canonical == loser or original == loser:
                    alias_to_canonical[original] = winner

    return alias_to_canonical


def _build_undirected_neighbors(relationships: list[dict[str, str]]) -> dict[str, set[str]]:
    neighbors: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        rel_type = rel["type"]
        if rel_type not in {"PART_OF", "RELATED_TO"}:
            continue

        source = rel["from"]
        target = rel["to"]
        if source == target:
            continue

        neighbors[source].add(target)
        neighbors[target].add(source)
    return neighbors


def _concept_importance_scores(
    concepts: set[str],
    relationships: list[dict[str, str]],
    concept_chunk_orders: dict[str, list[int]],
) -> dict[str, float]:
    appearance_counts = {name: len(concept_chunk_orders.get(name, [])) for name in concepts}
    incoming_prereqs: dict[str, int] = defaultdict(int)
    outgoing_prereqs: dict[str, int] = defaultdict(int)
    relation_counts: dict[str, int] = defaultdict(int)

    for rel in relationships:
        source = rel["from"]
        target = rel["to"]
        relation_counts[source] += 1
        relation_counts[target] += 1
        if rel["type"] == "PREREQUISITE_OF":
            outgoing_prereqs[source] += 1
            incoming_prereqs[target] += 1

    scores: dict[str, float] = {}
    for name in concepts:
        order_hint = min(concept_chunk_orders.get(name, [10]))
        early_bonus = max(0.0, 6.0 - float(order_hint))
        scores[name] = (
            3.0 * appearance_counts.get(name, 0)
            + 2.5 * outgoing_prereqs.get(name, 0)
            + 1.5 * relation_counts.get(name, 0)
            + 0.5 * incoming_prereqs.get(name, 0)
            + early_bonus
        )
    return scores


def _lecture_partitions(chunk_links: list[dict[str, Any]]) -> dict[str, set[str]]:
    lecture_to_concepts: dict[str, set[str]] = defaultdict(set)
    for link in chunk_links:
        lecture_id = str(link.get("lecture_id") or "unknown_lecture")
        lecture_to_concepts[lecture_id].add(link["concept_name"])
    return lecture_to_concepts


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


def _initial_lesson_candidates(
    lecture_to_concepts: dict[str, set[str]],
    neighbors: dict[str, set[str]],
) -> list[list[str]]:
    lesson_candidates: list[list[str]] = []
    for _, concepts in sorted(lecture_to_concepts.items()):
        components = _connected_components(concepts, neighbors)
        lesson_candidates.extend(component for component in components if component)
    return lesson_candidates


def _merge_small_components(
    components: list[list[str]],
    neighbors: dict[str, set[str]],
    importance: dict[str, float],
) -> list[list[str]]:
    if len(components) <= 1:
        return components

    merged = [set(component) for component in components]
    changed = True
    while changed:
        changed = False
        for index, component in enumerate(list(merged)):
            component_score = sum(importance.get(name, 0.0) for name in component)
            if len(component) > 1 and component_score >= 8.0:
                continue

            best_match_index = None
            best_match_score = -1.0
            for other_index, other in enumerate(merged):
                if other_index == index:
                    continue
                bridge_score = sum(
                    1.0
                    for name in component
                    for neighbor in neighbors.get(name, set())
                    if neighbor in other
                )
                if bridge_score > best_match_score:
                    best_match_index = other_index
                    best_match_score = bridge_score

            if best_match_index is None:
                continue

            merged[best_match_index].update(component)
            merged.pop(index)
            changed = True
            break

    return [sorted(component) for component in merged]


def _dedupe_lessons(
    lesson_components: list[list[str]],
    importance: dict[str, float],
) -> list[list[str]]:
    deduped: list[set[str]] = []
    for component in sorted(lesson_components, key=lambda names: (-len(names), sorted(names))):
        component_set = set(component)
        duplicate_index = None
        for index, existing in enumerate(deduped):
            overlap = len(component_set & existing)
            union = len(component_set | existing)
            if union and overlap / union >= 0.55:
                duplicate_index = index
                break

        if duplicate_index is None:
            deduped.append(component_set)
            continue

        current_score = sum(importance.get(name, 0.0) for name in component_set)
        existing_score = sum(importance.get(name, 0.0) for name in deduped[duplicate_index])
        if current_score > existing_score:
            deduped[duplicate_index] = component_set | deduped[duplicate_index]
        else:
            deduped[duplicate_index].update(component_set)

    return [sorted(component) for component in deduped]


def _select_lesson_title(component: list[str], importance: dict[str, float], concept_chunk_orders: dict[str, list[int]]) -> str:
    ranked = sorted(
        component,
        key=lambda name: (
            -importance.get(name, 0.0),
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

    ready = [node_id for node_id in node_ids if indegree[node_id] == 0]
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


def _build_rough_roadmap(graph_data: dict[str, Any], course: str) -> dict[str, Any]:
    concepts = graph_data.get("concepts", [])
    relationships = graph_data.get("relationships", [])
    chunk_links = graph_data.get("chunk_links", [])

    concept_names = {concept["name"] for concept in concepts}
    concept_descriptions = {concept["name"]: concept.get("description", "") for concept in concepts}

    concept_chunk_orders: dict[str, list[int]] = defaultdict(list)
    concept_chunk_ids: dict[str, set[str]] = defaultdict(set)
    concept_lecture_ids: dict[str, set[str]] = defaultdict(set)
    for link in chunk_links:
        concept_name = link["concept_name"]
        concept_chunk_orders[concept_name].append(int(link.get("chunk_order") or 0))
        concept_chunk_ids[concept_name].add(link["chunk_id"])
        lecture_id = link.get("lecture_id")
        if lecture_id:
            concept_lecture_ids[concept_name].add(str(lecture_id))

    alias_to_canonical = _dedupe_concept_names(concept_names, concept_chunk_orders)
    canonical_concepts = set(alias_to_canonical.values())

    canonical_descriptions: dict[str, str] = {}
    canonical_chunk_orders: dict[str, list[int]] = defaultdict(list)
    canonical_chunk_ids: dict[str, set[str]] = defaultdict(set)
    canonical_lecture_ids: dict[str, set[str]] = defaultdict(set)
    for original_name, canonical_name in alias_to_canonical.items():
        if canonical_name not in canonical_descriptions or (
            concept_descriptions.get(original_name) and not canonical_descriptions[canonical_name]
        ):
            canonical_descriptions[canonical_name] = concept_descriptions.get(original_name, "")
        canonical_chunk_orders[canonical_name].extend(concept_chunk_orders.get(original_name, []))
        canonical_chunk_ids[canonical_name].update(concept_chunk_ids.get(original_name, set()))
        canonical_lecture_ids[canonical_name].update(concept_lecture_ids.get(original_name, set()))

    canonical_relationships: list[dict[str, str]] = []
    seen_relationships: set[tuple[str, str, str]] = set()
    for rel in relationships:
        source = alias_to_canonical.get(rel["from"])
        target = alias_to_canonical.get(rel["to"])
        rel_type = rel["type"]
        if not source or not target or source == target:
            continue
        key = (source, target, rel_type)
        if key in seen_relationships:
            continue
        seen_relationships.add(key)
        canonical_relationships.append({"from": source, "to": target, "type": rel_type})

    canonical_chunk_links = []
    for link in chunk_links:
        canonical_name = alias_to_canonical.get(link["concept_name"])
        if not canonical_name:
            continue
        canonical_chunk_links.append(
            {
                "chunk_id": link["chunk_id"],
                "lecture_id": link.get("lecture_id"),
                "course_id": link.get("course_id"),
                "chunk_order": int(link.get("chunk_order") or 0),
                "concept_name": canonical_name,
            }
        )

    neighbors = _build_undirected_neighbors(canonical_relationships)
    importance = _concept_importance_scores(canonical_concepts, canonical_relationships, canonical_chunk_orders)
    lecture_to_concepts = _lecture_partitions(canonical_chunk_links)

    lesson_components = _initial_lesson_candidates(lecture_to_concepts, neighbors)
    if not lesson_components:
        lesson_components = [[name] for name in sorted(canonical_concepts)]

    lesson_components = _merge_small_components(lesson_components, neighbors, importance)
    lesson_components = _dedupe_lessons(lesson_components, importance)

    concept_to_lesson: dict[str, str] = {}
    lessons: list[dict[str, Any]] = []
    lesson_order_hint: dict[str, float] = {}
    lesson_titles: dict[str, str] = {}

    for index, component in enumerate(sorted(lesson_components, key=lambda names: min(canonical_chunk_orders.get(name, [10**9])[0] for name in names)), start=1):
        lesson_id = f"lesson_{index:03d}"
        title = _select_lesson_title(component, importance, canonical_chunk_orders)
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
        chunk_positions = [
            position
            for chunk_id in chunk_ids
            for position in [_chunk_position_from_id(chunk_id)]
            if position is not None
        ]
        lecture_ids = sorted({
            lecture_id
            for concept_name in component
            for lecture_id in canonical_lecture_ids.get(concept_name, set())
        })
        late_topic_penalty = 10_000.0 if _looks_like_late_topic(title, component) else 0.0

        lesson = {
            "lesson_id": lesson_id,
            "title": title,
            "importance_score": round(sum(importance.get(name, 0.0) for name in component), 2),
            "concepts": [
                {
                    "name": concept_name,
                    "description": canonical_descriptions.get(concept_name, ""),
                    "importance_score": round(importance.get(concept_name, 0.0), 2),
                }
                for concept_name in sorted(component, key=lambda name: (-importance.get(name, 0.0), name.lower()))
            ],
            "chunk_ids": chunk_ids,
            "lecture_ids": lecture_ids,
            "prerequisites": [],
        }
        lessons.append(lesson)

        for concept_name in component:
            concept_to_lesson[concept_name] = lesson_id
        lesson_order_hint[lesson_id] = (
            (sum(chunk_positions) / len(chunk_positions)) if chunk_positions else average_chunk_order
        ) + late_topic_penalty
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


def build_roadmap_from_graph_data(
    graph_data: dict[str, Any],
    course: str = "generated_course",
    refine_with_llm: bool = False,
) -> dict[str, Any]:
    graph_data = _filter_graph_data_for_course(graph_data, course)
    roadmap = _build_rough_roadmap(graph_data, course=course)

    if refine_with_llm:
        from graphdb.roadmap_refiner import refine_roadmap_with_llm

        return refine_roadmap_with_llm(roadmap)

    return roadmap


def build_roadmap(course: str = "generated_course", refine_with_llm: bool | None = None) -> dict[str, Any]:
    from graphdb.neo4j_client import get_concept_graph, get_concept_graph_by_course

    if refine_with_llm is None:
        refine_with_llm = os.getenv("ENABLE_ROADMAP_REFINEMENT", "false").lower() == "true"

    if course and course != "generated_course":
        graph_data = get_concept_graph_by_course(course)
    else:
        graph_data = get_concept_graph()

    return build_roadmap_from_graph_data(graph_data, course=course, refine_with_llm=refine_with_llm)


def build_roadmap_for_lecture(
    lecture_id: str,
    course: str = "generated_course",
    refine_with_llm: bool | None = None,
) -> dict[str, Any]:
    from graphdb.neo4j_client import get_concept_graph_by_lecture

    if refine_with_llm is None:
        refine_with_llm = os.getenv("ENABLE_ROADMAP_REFINEMENT", "false").lower() == "true"

    graph_data = get_concept_graph_by_lecture(lecture_id)
    roadmap = build_roadmap_from_graph_data(graph_data, course=course, refine_with_llm=refine_with_llm)
    roadmap["lecture_id"] = lecture_id
    return roadmap


if __name__ == "__main__":
    print(json.dumps(build_roadmap(), indent=2))
