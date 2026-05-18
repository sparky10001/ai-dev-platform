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

from runtime.ledger_drift import compare_trace_and_ledger, drift_detected, summarize_drift
from runtime.loader import RUNS_DIR


EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2


def _resolve_latest_run_dir() -> Path:
    if not RUNS_DIR.exists():
        raise FileNotFoundError(f"Runs directory not found: {RUNS_DIR}")
    run_dirs = [p for p in RUNS_DIR.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found under: {RUNS_DIR}")
    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return run_dirs[0]


def _resolve_targets(args: argparse.Namespace) -> list[Path]:
    mode_count = int(bool(args.run_or_path)) + int(args.latest) + int(args.all)
    if mode_count != 1:
        raise ValueError("Specify exactly one of: run_or_path, --latest, or --all")

    if args.all:
        if not RUNS_DIR.exists():
            return []
        return sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name)
    if args.latest:
        return [_resolve_latest_run_dir()]

    candidate = Path(args.run_or_path)
    if candidate.exists():
        return [candidate]
    return [RUNS_DIR / args.run_or_path]


def _print_human(reports: list[dict[str, Any]]) -> None:
    for report in reports:
        summary = summarize_drift(report)
        run_id = summary.get("run_id") or "<unknown>"
        status = summary.get("status")
        cats = summary.get("drift_categories", [])
        print(f"{run_id}: {status}")
        print(
            f"  trace_events={summary.get('trace_event_count', 0)} ledger_events={summary.get('ledger_event_count', 0)}"
        )
        if cats:
            print(f"  drift_categories={','.join(cats)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit trace/ledger drift for runtime runs")
    parser.add_argument("run_or_path", nargs="?", help="Run ID or run directory/file path")
    parser.add_argument("--latest", action="store_true", help="Audit latest run under runs/")
    parser.add_argument("--all", action="store_true", help="Audit all runs under runs/")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when drift is detected")
    args = parser.parse_args()

    try:
        targets = _resolve_targets(args)
        reports = [compare_trace_and_ledger(target, strict=False) for target in targets]
    except Exception as exc:
        payload = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"error: {exc}")
        return EXIT_ERROR

    drift = any(drift_detected(report) for report in reports)
    payload = {
        "status": "drift" if drift else "ok",
        "count": len(reports),
        "reports": reports,
    }

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        _print_human(reports)

    if args.strict and drift:
        return EXIT_DRIFT

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
