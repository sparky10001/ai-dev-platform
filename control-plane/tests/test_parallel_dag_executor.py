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

from core.dag.parallel_executor import dag_to_execution_batches
from core.dag.parallel_executor import execute_dag_parallel
from core.dag.validator import validate_dag


class ParallelDagExecutorTests(unittest.TestCase):

    def test_batch_generation(self):
        dag = validate_dag(
            {
                'dag_id': 'batches',
                'version': '1.0.0',
                'entry': 'A',
                'nodes': [
                    {'id': 'A', 'type': 'noop'},
                    {'id': 'B', 'type': 'noop'},
                    {'id': 'C', 'type': 'noop', 'depends_on': ['A', 'B']},
                    {'id': 'D', 'type': 'noop', 'depends_on': ['C']},
                ],
            }
        )
        batches = dag_to_execution_batches(dag)
        self.assertEqual(batches, [['A', 'B'], ['C'], ['D']])

    def test_successful_parallel_noop(self):
        dag = {
            'dag_id': 'parallel_noop',
            'version': '1.0.0',
            'entry': 'a',
            'nodes': [
                {'id': 'a', 'type': 'noop'},
                {'id': 'b', 'type': 'noop'},
                {'id': 'c', 'type': 'noop', 'depends_on': ['a', 'b']},
            ],
        }
        result = execute_dag_parallel(dag, max_workers=4)
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.execution_order, ['a', 'b', 'c'])

    def test_failure_stops_downstream(self):
        dag = {
            'dag_id': 'stop',
            'version': '1.0.0',
            'entry': 'x',
            'nodes': [
                {'id': 'x', 'type': 'tool', 'tool': 'no_such_tool', 'args': {}},
                {'id': 'y', 'type': 'noop', 'depends_on': ['x']},
            ],
        }
        result = execute_dag_parallel(dag, max_workers=2)
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.node_results['x']['status'], 'error')
        self.assertEqual(result.node_results['y']['status'], 'skipped')

    def test_max_workers_validation(self):
        with self.assertRaises(ValueError):
            execute_dag_parallel({'dag_id': 'x', 'version': '1.0.0', 'entry': 'a', 'nodes': [{'id': 'a', 'type': 'noop'}]}, max_workers=0)

    def test_llm_error(self):
        dag = {
            'dag_id': 'llm_parallel',
            'version': '1.0.0',
            'entry': 'a',
            'nodes': [{'id': 'a', 'type': 'llm', 'prompt': 'hi'}],
        }
        result = execute_dag_parallel(dag)
        self.assertEqual(result.status, 'error')
        self.assertIn('not implemented', result.node_results['a']['error'])

    def test_trace_true_deterministic_error(self):
        dag = {
            'dag_id': 'trace_parallel',
            'version': '1.0.0',
            'entry': 'a',
            'nodes': [{'id': 'a', 'type': 'noop'}],
        }
        result = execute_dag_parallel(dag, trace=True)
        self.assertEqual(result.status, 'error')
        self.assertIn('not implemented', result.metadata.get('error', ''))

    def test_cli_execute_dag_parallel(self):
        dag_path = CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json'
        proc = subprocess.run(
            ['/workspace/ai-orchestrate', 'execute-dag', str(dag_path), '--parallel', '--max-workers=2'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('execution_mode'), 'parallel')


if __name__ == '__main__':
    unittest.main()
