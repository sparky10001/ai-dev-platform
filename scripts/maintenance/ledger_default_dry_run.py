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

from runtime.event_ledger import evaluate_ledger_default_readiness
from runtime.loader import RUNS_DIR

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_ERROR = 2


def _latest_run_dir(runs_root: Path) -> Path:
    if not runs_root.exists():
        raise FileNotFoundError(f"Runs directory not found: {runs_root}")
    runs = _run_dirs(runs_root)
    if not runs:
        raise FileNotFoundError(f"No run directories found under: {runs_root}")
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]




def _run_dirs(runs_root: Path, recent: int | None = None) -> list[Path]:
    if not runs_root.exists():
        return []
    runs = [p for p in runs_root.iterdir() if p.is_dir()]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if recent is not None:
        runs = runs[: max(0, recent)]
    return runs


def _single(run_path: Path) -> dict[str, Any]:
    return evaluate_ledger_default_readiness(run_path)


def _aggregate(runs_root: Path, recent: int | None = None) -> dict[str, Any]:
    runs = _run_dirs(runs_root, recent=recent)
    reports = [_single(run) for run in runs]
    counts = {"ready": 0, "warning": 0, "blocked": 0}
    for report in reports:
        status = report.get("status", "blocked")
        if status in counts:
            counts[status] += 1

    return {
        "status": "blocked" if counts["blocked"] else ("warning" if counts["warning"] else "ready"),
        "runs_scanned": len(reports),
        "ready_runs": counts["ready"],
        "warning_runs": counts["warning"],
        "blocked_runs": counts["blocked"],
        "reports": reports,
    }


def _print_report(report: dict[str, Any]) -> None:
    print(f"status={report.get('status')} dry_run_enabled={report.get('ledger_default_dry_run_enabled')}")
    blockers = report.get("blocking_reasons", [])
    warnings = report.get("warnings", [])
    if blockers:
        print(f"  blockers={'; '.join(blockers)}")
    if warnings:
        print(f"  warnings={'; '.join(warnings)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ledger default dry-run readiness audit")
    parser.add_argument("run_or_path", nargs="?", help="Run id or run directory path")
    parser.add_argument("--latest", action="store_true", help="Audit latest run")
    parser.add_argument("--all", action="store_true", help="Audit all runs")
    parser.add_argument("--summary", action="store_true", help="Emit aggregate summary")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on blocked status")
    parser.add_argument("--runs-root", default=str(RUNS_DIR), help="Runs root for --latest/--all/--summary")
    parser.add_argument("--recent", type=int, default=None, help="Limit --all/--summary scan to most recent N runs by mtime")
    args = parser.parse_args()

    mode_count = int(bool(args.run_or_path)) + int(args.latest) + int(args.all)
    if mode_count > 1:
        print("error: choose only one of run_or_path, --latest, --all")
        return EXIT_ERROR

    runs_root = Path(args.runs_root)

    try:
        if args.summary or args.all:
            recent = args.recent
            if recent is not None and recent < 0:
                raise ValueError("--recent must be >= 0")
            payload = _aggregate(runs_root, recent=recent)
            blocked = payload.get("blocked_runs", 0) > 0
            if args.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                print(
                    f"status={payload.get('status')} runs={payload.get('runs_scanned')} "
                    f"ready={payload.get('ready_runs')} warning={payload.get('warning_runs')} "
                    f"blocked={payload.get('blocked_runs')}"
                )
            return EXIT_BLOCKED if args.strict and blocked else EXIT_OK

        target: Path
        if args.latest:
            target = _latest_run_dir(runs_root)
        elif args.run_or_path:
            candidate = Path(args.run_or_path)
            target = candidate if candidate.exists() else runs_root / args.run_or_path
        else:
            target = _latest_run_dir(runs_root)

        report = _single(target)
        blocked = report.get("status") == "blocked"

        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            _print_report(report)

        return EXIT_BLOCKED if args.strict and blocked else EXIT_OK
    except Exception as exc:
        payload = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"error: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
