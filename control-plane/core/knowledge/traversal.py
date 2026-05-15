#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter

from core.knowledge.models import KnowledgeGraph
from core.knowledge.models import LineageResult


def compute_lineage(
    graph: KnowledgeGraph,
    root_node_id: str,
) -> LineageResult:
    outgoing: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}

    for edge in sorted(graph.edges, key=lambda e: (e.source_id, e.target_id, e.relationship_type)):
        outgoing.setdefault(edge.source_id, []).append(edge.target_id)
        incoming.setdefault(edge.target_id, []).append(edge.source_id)

    def walk(start: str, mapping: dict[str, list[str]]) -> list[str]:
        seen: set[str] = set()
        stack: list[str] = sorted(mapping.get(start, []), reverse=True)
        while stack:
            cur = stack.pop()
            if cur in seen or cur == start:
                continue
            seen.add(cur)
            nxt = sorted(mapping.get(cur, []), reverse=True)
            stack.extend(nxt)
        return sorted(seen)

    ancestors = walk(root_node_id, incoming)
    descendants = walk(root_node_id, outgoing)

    return LineageResult(
        lineage_id=f'lineage_{root_node_id}',
        root_node_id=root_node_id,
        ancestor_ids=ancestors,
        descendant_ids=descendants,
        metadata={},
    )


def summarize_knowledge_graph(
    graph: KnowledgeGraph,
) -> dict:
    planner_freq = Counter([n.planner_strategy for n in graph.nodes if isinstance(n.planner_strategy, str) and n.planner_strategy])
    policy_freq = Counter([n.policy_id for n in graph.nodes if isinstance(n.policy_id, str) and n.policy_id])
    rel_freq = Counter([e.relationship_type for e in graph.edges if isinstance(e.relationship_type, str) and e.relationship_type])

    return {
        'total_nodes': graph.total_nodes,
        'total_edges': graph.total_edges,
        'planner_frequencies': {k: planner_freq[k] for k in sorted(planner_freq)},
        'policy_frequencies': {k: policy_freq[k] for k in sorted(policy_freq)},
        'relationship_frequencies': {k: rel_freq[k] for k in sorted(rel_freq)},
    }
