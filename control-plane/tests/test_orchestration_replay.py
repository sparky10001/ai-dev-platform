#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.orchestrator.orchestrator import orchestrate_task
from core.replay.exporter import export_replay_markdown
from core.replay.exporter import export_replay_summary_json
from core.replay.introspection import build_lineage_graph
from core.replay.introspection import get_failed_nodes
from core.replay.introspection import get_skipped_nodes
from core.replay.introspection import list_tools_used
from core.replay.introspection import get_execution_order
from core.replay.loader import load_orchestration_trace
from runtime.replay import replay_trace


class OrchestrationReplayTests(unittest.TestCase):

    def _make_traced_run(self):
        result = orchestrate_task({
            'task': "Create a file called hello.txt with content 'hi' and then list files",
            'trace': True,
        })
        self.assertEqual(result.status, 'success')
        self.assertTrue(result.run_path)
        return Path(result.run_path)

    def test_replay_loads(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        self.assertEqual(replay.summary.run_path, str(run_path))

    def test_summary_reconstructs_ids(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        self.assertTrue(replay.summary.dag_id)
        self.assertTrue(replay.summary.run_id)

    def test_tools_and_order(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        tools = list_tools_used(replay)
        order = get_execution_order(replay)
        self.assertIn('write_file', tools)
        self.assertIn('list_files', tools)
        self.assertEqual(order, ['write', 'list'])

    def test_duration_and_failed_skipped(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        self.assertIsNotNone(replay.summary.duration_ms)

        bad = orchestrate_task({'task': 'read file DOES_NOT_EXIST_12345.txt', 'trace': True})
        bad_replay = load_orchestration_trace(Path(bad.run_path))
        self.assertGreaterEqual(len(get_failed_nodes(bad_replay)), 1)

    def test_skipped_nodes_detection(self):
        result = orchestrate_task({'task': 'read file DOES_NOT_EXIST_12345.txt and then list files', 'trace': True})
        replay = load_orchestration_trace(Path(result.run_path))
        _ = get_skipped_nodes(replay)

    def test_lineage_deterministic(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        graph = build_lineage_graph(replay)
        self.assertIn('write', graph)
        self.assertEqual(graph['write'], ['list'])

    def test_exports(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        out_dir = Path('/workspace/tmp/control-plane-replay-exports')
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = export_replay_markdown(replay, out_dir / 'summary.md')
        js_path = export_replay_summary_json(replay, out_dir / 'summary.json')
        self.assertTrue(Path(md_path).exists())
        self.assertTrue(Path(js_path).exists())

    def test_tolerates_unrelated_events_and_missing_dag_result(self):
        run_path = self._make_traced_run()
        trace_path = run_path / 'trace.jsonl'
        lines = trace_path.read_text(encoding='utf-8').splitlines()
        modified = []
        for line in lines:
            obj = json.loads(line)
            if obj.get('event') != 'dag_result':
                modified.append(obj)
        modified.insert(1, {
            'run_id': modified[0].get('run_id'),
            'timestamp': modified[0].get('timestamp'),
            'event': 'tool_call',
            'data': {'tool': 'noop'},
        })

        temp_dir = Path('/workspace/tmp/control-plane-replay-mod') / run_path.name
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_trace = temp_dir / 'trace.jsonl'
        with open(temp_trace, 'w', encoding='utf-8') as f:
            for obj in modified:
                f.write(json.dumps(obj) + '\n')

        replay = load_orchestration_trace(temp_dir)
        self.assertGreaterEqual(len(replay.events), 1)
        self.assertIn(replay.summary.status, {'success', 'error', 'done'})

    def test_event_order_preserved(self):
        run_path = self._make_traced_run()
        replay = load_orchestration_trace(run_path)
        events = replay.events
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[0].get('event'), 'session_start')

    def test_runtime_replay_compatibility(self):
        run_path = self._make_traced_run()
        state = replay_trace(run_path / 'trace.jsonl')
        self.assertGreaterEqual(state.event_count, 1)

    def test_cli_replay_and_summarize(self):
        run_path = self._make_traced_run()
        import subprocess

        replay_proc = subprocess.run([
            '/workspace/ai-orchestrate', 'replay', str(run_path)
        ], capture_output=True, text=True)
        self.assertEqual(replay_proc.returncode, 0)
        replay_payload = json.loads(replay_proc.stdout)
        self.assertIn('summary', replay_payload)

        sum_proc = subprocess.run([
            '/workspace/ai-orchestrate', 'summarize-run', str(run_path)
        ], capture_output=True, text=True)
        self.assertEqual(sum_proc.returncode, 0)
        sum_payload = json.loads(sum_proc.stdout)
        self.assertIn('run_id', sum_payload)


if __name__ == '__main__':
    unittest.main()
