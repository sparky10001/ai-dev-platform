#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.authority_policy import runtime_authority_transition_state
from runtime.default_authority_simulation import evaluate_default_authority_simulation
from runtime.dual_authority_validation import evaluate_dual_authority_validation
from runtime.ledger_authority_matrix import evaluate_ledger_authority_readiness
from runtime.loader import RUNS_DIR
from runtime.trace_compatibility import audit_trace_compatibility, summarize_trace_dependencies
from runtime.trace_deprecation_inventory import build_trace_deprecation_inventory


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _run_dirs(runs_root: Path, recent: int | None = None) -> list[Path]:
    if not runs_root.exists():
        return []
    runs = [p for p in runs_root.iterdir() if p.is_dir()]
    runs = sorted(runs, key=lambda p: (-p.stat().st_mtime, p.name))
    if recent is not None:
        runs = runs[: max(0, recent)]
    return runs


def _resolve_target(run_or_path: str | Path | None, runs_root: Path) -> Path:
    if run_or_path is None:
        runs = _run_dirs(runs_root, recent=1)
        if not runs:
            raise FileNotFoundError(f'No run directories found under: {runs_root}')
        return runs[0]
    candidate = Path(run_or_path)
    if candidate.exists():
        return candidate
    return runs_root / str(run_or_path)


def _decision_payload() -> dict[str, Any]:
    transition = runtime_authority_transition_state()
    return {
        'cutover_approved': False,
        'future_cutover_safe': False,
        'actual_default': str(transition.get('current_default', 'trace')),
        'simulated_default': 'ledger',
        'authority_switch_performed': False,
    }


def _governance_snapshot(
    matrix: dict[str, Any],
    dual: dict[str, Any],
    simulation: dict[str, Any],
    compatibility: dict[str, Any],
    deprecation: dict[str, Any],
) -> dict[str, Any]:
    rollback = dict(simulation.get('rollback', {}))
    if not rollback:
        rollback = dict(matrix.get('matrix', {}).get('rollback', {}))
    return {
        'authority_matrix': matrix,
        'dual_validation': dual,
        'default_authority_simulation': simulation,
        'compatibility': compatibility,
        'deprecation_inventory': {
            'status': deprecation.get('status', 'informational'),
            'summary': dict(deprecation.get('summary', {})),
            'candidate_count': len(deprecation.get('candidates', [])),
            'retained_count': len(deprecation.get('retained', [])),
            'operational_count': len(deprecation.get('operational', [])),
        },
        'rollback': rollback,
    }


def ledger_cutover_blockers(gate: dict[str, Any]) -> list[dict[str, Any]]:
    g = gate.get('governance', {})
    blockers: list[dict[str, Any]] = []

    matrix = g.get('authority_matrix', {})
    dual = g.get('dual_validation', {})
    sim = g.get('default_authority_simulation', {})
    compat = g.get('compatibility', {})

    if matrix.get('status') == 'blocked':
        blockers.append({'area': 'authority_matrix', 'code': 'authority_matrix_blocked', 'message': 'Authority readiness matrix is blocked'})
    if dual.get('status') == 'blocked':
        blockers.append({'area': 'dual_validation', 'code': 'dual_validation_blocked', 'message': 'Dual-authority validation is blocked'})
    if sim.get('status') == 'blocked':
        blockers.append({'area': 'simulation', 'code': 'default_simulation_blocked', 'message': 'Default authority simulation is blocked'})

    if int(compat.get('summary', {}).get('cutover_blocker_count', 0)) > 0:
        blockers.append({'area': 'compatibility', 'code': 'compatibility_blockers', 'message': 'Trace compatibility blockers present'})

    for area in ('drift', 'corruption', 'replay', 'evals', 'registry', 'control_plane'):
        status = matrix.get('matrix', {}).get(area, {}).get('status')
        if status == 'blocked':
            blockers.append({'area': area, 'code': f'{area}_blocked', 'message': f'{area} is blocked'})

    if not bool(g.get('rollback', {}).get('supported', False)):
        blockers.append({'area': 'rollback', 'code': 'rollback_missing', 'message': 'Rollback capability not available'})

    return sorted(blockers, key=lambda item: (item.get('code', ''), item.get('area', ''), item.get('message', '')))


def _conditions(gate: dict[str, Any]) -> list[str]:
    if gate.get('blockers'):
        return []
    g = gate.get('governance', {})
    conditions: list[str] = []

    if int(g.get('deprecation_inventory', {}).get('retained_count', 0)) > 0:
        conditions.append('compatibility_retained')
    if int(g.get('deprecation_inventory', {}).get('candidate_count', 0)) > 0:
        conditions.append('future_deprecation_candidates')

    conditions.extend(str(item) for item in g.get('authority_matrix', {}).get('warnings', []))
    conditions.extend(str(item) for item in g.get('dual_validation', {}).get('warnings', []))
    conditions.extend(str(item) for item in g.get('default_authority_simulation', {}).get('warnings', []))

    return sorted(dict.fromkeys(conditions))


