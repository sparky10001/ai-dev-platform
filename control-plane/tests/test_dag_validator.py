#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path
import sys

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.dag.validator import dag_to_execution_order
from core.dag.validator import load_dag
from core.dag.validator import validate_dag


class DagValidatorTests(unittest.TestCase):

    def test_example_dag_loads(self):

        dag = load_dag(CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json')

        self.assertEqual(dag.dag_id, 'file_write_flow')

    def test_execution_order(self):

        dag = load_dag(CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json')

        self.assertEqual(dag_to_execution_order(dag), ['write', 'list'])

    def test_duplicate_node_ids_rejected(self):

        with self.assertRaises(ValueError):
            validate_dag(
                {
                    'dag_id': 'dup',
                    'version': '1.0.0',
                    'entry': 'a',
                    'nodes': [
                        {'id': 'a', 'type': 'noop'},
                        {'id': 'a', 'type': 'noop'},
                    ],
                }
            )

    def test_missing_entry_rejected(self):

        with self.assertRaises(ValueError):
            validate_dag(
                {
                    'dag_id': 'missing_entry',
                    'version': '1.0.0',
                    'entry': 'x',
                    'nodes': [
                        {'id': 'a', 'type': 'noop'},
                    ],
                }
            )

    def test_missing_dependency_rejected(self):

        with self.assertRaises(ValueError):
            validate_dag(
                {
                    'dag_id': 'missing_dep',
                    'version': '1.0.0',
                    'entry': 'a',
                    'nodes': [
                        {'id': 'a', 'type': 'noop', 'depends_on': ['z']},
                    ],
                }
            )

    def test_cycle_rejected(self):

        dag = validate_dag(
            {
                'dag_id': 'cycle',
                'version': '1.0.0',
                'entry': 'a',
                'nodes': [
                    {'id': 'a', 'type': 'noop', 'depends_on': ['b']},
                    {'id': 'b', 'type': 'noop', 'depends_on': ['a']},
                ],
            }
        )

        with self.assertRaises(ValueError):
            dag_to_execution_order(dag)

    def test_tool_node_without_tool_rejected(self):

        with self.assertRaises(ValueError):
            validate_dag(
                {
                    'dag_id': 'tool_missing',
                    'version': '1.0.0',
                    'entry': 'a',
                    'nodes': [
                        {'id': 'a', 'type': 'tool'},
                    ],
                }
            )

    def test_llm_node_without_prompt_rejected(self):

        with self.assertRaises(ValueError):
            validate_dag(
                {
                    'dag_id': 'llm_missing',
                    'version': '1.0.0',
                    'entry': 'a',
                    'nodes': [
                        {'id': 'a', 'type': 'llm'},
                    ],
                }
            )


if __name__ == '__main__':
    unittest.main()
