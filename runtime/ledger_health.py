#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from runtime.errors import EventLedgerError
from runtime.event_ledger import (
    event_hash,
    ledger_cutover_readiness,
    ledger_parity_required,
    ledger_authoritative_enabled,
    load_ledger,
    trace_compatibility_required,
    validate_ledger_file,
    validate_trace_ledger_parity,
)
from runtime.loader import RUNS_DIR
from runtime.replay import replay_trace
from runtime.trace_pipeline import load_trace


def _resolve_run_dir(run_or_path: str | Path) -> Path:
    path = Path(run_or_path)
    if path.is_dir():
        return path
    if path.name in {"trace.jsonl", "ledger.jsonl", "ledger.index.json", "result.json", "run.json"}:
        return path.parent
    candidate = RUNS_DIR / str(run_or_path)
    if candidate.exists():
        return candidate
    return path


def _resolve_run_id(run_dir: Path) -> str | None:
    run_json = run_dir / "run.json"
    if run_json.exists():
        try:
            import json

            payload = json.loads(run_json.read_text(encoding="utf-8"))
            rid = payload.get("id")
            if isinstance(rid, str) and rid:
                return rid
        except Exception:
            pass
    return run_dir.name if run_dir.name else None


def _maintenance_status(now: float | None = None) -> dict[str, Any]:
    ts = time.time() if now is None else float(now)
    enabled = os.getenv("AI_MAINTENANCE_ENABLED", "0") == "1"
    interval = int(os.getenv("AI_MAINTENANCE_INTERVAL_SEC", "300") or "300")
    if interval <= 0:
        interval = 300
    stamp_path = Path(
        os.getenv("AI_MAINTENANCE_STAMP_PATH")
        or (Path(__file__).resolve().parent.parent / "tmp" / ".last_log_maintenance")
    )

    last_value: str | None = None
    stale = False
    seconds_since_last: float | None = None

    if stamp_path.exists():
        try:
            raw = stamp_path.read_text(encoding="utf-8").strip()
            last = float(raw)
            last_value = raw
            seconds_since_last = max(0.0, ts - last)
            stale = seconds_since_last > (interval * 2)
        except Exception:
            last_value = "invalid"
            stale = True

    return {
        "maintenance_enabled": enabled,
        "last_maintenance": last_value,
        "stamp_path": str(stamp_path),
        "stale": stale,
        "interval_sec": interval,
        "seconds_since_last": seconds_since_last,
    }


def _event_counts(run_dir: Path) -> dict[str, int]:
    trace_count = 0
    trace_path = run_dir / "trace.jsonl"
    if trace_path.exists():
        try:
            with trace_path.open("r", encoding="utf-8") as f:
                trace_count = sum(1 for line in f if line.strip())
        except Exception:
            trace_count = 0

    ledger_count = 0
    ledger_path = run_dir / "ledger.jsonl"
    if ledger_path.exists():
        try:
            ledger_count = len(load_ledger(ledger_path, strict=False))
        except Exception:
            ledger_count = 0

    return {"trace": trace_count, "ledger": ledger_count}


def _local_drift_report(run_dir: Path) -> dict[str, Any]:
    trace_path = run_dir / "trace.jsonl"
    ledger_path = run_dir / "ledger.jsonl"

    report: dict[str, Any] = {
        "status": "ok",
        "run_id": _resolve_run_id(run_dir),
        "trace_exists": trace_path.exists(),
        "ledger_exists": ledger_path.exists(),
        "event_count_match": False,
        "event_sequence_match": False,
        "event_hash_match": False,
        "lifecycle_match": False,
        "replay_summary_match": True,
        "eval_summary_match": True,
        "registry_summary_match": True,
        "trace_event_count": 0,
        "ledger_event_count": 0,
        "drift_categories": [],
        "details": {},
    }
    categories: list[str] = []

    if not report["trace_exists"]:
        categories.append("missing_trace")
    if not report["ledger_exists"]:
        categories.append("missing_ledger")

    if report["trace_exists"] and report["ledger_exists"]:
        try:
            trace_events = load_trace(trace_path, strict=True)
            ledger_events = load_ledger(ledger_path, strict=True)
            trace_payloads = [e.model_dump(mode="json") if hasattr(e, "model_dump") else dict(e) for e in trace_events]
            ledger_payloads = [e.model_dump(mode="json") if hasattr(e, "model_dump") else dict(e) for e in ledger_events]

            report["trace_event_count"] = len(trace_payloads)
            report["ledger_event_count"] = len(ledger_payloads)

            trace_names = [p.get("event") for p in trace_payloads]
            ledger_names = [p.get("event") for p in ledger_payloads]
            trace_hashes = [event_hash(p) for p in trace_payloads]
            ledger_hashes = [event_hash(p) for p in ledger_payloads]

            report["event_count_match"] = len(trace_payloads) == len(ledger_payloads)
            report["event_sequence_match"] = trace_names == ledger_names
            report["event_hash_match"] = trace_hashes == ledger_hashes
            report["lifecycle_match"] = (
                (trace_names[0] if trace_names else None) == (ledger_names[0] if ledger_names else None)
                and (trace_names[-1] if trace_names else None) == (ledger_names[-1] if ledger_names else None)
                and ("session_start" in trace_names) == ("session_start" in ledger_names)
                and ("session_end" in trace_names) == ("session_end" in ledger_names)
            )

            if not report["event_count_match"]:
                categories.append("event_count_mismatch")
            if not report["event_sequence_match"]:
                categories.append("event_sequence_mismatch")
            if not report["event_hash_match"]:
                categories.append("event_hash_mismatch")
            if not report["lifecycle_match"]:
                categories.append("lifecycle_mismatch")
        except Exception as exc:
            categories.append("parse_error")
            report["details"]["parse_error"] = str(exc)

    report["drift_categories"] = sorted(set(categories))
    report["status"] = "drift" if report["drift_categories"] else "ok"
    return report