def _recommendations(status: str, gate: dict[str, Any]) -> list[str]:
    g = gate.get('governance', {})
    matrix = g.get('authority_matrix', {})
    recs: list[str] = []

    if status == 'blocked':
        return ['not eligible for cutover']

    recs.append('eligible for future cutover planning')

    mode = str(matrix.get('decision', {}).get('recommended_mode', 'trace'))
    if mode in {'canary', 'authoritative'}:
        recs.append('eligible for extended canary operation')
    if mode == 'authoritative':
        recs.append('eligible for authoritative testing only')

    if status == 'conditional':
        recs.append('conditionally eligible pending governance cleanup')

    return recs


def _single_gate(
    target: Path,
    *,
    deprecation: dict[str, Any] | None = None,
    compatibility_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    matrix = evaluate_ledger_authority_readiness(target)
    dual = evaluate_dual_authority_validation(target)
    simulation = evaluate_default_authority_simulation(target)
    compatibility_report = compatibility_report if compatibility_report is not None else summarize_trace_dependencies(audit_trace_compatibility())
    dep = deprecation if deprecation is not None else build_trace_deprecation_inventory()

    gate = {
        'status': 'eligible',
        'decision': _decision_payload(),
        'governance': _governance_snapshot(matrix, dual, simulation, compatibility_report, dep),
        'blockers': [],
        'conditions': [],
        'recommendations': [],
        'generated_at': _now_iso(),
    }

    blockers = ledger_cutover_blockers(gate)
    conditions = _conditions(gate | {'blockers': blockers})

    status = 'eligible'
    if blockers:
        status = 'blocked'
    elif conditions:
        status = 'conditional'

    gate['status'] = status
    gate['blockers'] = blockers
    gate['conditions'] = conditions
    gate['recommendations'] = _recommendations(status, gate)
    gate['decision']['future_cutover_safe'] = status != 'blocked'
    gate['decision']['cutover_approved'] = status == 'eligible'
    return gate


def _aggregate_gate(runs_root: Path, recent: int | None = None) -> dict[str, Any]:
    runs = _run_dirs(runs_root, recent=recent)
    dep = build_trace_deprecation_inventory()
    compat = summarize_trace_dependencies(audit_trace_compatibility())

    if not runs:
        gate = {
            'status': 'conditional',
            'decision': _decision_payload(),
            'governance': {
                'authority_matrix': {},
                'dual_validation': {},
                'default_authority_simulation': {},
                'compatibility': compat,
                'deprecation_inventory': {
                    'status': dep.get('status', 'informational'),
                    'summary': dict(dep.get('summary', {})),
                    'candidate_count': len(dep.get('candidates', [])),
                    'retained_count': len(dep.get('retained', [])),
                    'operational_count': len(dep.get('operational', [])),
                },
                'rollback': {'supported': True, 'method': 'env_unset', 'commands': []},
            },
            'blockers': [],
            'conditions': ['no_runs_available'],
            'recommendations': ['conditionally eligible pending governance cleanup'],
            'runs_scanned': 0,
            'generated_at': _now_iso(),
        }
        gate['decision']['future_cutover_safe'] = True
        gate['decision']['cutover_approved'] = False
        return gate

    # Bounded summary mode evaluates the latest representative run and surfaces
    # deterministic governance state while preserving recent-scan accounting.
    sample = _single_gate(runs[0], deprecation=dep, compatibility_report=compat)
    gate = {
        'status': sample.get('status', 'conditional'),
        'decision': dict(sample.get('decision', {})),
        'governance': dict(sample.get('governance', {})),
        'blockers': [dict(item, run=runs[0].name) for item in sample.get('blockers', [])],
        'conditions': list(sample.get('conditions', [])),
        'recommendations': list(sample.get('recommendations', [])),
        'runs_scanned': len(runs),
        'generated_at': _now_iso(),
    }
    return gate


def build_ledger_cutover_decision_gate(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    root = Path(runs_root) if runs_root is not None else RUNS_DIR
    if recent is not None and recent < 0:
        raise ValueError('recent must be >= 0')

    if run_or_path is None:
        return _aggregate_gate(root, recent=recent)

    target = _resolve_target(run_or_path, root)
    return _single_gate(target)


def evaluate_ledger_cutover_eligibility(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    return build_ledger_cutover_decision_gate(run_or_path, runs_root=runs_root, recent=recent)
