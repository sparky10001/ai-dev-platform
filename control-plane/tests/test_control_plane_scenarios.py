#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.scenarios.runner import load_scenario
from core.scenarios.runner import run_scenario
from runtime.replay import replay_trace

SCENARIO_DIR = CONTROL_PLANE_ROOT / 'scenarios' / 'tests'
SCENARIOS = [
    SCENARIO_DIR / 'list_files.json',
    SCENARIO_DIR / 'write_then_list.json',
    SCENARIO_DIR / 'safe_readonly_blocks_write.json',
    SCENARIO_DIR / 'traced_write_then_list.json',
    SCENARIO_DIR / 'unsupported_task_noop.json',
]


class ControlPlaneScenarioTests(unittest.TestCase):

    def test_scenarios_load(self):
        for path in SCENARIOS:
            scenario = load_scenario(path)
            self.assertTrue(scenario.scenario_id)

    def test_scenarios_pass(self):
        for path in SCENARIOS:
            result = run_scenario(path)
            self.assertEqual(result.status, 'passed', msg=str(path))

    def test_result_shape_deterministic(self):
        result = run_scenario(SCENARIO_DIR / 'list_files.json')
        payload = result.model_dump(mode='json')
        self.assertIn('scenario_id', payload)
        self.assertIn('checks', payload)
        self.assertIn('orchestration_result', payload)

    def test_failed_expectation_produces_failed_result(self):
        bad = {
            'scenario_id': 'bad_expect',
            'task': 'list files',
            'expect': {'status': 'error'},
        }
        tmp = SCENARIO_DIR / 'tmp_bad_expect.json'
        tmp.write_text(json.dumps(bad), encoding='utf-8')
        try:
            result = run_scenario(tmp)
            self.assertEqual(result.status, 'failed')
        finally:
            if tmp.exists():
                tmp.unlink()

    def test_traced_scenario_replayable(self):
        result = run_scenario(SCENARIO_DIR / 'traced_write_then_list.json')
        orch = result.orchestration_result
        run_path = orch.get('run_path')
        if run_path:
            trace_path = Path(run_path) / 'trace.jsonl'
            self.assertTrue(trace_path.exists())
            replayed = replay_trace(trace_path)
            self.assertGreaterEqual(replayed.event_count, 1)

    def test_policy_violation_codes_present(self):
        result = run_scenario(SCENARIO_DIR / 'safe_readonly_blocks_write.json')
        policy = ((result.orchestration_result.get('metadata') or {}).get('policy') or {})
        violations = policy.get('violations') or []
        codes = [v.get('code') for v in violations if isinstance(v, dict)]
        self.assertIn('tool_denied', codes)


if __name__ == '__main__':
    unittest.main()
