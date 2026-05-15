#!/usr/bin/env python3
from __future__ import annotations

from core.knowledge.models import KnowledgeEdge
from core.knowledge.models import KnowledgeGraph
from core.knowledge.models import KnowledgeNode


def build_relationship_index(
    graph: KnowledgeGraph,
) -> dict[str, list[KnowledgeEdge]]:
    index: dict[str, list[KnowledgeEdge]] = {n.node_id: [] for n in graph.nodes}
    for edge in sorted(graph.edges, key=lambda e: (e.source_id, e.relationship_type, e.target_id, e.edge_id)):
        index.setdefault(edge.source_id, []).append(edge)
    return index


def find_related_nodes(
    graph: KnowledgeGraph,
    node_id: str,
    relationship_type: str | None = None,
) -> list[KnowledgeNode]:
    idx = build_relationship_index(graph)
    node_map = {n.node_id: n for n in graph.nodes}

    related_ids: list[str] = []
    for edge in idx.get(node_id, []):
        if relationship_type and edge.relationship_type != relationship_type:
            continue
        if edge.target_id in node_map:
            related_ids.append(edge.target_id)

    return [node_map[nid] for nid in sorted(set(related_ids))]
