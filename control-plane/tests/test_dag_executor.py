#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path
import sys

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path('/workspace')
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.dag.executor import execute_dag


class DagExecutorTests(unittest.TestCase):

    def _cleanup_file(self, rel_path: str) -> None:
        WORKSPACE_ROOT.joinpath(rel_path).unlink(missing_ok=True)

    def test_execute_example_dag_success(self):

        dag_path = CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json'
        expected_rel_path = 'tmp/file_write_flow_hello.txt'
        expected_name = Path(expected_rel_path).name
        self._cleanup_file(expected_rel_path)
        self.addCleanup(lambda: self._cleanup_file(expected_rel_path))

        result = execute_dag(dag_path)

        self.assertEqual(result.status, 'success')
        self.assertEqual(result.execution_order, ['write', 'list'])
        self.assertEqual(result.results['write'].status, 'success')
        self.assertEqual(result.results['list'].status, 'success')

        list_out = result.results['list'].output
        self.assertIsInstance(list_out, dict)
        entries = list_out.get('entries', [])
        self.assertTrue(any(item.get('name') == expected_name for item in entries if isinstance(item, dict)))

    def test_noop_node_succeeds(self):

        dag = {
            'dag_id': 'noop_only',
            'version': '1.0.0',
            'entry': 'n1',
            'nodes': [
                {'id': 'n1', 'type': 'noop'},
            ],
        }

        result = execute_dag(dag)

        self.assertEqual(result.status, 'success')
        self.assertEqual(result.results['n1'].status, 'success')

    def test_llm_node_returns_error(self):

        dag = {
            'dag_id': 'llm_only',
            'version': '1.0.0',
            'entry': 'n1',
            'nodes': [
                {'id': 'n1', 'type': 'llm', 'prompt': 'Hello'},
            ],
        }

        result = execute_dag(dag)

        self.assertEqual(result.status, 'error')
        self.assertEqual(result.results['n1'].status, 'error')
        self.assertIn('not implemented', result.results['n1'].error)

    def test_missing_tool_returns_error(self):

        dag = {
            'dag_id': 'missing_tool',
            'version': '1.0.0',
            'entry': 'bad',
            'nodes': [
                {'id': 'bad', 'type': 'tool', 'tool': 'no_such_tool', 'args': {}},
            ],
        }

        result = execute_dag(dag)

        self.assertEqual(result.status, 'error')
        self.assertEqual(result.results['bad'].status, 'error')
        self.assertIn('unknown tool', result.results['bad'].error)

    def test_missing_required_args_returns_error(self):

        dag = {
            'dag_id': 'missing_args',
            'version': '1.0.0',
            'entry': 'w',
            'nodes': [
                {'id': 'w', 'type': 'tool', 'tool': 'write_file', 'args': {'path': 'x.txt'}},
            ],
        }

        result = execute_dag(dag)

        self.assertEqual(result.status, 'error')
        self.assertEqual(result.results['w'].status, 'error')
        self.assertIn('missing required', result.results['w'].error)

    def test_failed_node_stops_execution(self):

        dag = {
            'dag_id': 'stop_on_error',
            'version': '1.0.0',
            'entry': 'bad',
            'nodes': [
                {'id': 'bad', 'type': 'tool', 'tool': 'no_such_tool', 'args': {}},
                {'id': 'later', 'type': 'noop', 'depends_on': ['bad']},
            ],
        }

        result = execute_dag(dag)

        self.assertEqual(result.status, 'error')
        self.assertEqual(result.results['bad'].status, 'error')
        self.assertEqual(result.results['later'].status, 'skipped')

    def test_invalid_tool_json_output_handling(self):

        import core.dag.executor as executor

        original = executor._run_tool_command

        class FakeProc:
            returncode = 0
            stdout = 'not-json'
            stderr = ''

        def fake_run(*_args, **_kwargs):
            return FakeProc()

        try:
            executor._run_tool_command = fake_run

            dag = {
                'dag_id': 'bad_json',
                'version': '1.0.0',
                'entry': 'r',
                'nodes': [
                    {'id': 'r', 'type': 'tool', 'tool': 'read_file', 'args': {'path': 'README.md'}},
                ],
            }

            result = execute_dag(dag)

            self.assertEqual(result.status, 'error')
            self.assertEqual(result.results['r'].status, 'error')
            self.assertIn('invalid JSON', result.results['r'].error)

        finally:
            executor._run_tool_command = original


if __name__ == '__main__':
    unittest.main()
