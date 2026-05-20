#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from runtime.authority_policy import (
    effective_runtime_event_source,
    ledger_authoritative_enabled,
    ledger_canary_enabled,
    ledger_default_dry_run_enabled,
    runtime_authority_mode,
    runtime_authority_policy,
    runtime_authority_transition_state,
)
from runtime.evals import eval_source
from runtime.event_loader import runtime_event_source
from runtime.registry import registry_source
from runtime.replay import replay_source
from runtime.run import create_run
from runtime.trace_pipeline import append_trace_event

CONTROL_PLANE_ROOT = Path('/workspace/control-plane')
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))
from core.runtime_events import control_plane_runtime_event_source  # noqa: E402


class RuntimeAuthorityPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            'RUNTIME_LEDGER_CANARY': os.environ.get('RUNTIME_LEDGER_CANARY'),
            'RUNTIME_LEDGER_AUTHORITATIVE': os.environ.get('RUNTIME_LEDGER_AUTHORITATIVE'),
            'RUNTIME_LEDGER_DRY_RUN_DEFAULT': os.environ.get('RUNTIME_LEDGER_DRY_RUN_DEFAULT'),
            'RUNTIME_EVENT_SOURCE': os.environ.get('RUNTIME_EVENT_SOURCE'),
            'RUNTIME_REPLAY_SOURCE': os.environ.get('RUNTIME_REPLAY_SOURCE'),
            'RUNTIME_EVAL_SOURCE': os.environ.get('RUNTIME_EVAL_SOURCE'),
            'RUNTIME_REGISTRY_SOURCE': os.environ.get('RUNTIME_REGISTRY_SOURCE'),
        }
        for key in self._env:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_default_trace_mode(self) -> None:
        self.assertEqual(runtime_authority_mode(), 'trace')
        self.assertEqual(runtime_event_source(), 'trace')

    def test_canary_mode(self) -> None:
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertTrue(ledger_canary_enabled())
        self.assertEqual(runtime_authority_mode(), 'canary')
        self.assertEqual(runtime_event_source(), 'ledger')

    def test_authoritative_mode(self) -> None:
        os.environ['RUNTIME_LEDGER_AUTHORITATIVE'] = '1'
        self.assertTrue(ledger_authoritative_enabled())
        self.assertEqual(runtime_authority_mode(), 'authoritative')
        self.assertEqual(runtime_event_source(), 'ledger')

    def test_authoritative_precedence(self) -> None:
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        os.environ['RUNTIME_LEDGER_AUTHORITATIVE'] = '1'
        self.assertEqual(runtime_authority_mode(), 'authoritative')

    def test_dry_run_flag_behavior(self) -> None:
        self.assertFalse(ledger_default_dry_run_enabled())
        os.environ['RUNTIME_LEDGER_DRY_RUN_DEFAULT'] = '1'
        self.assertTrue(ledger_default_dry_run_enabled())

    def test_explicit_source_override(self) -> None:
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(effective_runtime_event_source(source='trace'), 'trace')
        self.assertEqual(effective_runtime_event_source(source='ledger'), 'ledger')

    def test_invalid_source_fallback(self) -> None:
        self.assertEqual(effective_runtime_event_source(source='bogus'), 'trace')
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(effective_runtime_event_source(source='bogus'), 'ledger')

    def test_transition_state_payload_deterministic(self) -> None:
        payload = runtime_authority_transition_state()
        self.assertEqual(payload['current_default'], 'trace')
        self.assertEqual(payload['effective_mode'], 'trace')
        self.assertFalse(payload['default_cutover_performed'])
        self.assertTrue(payload['trace_emission_enabled'])
        self.assertTrue(payload['rollback_supported'])
        self.assertEqual(
            payload['rollback_unset'],
            [
                'RUNTIME_LEDGER_CANARY',
                'RUNTIME_LEDGER_AUTHORITATIVE',
                'RUNTIME_LEDGER_PARITY_REQUIRED',
                'RUNTIME_LEDGER_CANARY_PARITY_REQUIRED',
            ],
        )

    def test_policy_payload_deterministic(self) -> None:
        payload = runtime_authority_policy()
        self.assertEqual(payload['mode'], 'trace')
        self.assertEqual(payload['event_source'], 'trace')
        self.assertIn('flags', payload)
        self.assertIn('transition', payload)

    def test_replay_eval_registry_source_consistency(self) -> None:
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(replay_source(), 'ledger')
        self.assertEqual(eval_source(), 'ledger')
        self.assertEqual(registry_source(), 'ledger')

    def test_control_plane_bridge_consistency(self) -> None:
        self.assertEqual(control_plane_runtime_event_source(), 'trace')
        os.environ['RUNTIME_LEDGER_CANARY'] = '1'
        self.assertEqual(control_plane_runtime_event_source(), 'ledger')

    def test_no_runtime_mutation_and_no_default_cutover(self) -> None:
        run = create_run(task='authority_policy_mutation_check', command='test', model='runtime-test')
        run_dir = Path(run['run_path'])
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))

        append_trace_event(run, 'session_start', {'command': 'test'})
        append_trace_event(run, 'agent_output', {'status': 'done', 'output': 'ok'})
        append_trace_event(run, 'session_end', {'status': 'done'})

        trace_path = run_dir / 'trace.jsonl'
        ledger_path = run_dir / 'ledger.jsonl'
        trace_before = trace_path.read_text(encoding='utf-8')
        ledger_before = ledger_path.read_text(encoding='utf-8')

        _ = runtime_authority_policy()
        _ = runtime_authority_transition_state()
        _ = runtime_event_source()

        self.assertEqual(trace_path.read_text(encoding='utf-8'), trace_before)
        self.assertEqual(ledger_path.read_text(encoding='utf-8'), ledger_before)
        self.assertFalse(runtime_authority_transition_state()['default_cutover_performed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
