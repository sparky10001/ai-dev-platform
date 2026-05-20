#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from runtime.trace_deprecation_inventory import (
    build_trace_deprecation_inventory,
    trace_compatibility_retained,
    trace_deprecation_candidates,
    trace_operational_dependencies,
)


class RuntimeTraceDeprecationInventoryTests(unittest.TestCase):
    def _fixture_repo(self, root: Path) -> None:
        for d in ('runtime', 'control-plane/core', 'scripts/maintenance', 'scripts', 'docs', 'runtime/tests'):
            (root / d).mkdir(parents=True, exist_ok=True)

        (root / 'runtime' / 'replay.py').write_text('TRACE_PATH = "trace.jsonl"\n', encoding='utf-8')
        (root / 'runtime' / 'loader.py').write_text('def load_trace():\n  return "trace.jsonl"\n', encoding='utf-8')
        (root / 'runtime' / 'hard_block.py').write_text('TRACE = "trace.jsonl"\n', encoding='utf-8')
        (root / 'scripts' / 'maintenance' / 'tool.py').write_text('print("trace.jsonl maintenance")\n', encoding='utf-8')
        (root / 'scripts' / 'misc.py').write_text('TRACE = "trace.jsonl"\n', encoding='utf-8')
        (root / 'runtime' / 'tests' / 'test_trace.py').write_text('x="trace.jsonl"\n', encoding='utf-8')
        (root / 'docs' / 'runtime.md').write_text('trace.jsonl compatibility operational notes\n', encoding='utf-8')
        (root / 'docs' / 'history.md').write_text('Phase 3.8 trace compatibility notes and trace.jsonl\n', encoding='utf-8')

    def test_deterministic_inventory_generation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            a = build_trace_deprecation_inventory(root)
            b = build_trace_deprecation_inventory(root)
            self.assertEqual(a['summary'], b['summary'])
            self.assertEqual([x['path'] for x in a['candidates']], [x['path'] for x in b['candidates']])

    def test_candidate_classification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            inv = build_trace_deprecation_inventory(root)
            candidates = trace_deprecation_candidates(inv)
            self.assertTrue(any(item['category'] == 'future_deprecation_candidate' for item in candidates))
            self.assertTrue(any(item['category'] == 'future_removal_candidate' for item in candidates))

    def test_retained_classification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            inv = build_trace_deprecation_inventory(root)
            retained = trace_compatibility_retained(inv)
            cats = {item['category'] for item in retained}
            self.assertIn('compatibility_retained', cats)
            self.assertIn('legacy_runtime_dependency', cats)

    def test_operational_classification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            inv = build_trace_deprecation_inventory(root)
            operational = trace_operational_dependencies(inv)
            self.assertTrue(any(item['path'] == 'scripts/maintenance/tool.py' for item in operational))

    def test_docs_tests_and_historical_classification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            inv = build_trace_deprecation_inventory(root)
            docs = inv['categories']['documentation_only']
            tests = inv['categories']['test_only']
            hist = inv['categories']['historical_reference']
            self.assertTrue(any(item['path'] == 'docs/runtime.md' for item in docs))
            self.assertTrue(any(item['path'] == 'runtime/tests/test_trace.py' for item in tests))
            self.assertTrue(any(item['path'] == 'docs/history.md' for item in hist))

    def test_no_false_blocker_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            inv = build_trace_deprecation_inventory(root)
            self.assertEqual(inv['status'], 'informational')

    def test_strict_informational_behavior(self) -> None:
        proc = subprocess.run(
            ['python3', 'scripts/maintenance/trace_deprecation_inventory.py', '--strict'],
            capture_output=True,
            text=True,
            check=False,
            cwd='/workspace',
        )
        self.assertEqual(proc.returncode, 0)

    def test_cli_json_behavior(self) -> None:
        proc = subprocess.run(
            ['python3', 'scripts/maintenance/trace_deprecation_inventory.py', '--json'],
            capture_output=True,
            text=True,
            check=False,
            cwd='/workspace',
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn('summary', payload)
        self.assertIn('categories', payload)

    def test_deterministic_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            inv = build_trace_deprecation_inventory(root)
            paths = [item['path'] for item in inv['candidates']]
            self.assertEqual(paths, sorted(paths))

    def test_no_runtime_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._fixture_repo(root)
            before = {p: (root / p).read_text(encoding='utf-8') for p in [
                'runtime/replay.py',
                'runtime/loader.py',
                'scripts/maintenance/tool.py',
                'docs/runtime.md',
            ]}
            _ = build_trace_deprecation_inventory(root)
            after = {p: (root / p).read_text(encoding='utf-8') for p in before}
            self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main(verbosity=2)
