#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.dual_authority_validation import evaluate_dual_authority_validation
from runtime.loader import RUNS_DIR

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_ERROR = 2


def _run_dirs(runs_root: Path, recent: int | None = None) -> list[Path]:
    if not runs_root.exists():
        return []
    runs = [p for p in runs_root.iterdir() if p.is_dir()]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if recent is not None:
        runs = runs[: max(0, recent)]
    return runs


def _latest_run_dir(runs_root: Path) -> Path:
    runs = _run_dirs(runs_root)
    if not runs:
        raise FileNotFoundError(f'No run directories found under: {runs_root}')
    return runs[0]


def _print_report(report: dict[str, Any]) -> None:
    authority = report.get('authority', {})
    print(
        'status={status} authority_mode={mode} dual_validation_active={active}'.format(
            status=report.get('status'),
            mode=authority.get('mode'),
            active=authority.get('dual_validation_active'),
        )
    )

    validation = report.get('validation', {})
    parity_parts = [
        f"replay={validation.get('replay_parity', {}).get('status')}",
        f"eval={validation.get('eval_parity', {}).get('status')}",
        f"registry={validation.get('registry_parity', {}).get('status')}",
    ]
    print('  parity=' + ' '.join(parity_parts))

    blockers = report.get('blockers', [])
    warnings = report.get('warnings', [])
    recommendations = report.get('recommendations', [])

    if blockers:
        print('  blockers=' + '; '.join(item.get('message', '<unknown>') for item in blockers))
    if warnings:
        print('  warnings=' + '; '.join(str(item) for item in warnings))
    if recommendations:
        print('  recommendations=' + '; '.join(recommendations))

    rollback = validation.get('rollback', {})
    if rollback:
        print('  rollback_supported={supported} method={method}'.format(
            supported=rollback.get('supported'),
            method=rollback.get('method'),
        ))


def main() -> int:
    parser = argparse.ArgumentParser(description='Dual-authority validation window')
    parser.add_argument('run_or_path', nargs='?', help='Run ID or run directory path')
    parser.add_argument('--latest', action='store_true', help='Audit latest run')
    parser.add_argument('--all', action='store_true', help='Audit all runs')
    parser.add_argument('--summary', action='store_true', help='Emit aggregate summary')
    parser.add_argument('--recent', type=int, default=None, help='Limit --all/--summary scan to most recent N runs')
    parser.add_argument('--json', action='store_true', help='Emit JSON output')
    parser.add_argument('--strict', action='store_true', help='Exit 1 when blocked')
    parser.add_argument('--runs-root', default=str(RUNS_DIR), help='Runs root for --latest/--all/--summary')
    args = parser.parse_args()

    mode_count = int(bool(args.run_or_path)) + int(args.latest) + int(args.all)
    if mode_count > 1:
        print('error: choose only one of run_or_path, --latest, --all')
        return EXIT_ERROR

    if args.recent is not None and args.recent < 0:
        print('error: --recent must be >= 0')
        return EXIT_ERROR

    runs_root = Path(args.runs_root)

    try:
        if args.summary or args.all:
            payload = evaluate_dual_authority_validation(None, runs_root=runs_root, recent=args.recent)
            blocked = payload.get('status') == 'blocked'
            if args.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                _print_report(payload)
            return EXIT_BLOCKED if args.strict and blocked else EXIT_OK

        if args.latest:
            target = _latest_run_dir(runs_root)
        elif args.run_or_path:
            candidate = Path(args.run_or_path)
            target = candidate if candidate.exists() else runs_root / args.run_or_path
        else:
            target = _latest_run_dir(runs_root)

        report = evaluate_dual_authority_validation(target, runs_root=runs_root)
        blocked = report.get('status') == 'blocked'

        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            _print_report(report)

        return EXIT_BLOCKED if args.strict and blocked else EXIT_OK
    except Exception as exc:
        payload = {'status': 'error', 'reason': str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f'error: {exc}')
        return EXIT_ERROR


if __name__ == '__main__':
    raise SystemExit(main())
