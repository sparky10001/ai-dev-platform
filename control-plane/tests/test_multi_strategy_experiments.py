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

from core.strategies.branching import execute_strategy_experiment
from core.strategies.evaluator import compare_strategy_variants
from core.strategies.evaluator import select_best_strategy
from core.strategies.exporter import export_strategy_experiment_json
from core.strategies.exporter import export_strategy_experiment_markdown
from core.strategies.planner_variants import build_strategy_variants


class MultiStrategyExperimentTests(unittest.TestCase):

    def test_variant_generation_and_order(self):
        variants = build_strategy_variants(
            task='list files',
            planner_strategies=['noop', 'deterministic', 'noop'],
            policies=['safe-readonly', 'default', 'safe-readonly'],
        )
        ids = [v.strategy_id for v in variants]
        self.assertEqual(ids, sorted(ids))

    def test_strategy_experiment_execution(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic', 'noop'],
            policies=['default'],
            trace=True,
        )
        self.assertGreaterEqual(len(exp.variants), 1)
        self.assertGreaterEqual(exp.average_score, 0.0)

    def test_best_strategy_selection(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic', 'noop'],
            policies=['default'],
            trace=True,
        )
        best = select_best_strategy(exp)
        self.assertEqual(best, exp.best_strategy_id)

    def test_strategy_comparison_output(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic', 'noop'],
            policies=['default'],
            trace=True,
        )
        if len(exp.variants) >= 2:
            cmp = compare_strategy_variants(exp.variants[0], exp.variants[1])
            self.assertTrue(cmp.comparison_id)

    def test_tie_breaking_deterministic(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic', 'noop'],
            policies=['default'],
            trace=False,
        )
        best = select_best_strategy(exp)
        if best is not None:
            self.assertEqual(best, sorted([v.strategy_id for v in exp.variants])[0])

    def test_exports(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic'],
            policies=['default'],
            trace=True,
        )
        out = Path('/workspace/tmp/control-plane-strategies')
        out.mkdir(parents=True, exist_ok=True)
        self.assertTrue(Path(export_strategy_experiment_json(exp, out / 'exp.json')).exists())
        self.assertTrue(Path(export_strategy_experiment_markdown(exp, out / 'exp.md')).exists())

    def test_cli_commands(self):
        p1 = subprocess.run([
            '/workspace/ai-orchestrate',
            'strategy-experiment',
            'list files',
            '--planner=deterministic',
            '--planner=noop',
            '--policy=default',
        ], capture_output=True, text=True)
        self.assertEqual(p1.returncode, 0)
        j1 = json.loads(p1.stdout)
        self.assertIn('experiment_id', j1)

        p2 = subprocess.run([
            '/workspace/ai-orchestrate',
            'compare-strategies',
            'list files',
            '--planner=deterministic',
            '--planner=noop',
        ], capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        j2 = json.loads(p2.stdout)
        self.assertIsInstance(j2, list)


if __name__ == '__main__':
    unittest.main()
