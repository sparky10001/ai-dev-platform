#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.boundary_audit import audit_runtime_boundaries, boundary_violations
from runtime.derived_purity import audit_runtime_derived_purity, derived_purity_violations
from runtime.authority_policy import runtime_authority_transition_state
from runtime.event_ledger import evaluate_ledger_canary_readiness, evaluate_ledger_default_readiness, ledger_authoritative_enabled, ledger_canary_enabled
from runtime.ledger_corruption import classify_ledger_corruption
from runtime.ledger_drift import compare_trace_and_ledger, drift_detected
from runtime.ledger_health import aggregate_ledger_health, ledger_health_report
from runtime.loader import RUNS_DIR
from runtime.trace_compatibility import audit_trace_compatibility, summarize_trace_dependencies


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


def _authority_transition() -> dict[str, Any]:
    return runtime_authority_transition_state()


def _rollback_payload() -> dict[str, Any]:
    transition = runtime_authority_transition_state()
    unset = list(transition.get('rollback_unset', []))
    commands = [f'unset {name}' for name in unset]
    return {
        'supported': bool(transition.get('rollback_supported', False)),
        'method': transition.get('rollback_method', 'env_unset'),
        'commands': commands,
        'unset': unset,
    }


def _single_matrix(target: Path) -> dict[str, Any]:
    drift_report = compare_trace_and_ledger(target, strict=False)
    corruption_report = classify_ledger_corruption(target)
    health_report = ledger_health_report(target)
    compat_report = audit_trace_compatibility('.')
    compat_summary = summarize_trace_dependencies(compat_report)
    boundary_report = audit_runtime_boundaries()
    purity_report = audit_runtime_derived_purity()
    canary_report = evaluate_ledger_canary_readiness(target)
    dry_run_report = evaluate_ledger_default_readiness(target)

    boundary_issues = boundary_violations(boundary_report)
    purity_issues = derived_purity_violations(purity_report)
    compat_blockers = compat_summary.get('cutover_blockers', [])
    control_plane_blockers = [b for b in compat_blockers if str(b.get('path', '')).startswith('control-plane/')]

    replay_ready = bool(dry_run_report.get('replay_ledger_ready'))
    eval_ready = bool(dry_run_report.get('eval_ledger_ready'))
    registry_ready = bool(dry_run_report.get('registry_ledger_ready'))
    drift_flag = bool(dry_run_report.get('drift_detected') or drift_detected(drift_report))
    corruption_flag = bool(dry_run_report.get('corruption_detected') or corruption_report.get('corruption_categories'))

    matrix = {
        'drift': {
            'status': 'blocked' if drift_flag else 'ready',
            'detected': drift_flag,
            'categories': list(drift_report.get('drift_categories', [])),
        },
        'corruption': {
            'status': 'blocked' if corruption_flag else 'ready',
            'detected': corruption_flag,
            'categories': list(corruption_report.get('corruption_categories', [])),
        },
        'health': {
            'status': health_report.get('status', 'warning'),
            'categories': list(health_report.get('categories', [])),
        },
        'compatibility': {
            'status': compat_summary.get('status', 'warning'),
            'cutover_blocker_count': int(compat_summary.get('summary', {}).get('cutover_blocker_count', 0)),
            'cutover_blockers': compat_summary.get('cutover_blockers', []),
        },
        'boundary': {
            'status': boundary_report.get('status', 'violations'),
            'violations': boundary_issues,
        },
        'purity': {
            'status': purity_report.get('status', 'violations'),
            'violations': purity_issues,
        },
        'canary': {
            'status': canary_report.get('status', 'warning'),
            'canary_enabled': bool(canary_report.get('canary_enabled')),
            'authoritative_effective': bool(canary_report.get('authoritative_effective')),
            'warnings': list(canary_report.get('warnings', [])),
            'blocking_reasons': list(canary_report.get('blocking_reasons', [])),
        },
        'dry_run': {
            'status': dry_run_report.get('status', 'warning'),
            'warnings': list(dry_run_report.get('warnings', [])),
            'blocking_reasons': list(dry_run_report.get('blocking_reasons', [])),
        },
        'replay': {
            'status': 'ready' if replay_ready else 'blocked',
            'ledger_ready': replay_ready,
        },
        'evals': {
            'status': 'ready' if eval_ready else 'blocked',
            'ledger_ready': eval_ready,
        },
        'registry': {
            'status': 'ready' if registry_ready else 'blocked',
            'ledger_ready': registry_ready,
        },
        'control_plane': {
            'status': 'blocked' if (control_plane_blockers or any(v.get('module', '').startswith('control-plane') for v in boundary_issues)) else 'ready',
            'compatibility_blockers': control_plane_blockers,
            'boundary_violations': [v for v in boundary_issues if str(v.get('module', '')).startswith('control-plane')],
        },
        'rollback': _rollback_payload(),
    }

    blockers = ledger_authority_cutover_blockers({'matrix': matrix})
    warnings: list[str] = []
    if matrix['health']['status'] == 'warning':
        warnings.append('health_warning')
    if matrix['compatibility']['status'] == 'warning':
        warnings.append('compatibility_warning')
    if not matrix['canary']['canary_enabled']:
        warnings.append('canary_disabled')

    status = 'ready'
    if blockers:
        status = 'blocked'
    elif warnings:
        status = 'warning'

    decision = {
        'ledger_default_safe': status == 'ready',
        'recommended_mode': 'trace',
        'cutover_ready': status == 'ready',
    }
    if status == 'warning':
        decision['recommended_mode'] = 'canary'
    if status == 'ready' and not ledger_authoritative_enabled():
        decision['recommended_mode'] = 'authoritative'

    recommendations = ['remain trace-first']
    if status == 'warning':
        recommendations.append('use canary for controlled validation')
    if status == 'ready':
        recommendations.append('safe for authoritative testing')
    if status == 'blocked':
        recommendations.append('not cutover ready')

    payload = {
        'status': status,
        'decision': decision,
        'authority_transition': _authority_transition(),
        'matrix': matrix,
        'blockers': blockers,
        'warnings': sorted(set(warnings)),
        'recommendations': recommendations,
        'generated_at': _now_iso(),
    }
    return payload


