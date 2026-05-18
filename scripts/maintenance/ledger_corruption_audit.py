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

from runtime.ledger_corruption import classify_ledger_corruption, ledger_corruption_detected
from runtime.loader import RUNS_DIR


EXIT_OK = 0
EXIT_CORRUPT = 1
EXIT_ERROR = 2


def _latest_run_dir() -> Path:
    if not RUNS_DIR.exists():
        raise FileNotFoundError(f"Runs directory not found: {RUNS_DIR}")
    runs = [p for p in RUNS_DIR.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError(f"No run directories found under: {RUNS_DIR}")
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]


def _resolve_targets(args: argparse.Namespace) -> list[Path]:
    mode_count = int(bool(args.run_or_path)) + int(args.latest) + int(args.all)
    if mode_count != 1:
        raise ValueError("Specify exactly one of: run_or_path, --latest, or --all")

    if args.latest:
        return [_latest_run_dir()]
    if args.all:
        if not RUNS_DIR.exists():
            return []
        return sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name)

    candidate = Path(args.run_or_path)
    if candidate.exists():
        return [candidate]
    return [RUNS_DIR / args.run_or_path]


def _print_human(reports: list[dict[str, Any]]) -> None:
    for report in reports:
        rid = report.get("run_id") or "<unknown>"
        print(f"{rid}: {report.get('status')}")
        cats = report.get("corruption_categories", [])
        if cats:
            print(f"  corruption_categories={','.join(cats)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit ledger corruption and recovery readiness")
    parser.add_argument("run_or_path", nargs="?", help="Run ID or run path")
    parser.add_argument("--latest", action="store_true", help="Audit latest run")
    parser.add_argument("--all", action="store_true", help="Audit all runs")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on corruption")
    args = parser.parse_args()

    try:
        targets = _resolve_targets(args)
        reports = [classify_ledger_corruption(target) for target in targets]
    except Exception as exc:
        payload = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"error: {exc}")
        return EXIT_ERROR

    has_corruption = any(ledger_corruption_detected(report) for report in reports)
    payload = {
        "status": "corrupt" if has_corruption else "ok",
        "count": len(reports),
        "reports": reports,
    }

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        _print_human(reports)

    if args.strict and has_corruption:
        return EXIT_CORRUPT

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