def _local_corruption_categories(run_dir: Path, trace_exists: bool, ledger_exists: bool) -> tuple[list[str], dict[str, Any]]:
    categories: list[str] = []
    strict_validation = {
        "ledger_valid": False,
        "ledger_error": None,
        "parity_valid": False,
        "parity_error": None,
    }

    if not trace_exists:
        categories.append("missing_trace")
    if not ledger_exists:
        categories.append("missing_ledger")

    if ledger_exists:
        try:
            validate_ledger_file(run_dir, strict=True)
            strict_validation["ledger_valid"] = True
        except Exception as exc:
            strict_validation["ledger_error"] = str(exc)
            categories.append("malformed_ndjson")

    if trace_exists and ledger_exists:
        try:
            parity = validate_trace_ledger_parity(run_dir, strict=False)
            strict_validation["parity_valid"] = parity.get("status") == "success"
            if parity.get("status") != "success":
                categories.append("parity_mismatch")
        except Exception as exc:
            strict_validation["parity_error"] = str(exc)
            categories.append("parity_mismatch")

    return sorted(set(categories)), strict_validation


def ledger_health_status(report: dict[str, Any]) -> str:
    categories = set(report.get("categories", []))

    unhealthy_markers = {
        "corruption_detected",
        "parity_failed",
        "replay_failed",
        "eval_failed",
        "registry_failed",
        "missing_trace_required",
        "strict_validation_failed",
    }
    warning_markers = {
        "missing_ledger",
        "missing_index",
        "maintenance_disabled",
        "maintenance_stale",
        "cutover_not_ready",
        "drift_detected",
    }

    if categories & unhealthy_markers:
        return "unhealthy"
    if categories & warning_markers:
        return "warning"
    return "healthy"


