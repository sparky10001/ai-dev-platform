#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.authority_policy import runtime_authority_transition_state
from runtime.event_ledger import evaluate_ledger_default_readiness
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


def _status_from_bool(ok: bool) -> str:
    return 'ready' if ok else 'blocked'


def _rollback_payload() -> dict[str, Any]:
    transition = runtime_authority_transition_state()
    unset = list(transition.get('rollback_unset', []))
    commands = [f'unset {name}' for name in unset]
    return {
        'status': 'ready' if bool(transition.get('rollback_supported', False)) else 'blocked',
        'supported': bool(transition.get('rollback_supported', False)),
        'method': transition.get('rollback_method', 'env_unset'),
        'commands': commands,
        'unset': unset,
    }


def _single_window(target: Path) -> dict[str, Any]:
    transition = runtime_authority_transition_state()
    mode = str(transition.get('effective_mode', 'trace'))
    dual_active = mode in {'canary', 'authoritative'}

    drift_report = compare_trace_and_ledger(target, strict=False)
    corruption_report = classify_ledger_corruption(target)
    health_report = ledger_health_report(target)
    compatibility_report = summarize_trace_dependencies(audit_trace_compatibility('.'))
    dry_run_report = evaluate_ledger_default_readiness(target)

    drift_flag = bool(dry_run_report.get('drift_detected') or drift_detected(drift_report))
    corruption_flag = bool(dry_run_report.get('corruption_detected') or corruption_report.get('corruption_categories'))

    replay_ok = bool(dry_run_report.get('replay_ledger_ready')) and bool(drift_report.get('replay_summary_match'))
    eval_ok = bool(dry_run_report.get('eval_ledger_ready')) and bool(drift_report.get('eval_summary_match'))
    registry_ok = bool(dry_run_report.get('registry_ledger_ready')) and bool(drift_report.get('registry_summary_match'))

    validation = {
        'drift': {
            'status': _status_from_bool(not drift_flag),
            'detected': drift_flag,
            'categories': list(drift_report.get('drift_categories', [])),
        },
        'corruption': {
            'status': _status_from_bool(not corruption_flag),
            'detected': corruption_flag,
            'categories': list(corruption_report.get('corruption_categories', [])),
        },
        'health': {
            'status': health_report.get('status', 'warning'),
            'categories': list(health_report.get('categories', [])),
        },
        'compatibility': {
            'status': compatibility_report.get('status', 'warning'),
            'cutover_blocker_count': int(compatibility_report.get('summary', {}).get('cutover_blocker_count', 0)),
            'cutover_blockers': list(compatibility_report.get('cutover_blockers', [])),
        },
        'replay_parity': {
            'status': _status_from_bool(replay_ok),
            'parity_ok': replay_ok,
            'trace_ledger_match': bool(drift_report.get('replay_summary_match')),
            'ledger_ready': bool(dry_run_report.get('replay_ledger_ready')),
        },
        'eval_parity': {
            'status': _status_from_bool(eval_ok),
            'parity_ok': eval_ok,
            'trace_ledger_match': bool(drift_report.get('eval_summary_match')),
            'ledger_ready': bool(dry_run_report.get('eval_ledger_ready')),
        },
        'registry_parity': {
            'status': _status_from_bool(registry_ok),
            'parity_ok': registry_ok,
            'trace_ledger_match': bool(drift_report.get('registry_summary_match')),
            'ledger_ready': bool(dry_run_report.get('registry_ledger_ready')),
        },
        'rollback': _rollback_payload(),
    }

    window = {
        'authority': {
            'mode': mode,
            'dual_validation_active': dual_active,
            'trace_emission_enabled': bool(transition.get('trace_emission_enabled', True)),
        },
        'validation': validation,
    }

    blockers = dual_authority_validation_blockers(window)

    warnings: list[str] = []
    if validation['health']['status'] == 'warning':
        warnings.append('health_warning')
    if validation['compatibility']['status'] == 'warning':
        warnings.append('compatibility_warning')
    if not dual_active:
        warnings.append('dual_validation_inactive')

    status = 'ready'
    if blockers:
        status = 'blocked'
    elif warnings:
        status = 'warning'

    recommendations = ['remain trace-first']
    if dual_active and status == 'ready':
        recommendations.append('dual-authority validation window is healthy')
    if dual_active and status == 'warning':
        recommendations.append('keep canary/authoritative observational and monitor warnings')
    if status == 'blocked':
        recommendations.append('resolve drift/corruption/parity blockers before authority progression')

    return {
        'status': status,
        'authority': window['authority'],
        'validation': validation,
        'blockers': blockers,
        'warnings': sorted(set(warnings)),
        'recommendations': recommendations,
        'generated_at': _now_iso(),
    }


