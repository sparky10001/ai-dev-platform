#!/usr/bin/env python3
from __future__ import annotations

from core.graph_analytics.metrics import compute_max_lineage_depth
from core.graph_analytics.metrics import compute_node_metrics
from core.graph_analytics.metrics import compute_relationship_frequencies
from core.graph_analytics.metrics import find_isolated_nodes
from core.graph_analytics.models import GraphAnalyticsResult
from core.graph_analytics.models import GraphMetric
from core.knowledge.models import KnowledgeGraph


def analyze_knowledge_graph(
    graph: KnowledgeGraph,
    analytics_id: str = 'graph-analytics',
) -> GraphAnalyticsResult:
    relationship_frequencies = compute_relationship_frequencies(graph)
    node_metrics = compute_node_metrics(graph)
    isolated_nodes = find_isolated_nodes(graph)
    max_lineage_depth = compute_max_lineage_depth(graph)

    metrics = [
        GraphMetric(name='node_count', value=graph.total_nodes, metadata={}),
        GraphMetric(name='edge_count', value=graph.total_edges, metadata={}),
        GraphMetric(name='isolated_node_count', value=len(isolated_nodes), metadata={}),
        GraphMetric(name='relationship_type_count', value=len(relationship_frequencies), metadata={}),
        GraphMetric(name='max_lineage_depth', value=max_lineage_depth, metadata={}),
    ]

    return GraphAnalyticsResult(
        analytics_id=analytics_id,
        graph_id=graph.graph_id,
        total_nodes=graph.total_nodes,
        total_edges=graph.total_edges,
        relationship_frequencies=relationship_frequencies,
        isolated_nodes=sorted(isolated_nodes),
        max_lineage_depth=max_lineage_depth,
        node_metrics=node_metrics,
        metrics=metrics,
        metadata={},
    )