def ledger_health_report(run_or_path: str | Path) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_or_path)
    run_id = _resolve_run_id(run_dir)

    trace_path = run_dir / "trace.jsonl"
    ledger_path = run_dir / "ledger.jsonl"
    index_path = run_dir / "ledger.index.json"

    trace_exists = trace_path.exists()
    ledger_exists = ledger_path.exists()
    index_exists = index_path.exists()

    categories: list[str] = []
    details: dict[str, Any] = {}

    if not ledger_exists:
        categories.append("missing_ledger")
    if not index_exists:
        categories.append("missing_index")

    maintenance = _maintenance_status()
    if not maintenance["maintenance_enabled"]:
        categories.append("maintenance_disabled")
    if maintenance["stale"]:
        categories.append("maintenance_stale")

    local_corruption_categories, strict_validation = _local_corruption_categories(run_dir, trace_exists, ledger_exists)
    corruption_detected = bool(set(local_corruption_categories) - {"missing_ledger"})
    if corruption_detected:
        categories.append("corruption_detected")

    drift_report = _local_drift_report(run_dir)
    drift_detected = bool(drift_report.get("drift_categories"))
    if drift_detected:
        categories.append("drift_detected")

    parity_ok = bool(strict_validation.get("parity_valid", False)) if not corruption_detected else False
    if not parity_ok and trace_exists and ledger_exists:
        categories.append("parity_failed")

    replay_ok = False
    if ledger_exists:
        try:
            replay_trace(trace_path if trace_exists else ledger_path, strict=True, source="ledger")
            replay_ok = True
        except Exception as exc:
            details["replay_error"] = str(exc)
            categories.append("replay_failed")

    # For single-run local health, eval/registry flags are local readiness markers.
    eval_ok = replay_ok and ledger_exists
    registry_ok = replay_ok and ledger_exists

    if not trace_exists and (ledger_authoritative_enabled() or trace_compatibility_required()):
        categories.append("missing_trace_required")

    if strict_validation.get("ledger_valid") is False and ledger_exists:
        categories.append("strict_validation_failed")

    readiness = ledger_cutover_readiness(run_dir)
    details["readiness"] = readiness
    details["drift_report"] = drift_report
    details["corruption_categories"] = local_corruption_categories
    details["strict_validation"] = strict_validation

    report = {
        "status": "error",
        "run_id": run_id,
        "trace_exists": trace_exists,
        "ledger_exists": ledger_exists,
        "index_exists": index_exists,
        "parity_ok": parity_ok,
        "drift_detected": drift_detected,
        "corruption_detected": corruption_detected,
        "replay_ok": replay_ok,
        "eval_ok": eval_ok,
        "registry_ok": registry_ok,
        "ledger_authoritative_enabled": ledger_authoritative_enabled(),
        "ledger_parity_required": ledger_parity_required(),
        "event_counts": _event_counts(run_dir),
        "categories": sorted(set(categories)),
        "maintenance": maintenance,
        "cutover_readiness": {
            "ready": readiness.get("status") == "ready",
            "reason": readiness.get("status"),
        },
        "details": details,
    }
    report["status"] = ledger_health_status(report)
    return report


def recent_run_paths(runs_root: str | Path, limit: int | None = None) -> list[Path]:
    runs_dir = Path(runs_root)
    if not runs_dir.is_absolute():
        runs_dir = Path(__file__).resolve().parent.parent / runs_dir

    if not runs_dir.exists():
        return []

    run_dirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    run_dirs = sorted(run_dirs, key=lambda p: (-p.stat().st_mtime, p.name))

    if limit is not None:
        run_dirs = run_dirs[: max(0, limit)]

    return run_dirs


def aggregate_ledger_health(runs_root: str | Path = "runs", recent: int | None = None) -> dict[str, Any]:
    runs_dir = Path(runs_root)
    if not runs_dir.is_absolute():
        runs_dir = Path(__file__).resolve().parent.parent / runs_dir

    if recent is not None and recent < 0:
        raise ValueError("recent must be >= 0")

    run_dirs = recent_run_paths(runs_dir, limit=recent)
    reports = [ledger_health_report(p) for p in run_dirs]

    summary_categories: dict[str, int] = {}
    for report in reports:
        for cat in report.get("categories", []):
            summary_categories[cat] = summary_categories.get(cat, 0) + 1

    healthy_runs = sum(1 for r in reports if r.get("status") == "healthy")
    warning_runs = sum(1 for r in reports if r.get("status") == "warning")
    unhealthy_runs = sum(1 for r in reports if r.get("status") in {"unhealthy", "error"})

    aggregate = {
        "status": "healthy",
        "runs_scanned": len(reports),
        "healthy_runs": healthy_runs,
        "warning_runs": warning_runs,
        "unhealthy_runs": unhealthy_runs,
        "drifted_runs": sum(1 for r in reports if r.get("drift_detected")),
        "corrupt_runs": sum(1 for r in reports if r.get("corruption_detected")),
        "missing_ledger_runs": sum(1 for r in reports if not r.get("ledger_exists")),
        "parity_failures": sum(1 for r in reports if not r.get("parity_ok")),
        "ledger_authoritative_runs": sum(1 for r in reports if r.get("ledger_authoritative_enabled")),
        "categories": dict(sorted(summary_categories.items())),
        "recent_failures": [
            {
                "run_id": r.get("run_id"),
                "status": r.get("status"),
                "categories": r.get("categories", []),
            }
            for r in reports
            if r.get("status") in {"warning", "unhealthy", "error"}
        ][:10],
        "maintenance": _maintenance_status(),
        "reports": reports,
    }

    if unhealthy_runs > 0:
        aggregate["status"] = "unhealthy"
    elif warning_runs > 0:
        aggregate["status"] = "warning"

    return aggregate


def validate_ledger_health(run_or_path: str | Path) -> None:
    report = ledger_health_report(run_or_path)
    if report.get("status") in {"unhealthy", "error"}:
        raise EventLedgerError(
            f"Ledger health check failed for {report.get('run_id') or run_or_path}: "
            f"{', '.join(report.get('categories', []))}"
        )
