#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter

from core.graph_analytics.models import NodeMetric
from core.knowledge.models import KnowledgeGraph


def compute_relationship_frequencies(graph: KnowledgeGraph) -> dict[str, int]:
    counter = Counter(
        e.relationship_type
        for e in graph.edges
        if isinstance(e.relationship_type, str) and e.relationship_type
    )
    return {k: counter[k] for k in sorted(counter)}


def compute_node_metrics(graph: KnowledgeGraph) -> list[NodeMetric]:
    incoming: dict[str, int] = {n.node_id: 0 for n in graph.nodes}
    outgoing: dict[str, int] = {n.node_id: 0 for n in graph.nodes}
    rel_types: dict[str, set[str]] = {n.node_id: set() for n in graph.nodes}

    for edge in graph.edges:
        if edge.source_id in outgoing:
            outgoing[edge.source_id] += 1
            rel_types[edge.source_id].add(edge.relationship_type)
        if edge.target_id in incoming:
            incoming[edge.target_id] += 1
            rel_types[edge.target_id].add(edge.relationship_type)

    results: list[NodeMetric] = []
    for node_id in sorted(incoming):
        inc = incoming[node_id]
        out = outgoing[node_id]
        results.append(
            NodeMetric(
                node_id=node_id,
                degree=inc + out,
                incoming_edges=inc,
                outgoing_edges=out,
                relationship_types=sorted(rt for rt in rel_types[node_id] if isinstance(rt, str)),
                metadata={},
            )
        )
    return results


def find_isolated_nodes(graph: KnowledgeGraph) -> list[str]:
    metrics = compute_node_metrics(graph)
    return [m.node_id for m in metrics if m.degree == 0]


def compute_max_lineage_depth(graph: KnowledgeGraph) -> int:
    outgoing: dict[str, list[str]] = {n.node_id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.source_id in outgoing and edge.target_id in outgoing:
            outgoing[edge.source_id].append(edge.target_id)

    for node_id in outgoing:
        outgoing[node_id] = sorted(set(outgoing[node_id]))

    def max_depth_from(start: str) -> int:
        best = 0
        stack: list[tuple[str, int, tuple[str, ...]]] = [(start, 0, (start,))]
        while stack:
            node_id, depth, path = stack.pop()
            if depth > best:
                best = depth
            for nxt in outgoing.get(node_id, []):
                if nxt in path:
                    continue
                stack.append((nxt, depth + 1, path + (nxt,)))
        return best

    max_depth = 0
    for node_id in sorted(outgoing):
        d = max_depth_from(node_id)
        if d > max_depth:
            max_depth = d
    return max_depth
