#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.graph_analytics.analyzer import analyze_knowledge_graph
from core.graph_analytics.exporter import export_graph_analytics_json
from core.graph_analytics.exporter import export_graph_analytics_markdown
from core.graph_analytics.metrics import compute_max_lineage_depth
from core.graph_analytics.metrics import compute_node_metrics
from core.graph_analytics.metrics import compute_relationship_frequencies
from core.graph_analytics.metrics import find_isolated_nodes
from core.knowledge.models import KnowledgeEdge
from core.knowledge.models import KnowledgeGraph
from core.knowledge.models import KnowledgeNode


class OrchestrationGraphAnalyticsTests(unittest.TestCase):

    def _graph(self) -> KnowledgeGraph:
        nodes = [
            KnowledgeNode(node_id='n1', node_type='memory_record', planner_strategy='deterministic', policy_id='default'),
            KnowledgeNode(node_id='n2', node_type='memory_record', planner_strategy='deterministic', policy_id='default'),
            KnowledgeNode(node_id='n3', node_type='memory_record', planner_strategy='noop', policy_id='safe-readonly'),
            KnowledgeNode(node_id='n4', node_type='memory_record'),
        ]
        edges = [
            KnowledgeEdge(edge_id='e1', source_id='n1', target_id='n2', relationship_type='precedes'),
            KnowledgeEdge(edge_id='e2', source_id='n2', target_id='n3', relationship_type='precedes'),
            KnowledgeEdge(edge_id='e3', source_id='n1', target_id='n3', relationship_type='same_planner'),
        ]
        return KnowledgeGraph(
            graph_id='g1',
            created_at=1.0,
            total_nodes=len(nodes),
            total_edges=len(edges),
            nodes=nodes,
            edges=edges,
            metadata={},
        )

    def test_relationship_frequency_computation(self):
        freq = compute_relationship_frequencies(self._graph())
        self.assertEqual(freq['precedes'], 2)
        self.assertEqual(freq['same_planner'], 1)

    def test_node_metric_computation(self):
        metrics = compute_node_metrics(self._graph())
        ids = [m.node_id for m in metrics]
        self.assertEqual(ids, sorted(ids))
        m1 = next(m for m in metrics if m.node_id == 'n1')
        self.assertEqual(m1.outgoing_edges, 2)

    def test_isolated_node_detection(self):
        isolated = find_isolated_nodes(self._graph())
        self.assertIn('n4', isolated)

    def test_max_lineage_depth_computation(self):
        depth = compute_max_lineage_depth(self._graph())
        self.assertEqual(depth, 2)

    def test_cycle_safe_depth_handling(self):
        g = self._graph()
        g.edges.append(KnowledgeEdge(edge_id='e4', source_id='n3', target_id='n1', relationship_type='precedes'))
        depth = compute_max_lineage_depth(g)
        self.assertGreaterEqual(depth, 1)

    def test_analytics_result_generation(self):
        res = analyze_knowledge_graph(self._graph(), analytics_id='a1')
        self.assertEqual(res.analytics_id, 'a1')
        self.assertEqual(res.graph_id, 'g1')
        self.assertEqual(res.total_nodes, 4)

    def test_deterministic_metric_ordering(self):
        a = analyze_knowledge_graph(self._graph())
        b = analyze_knowledge_graph(self._graph())
        self.assertEqual([m.name for m in a.metrics], [m.name for m in b.metrics])

    def test_deterministic_node_metric_ordering(self):
        a = analyze_knowledge_graph(self._graph())
        b = analyze_knowledge_graph(self._graph())
        self.assertEqual([m.node_id for m in a.node_metrics], [m.node_id for m in b.node_metrics])

    def test_markdown_export_succeeds(self):
        res = analyze_knowledge_graph(self._graph())
        out = Path('/workspace/tmp/control-plane-graph-analytics')
        out.mkdir(parents=True, exist_ok=True)
        path = Path(export_graph_analytics_markdown(res, out / 'report.md'))
        self.assertTrue(path.exists())

    def test_json_export_succeeds(self):
        res = analyze_knowledge_graph(self._graph())
        out = Path('/workspace/tmp/control-plane-graph-analytics')
        out.mkdir(parents=True, exist_ok=True)
        path = Path(export_graph_analytics_json(res, out / 'report.json'))
        self.assertTrue(path.exists())

    def test_cli_analyze_knowledge_graph(self):
        p = subprocess.run(
            ['/workspace/ai-orchestrate', 'analyze-knowledge-graph', '/workspace/runs', '--max-records=25'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertIn('analytics_id', data)
        self.assertIn('node_metrics', data)

    def test_cli_export_graph_analytics(self):
        out = Path('/workspace/tmp/control-plane-graph-analytics-cli')
        out.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(
            ['/workspace/ai-orchestrate', 'export-graph-analytics', '/workspace/runs', str(out / 'report.md'), '--max-records=25'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertEqual(data.get('status'), 'success')
        self.assertTrue((out / 'report.md').exists())


if __name__ == '__main__':
    unittest.main()