def _aggregate_matrix(runs_root: Path, recent: int | None = None) -> dict[str, Any]:
    runs = _run_dirs(runs_root, recent=recent)
    reports = [_single_matrix(run) for run in runs]

    status = 'ready'
    if any(r.get('status') == 'blocked' for r in reports):
        status = 'blocked'
    elif any(r.get('status') == 'warning' for r in reports):
        status = 'warning'

    blockers = []
    for report in reports:
        blockers.extend(report.get('blockers', []))
    blockers = sorted(blockers, key=lambda item: (item.get('code', ''), item.get('area', ''), item.get('message', '')))

    warnings = sorted({w for report in reports for w in report.get('warnings', [])})

    decision = {
        'ledger_default_safe': status == 'ready',
        'recommended_mode': 'trace' if status == 'blocked' else ('canary' if status == 'warning' else 'authoritative'),
        'cutover_ready': status == 'ready',
    }

    recommendations = ['remain trace-first']
    if status == 'warning':
        recommendations.append('use canary for controlled validation')
    if status == 'ready':
        recommendations.append('safe for authoritative testing')
    if status == 'blocked':
        recommendations.append('not cutover ready')

    return {
        'status': status,
        'decision': decision,
        'authority_transition': _authority_transition(),
        'matrix': {
            'drift': {'status': status, 'runs_scanned': len(reports)},
            'corruption': {'status': status, 'runs_scanned': len(reports)},
            'health': aggregate_ledger_health(runs_root, recent=recent),
            'compatibility': summarize_trace_dependencies(audit_trace_compatibility('.')),
            'boundary': {'status': audit_runtime_boundaries().get('status')},
            'purity': {'status': audit_runtime_derived_purity().get('status')},
            'canary': {'enabled': ledger_canary_enabled()},
            'dry_run': {'status': status},
            'replay': {'status': status},
            'evals': {'status': status},
            'registry': {'status': status},
            'control_plane': {'status': status},
            'rollback': _rollback_payload(),
        },
        'blockers': blockers,
        'warnings': warnings,
        'recommendations': recommendations,
        'runs_scanned': len(reports),
        'reports': reports,
        'generated_at': _now_iso(),
    }


def build_ledger_authority_matrix(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    root = Path(runs_root) if runs_root is not None else Path(RUNS_DIR)
    if recent is not None and recent < 0:
        raise ValueError('recent must be >= 0')

    if run_or_path is None:
        return _aggregate_matrix(root, recent=recent)

    target = _resolve_target(run_or_path, root)
    return _single_matrix(target)


def evaluate_ledger_authority_readiness(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    return build_ledger_authority_matrix(run_or_path, runs_root=runs_root, recent=recent)


def ledger_authority_cutover_blockers(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    m = matrix.get('matrix', {})
    blockers: list[dict[str, Any]] = []

    if m.get('drift', {}).get('detected'):
        blockers.append({'area': 'drift', 'code': 'drift_detected', 'message': 'Trace/ledger drift detected'})
    if m.get('corruption', {}).get('detected'):
        blockers.append({'area': 'corruption', 'code': 'corruption_detected', 'message': 'Ledger corruption detected'})
    if m.get('health', {}).get('status') in {'unhealthy', 'error'}:
        blockers.append({'area': 'health', 'code': 'health_unhealthy', 'message': 'Ledger health is unhealthy'})

    compat = m.get('compatibility', {})
    if int(compat.get('cutover_blocker_count', 0)) > 0:
        blockers.append({'area': 'compatibility', 'code': 'trace_cutover_blockers', 'message': f"Trace cutover blockers present: {compat.get('cutover_blocker_count')}"})

    if m.get('boundary', {}).get('status') == 'violations' or m.get('boundary', {}).get('violations'):
        blockers.append({'area': 'boundary', 'code': 'boundary_violations', 'message': 'Runtime boundary audit violations detected'})
    if m.get('purity', {}).get('status') == 'violations' or m.get('purity', {}).get('violations'):
        blockers.append({'area': 'purity', 'code': 'purity_violations', 'message': 'Derived purity violations detected'})

    if m.get('replay', {}).get('status') == 'blocked':
        blockers.append({'area': 'replay', 'code': 'replay_not_ready', 'message': 'Replay is not ledger-ready'})
    if m.get('evals', {}).get('status') == 'blocked':
        blockers.append({'area': 'evals', 'code': 'evals_not_ready', 'message': 'Evals are not ledger-ready'})
    if m.get('registry', {}).get('status') == 'blocked':
        blockers.append({'area': 'registry', 'code': 'registry_not_ready', 'message': 'Registry is not ledger-ready'})

    if m.get('control_plane', {}).get('status') == 'blocked':
        blockers.append({'area': 'control_plane', 'code': 'control_plane_incompatibility', 'message': 'Control-plane compatibility blockers detected'})

    rollback_supported = bool(m.get('rollback', {}).get('supported', False))
    if not rollback_supported:
        blockers.append({'area': 'rollback', 'code': 'rollback_missing', 'message': 'Rollback capability not available'})

    return sorted(blockers, key=lambda item: (item.get('code', ''), item.get('area', ''), item.get('message', '')))
