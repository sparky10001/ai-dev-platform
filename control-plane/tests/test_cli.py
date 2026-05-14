#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path('/workspace')
CLI = ROOT / 'control-plane' / 'cli' / 'main.py'
AI_ORCH = ROOT / 'ai-orchestrate'


class CliTests(unittest.TestCase):

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['python3', str(CLI), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

    def _run_shim(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(AI_ORCH), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

    def test_plan_emits_valid_json(self):
        proc = self._run('plan', 'list files')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')

    def test_run_returns_success(self):
        proc = self._run('run', 'list files')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')

    def test_run_trace_includes_run_metadata(self):
        proc = self._run('run', 'list files', '--trace')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')
        self.assertTrue(payload.get('run_id'))
        self.assertTrue(payload.get('run_path'))

    def test_validate_dag_success(self):
        proc = self._run('validate-dag', 'control-plane/dags/examples/file_write_flow.json')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')
        self.assertEqual(payload.get('execution_order'), ['write', 'list'])

    def test_execute_dag_success(self):
        proc = self._run('execute-dag', 'control-plane/dags/examples/file_write_flow.json')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')

    def test_execute_dag_trace_success(self):
        proc = self._run('execute-dag', 'control-plane/dags/examples/file_write_flow.json', '--trace')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')
        self.assertTrue(payload.get('run_id'))
        self.assertTrue(payload.get('run_path'))

    def test_pretty_output_is_valid_json(self):
        proc = self._run('plan', 'list files', '--pretty')
        self.assertEqual(proc.returncode, 0)
        self.assertIn('\n  "', proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')

    def test_unknown_command_nonzero(self):
        proc = self._run('unknown-cmd')
        self.assertNotEqual(proc.returncode, 0)

    def test_missing_args_nonzero(self):
        proc = self._run('run')
        self.assertNotEqual(proc.returncode, 0)

    def test_stdout_json_only(self):
        proc = self._run_shim('plan', 'list files')
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get('status'), 'success')
        self.assertEqual(proc.stderr.strip(), '')


if __name__ == '__main__':
    unittest.main()
