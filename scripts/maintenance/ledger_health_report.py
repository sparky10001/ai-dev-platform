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

from runtime.ledger_health import aggregate_ledger_health, ledger_health_report
from runtime.loader import RUNS_DIR


EXIT_OK = 0
EXIT_UNHEALTHY = 1
EXIT_ERROR = 2


def _latest_run_dir(runs_root: Path) -> Path:
    if not runs_root.exists():
        raise FileNotFoundError(f"Runs directory not found: {runs_root}")
    runs = [p for p in runs_root.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError(f"No run directories found under: {runs_root}")
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]


def _print_single(report: dict[str, Any]) -> None:
    print(f"{report.get('run_id') or '<unknown>'}: {report.get('status')}")
    cats = report.get("categories", [])
    if cats:
        print(f"  categories={','.join(cats)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime ledger health observability report")
    parser.add_argument("run_or_path", nargs="?", help="Run ID or run path")
    parser.add_argument("--latest", action="store_true", help="Report latest run")
    parser.add_argument("--all", action="store_true", help="Report all runs")
    parser.add_argument("--summary", action="store_true", help="Emit aggregate summary")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--runs-root", default=str(RUNS_DIR), help="Runs root for --all/--summary/--latest")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when unhealthy")
    args = parser.parse_args()

    mode_count = int(bool(args.run_or_path)) + int(args.latest) + int(args.all)
    if mode_count > 1:
        print("error: specify only one of run_or_path, --latest, or --all")
        return EXIT_ERROR

    runs_root = Path(args.runs_root)

    try:
        if args.summary or args.all:
            payload = aggregate_ledger_health(runs_root)
            unhealthy = payload.get("status") == "unhealthy"
            if args.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                print(f"runs={payload.get('runs_scanned')} status={payload.get('status')}")
                print(
                    "  healthy={healthy} warning={warning} unhealthy={unhealthy}".format(
                        healthy=payload.get("healthy_runs"),
                        warning=payload.get("warning_runs"),
                        unhealthy=payload.get("unhealthy_runs"),
                    )
                )
            return EXIT_UNHEALTHY if args.strict and unhealthy else EXIT_OK

        target: Path
        if args.latest:
            target = _latest_run_dir(runs_root)
        elif args.run_or_path:
            candidate = Path(args.run_or_path)
            target = candidate if candidate.exists() else runs_root / args.run_or_path
        else:
            target = _latest_run_dir(runs_root)

        report = ledger_health_report(target)
        unhealthy = report.get("status") in {"unhealthy", "error"}

        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            _print_single(report)

        return EXIT_UNHEALTHY if args.strict and unhealthy else EXIT_OK

    except Exception as exc:
        payload = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"error: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
