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

from runtime.event_ledger import write_ledger_index
from runtime.ledger_authority_matrix import (
    build_ledger_authority_matrix,
    evaluate_ledger_authority_readiness,
    ledger_authority_cutover_blockers,
)
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerAuthorityMatrixTests(unittest.TestCase):
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

    def _clean_patches(self, **overrides):
        drift_report = {
            'drift_categories': [],
            'event_count_match': True,
            'event_sequence_match': True,
            'event_hash_match': True,
            'lifecycle_match': True,
        }
        corruption_report = {'corruption_categories': []}
        health_report = {
            'status': 'healthy',
            'categories': [],
            'maintenance': {'maintenance_enabled': True, 'stale': False},
            'replay_ok': True,
            'eval_ok': True,
            'registry_ok': True,
        }
        compat_report = {'status': 'ok', 'summary': {'cutover_blocker_count': 0}, 'cutover_blockers': []}
        boundary_report = {'status': 'ok', 'modules': [{'module': 'control-plane', 'status': 'ok', 'violations': []}], 'violations': []}
        purity_report = {'status': 'ok', 'modules': [], 'violations': []}
        canary_report = {
            'status': 'ready',
            'canary_enabled': True,
            'warnings': [],
            'blocking_reasons': [],
            'authoritative_effective': True,
        }
        dry_run_report = {
            'status': 'ready',
            'drift_detected': False,
            'corruption_detected': False,
            'parity_ok': True,
            'replay_ledger_ready': True,
            'eval_ledger_ready': True,
            'registry_ledger_ready': True,
            'warnings': [],
            'blocking_reasons': [],
        }
        aggregate_health = {'status': 'healthy', 'runs_scanned': 0, 'healthy_runs': 0, 'warning_runs': 0, 'unhealthy_runs': 0, 'reports': []}

        drift_report = overrides.get('drift_report', drift_report)
        corruption_report = overrides.get('corruption_report', corruption_report)
        health_report = overrides.get('health_report', health_report)
        compat_report = overrides.get('compat_report', compat_report)
        boundary_report = overrides.get('boundary_report', boundary_report)
        purity_report = overrides.get('purity_report', purity_report)
        canary_report = overrides.get('canary_report', canary_report)
        dry_run_report = overrides.get('dry_run_report', dry_run_report)
        aggregate_health = overrides.get('aggregate_health', aggregate_health)

        stack = ExitStack()
        stack.enter_context(patch('runtime.ledger_authority_matrix.compare_trace_and_ledger', return_value=drift_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.drift_detected', return_value=bool(drift_report.get('drift_categories'))))
        stack.enter_context(patch('runtime.ledger_authority_matrix.classify_ledger_corruption', return_value=corruption_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.ledger_health_report', return_value=health_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.audit_trace_compatibility', return_value=compat_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.summarize_trace_dependencies', return_value=compat_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.audit_runtime_boundaries', return_value=boundary_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.boundary_violations', return_value=list(boundary_report.get('violations', []))))
        stack.enter_context(patch('runtime.ledger_authority_matrix.audit_runtime_derived_purity', return_value=purity_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.derived_purity_violations', return_value=list(purity_report.get('violations', []))))
        stack.enter_context(patch('runtime.ledger_authority_matrix.evaluate_ledger_canary_readiness', return_value=canary_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.evaluate_ledger_default_readiness', return_value=dry_run_report))
        stack.enter_context(patch('runtime.ledger_authority_matrix.aggregate_ledger_health', return_value=aggregate_health))
        return stack

    def test_ready_matrix_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_ready')
            with self._clean_patches():
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['status'], 'ready')
            self.assertTrue(matrix['decision']['cutover_ready'])

    def test_warning_matrix_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_warning')
            with self._clean_patches(
                canary_report={'status': 'warning', 'canary_enabled': False, 'warnings': ['canary_disabled'], 'blocking_reasons': [], 'authoritative_effective': False},
                dry_run_report={'status': 'warning', 'drift_detected': False, 'corruption_detected': False, 'parity_ok': True, 'replay_ledger_ready': True, 'eval_ledger_ready': True, 'registry_ledger_ready': True, 'warnings': ['compatibility_warning'], 'blocking_reasons': []},
            ):
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['status'], 'warning')

    def test_blocked_matrix_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_blocked')
            with self._clean_patches(
                drift_report={'drift_categories': ['event_count_mismatch'], 'event_count_match': False, 'event_sequence_match': True, 'event_hash_match': True, 'lifecycle_match': True},
                dry_run_report={'status': 'blocked', 'drift_detected': True, 'corruption_detected': False, 'parity_ok': False, 'replay_ledger_ready': False, 'eval_ledger_ready': False, 'registry_ledger_ready': False, 'warnings': [], 'blocking_reasons': ['x']},
            ):
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['status'], 'blocked')

    def test_deterministic_blocker_ordering(self) -> None:
        blockers = ledger_authority_cutover_blockers(
            {
                'matrix': {
                    'replay': {'status': 'blocked'},
                    'evals': {'status': 'blocked'},
                    'registry': {'status': 'blocked'},
                    'drift': {'detected': True},
                    'corruption': {'detected': True},
                    'compatibility': {'cutover_blocker_count': 2},
                    'boundary': {'status': 'violations', 'violations': [{}]},
                    'purity': {'status': 'violations', 'violations': [{}]},
                    'control_plane': {'status': 'blocked'},
                    'rollback': {'supported': False},
                    'health': {'status': 'unhealthy'},
                }
            }
        )
        codes = [item['code'] for item in blockers]
        self.assertEqual(codes, sorted(codes))

    def test_rollback_payload_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_rollback')
            with self._clean_patches():
                matrix = build_ledger_authority_matrix(run_dir)
            rollback = matrix['matrix']['rollback']
            self.assertTrue(rollback['supported'])
            self.assertEqual(rollback['method'], 'env_unset')
            self.assertEqual(
                rollback['unset'],
                [
                    'RUNTIME_LEDGER_CANARY',
                    'RUNTIME_LEDGER_AUTHORITATIVE',
                    'RUNTIME_LEDGER_PARITY_REQUIRED',
                    'RUNTIME_LEDGER_CANARY_PARITY_REQUIRED',
                ],
            )

    def test_canary_recommendation_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_canary_rec')
            with self._clean_patches(
                canary_report={'status': 'warning', 'canary_enabled': False, 'warnings': ['canary_disabled'], 'blocking_reasons': [], 'authoritative_effective': False},
                dry_run_report={'status': 'warning', 'drift_detected': False, 'corruption_detected': False, 'parity_ok': True, 'replay_ledger_ready': True, 'eval_ledger_ready': True, 'registry_ledger_ready': True, 'warnings': ['compatibility_warning'], 'blocking_reasons': []},
            ):
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['decision']['recommended_mode'], 'canary')

    def test_authoritative_recommendation_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_auth_rec')
            with self._clean_patches():
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['decision']['recommended_mode'], 'authoritative')

    def test_compatibility_blocker_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_comp_block')
            compat = {'status': 'blocked', 'summary': {'cutover_blocker_count': 1}, 'cutover_blockers': [{'path': 'runtime/x.py', 'reason': 'x'}]}
            with self._clean_patches(compat_report=compat):
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['status'], 'blocked')
            self.assertTrue(any(b['code'] == 'trace_cutover_blockers' for b in matrix['blockers']))

    def test_drift_corruption_purity_boundary_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_pb')
            boundary = {'status': 'violations', 'modules': [], 'violations': [{'module': 'runtime/replay.py'}]}
            purity = {'status': 'violations', 'modules': [], 'violations': [{'module': 'runtime/evals.py'}]}
            with self._clean_patches(
                drift_report={'drift_categories': ['event_count_mismatch'], 'event_count_match': False, 'event_sequence_match': False, 'event_hash_match': False, 'lifecycle_match': False},
                corruption_report={'corruption_categories': ['malformed_ndjson']},
                boundary_report=boundary,
                purity_report=purity,
                dry_run_report={'status': 'blocked', 'drift_detected': True, 'corruption_detected': True, 'parity_ok': False, 'replay_ledger_ready': False, 'eval_ledger_ready': False, 'registry_ledger_ready': False, 'warnings': [], 'blocking_reasons': ['x']},
            ):
                matrix = build_ledger_authority_matrix(run_dir)
            codes = {b['code'] for b in matrix['blockers']}
            self.assertIn('drift_detected', codes)
            self.assertIn('corruption_detected', codes)
            self.assertIn('boundary_violations', codes)
            self.assertIn('purity_violations', codes)

    def test_control_plane_compatibility_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_cp')
            compat = {'status': 'blocked', 'summary': {'cutover_blocker_count': 1}, 'cutover_blockers': [{'path': 'control-plane/core/x.py', 'reason': 'x'}]}
            with self._clean_patches(compat_report=compat):
                matrix = build_ledger_authority_matrix(run_dir)
            self.assertEqual(matrix['matrix']['control_plane']['status'], 'blocked')

    def test_summary_recent_limiting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = 1000
            for idx in range(4):
                run_dir = self._make_run(root, f'run_{idx}')
                os.utime(run_dir, (base + idx * 10, base + idx * 10))
            with self._clean_patches():
                matrix = build_ledger_authority_matrix(None, runs_root=root, recent=2)
            self.assertEqual(matrix['runs_scanned'], 2)

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._make_run(root, 'run_cli_json')
            proc = subprocess.run(
                ['python3', 'scripts/maintenance/ledger_authority_matrix.py', '--latest', '--json', '--runs-root', str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn('status', payload)
            self.assertIn('matrix', payload)

    def test_cli_strict_exit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = self._make_run(root, 'run_cli_strict')
            (run_dir / 'ledger.jsonl').write_text('{bad}\n', encoding='utf-8')
            proc = subprocess.run(
                ['python3', 'scripts/maintenance/ledger_authority_matrix.py', '--latest', '--strict', '--runs-root', str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_no_runtime_mutation_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_nomut')
            trace_before = (run_dir / 'trace.jsonl').read_text(encoding='utf-8')
            ledger_before = (run_dir / 'ledger.jsonl').read_text(encoding='utf-8')
            with self._clean_patches():
                _ = evaluate_ledger_authority_readiness(run_dir)
            self.assertEqual((run_dir / 'trace.jsonl').read_text(encoding='utf-8'), trace_before)
            self.assertEqual((run_dir / 'ledger.jsonl').read_text(encoding='utf-8'), ledger_before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
