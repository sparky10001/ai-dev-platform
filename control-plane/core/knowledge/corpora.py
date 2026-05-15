#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter

from core.knowledge.models import KnowledgeGraph


def build_relationship_corpus(
    graph: KnowledgeGraph,
) -> dict:
    rel_counter = Counter([e.relationship_type for e in graph.edges if isinstance(e.relationship_type, str) and e.relationship_type])

    return {
        'graph_id': graph.graph_id,
        'total_nodes': graph.total_nodes,
        'total_edges': graph.total_edges,
        'relationship_frequencies': {k: rel_counter[k] for k in sorted(rel_counter)},
        'metadata': dict(graph.metadata) if isinstance(graph.metadata, dict) else {},
    }
