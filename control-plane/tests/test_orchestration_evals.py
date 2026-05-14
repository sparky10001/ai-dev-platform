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

from core.evals.benchmarks import benchmark_replays
from core.evals.comparator import compare_replays
from core.evals.evaluator import evaluate_replay
from core.evals.exporter import export_benchmark_markdown
from core.evals.exporter import export_comparison_json
from core.evals.exporter import export_evaluation_json
from core.orchestrator.orchestrator import orchestrate_task
from core.replay.loader import load_orchestration_trace


class OrchestrationEvalTests(unittest.TestCase):

    def _run(self, task: str):
        result = orchestrate_task({'task': task, 'trace': True})
        self.assertTrue(result.run_path)
        return load_orchestration_trace(result.run_path)

    def test_evaluation_succeeds_and_deterministic(self):
        replay = self._run("Create a file called hello.txt with content 'hi' and then list files")
        a = evaluate_replay(replay)
        b = evaluate_replay(replay)
        self.assertEqual(a.model_dump(mode='json'), b.model_dump(mode='json'))

    def test_score_range_and_metric_order(self):
        replay = self._run('list files')
        ev = evaluate_replay(replay)
        self.assertGreaterEqual(ev.score, 0.0)
        self.assertLessEqual(ev.score, 1.0)
        names = [m.name for m in ev.metrics]
        self.assertEqual(names, ['duration_ms', 'execution_completeness', 'failure_count', 'skipped_count', 'success_rate', 'tool_count', 'trace_available'])

    def test_comparison_identical(self):
        replay = self._run('list files')
        cmp = compare_replays(replay, replay)
        self.assertTrue(cmp.identical)

    def test_comparison_differences(self):
        left = self._run('list files')
        right = self._run("Create a file called hello.txt with content 'hi' and then list files")
        cmp = compare_replays(left, right)
        self.assertFalse(cmp.identical)
        self.assertTrue(cmp.execution_order_changed or len(cmp.tool_delta) > 0 or cmp.node_count_delta != 0)

    def test_benchmark_aggregation(self):
        a = self._run('list files')
        b = self._run("Create a file called hello.txt with content 'hi' and then list files")
        bench = benchmark_replays([a, b], benchmark_id='b1')
        self.assertEqual(bench.total_runs, 2)
        self.assertGreaterEqual(bench.average_score, 0.0)
        self.assertLessEqual(bench.average_score, 1.0)

    def test_exporters(self):
        replay = self._run('list files')
        ev = evaluate_replay(replay)
        cmp = compare_replays(replay, replay)
        bench = benchmark_replays([replay], benchmark_id='b2')

        out = Path('/workspace/tmp/control-plane-evals')
        out.mkdir(parents=True, exist_ok=True)
        self.assertTrue(Path(export_evaluation_json(ev, out / 'eval.json')).exists())
        self.assertTrue(Path(export_comparison_json(cmp, out / 'cmp.json')).exists())
        self.assertTrue(Path(export_benchmark_markdown(bench, out / 'bench.md')).exists())

    def test_cli_commands(self):
        result = orchestrate_task({'task': 'list files', 'trace': True})
        run_path = result.run_path

        p1 = subprocess.run(['/workspace/ai-orchestrate', 'evaluate-run', run_path], capture_output=True, text=True)
        self.assertEqual(p1.returncode, 0)
        j1 = json.loads(p1.stdout)
        self.assertIn('evaluation_id', j1)

        p2 = subprocess.run(['/workspace/ai-orchestrate', 'compare-runs', run_path, run_path], capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        j2 = json.loads(p2.stdout)
        self.assertIn('comparison_id', j2)

        p3 = subprocess.run(['/workspace/ai-orchestrate', 'benchmark-runs', run_path, run_path], capture_output=True, text=True)
        self.assertEqual(p3.returncode, 0)
        j3 = json.loads(p3.stdout)
        self.assertIn('benchmark_id', j3)


if __name__ == '__main__':
    unittest.main()
