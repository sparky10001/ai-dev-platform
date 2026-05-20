#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from runtime.dual_authority_validation import (
    build_dual_authority_validation_window,
    dual_authority_validation_blockers,
    evaluate_dual_authority_validation,
)
from runtime.event_ledger import write_ledger_index
from runtime.trace_pipeline import append_trace_event


class RuntimeDualAuthorityValidationTests(unittest.TestCase):
    def _make_run(self, root: Path, run_id: str) -> Path:
        run_dir = root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        run = {
            'id': run_id,
            'run_path': str(run_dir),
            'trace_path': str(run_dir / 'trace.jsonl'),
        }
        append_trace_event(run, 'session_start', {'command': 'hello'})
        append_trace_event(run, 'agent_output', {'status': 'done', 'output': 'ok'})
        append_trace_event(run, 'session_end', {'status': 'done'})
        write_ledger_index(run_dir)
        return run_dir

    def _clean_patches(self, *, mode: str = 'trace', **overrides):
        transition = {
            'current_default': 'trace',
            'effective_mode': mode,
            'canary_enabled': mode == 'canary',
            'authoritative_enabled': mode == 'authoritative',
            'dry_run_enabled': False,
            'default_cutover_performed': False,
            'trace_emission_enabled': True,
            'rollback_supported': True,
            'rollback_method': 'env_unset',
            'rollback_unset': [
                'RUNTIME_LEDGER_CANARY',
                'RUNTIME_LEDGER_AUTHORITATIVE',
                'RUNTIME_LEDGER_PARITY_REQUIRED',
                'RUNTIME_LEDGER_CANARY_PARITY_REQUIRED',
            ],
        }
        drift_report = {
            'drift_categories': [],
            'replay_summary_match': True,
            'eval_summary_match': True,
            'registry_summary_match': True,
        }
        corruption_report = {'corruption_categories': []}
        health_report = {'status': 'healthy', 'categories': []}
        compatibility = {'status': 'ok', 'summary': {'cutover_blocker_count': 0}, 'cutover_blockers': []}
        dry_run = {
            'drift_detected': False,
            'corruption_detected': False,
            'replay_ledger_ready': True,
            'eval_ledger_ready': True,
            'registry_ledger_ready': True,
        }
        aggregate_health = {'status': 'healthy', 'runs_scanned': 0, 'reports': []}

        transition = overrides.get('transition', transition)
        drift_report = overrides.get('drift_report', drift_report)
        corruption_report = overrides.get('corruption_report', corruption_report)
        health_report = overrides.get('health_report', health_report)
        compatibility = overrides.get('compatibility', compatibility)
        dry_run = overrides.get('dry_run', dry_run)
        aggregate_health = overrides.get('aggregate_health', aggregate_health)

        stack = ExitStack()
        stack.enter_context(patch('runtime.dual_authority_validation.runtime_authority_transition_state', return_value=transition))
        stack.enter_context(patch('runtime.dual_authority_validation.compare_trace_and_ledger', return_value=drift_report))
        stack.enter_context(patch('runtime.dual_authority_validation.drift_detected', return_value=bool(drift_report.get('drift_categories'))))
        stack.enter_context(patch('runtime.dual_authority_validation.classify_ledger_corruption', return_value=corruption_report))
        stack.enter_context(patch('runtime.dual_authority_validation.ledger_health_report', return_value=health_report))
        stack.enter_context(patch('runtime.dual_authority_validation.audit_trace_compatibility', return_value=compatibility))
        stack.enter_context(patch('runtime.dual_authority_validation.summarize_trace_dependencies', return_value=compatibility))
        stack.enter_context(patch('runtime.dual_authority_validation.evaluate_ledger_default_readiness', return_value=dry_run))
        stack.enter_context(patch('runtime.dual_authority_validation.aggregate_ledger_health', return_value=aggregate_health))
        return stack

    def test_trace_mode_inactive_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_trace')
            with self._clean_patches(mode='trace'):
                report = build_dual_authority_validation_window(run_dir)
            self.assertFalse(report['authority']['dual_validation_active'])
            self.assertEqual(report['authority']['mode'], 'trace')

    def test_canary_mode_active_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_canary')
            with self._clean_patches(mode='canary'):
                report = build_dual_authority_validation_window(run_dir)
            self.assertTrue(report['authority']['dual_validation_active'])
            self.assertEqual(report['authority']['mode'], 'canary')

    def test_authoritative_mode_active_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_auth')
            with self._clean_patches(mode='authoritative'):
                report = build_dual_authority_validation_window(run_dir)
            self.assertTrue(report['authority']['dual_validation_active'])
            self.assertEqual(report['authority']['mode'], 'authoritative')

    def test_drift_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_drift')
            with self._clean_patches(
                mode='canary',
                drift_report={'drift_categories': ['event_count_mismatch'], 'replay_summary_match': True, 'eval_summary_match': True, 'registry_summary_match': True},
                dry_run={'drift_detected': True, 'corruption_detected': False, 'replay_ledger_ready': True, 'eval_ledger_ready': True, 'registry_ledger_ready': True},
            ):
                report = build_dual_authority_validation_window(run_dir)
            self.assertTrue(any(b['code'] == 'drift_detected' for b in report['blockers']))

    def test_corruption_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_corruption')
            with self._clean_patches(
                mode='canary',
                corruption_report={'corruption_categories': ['malformed_ndjson']},
                dry_run={'drift_detected': False, 'corruption_detected': True, 'replay_ledger_ready': True, 'eval_ledger_ready': True, 'registry_ledger_ready': True},
            ):
                report = build_dual_authority_validation_window(run_dir)
            self.assertTrue(any(b['code'] == 'corruption_detected' for b in report['blockers']))

    def test_parity_blocker_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_parity')
            with self._clean_patches(
                mode='authoritative',
                drift_report={'drift_categories': [], 'replay_summary_match': False, 'eval_summary_match': False, 'registry_summary_match': False},
                dry_run={'drift_detected': False, 'corruption_detected': False, 'replay_ledger_ready': True, 'eval_ledger_ready': True, 'registry_ledger_ready': True},
            ):
                report = build_dual_authority_validation_window(run_dir)
            codes = {b['code'] for b in report['blockers']}
            self.assertIn('replay_parity_failed', codes)
            self.assertIn('eval_parity_failed', codes)
            self.assertIn('registry_parity_failed', codes)

    def test_compatibility_blocker_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_compat')
            compat = {'status': 'blocked', 'summary': {'cutover_blocker_count': 2}, 'cutover_blockers': [{'path': 'runtime/x.py'}]}
            with self._clean_patches(mode='canary', compatibility=compat):
                report = build_dual_authority_validation_window(run_dir)
            self.assertTrue(any(b['code'] == 'compatibility_blockers' for b in report['blockers']))

    def test_rollback_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_rollback')
            transition = {
                'current_default': 'trace', 'effective_mode': 'canary', 'canary_enabled': True, 'authoritative_enabled': False,
                'dry_run_enabled': False, 'default_cutover_performed': False, 'trace_emission_enabled': True,
                'rollback_supported': False, 'rollback_method': 'env_unset', 'rollback_unset': [],
            }
            with self._clean_patches(mode='canary', transition=transition):
                report = build_dual_authority_validation_window(run_dir)
            self.assertTrue(any(b['code'] == 'rollback_missing' for b in report['blockers']))

    def test_deterministic_blocker_ordering(self) -> None:
        blockers = dual_authority_validation_blockers(
            {
                'validation': {
                    'drift': {'detected': True},
                    'corruption': {'detected': True},
                    'health': {'status': 'unhealthy'},
                    'compatibility': {'cutover_blocker_count': 2},
                    'replay_parity': {'status': 'blocked'},
                    'eval_parity': {'status': 'blocked'},
                    'registry_parity': {'status': 'blocked'},
                    'rollback': {'supported': False},
                }
            }
        )
        codes = [b['code'] for b in blockers]
        self.assertEqual(codes, sorted(codes))

    def test_summary_recent_limiting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = 1000
            for idx in range(4):
                run_dir = self._make_run(root, f'run_{idx}')
                os.utime(run_dir, (base + idx * 10, base + idx * 10))
            with self._clean_patches(mode='trace'):
                report = build_dual_authority_validation_window(None, runs_root=root, recent=2)
            self.assertEqual(report['runs_scanned'], 2)

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._make_run(root, 'run_cli_json')
            proc = subprocess.run(
                ['python3', 'scripts/maintenance/dual_authority_validation.py', '--latest', '--json', '--runs-root', str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn('status', payload)
            self.assertIn('validation', payload)

    def test_cli_strict_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = self._make_run(root, 'run_cli_strict')
            (run_dir / 'ledger.jsonl').write_text('{bad}\n', encoding='utf-8')
            proc = subprocess.run(
                ['python3', 'scripts/maintenance/dual_authority_validation.py', '--latest', '--strict', '--runs-root', str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_no_runtime_mutation_and_no_auto_switch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_nomut')
            trace_before = (run_dir / 'trace.jsonl').read_text(encoding='utf-8')
            ledger_before = (run_dir / 'ledger.jsonl').read_text(encoding='utf-8')

            _ = evaluate_dual_authority_validation(run_dir)

            self.assertEqual((run_dir / 'trace.jsonl').read_text(encoding='utf-8'), trace_before)
            self.assertEqual((run_dir / 'ledger.jsonl').read_text(encoding='utf-8'), ledger_before)
            self.assertEqual(evaluate_dual_authority_validation(run_dir)['authority']['mode'], 'trace')


if __name__ == '__main__':
    unittest.main(verbosity=2)
