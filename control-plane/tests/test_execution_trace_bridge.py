#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CONTROL_PLANE_ROOT.parent
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from core.dag.executor import execute_dag
from core.observability.trace import create_control_plane_run
from runtime.loader import load_result
from runtime.replay import replay_trace
from runtime.validator import validate_response


class ExecutionTraceBridgeTests(unittest.TestCase):

    def test_create_control_plane_run(self):

        run = create_control_plane_run('trace_bridge_smoke')

        self.assertIn('id', run)
        self.assertTrue(Path(run['run_path']).exists())
        self.assertTrue(Path(run['trace_path']).exists() or Path(run['trace_path']).parent.exists())

    def test_traced_execute_dag_success(self):

        dag_path = CONTROL_PLANE_ROOT / 'dags' / 'examples' / 'file_write_flow.json'
        result = execute_dag(dag_path, trace=True)

        self.assertEqual(result.status, 'success')

        run_id = None
        for node_result in result.results.values():
            if node_result.raw_result and isinstance(node_result.raw_result, dict):
                meta = node_result.raw_result.get('meta')
                if isinstance(meta, dict) and meta.get('run_id'):
                    run_id = meta.get('run_id')
                    break

        # run_id may not be present in tool raw meta; find latest dag run via runs dir scan.
        if run_id is None:
            runs_dir = WORKSPACE_ROOT / 'runs'
            dag_runs = sorted(runs_dir.glob('run_*/run.json'), key=lambda p: p.stat().st_mtime, reverse=True)
            for run_json in dag_runs:
                payload = json.loads(run_json.read_text(encoding='utf-8'))
                if payload.get('command') == 'dag' and payload.get('task') == 'file_write_flow':
                    run_id = payload.get('id')
                    break

        self.assertIsNotNone(run_id)

        run_dir = WORKSPACE_ROOT / 'runs' / run_id
        trace_path = run_dir / 'trace.jsonl'
        result_path = run_dir / 'result.json'

        self.assertTrue(trace_path.exists())
        self.assertTrue(result_path.exists())

        lines = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        events = [item.get('event') for item in lines]

        self.assertIn('session_start', events)
        self.assertIn('dag_start', events)
        self.assertIn('dag_node_start', events)
        self.assertIn('dag_node_result', events)
        self.assertIn('dag_result', events)
        self.assertIn('agent_output', events)
        self.assertIn('session_end', events)

        replay = replay_trace(trace_path, strict=True)
        self.assertGreater(replay.event_count, 0)

        final_result = load_result(run_id)
        validated = validate_response(final_result)
        self.assertEqual(validated.status, 'done')

    def test_failed_dag_has_session_end(self):

        dag = {
            'dag_id': 'trace_fail',
            'version': '1.0.0',
            'entry': 'bad',
            'nodes': [
                {'id': 'bad', 'type': 'tool', 'tool': 'no_such_tool', 'args': {}},
            ],
        }

        result = execute_dag(dag, trace=True)
        self.assertEqual(result.status, 'error')

        runs_dir = WORKSPACE_ROOT / 'runs'
        dag_runs = sorted(runs_dir.glob('run_*/run.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        run_id = None
        for run_json in dag_runs:
            payload = json.loads(run_json.read_text(encoding='utf-8'))
            if payload.get('command') == 'dag' and payload.get('task') == 'trace_fail':
                run_id = payload.get('id')
                break

        self.assertIsNotNone(run_id)

        trace_path = WORKSPACE_ROOT / 'runs' / run_id / 'trace.jsonl'
        lines = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        events = [item.get('event') for item in lines]

        self.assertIn('session_end', events)
        self.assertIn('dag_result', events)


if __name__ == '__main__':
    unittest.main()
