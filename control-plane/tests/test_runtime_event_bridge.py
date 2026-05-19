#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CONTROL_PLANE_ROOT.parent
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from core.replay.loader import load_orchestration_trace
from core.runtime_events import control_plane_runtime_event_source
from core.runtime_events import load_control_plane_runtime_events
from core.runtime_events import iter_control_plane_runtime_events
from runtime.boundary_audit import audit_runtime_boundaries
from runtime.run import create_run
from runtime.trace_compatibility import audit_trace_compatibility
from runtime.trace_pipeline import append_trace_event


class ControlPlaneRuntimeEventBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            "RUNTIME_EVENT_SOURCE": os.environ.get("RUNTIME_EVENT_SOURCE"),
            "RUNTIME_LEDGER_CANARY": os.environ.get("RUNTIME_LEDGER_CANARY"),
            "RUNTIME_LEDGER_AUTHORITATIVE": os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE"),
        }
        for key in self._env:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _make_run(self, *, write_ledger: bool = True) -> Path:
        run = create_run(task='cp_runtime_event_bridge', command='test', model='control-plane-test')
        run_dir = Path(run['run_path'])

        append_trace_event(run, 'session_start', {'command': 'test'})
        append_trace_event(run, 'dag_start', {'dag_id': 'bridge_dag', 'execution_order': ['n1']})
        append_trace_event(run, 'dag_node_start', {'node_id': 'n1', 'node_type': 'tool', 'tool': 'list_files'})
        append_trace_event(run, 'dag_node_result', {'node_id': 'n1', 'node_type': 'tool', 'status': 'success', 'output': 'ok'})
        append_trace_event(run, 'dag_result', {'dag_id': 'bridge_dag', 'status': 'success', 'execution_order': ['n1']})
        append_trace_event(run, 'agent_output', {'status': 'done', 'output': 'ok'})
        append_trace_event(run, 'session_end', {'status': 'done'})

        if not write_ledger:
            ledger_path = run_dir / 'ledger.jsonl'
            if ledger_path.exists():
                ledger_path.unlink()

        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))
        return run_dir

    def test_default_source_resolves_trace(self) -> None:
        self.assertEqual(control_plane_runtime_event_source(), 'trace')

    def test_canary_and_authoritative_default_to_ledger(self) -> None:
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(control_plane_runtime_event_source(), 'ledger')
        os.environ.pop('RUNTIME_LEDGER_CANARY', None)
        os.environ['RUNTIME_LEDGER_AUTHORITATIVE'] = '1'
        self.assertEqual(control_plane_runtime_event_source(), 'ledger')

    def test_explicit_source_trace_wins(self) -> None:
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(control_plane_runtime_event_source(source='trace'), 'trace')

    def test_explicit_source_ledger_works(self) -> None:
        run_dir = self._make_run(write_ledger=True)
        events = load_control_plane_runtime_events(run_dir, source='ledger', strict=True)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0].get('event'), 'session_start')

    def test_invalid_source_fallback_is_deterministic(self) -> None:
        self.assertEqual(control_plane_runtime_event_source(source='not-a-source'), 'trace')
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(control_plane_runtime_event_source(source='not-a-source'), 'ledger')

    def test_missing_ledger_fails_deterministically(self) -> None:
        run_dir = self._make_run(write_ledger=False)
        with self.assertRaises(RuntimeError):
            load_control_plane_runtime_events(run_dir, source='ledger', strict=True)

    def test_bridge_load_and_iter_from_fixture(self) -> None:
        run_dir = self._make_run(write_ledger=True)
        loaded = load_control_plane_runtime_events(run_dir, source='trace', strict=True)
        itered = list(iter_control_plane_runtime_events(run_dir, source='trace', strict=True))
        self.assertEqual(len(loaded), len(itered))
        self.assertTrue(all(isinstance(item, dict) for item in loaded))

    def test_replay_behavior_preserved_through_bridge(self) -> None:
        run_dir = self._make_run(write_ledger=True)
        replay = load_orchestration_trace(run_dir)
        self.assertEqual(replay.summary.run_path, str(run_dir))
        self.assertGreaterEqual(replay.summary.total_nodes, 1)
        self.assertGreaterEqual(len(replay.events), 1)

    def test_no_runtime_engine_import_and_audits_green(self) -> None:
        boundary_report = audit_runtime_boundaries()
        self.assertEqual(boundary_report.get('status'), 'ok')

        trace_report = audit_trace_compatibility('.')
        self.assertEqual(trace_report.get('summary', {}).get('cutover_blocker_count'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
