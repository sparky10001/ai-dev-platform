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

from core.evals.evaluator import evaluate_replay
from core.experiments.datasets import build_replay_dataset
from core.experiments.datasets import replay_to_dataset_entry
from core.experiments.exporter import export_dataset_json
from core.experiments.exporter import export_manifest_json
from core.experiments.exporter import export_manifest_markdown
from core.experiments.manifests import create_experiment_manifest
from core.experiments.models import ExperimentRun
from core.experiments.tracker import track_replay
from core.experiments.tracker import track_replays
from core.orchestrator.orchestrator import orchestrate_task
from core.replay.loader import load_orchestration_trace


class OrchestrationExperimentTests(unittest.TestCase):

    def _replay(self, task: str):
        result = orchestrate_task({'task': task, 'trace': True})
        self.assertTrue(result.run_path)
        return load_orchestration_trace(result.run_path)

    def test_experiment_run_creation(self):
        replay = self._replay('list files')
        ev = evaluate_replay(replay)
        run = track_replay(replay, evaluation=ev)
        self.assertEqual(run.run_id, replay.summary.run_id)

    def test_manifest_aggregation_and_order(self):
        a = ExperimentRun(run_id='b', score=0.2)
        b = ExperimentRun(run_id='a', score=0.8)
        manifest = create_experiment_manifest('exp', [a, b])
        self.assertEqual([r.run_id for r in manifest.runs], ['a', 'b'])
        self.assertAlmostEqual(manifest.average_score, 0.5)

    def test_dataset_generation(self):
        replay = self._replay('list files')
        ev = evaluate_replay(replay)
        entry = replay_to_dataset_entry(replay, ev)
        self.assertEqual(entry.run_id, replay.summary.run_id)

        dataset = build_replay_dataset([replay], [ev], dataset_id='d1')
        self.assertEqual(dataset.total_entries, 1)

    def test_tracker_tolerates_missing_eval(self):
        replay = self._replay('list files')
        manifest = track_replays([replay], evaluations=None, experiment_id='e1')
        self.assertEqual(manifest.total_runs, 1)

    def test_exports(self):
        replay = self._replay('list files')
        ev = evaluate_replay(replay)
        manifest = track_replays([replay], [ev], experiment_id='e2')
        dataset = build_replay_dataset([replay], [ev], dataset_id='d2')

        out = Path('/workspace/tmp/control-plane-experiments')
        out.mkdir(parents=True, exist_ok=True)
        self.assertTrue(Path(export_manifest_json(manifest, out / 'manifest.json')).exists())
        self.assertTrue(Path(export_dataset_json(dataset, out / 'dataset.json')).exists())
        self.assertTrue(Path(export_manifest_markdown(manifest, out / 'manifest.md')).exists())

    def test_lineage_metadata_preserved(self):
        replay = self._replay('list files')
        ev = evaluate_replay(replay)
        run = track_replay(replay, evaluation=ev)
        self.assertIn('run_path', run.metadata)

    def test_cli_commands(self):
        result = orchestrate_task({'task': 'list files', 'trace': True})
        run_path = result.run_path

        p1 = subprocess.run(['/workspace/ai-orchestrate', 'track-run', run_path], capture_output=True, text=True)
        self.assertEqual(p1.returncode, 0)
        j1 = json.loads(p1.stdout)
        self.assertIn('run_id', j1)

        p2 = subprocess.run(['/workspace/ai-orchestrate', 'track-experiment', run_path, run_path], capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        j2 = json.loads(p2.stdout)
        self.assertIn('experiment_id', j2)

        p3 = subprocess.run(['/workspace/ai-orchestrate', 'build-dataset', run_path, run_path], capture_output=True, text=True)
        self.assertEqual(p3.returncode, 0)
        j3 = json.loads(p3.stdout)
        self.assertIn('dataset_id', j3)


if __name__ == '__main__':
    unittest.main()
