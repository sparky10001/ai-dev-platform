#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.orchestrator.models import OrchestrationRequest
from core.orchestrator.orchestrator import orchestrate_task
from runtime.replay import replay_trace


class OrchestratorTests(unittest.TestCase):

    def test_request_rejects_empty_task(self):
        with self.assertRaises(Exception):
            OrchestrationRequest(task='   ')

    def test_accepts_plain_string(self):
        result = orchestrate_task('list files')
        self.assertIn(result.status, {'success', 'error'})

    def test_accepts_dict(self):
        result = orchestrate_task({'task': 'list files'})
        self.assertIn(result.status, {'success', 'error'})

    def test_write_list_end_to_end(self):
        result = orchestrate_task("Create a file called hello.txt with content 'hi' and then list files")
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.dag_id, 'plan_write_list')
        self.assertEqual(result.execution_order, ['write', 'list'])
        self.assertIn('write', result.node_results)
        self.assertIn('list', result.node_results)
        entries = result.node_results['list'].get('output', {}).get('entries', [])
        self.assertTrue(any(isinstance(item, dict) and item.get('name') == 'hello.txt' for item in entries))

    def test_noop_strategy_succeeds(self):
        result = orchestrate_task({'task': 'anything', 'planner_strategy': 'noop'})
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.dag_id, 'plan_noop')

    def test_unsupported_task_falls_back_to_noop(self):
        result = orchestrate_task('do something unknown and advanced')
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.dag_id, 'plan_noop')

    def test_planner_unsupported_strategy_errors(self):
        result = orchestrate_task({'task': 'list files', 'planner_strategy': 'invalid'})
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.execution_status, 'skipped')

    def test_trace_false_has_no_run_metadata(self):
        result = orchestrate_task('list files')
        self.assertIsNone(result.run_id)
        self.assertIsNone(result.run_path)

    def test_trace_true_has_run_metadata(self):
        result = orchestrate_task({'task': 'list files', 'trace': True})
        self.assertEqual(result.status, 'success')
        self.assertIsNotNone(result.run_id)
        self.assertIsNotNone(result.run_path)

    def test_trace_true_replayable(self):
        result = orchestrate_task({'task': "Create a file called hello.txt with content 'hi' and then list files", 'trace': True})
        trace_path = Path(result.run_path) / 'trace.jsonl'
        self.assertTrue(trace_path.exists())
        replayed = replay_trace(trace_path)
        self.assertGreaterEqual(replayed.event_count, 1)

    def test_failed_execution_returns_error(self):
        result = orchestrate_task('read file DOES_NOT_EXIST_12345.txt')
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.execution_status, 'error')

    def test_planner_failure_skips_execution(self):
        result = orchestrate_task({'task': '', 'planner_strategy': 'deterministic'})
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.execution_status, 'skipped')


if __name__ == '__main__':
    unittest.main()
