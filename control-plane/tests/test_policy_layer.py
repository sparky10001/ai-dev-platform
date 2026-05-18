#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.dag.validator import load_dag
from core.dag.validator import validate_dag
from core.orchestrator.orchestrator import orchestrate_task
from core.policy.defaults import DEFAULT_POLICY
from core.policy.defaults import SAFE_READONLY_POLICY
from core.policy.models import PolicySpec
from core.policy.validator import validate_dag_against_policy
from core.policy.validator import validate_policy


class PolicyLayerTests(unittest.TestCase):

    def test_validate_policy_none_returns_default(self):
        policy = validate_policy(None)
        self.assertEqual(policy.policy_id, DEFAULT_POLICY.policy_id)

    def test_invalid_max_nodes_rejected(self):
        with self.assertRaises(Exception):
            PolicySpec(policy_id='x', max_nodes=0)

    def test_default_policy_allows_example_dag(self):
        dag = load_dag(CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json')
        result = validate_dag_against_policy(dag, DEFAULT_POLICY)
        self.assertEqual(result.status, 'success')

    def test_safe_readonly_rejects_write_file(self):
        dag = load_dag(CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json')
        result = validate_dag_against_policy(dag, SAFE_READONLY_POLICY)
        self.assertEqual(result.status, 'error')
        codes = [v.code for v in result.violations]
        self.assertIn('tool_denied', codes)

    def test_safe_readonly_allows_list_files(self):
        dag = validate_dag({
            'dag_id': 'list_only',
            'version': '1.0',
            'entry': 'list',
            'nodes': [{'id': 'list', 'type': 'tool', 'tool': 'list_files', 'args': {'path': '.'}}],
        })
        result = validate_dag_against_policy(dag, SAFE_READONLY_POLICY)
        self.assertEqual(result.status, 'success')

    def test_llm_rejected_by_default(self):
        dag = validate_dag({
            'dag_id': 'llm',
            'version': '1.0',
            'entry': 'n1',
            'nodes': [{'id': 'n1', 'type': 'llm', 'prompt': 'hi'}],
        })
        result = validate_dag_against_policy(dag, DEFAULT_POLICY)
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.violations[0].code, 'llm_nodes_not_allowed')

    def test_max_nodes_exceeded(self):
        dag = validate_dag({
            'dag_id': 'many',
            'version': '1.0',
            'entry': 'n0',
            'nodes': [{'id': f'n{i}', 'type': 'noop'} for i in range(3)],
        })
        result = validate_dag_against_policy(dag, {'policy_id': 'p', 'max_nodes': 2})
        self.assertEqual(result.status, 'error')
        self.assertIn('max_nodes_exceeded', [v.code for v in result.violations])

    def test_max_dependencies_exceeded(self):
        dag = validate_dag({
            'dag_id': 'deps',
            'version': '1.0',
            'entry': 'n0',
            'nodes': [
                {'id': 'n0', 'type': 'noop'},
                {'id': 'n1', 'type': 'noop'},
                {'id': 'n2', 'type': 'noop'},
                {'id': 'n3', 'type': 'noop', 'depends_on': ['n0', 'n1', 'n2']},
            ],
        })
        result = validate_dag_against_policy(dag, {'policy_id': 'p', 'max_dependencies_per_node': 2})
        self.assertEqual(result.status, 'error')
        self.assertIn('max_dependencies_exceeded', [v.code for v in result.violations])

    def test_deny_overrides_allow(self):
        dag = validate_dag({
            'dag_id': 'deny',
            'version': '1.0',
            'entry': 'w',
            'nodes': [{'id': 'w', 'type': 'tool', 'tool': 'write_file', 'args': {'path': '/workspace/a.txt', 'content': 'x'}}],
        })
        result = validate_dag_against_policy(dag, {
            'policy_id': 'p',
            'allow_tools': ['write_file'],
            'deny_tools': ['write_file'],
        })
        self.assertEqual(result.status, 'error')
        self.assertIn('tool_denied', [v.code for v in result.violations])

    def test_traversal_path_rejected(self):
        dag = validate_dag({
            'dag_id': 'trav',
            'version': '1.0',
            'entry': 'r',
            'nodes': [{'id': 'r', 'type': 'tool', 'tool': 'read_file', 'args': {'path': '../../etc/passwd'}}],
        })
        result = validate_dag_against_policy(dag, DEFAULT_POLICY)
        self.assertEqual(result.status, 'error')
        self.assertIn('path_outside_workspace_boundary', [v.code for v in result.violations])

    def test_outside_workspace_rejected(self):
        dag = validate_dag({
            'dag_id': 'outside',
            'version': '1.0',
            'entry': 'r',
            'nodes': [{'id': 'r', 'type': 'tool', 'tool': 'read_file', 'args': {'path': '/etc/passwd'}}],
        })
        result = validate_dag_against_policy(dag, DEFAULT_POLICY)
        self.assertEqual(result.status, 'error')
        self.assertIn('path_outside_workspace_boundary', [v.code for v in result.violations])

    def test_inside_workspace_allowed(self):
        dag = validate_dag({
            'dag_id': 'inside',
            'version': '1.0',
            'entry': 'r',
            'nodes': [{'id': 'r', 'type': 'tool', 'tool': 'read_file', 'args': {'path': '/workspace/README.md'}}],
        })
        result = validate_dag_against_policy(dag, DEFAULT_POLICY)
        self.assertEqual(result.status, 'success')

    def test_violation_ordering_deterministic(self):
        dag = validate_dag({
            'dag_id': 'order',
            'version': '1.0',
            'entry': 'w',
            'nodes': [
                {'id': 'w', 'type': 'tool', 'tool': 'write_file', 'args': {'path': '/etc/passwd', 'content': 'x'}},
            ],
        })
        result = validate_dag_against_policy(dag, SAFE_READONLY_POLICY)
        codes = [v.code for v in result.violations]
        self.assertEqual(codes, sorted(codes, key=lambda c: codes.index(c)))

    def test_orchestrator_skips_on_policy_violation(self):
        result = orchestrate_task({
            'task': "Create a file called tmp/hello.txt with content 'hi' and then list files",
            'policy': SAFE_READONLY_POLICY.model_dump(mode='json'),
        })
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.execution_status, 'skipped')

    def test_orchestrator_metadata_contains_violations(self):
        result = orchestrate_task({
            'task': "Create a file called tmp/hello.txt with content 'hi' and then list files",
            'policy': SAFE_READONLY_POLICY.model_dump(mode='json'),
        })
        self.assertIn('policy', result.metadata)
        self.assertIn('violations', result.metadata['policy'])
        self.assertGreaterEqual(len(result.metadata['policy']['violations']), 1)


if __name__ == '__main__':
    unittest.main()
