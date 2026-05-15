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

from core.evals.evaluator import evaluate_replay
from core.knowledge.corpora import build_relationship_corpus
from core.knowledge.exporter import export_knowledge_graph_json
from core.knowledge.exporter import export_knowledge_graph_markdown
from core.knowledge.exporter import export_lineage_markdown
from core.knowledge.lineage import build_knowledge_graph
from core.knowledge.lineage import memory_record_to_node
from core.knowledge.relationships import build_relationship_index
from core.knowledge.relationships import find_related_nodes
from core.knowledge.traversal import compute_lineage
from core.knowledge.traversal import summarize_knowledge_graph
from core.memory.history import replay_to_memory_record
from core.orchestrator.orchestrator import orchestrate_task
from core.replay.loader import load_orchestration_trace


class OrchestrationKnowledgeGraphTests(unittest.TestCase):

    def _records(self):
        outputs = [
            orchestrate_task({'task': 'list files', 'trace': True}),
            orchestrate_task({'task': "Create a file called hello.txt with content 'hi' and then list files", 'trace': True}),
            orchestrate_task({'task': 'list files', 'trace': True}),
        ]

        records = []
        for output in outputs:
            replay = load_orchestration_trace(output.run_path)
            evaluation = evaluate_replay(replay)
            records.append(replay_to_memory_record(replay, evaluation))
        return records

    def test_knowledge_node_generation(self):
        node = memory_record_to_node(self._records()[0])
        self.assertEqual(node.node_type, 'memory_record')

    def test_deterministic_graph_construction(self):
        records = self._records()
        graph_a = build_knowledge_graph(records, graph_id='graph_test')
        graph_b = build_knowledge_graph(records, graph_id='graph_test')
        self.assertEqual([n.node_id for n in graph_a.nodes], [n.node_id for n in graph_b.nodes])
        self.assertEqual([n.run_id for n in graph_a.nodes], [n.run_id for n in graph_b.nodes])

    def test_deterministic_edge_ordering(self):
        records = self._records()
        graph_a = build_knowledge_graph(records, graph_id='graph_test')
        graph_b = build_knowledge_graph(records, graph_id='graph_test')
        self.assertEqual([e.edge_id for e in graph_a.edges], [e.edge_id for e in graph_b.edges])

    def test_relationship_index_generation(self):
        graph = build_knowledge_graph(self._records())
        rel_index = build_relationship_index(graph)
        self.assertEqual(sorted(rel_index.keys()), sorted([n.node_id for n in graph.nodes]))

    def test_related_node_lookup(self):
        graph = build_knowledge_graph(self._records())
        root_id = graph.nodes[0].node_id
        related = find_related_nodes(graph, root_id)
        self.assertIsInstance(related, list)

    def test_lineage_traversal(self):
        graph = build_knowledge_graph(self._records())
        root_id = graph.nodes[0].node_id
        lineage = compute_lineage(graph, root_id)
        self.assertEqual(lineage.root_node_id, root_id)
        self.assertIsInstance(lineage.ancestor_ids, list)
        self.assertIsInstance(lineage.descendant_ids, list)

    def test_cycle_safe_traversal(self):
        graph = build_knowledge_graph(self._records())
        if len(graph.nodes) < 2:
            self.skipTest('requires at least two nodes')

        graph.edges.append(
            type(graph.edges[0])(
                edge_id='edge_cycle',
                source_id=graph.nodes[-1].node_id,
                target_id=graph.nodes[0].node_id,
                relationship_type='precedes',
                metadata={},
            )
        )

        lineage = compute_lineage(graph, graph.nodes[0].node_id)
        self.assertIn(graph.nodes[-1].node_id, lineage.ancestor_ids)

    def test_graph_summary_aggregation(self):
        graph = build_knowledge_graph(self._records())
        summary = summarize_knowledge_graph(graph)
        self.assertEqual(summary['total_nodes'], graph.total_nodes)
        self.assertEqual(summary['total_edges'], graph.total_edges)

    def test_relationship_corpus_generation(self):
        graph = build_knowledge_graph(self._records())
        corpus = build_relationship_corpus(graph)
        self.assertEqual(corpus['total_nodes'], graph.total_nodes)
        self.assertEqual(corpus['total_edges'], graph.total_edges)

    def test_export_markdown_json_and_lineage(self):
        graph = build_knowledge_graph(self._records(), graph_id='graph_export')
        lineage = compute_lineage(graph, graph.nodes[0].node_id)

        out_dir = Path('/workspace/tmp/control-plane-knowledge')
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = Path(export_knowledge_graph_json(graph, out_dir / 'graph.json'))
        markdown_path = Path(export_knowledge_graph_markdown(graph, out_dir / 'graph.md'))
        lineage_path = Path(export_lineage_markdown(lineage, out_dir / 'lineage.md'))

        self.assertTrue(json_path.exists())
        self.assertTrue(markdown_path.exists())
        self.assertTrue(lineage_path.exists())

    def test_deterministic_traversal_ordering(self):
        graph = build_knowledge_graph(self._records())
        root_id = graph.nodes[0].node_id
        lineage_a = compute_lineage(graph, root_id)
        lineage_b = compute_lineage(graph, root_id)
        self.assertEqual(lineage_a.ancestor_ids, lineage_b.ancestor_ids)
        self.assertEqual(lineage_a.descendant_ids, lineage_b.descendant_ids)

    def test_cli_build_knowledge_graph(self):
        proc = subprocess.run(
            ['/workspace/ai-orchestrate', 'build-knowledge-graph', '/workspace/runs'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn('graph_id', payload)
        self.assertIn('nodes', payload)

    def test_cli_compute_lineage(self):
        graph_proc = subprocess.run(
            ['/workspace/ai-orchestrate', 'build-knowledge-graph', '/workspace/runs'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(graph_proc.returncode, 0)
        graph = json.loads(graph_proc.stdout)
        if not graph.get('nodes'):
            self.skipTest('no nodes available for lineage')
        node_id = graph['nodes'][0]['node_id']

        proc = subprocess.run(
            ['/workspace/ai-orchestrate', 'compute-lineage', '/workspace/runs', node_id],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('root_node_id'), node_id)

    def test_cli_export_knowledge_graph(self):
        out_dir = Path('/workspace/tmp/control-plane-knowledge-cli')
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'graph.md'

        proc = subprocess.run(
            ['/workspace/ai-orchestrate', 'export-knowledge-graph', '/workspace/runs', str(out_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')
        self.assertTrue(out_path.exists())


if __name__ == '__main__':
    unittest.main()
