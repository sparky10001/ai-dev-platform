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
from runtime.ledger_cutover_decision_gate import (
    build_ledger_cutover_decision_gate,
    evaluate_ledger_cutover_eligibility,
    ledger_cutover_blockers,
)
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerCutoverDecisionGateTests(unittest.TestCase):
    def _make_run(self, root: Path, run_id: str) -> Path:
        run_dir = root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        run = {'id': run_id, 'run_path': str(run_dir), 'trace_path': str(run_dir / 'trace.jsonl')}
        append_trace_event(run, 'session_start', {'command': 'hello'})
        append_trace_event(run, 'agent_output', {'status': 'done', 'output': 'ok'})
        append_trace_event(run, 'session_end', {'status': 'done'})
        write_ledger_index(run_dir)
        return run_dir

    def _patched_deps(
        self,
        *,
        matrix_status: str = 'ready',
        dual_status: str = 'ready',
        sim_status: str = 'ready',
        compat_blockers: int = 0,
        rollback_supported: bool = True,
        retained_count: int = 0,
        candidate_count: int = 0,
        replay_status: str = 'ready',
        evals_status: str = 'ready',
        registry_status: str = 'ready',
        drift_status: str = 'ready',
        corruption_status: str = 'ready',
        control_plane_status: str = 'ready',
    ):
        matrix = {
            'status': matrix_status,
            'decision': {'recommended_mode': 'canary', 'cutover_ready': matrix_status != 'blocked', 'ledger_default_safe': matrix_status != 'blocked'},
            'warnings': ['compatibility_warning'] if matrix_status == 'warning' else [],
            'matrix': {
                'drift': {'status': drift_status, 'detected': drift_status == 'blocked'},
                'corruption': {'status': corruption_status, 'detected': corruption_status == 'blocked'},
                'replay': {'status': replay_status},
                'evals': {'status': evals_status},
                'registry': {'status': registry_status},
                'control_plane': {'status': control_plane_status},
                'rollback': {'supported': rollback_supported, 'method': 'env_unset', 'commands': ['unset RUNTIME_LEDGER_CANARY']},
            },
        }
        dual = {'status': dual_status, 'warnings': ['dual_validation_inactive'] if dual_status == 'warning' else []}
        simulation = {
            'status': sim_status,
            'warnings': ['future_deprecation_candidates'] if sim_status == 'warning' else [],
            'rollback': {'supported': rollback_supported, 'method': 'env_unset', 'commands': ['unset RUNTIME_LEDGER_CANARY']},
        }
        compatibility = {
            'status': 'blocked' if compat_blockers else 'ok',
            'summary': {'cutover_blocker_count': compat_blockers},
            'cutover_blockers': [{}] * compat_blockers,
        }
        deprecation = {
            'status': 'informational',
            'summary': {'total_references': 1},
            'retained': [{}] * retained_count,
            'candidates': [{}] * candidate_count,
            'operational': [],
        }
        transition = {
            'current_default': 'trace',
            'effective_mode': 'trace',
            'canary_enabled': False,
            'authoritative_enabled': False,
            'dry_run_enabled': False,
            'default_cutover_performed': False,
            'trace_emission_enabled': True,
            'rollback_supported': rollback_supported,
            'rollback_method': 'env_unset',
            'rollback_unset': ['RUNTIME_LEDGER_CANARY', 'RUNTIME_LEDGER_AUTHORITATIVE'],
        }

        stack = ExitStack()
        stack.enter_context(patch('runtime.ledger_cutover_decision_gate.evaluate_ledger_authority_readiness', return_value=matrix))
        stack.enter_context(patch('runtime.ledger_cutover_decision_gate.evaluate_dual_authority_validation', return_value=dual))
        stack.enter_context(patch('runtime.ledger_cutover_decision_gate.evaluate_default_authority_simulation', return_value=simulation))
        stack.enter_context(patch('runtime.ledger_cutover_decision_gate.audit_trace_compatibility', return_value=compatibility))
        stack.enter_context(patch('runtime.ledger_cutover_decision_gate.build_trace_deprecation_inventory', return_value=deprecation))
        stack.enter_context(patch('runtime.ledger_cutover_decision_gate.runtime_authority_transition_state', return_value=transition))
        return stack

    def test_eligible_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_eligible')
            with self._patched_deps():
                report = evaluate_ledger_cutover_eligibility(run_dir)
            self.assertEqual(report['status'], 'eligible')
            self.assertTrue(report['decision']['cutover_approved'])

    def test_conditional_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_conditional')
            with self._patched_deps(matrix_status='warning', dual_status='warning', sim_status='warning', retained_count=1, candidate_count=1):
                report = evaluate_ledger_cutover_eligibility(run_dir)
            self.assertEqual(report['status'], 'conditional')
            self.assertIn('compatibility_retained', report['conditions'])

    def test_blocked_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_blocked')
            with self._patched_deps(matrix_status='blocked', compat_blockers=1):
                report = evaluate_ledger_cutover_eligibility(run_dir)
            self.assertEqual(report['status'], 'blocked')
            self.assertFalse(report['decision']['future_cutover_safe'])

    def test_deterministic_blocker_ordering(self) -> None:
        payload = {
            'governance': {
                'authority_matrix': {'status': 'blocked', 'matrix': {'drift': {'status': 'blocked'}, 'corruption': {'status': 'blocked'}, 'replay': {'status': 'blocked'}, 'evals': {'status': 'blocked'}, 'registry': {'status': 'blocked'}, 'control_plane': {'status': 'blocked'}}},
                'dual_validation': {'status': 'blocked'},
                'default_authority_simulation': {'status': 'blocked'},
                'compatibility': {'summary': {'cutover_blocker_count': 1}},
                'rollback': {'supported': False},
            }
        }
        blockers = ledger_cutover_blockers(payload)
        self.assertEqual(blockers, sorted(blockers, key=lambda item: (item['code'], item['area'], item['message'])))

    def test_deterministic_condition_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_conditions')
            with self._patched_deps(matrix_status='warning', dual_status='warning', sim_status='warning', retained_count=1, candidate_count=1):
                report = evaluate_ledger_cutover_eligibility(run_dir)
            self.assertEqual(report['conditions'], sorted(report['conditions']))

    def test_governance_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_props')
            with self._patched_deps():
                report = evaluate_ledger_cutover_eligibility(run_dir)
            gov = report['governance']
            self.assertIn('authority_matrix', gov)
            self.assertIn('dual_validation', gov)
            self.assertIn('default_authority_simulation', gov)
            self.assertIn('compatibility', gov)
            self.assertIn('deprecation_inventory', gov)
            self.assertIn('rollback', gov)

    def test_summary_recent_limiting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = 1000
            for idx in range(4):
                run_dir = self._make_run(root, f'run_{idx}')
                os.utime(run_dir, (base + idx * 10, base + idx * 10))
            with self._patched_deps():
                report = build_ledger_cutover_decision_gate(None, runs_root=root, recent=2)
            self.assertEqual(report['runs_scanned'], 2)

    def test_cli_json_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._make_run(root, 'run_cli_json')
            proc = subprocess.run(
                ['python3', 'scripts/maintenance/ledger_cutover_decision_gate.py', '--latest', '--json', '--runs-root', str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn('decision', payload)
            self.assertIn('governance', payload)

    def test_cli_strict_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = self._make_run(root, 'run_cli_strict')
            (run_dir / 'ledger.jsonl').write_text('{bad}\n', encoding='utf-8')
            proc = subprocess.run(
                ['python3', 'scripts/maintenance/ledger_cutover_decision_gate.py', '--latest', '--strict', '--runs-root', str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_no_authority_or_runtime_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), 'run_no_mut')
            trace_before = (run_dir / 'trace.jsonl').read_text(encoding='utf-8')
            ledger_before = (run_dir / 'ledger.jsonl').read_text(encoding='utf-8')
            before_flag = os.environ.get('RUNTIME_LEDGER_AUTHORITATIVE')

            _ = evaluate_ledger_cutover_eligibility(run_dir)

            self.assertEqual((run_dir / 'trace.jsonl').read_text(encoding='utf-8'), trace_before)
            self.assertEqual((run_dir / 'ledger.jsonl').read_text(encoding='utf-8'), ledger_before)
            self.assertEqual(os.environ.get('RUNTIME_LEDGER_AUTHORITATIVE'), before_flag)


if __name__ == '__main__':
    unittest.main(verbosity=2)
