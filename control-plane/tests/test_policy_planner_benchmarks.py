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

from core.benchmarks.exporter import export_benchmark_suite_json
from core.benchmarks.exporter import export_benchmark_suite_markdown
from core.benchmarks.matrices import build_benchmark_matrix
from core.benchmarks.models import BenchmarkSuiteResult
from core.benchmarks.runner import run_benchmark_matrix


class PolicyPlannerBenchmarkTests(unittest.TestCase):

    def setUp(self):
        self.scenario_dir = '/workspace/control-plane/scenarios/tests'

    def test_matrix_creation_and_order(self):
        m = build_benchmark_matrix(
            scenarios=['b.json', 'a.json', 'a.json'],
            planner_strategies=['noop', 'deterministic', 'noop'],
            policies=['safe-readonly', 'default', 'safe-readonly'],
            matrix_id='m1',
        )
        self.assertEqual(m.scenarios, ['a.json', 'b.json'])
        self.assertEqual(m.planner_strategies, ['deterministic', 'noop'])
        self.assertEqual(m.policies, ['default', 'safe-readonly'])

    def test_suite_execution_and_aggregation(self):
        m = build_benchmark_matrix(
            scenarios=['list_files.json', 'unsupported_task_noop.json'],
            planner_strategies=['deterministic'],
            policies=['default'],
            matrix_id='suite1',
        )
        suite = run_benchmark_matrix(m, self.scenario_dir)
        self.assertGreaterEqual(suite.total_runs, 1)
        self.assertIn('deterministic', suite.planner_scores)
        self.assertIn('default', suite.policy_scores)
        self.assertGreaterEqual(suite.average_score, 0.0)

    def test_deterministic_result_order(self):
        m = build_benchmark_matrix(
            scenarios=['unsupported_task_noop.json', 'list_files.json'],
            planner_strategies=['deterministic', 'noop'],
            policies=['default', 'safe-readonly'],
            matrix_id='suite2',
        )
        a = run_benchmark_matrix(m, self.scenario_dir)
        b = run_benchmark_matrix(m, self.scenario_dir)

        seq_a = [(r.scenario_id, r.planner_strategy, r.policy_id or '') for r in a.results]
        seq_b = [(r.scenario_id, r.planner_strategy, r.policy_id or '') for r in b.results]
        self.assertEqual(seq_a, seq_b)

    def test_exporters(self):
        m = build_benchmark_matrix(
            scenarios=['list_files.json'],
            planner_strategies=['deterministic'],
            policies=['default'],
            matrix_id='suite3',
        )
        suite = run_benchmark_matrix(m, self.scenario_dir)
        out = Path('/workspace/tmp/control-plane-benchmarks')
        out.mkdir(parents=True, exist_ok=True)

        j = export_benchmark_suite_json(suite, out / 'suite.json')
        md = export_benchmark_suite_markdown(suite, out / 'suite.md')
        self.assertTrue(Path(j).exists())
        self.assertTrue(Path(md).exists())

    def test_missing_scores_safe(self):
        suite = BenchmarkSuiteResult(
            benchmark_id='x',
            created_at=0.0,
            results=[],
        )
        self.assertEqual(suite.average_score, 0.0)

    def test_cli_commands(self):
        p1 = subprocess.run([
            '/workspace/ai-orchestrate', 'benchmark-suite', self.scenario_dir
        ], capture_output=True, text=True)
        self.assertEqual(p1.returncode, 0)
        j1 = json.loads(p1.stdout)
        self.assertIn('benchmark_id', j1)

        p2 = subprocess.run([
            '/workspace/ai-orchestrate', 'benchmark-matrix', self.scenario_dir,
            '--planner=deterministic', '--policy=default'
        ], capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        j2 = json.loads(p2.stdout)
        self.assertIn('benchmark_id', j2)


if __name__ == '__main__':
    unittest.main()