def _aggregate_window(runs_root: Path, recent: int | None = None) -> dict[str, Any]:
    runs = _run_dirs(runs_root, recent=recent)
    reports = [_single_window(run) for run in runs]

    status = 'ready'
    if any(r.get('status') == 'blocked' for r in reports):
        status = 'blocked'
    elif any(r.get('status') == 'warning' for r in reports):
        status = 'warning'

    blockers: list[dict[str, Any]] = []
    for report in reports:
        blockers.extend(report.get('blockers', []))
    blockers = sorted(
        blockers,
        key=lambda item: (item.get('code', ''), item.get('area', ''), item.get('message', '')),
    )

    warnings = sorted({w for report in reports for w in report.get('warnings', [])})

    transition = runtime_authority_transition_state()
    mode = str(transition.get('effective_mode', 'trace'))
    dual_active = mode in {'canary', 'authoritative'}

    validation = {
        'drift': {'status': status, 'runs_scanned': len(reports)},
        'corruption': {'status': status, 'runs_scanned': len(reports)},
        'health': aggregate_ledger_health(runs_root, recent=recent),
        'compatibility': summarize_trace_dependencies(audit_trace_compatibility('.')),
        'replay_parity': {'status': status},
        'eval_parity': {'status': status},
        'registry_parity': {'status': status},
        'rollback': _rollback_payload(),
    }

    recommendations = ['remain trace-first']
    if dual_active and status == 'ready':
        recommendations.append('dual-authority validation window is healthy')
    if dual_active and status == 'warning':
        recommendations.append('keep canary/authoritative observational and monitor warnings')
    if status == 'blocked':
        recommendations.append('resolve drift/corruption/parity blockers before authority progression')

    return {
        'status': status,
        'authority': {
            'mode': mode,
            'dual_validation_active': dual_active,
            'trace_emission_enabled': bool(transition.get('trace_emission_enabled', True)),
        },
        'validation': validation,
        'blockers': blockers,
        'warnings': warnings,
        'recommendations': recommendations,
        'runs_scanned': len(reports),
        'reports': reports,
        'generated_at': _now_iso(),
    }


def build_dual_authority_validation_window(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    root = Path(runs_root) if runs_root is not None else Path(RUNS_DIR)
    if recent is not None and recent < 0:
        raise ValueError('recent must be >= 0')

    if run_or_path is None:
        return _aggregate_window(root, recent=recent)

    target = _resolve_target(run_or_path, root)
    return _single_window(target)


def evaluate_dual_authority_validation(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    return build_dual_authority_validation_window(run_or_path, runs_root=runs_root, recent=recent)


def dual_authority_validation_blockers(window: dict[str, Any]) -> list[dict[str, Any]]:
    validation = window.get('validation', {})
    blockers: list[dict[str, Any]] = []

    if validation.get('drift', {}).get('detected'):
        blockers.append({'area': 'drift', 'code': 'drift_detected', 'message': 'Trace/ledger drift detected'})
    if validation.get('corruption', {}).get('detected'):
        blockers.append({'area': 'corruption', 'code': 'corruption_detected', 'message': 'Ledger corruption detected'})
    if validation.get('health', {}).get('status') in {'unhealthy', 'error'}:
        blockers.append({'area': 'health', 'code': 'health_unhealthy', 'message': 'Ledger health is unhealthy'})

    compatibility = validation.get('compatibility', {})
    if int(compatibility.get('cutover_blocker_count', 0)) > 0:
        blockers.append({'area': 'compatibility', 'code': 'compatibility_blockers', 'message': f"Trace compatibility blockers present: {compatibility.get('cutover_blocker_count')}"})

    if validation.get('replay_parity', {}).get('status') == 'blocked':
        blockers.append({'area': 'replay_parity', 'code': 'replay_parity_failed', 'message': 'Replay parity validation failed'})
    if validation.get('eval_parity', {}).get('status') == 'blocked':
        blockers.append({'area': 'eval_parity', 'code': 'eval_parity_failed', 'message': 'Eval parity validation failed'})
    if validation.get('registry_parity', {}).get('status') == 'blocked':
        blockers.append({'area': 'registry_parity', 'code': 'registry_parity_failed', 'message': 'Registry parity validation failed'})

    if not bool(validation.get('rollback', {}).get('supported', False)):
        blockers.append({'area': 'rollback', 'code': 'rollback_missing', 'message': 'Rollback capability not available'})

    return sorted(blockers, key=lambda item: (item.get('code', ''), item.get('area', ''), item.get('message', '')))
