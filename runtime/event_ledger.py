#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from runtime.errors import EventLedgerError, NDJSONIntegrityError, TraceValidationError
from runtime.validator import validate_event


LEDGER_INDEX_SCHEMA_VERSION = 1


def ledger_authoritative_enabled() -> bool:
    return os.getenv("RUNTIME_LEDGER_AUTHORITATIVE") == "1"


def ledger_default_dry_run_enabled() -> bool:
    return os.getenv("RUNTIME_LEDGER_DRY_RUN_DEFAULT") == "1"


def ledger_canary_enabled() -> bool:
    return os.getenv("RUNTIME_LEDGER_CANARY") == "1"


def ledger_canary_parity_required() -> bool:
    return os.getenv("RUNTIME_LEDGER_CANARY_PARITY_REQUIRED") == "1"


def ledger_canary_environment() -> dict[str, str]:
    parity = "1" if ledger_canary_parity_required() else "0"
    return {
        "RUNTIME_LEDGER_CANARY": "1",
        "RUNTIME_LEDGER_AUTHORITATIVE": "1",
        "RUNTIME_LEDGER_PARITY_REQUIRED": parity,
        "RUNTIME_LEDGER_CANARY_PARITY_REQUIRED": parity,
    }


def ledger_parity_required() -> bool:
    return os.getenv("RUNTIME_LEDGER_PARITY_REQUIRED") == "1"


def enforce_trace_ledger_parity_if_required(run_or_path: str | Path | dict[str, Any]) -> None:
    authoritative_effective = ledger_authoritative_enabled() or ledger_canary_enabled()
    parity_effective = ledger_parity_required() or (ledger_canary_enabled() and ledger_canary_parity_required())
    if authoritative_effective and parity_effective:
        validate_trace_ledger_parity(run_or_path, strict=True)


def _to_event_dict(event: dict[str, Any] | Any) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    return dict(event)


def canonical_event_payload(event: dict[str, Any] | Any) -> dict[str, Any]:
    payload = _to_event_dict(event)
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "event": payload.get("event"),
        "timestamp": payload.get("timestamp"),
        "data": payload.get("data"),
    }


def event_hash(event: dict[str, Any] | Any) -> str:
    canonical = canonical_event_payload(event)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ledger_event_record(event: dict[str, Any] | Any, index: int) -> dict[str, Any]:
    canonical = canonical_event_payload(event)
    return {
        "index": int(index),
        "event_hash": event_hash(canonical),
        "event": canonical,
    }


def ledger_path_for_run(run: dict[str, Any]) -> Path:
    if isinstance(run, dict) and run.get("ledger_path"):
        return Path(run["ledger_path"])
    if isinstance(run, dict) and run.get("run_path"):
        return Path(run["run_path"]) / "ledger.jsonl"
    if isinstance(run, dict) and run.get("path"):
        return Path(run["path"]) / "ledger.jsonl"
    if isinstance(run, dict) and run.get("trace_path"):
        return Path(run["trace_path"]).parent / "ledger.jsonl"
    raise ValueError("Unable to derive ledger path for run")


def _resolve_ledger_path(path_or_run: str | Path | dict[str, Any]) -> Path:
    if isinstance(path_or_run, (str, Path)):
        p = Path(path_or_run)
        if p.is_dir():
            return p / "ledger.jsonl"
        return p
    return ledger_path_for_run(path_or_run)


def ledger_index_path_for_run(path_or_run: str | Path | dict[str, Any]) -> Path:
    ledger_path = _resolve_ledger_path(path_or_run)
    return ledger_path.with_name("ledger.index.json")


def append_event(run: dict[str, Any], event: dict[str, Any] | Any) -> None:
    payload = _to_event_dict(event)
    validated = validate_event(payload)
    ledger_path = ledger_path_for_run(run)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(validated.model_dump(mode="json")) + "\n")
        f.flush()
        os.fsync(f.fileno())


def iter_ledger_events(path_or_run: str | Path | dict[str, Any], *, strict: bool = False) -> Iterator[Any]:
    path = _resolve_ledger_path(path_or_run)
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception as exc:
                if strict:
                    raise NDJSONIntegrityError(f"Malformed NDJSON at {path}:{lineno}: {exc}") from exc
                continue
            try:
                yield validate_event(payload)
            except Exception as exc:
                if strict:
                    raise TraceValidationError(f"Invalid ledger event at {path}:{lineno}: {exc}") from exc
                continue


def load_ledger(path_or_run: str | Path | dict[str, Any], *, strict: bool = False) -> list[Any]:
    return list(iter_ledger_events(path_or_run, strict=strict))


def validate_ledger_file(path_or_run: str | Path | dict[str, Any], *, strict: bool = True) -> list[Any]:
    path = _resolve_ledger_path(path_or_run)
    if not path.exists():
        raise FileNotFoundError(path)
    events = load_ledger(path, strict=strict)
    if not strict:
        return events
    if not events:
        raise TraceValidationError("Ledger is empty in strict mode")

    run_ids = {getattr(evt, "run_id", None) for evt in events}
    if len(run_ids) != 1:
        raise TraceValidationError("Inconsistent run_id values in ledger")

    versions = {getattr(evt, "schema_version", None) for evt in events}
    if len(versions) != 1:
        raise TraceValidationError("Inconsistent schema_version values in ledger")

    last_ts: float | None = None
    for evt in events:
        event_dict = _to_event_dict(evt)
        event_hash(event_dict)

        ts = getattr(evt, "timestamp", None)
        if not isinstance(ts, (int, float)):
            raise TraceValidationError("Ledger contains non-numeric timestamp")
        current_ts = float(ts)
        if last_ts is not None and current_ts < last_ts:
            raise TraceValidationError("Ledger timestamps are not monotonic")
        last_ts = current_ts

    return events


def build_ledger_index(path_or_run: str | Path | dict[str, Any]) -> dict[str, Any]:
    events = validate_ledger_file(path_or_run, strict=True)
    event_records: list[dict[str, Any]] = []
    event_hashes: list[str] = []

    for idx, evt in enumerate(events):
        record = ledger_event_record(evt, idx)
        event_records.append(record)
        event_hashes.append(record["event_hash"])

    first_event = _to_event_dict(events[0])
    ledger_hash = hashlib.sha256("".join(event_hashes).encode("utf-8")).hexdigest()
    return {
        "schema_version": LEDGER_INDEX_SCHEMA_VERSION,
        "run_id": first_event.get("run_id"),
        "event_count": len(event_records),
        "ledger_hash": ledger_hash,
        "events": event_records,
    }


def write_ledger_index(path_or_run: str | Path | dict[str, Any]) -> Path:
    index = build_ledger_index(path_or_run)
    index_path = ledger_index_path_for_run(path_or_run)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return index_path


def load_ledger_index(path_or_run: str | Path | dict[str, Any]) -> dict[str, Any]:
    index_path = ledger_index_path_for_run(path_or_run)
    return json.loads(index_path.read_text(encoding="utf-8"))


def validate_trace_ledger_parity(run_or_path: str | Path | dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    if isinstance(run_or_path, dict):
        run_dir = Path(
            run_or_path.get("run_path")
            or run_or_path.get("path")
            or Path(run_or_path.get("trace_path", "")).parent
        )
    else:
        path = Path(run_or_path)
        run_dir = path if path.is_dir() else path.parent

    trace_path = run_dir / "trace.jsonl"
    ledger_path = run_dir / "ledger.jsonl"

    from runtime.trace_pipeline import load_trace

    trace_events = load_trace(trace_path, strict=True)
    ledger_events = load_ledger(ledger_path, strict=True)

    trace_payloads = [_to_event_dict(evt) for evt in trace_events]
    ledger_payloads = [_to_event_dict(evt) for evt in ledger_events]

    trace_event_names = [payload.get("event") for payload in trace_payloads]
    ledger_event_names = [payload.get("event") for payload in ledger_payloads]
    trace_hashes = [event_hash(payload) for payload in trace_payloads]
    ledger_hashes = [event_hash(payload) for payload in ledger_payloads]

    errors: list[str] = []
    if len(trace_payloads) != len(ledger_payloads):
        errors.append("event_count_mismatch")
    if trace_event_names != ledger_event_names:
        errors.append("event_sequence_mismatch")
    if trace_hashes != ledger_hashes:
        errors.append("hash_sequence_mismatch")

    report = {
        "status": "success" if not errors else "error",
        "trace_event_count": len(trace_payloads),
        "ledger_event_count": len(ledger_payloads),
        "event_sequence_match": trace_event_names == ledger_event_names,
        "hash_sequence_match": trace_hashes == ledger_hashes,
        "errors": errors,
    }

    if strict and errors:
        raise EventLedgerError("trace/ledger parity validation failed: " + ",".join(errors))

    return report


def trace_compatibility_required() -> bool:
    # Compatibility remains required until trace removal is explicitly planned.
    return True


def _resolve_run_dir(run_or_path: str | Path | dict[str, Any]) -> Path:
    if isinstance(run_or_path, dict):
        return Path(
            run_or_path.get("run_path")
            or run_or_path.get("path")
            or Path(run_or_path.get("trace_path", "")).parent
        )
    path = Path(run_or_path)
    return path if path.is_dir() else path.parent


def audit_trace_dependencies() -> dict[str, Any]:
    root = Path(__file__).resolve().parent.parent
    scopes = [
        ("runtime", root / "runtime"),
        ("scripts", root / "scripts"),
        ("control-plane", root / "control-plane"),
        ("docs", root / "docs"),
    ]

    dependencies: list[dict[str, Any]] = []

    for scope, base in scopes:
        if not base.exists():
            continue
        for fp in sorted(base.rglob("*")):
            if not fp.is_file():
                continue
            if "__pycache__" in fp.parts:
                continue
            try:
                content = fp.read_text(encoding="utf-8")
            except Exception:
                continue
            if "trace.jsonl" not in content:
                continue
            rel = str(fp.relative_to(root))
            # Heuristic: runtime modules with source-switching are compatibility usage.
            kind = "compatibility_only" if rel in {
                "runtime/replay.py",
                "runtime/evals.py",
                "runtime/registry.py",
                "runtime/event_ledger.py",
            } else "trace_assumption"
            dependencies.append({"scope": scope, "path": rel, "kind": kind})

    compatibility_only = [d["path"] for d in dependencies if d["kind"] == "compatibility_only"]
    assumptions = [d["path"] for d in dependencies if d["kind"] == "trace_assumption"]

    status = "ready"
    if assumptions:
        status = "warning"

    return {
        "status": status,
        "total_dependencies": len(dependencies),
        "remaining_trace_dependencies": assumptions,
        "compatibility_only_dependencies": compatibility_only,
        "dependencies": dependencies,
    }


def ledger_cutover_readiness(run_or_path: str | Path | dict[str, Any]) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_or_path)
    trace_path = run_dir / "trace.jsonl"
    ledger_path = run_dir / "ledger.jsonl"

    trace_exists = trace_path.exists()
    ledger_exists = ledger_path.exists()

    warnings: list[str] = []
    errors: list[str] = []

    parity_valid = False
    if trace_exists and ledger_exists:
        try:
            validate_trace_ledger_parity(run_dir, strict=True)
            parity_valid = True
        except Exception as exc:
            errors.append(f"parity_validation_failed: {exc}")
    else:
        if not trace_exists:
            errors.append("missing_trace")
        if not ledger_exists:
            errors.append("missing_ledger")

    dep_audit = audit_trace_dependencies()

    replay_ledger_ready = ledger_exists and parity_valid
    eval_ledger_ready = ledger_exists and parity_valid
    registry_ledger_ready = ledger_exists and parity_valid

    if dep_audit["remaining_trace_dependencies"]:
        warnings.append("remaining_trace_dependencies_present")

    status = "ready"
    if errors:
        status = "blocked"
    elif warnings:
        status = "warning"

    return {
        "status": status,
        "run_path": str(run_dir),
        "trace_exists": trace_exists,
        "ledger_exists": ledger_exists,
        "parity_valid": parity_valid,
        "replay_ledger_ready": replay_ledger_ready,
        "eval_ledger_ready": eval_ledger_ready,
        "registry_ledger_ready": registry_ledger_ready,
        "authoritative_mode_available": True,
        "authoritative_mode_enabled": ledger_authoritative_enabled(),
        "trace_compatibility_required": trace_compatibility_required(),
        "remaining_trace_dependencies": dep_audit["remaining_trace_dependencies"],
        "compatibility_only_dependencies": dep_audit["compatibility_only_dependencies"],
        "warnings": warnings,
        "errors": errors,
    }


def evaluate_ledger_default_readiness(run_or_path: str | Path | dict[str, Any]) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_or_path)

    from runtime.ledger_corruption import classify_ledger_corruption
    from runtime.ledger_drift import compare_trace_and_ledger, drift_detected
    from runtime.ledger_health import ledger_health_report
    from runtime.trace_compatibility import audit_trace_compatibility

    categories: list[str] = []
    warnings: list[str] = []
    blocking_reasons: list[str] = []
    details: dict[str, Any] = {}

    parity_ok = False
    try:
        parity = validate_trace_ledger_parity(run_dir, strict=False)
        parity_ok = parity.get("status") == "success"
        details["parity_report"] = parity
    except Exception as exc:
        details["parity_error"] = str(exc)
        categories.append("parity_failure")
        blocking_reasons.append(f"parity validation error: {exc}")

    if not parity_ok:
        categories.append("parity_failure")
        blocking_reasons.append("trace/ledger parity check failed")

    drift_report = compare_trace_and_ledger(run_dir, strict=False)
    details["drift_report"] = drift_report
    drift_categories = list(drift_report.get("drift_categories", []))
    # Parse-only drift from non-local eval/registry contexts is a compatibility warning
    # when core parity and lifecycle dimensions already match for this run.
    parse_only = set(drift_categories) == {"parse_error"}
    core_match = bool(drift_report.get("event_count_match")) and bool(drift_report.get("event_sequence_match")) and bool(drift_report.get("event_hash_match")) and bool(drift_report.get("lifecycle_match"))
    drift_flag = drift_detected(drift_report) and not (parse_only and core_match and parity_ok)
    if drift_flag:
        categories.append("drift_detected")
        blocking_reasons.append("trace/ledger drift detected")

    corruption_report = classify_ledger_corruption(run_dir)
    details["corruption_report"] = corruption_report
    corruption_categories = list(corruption_report.get("corruption_categories", []))
    corruption_flag = bool(corruption_categories)
    if corruption_flag:
        categories.append("corruption_detected")
        blocking_reasons.append("ledger corruption categories present")

    health_report = ledger_health_report(run_dir)
    details["ledger_health_report"] = health_report

    replay_ready = bool(health_report.get("replay_ok"))
    eval_ready = bool(health_report.get("eval_ok"))
    registry_ready = bool(health_report.get("registry_ok"))
    if not replay_ready:
        categories.append("replay_not_ready")
        blocking_reasons.append("ledger replay readiness failed")
    if not eval_ready:
        categories.append("eval_not_ready")
        blocking_reasons.append("ledger eval readiness failed")
    if not registry_ready:
        categories.append("registry_not_ready")
        blocking_reasons.append("ledger registry readiness failed")

    trace_compat = audit_trace_compatibility()
    cutover_blockers = int(trace_compat.get("summary", {}).get("cutover_blocker_count", 0))
    if cutover_blockers > 0:
        categories.append("trace_blockers_present")
        blocking_reasons.append(f"trace cutover blockers present: {cutover_blockers}")
    if trace_compat.get("status") == "warning":
        categories.append("compatibility_warning")
        warnings.append("trace compatibility audit reports warnings")

    maintenance = health_report.get("maintenance", {})
    if not maintenance.get("maintenance_enabled", False) or maintenance.get("stale", False):
        categories.append("maintenance_warning")
        warnings.append("maintenance is disabled or stale")

    cutover = ledger_cutover_readiness(run_dir)
    details["cutover_readiness"] = cutover

    status = "ready"
    if blocking_reasons:
        status = "blocked"
    elif warnings:
        status = "warning"

    return {
        "status": status,
        "ledger_default_dry_run_enabled": ledger_default_dry_run_enabled(),
        "ledger_authoritative_enabled": ledger_authoritative_enabled(),
        "parity_ok": parity_ok,
        "drift_detected": drift_flag,
        "corruption_detected": corruption_flag,
        "cutover_blockers": cutover_blockers,
        "trace_compatibility_status": trace_compat.get("status"),
        "replay_ledger_ready": replay_ready,
        "eval_ledger_ready": eval_ready,
        "registry_ledger_ready": registry_ready,
        "categories": sorted(set(categories)),
        "warnings": sorted(set(warnings)),
        "blocking_reasons": sorted(set(blocking_reasons)),
        "details": details,
    }


def evaluate_ledger_canary_readiness(run_or_path: str | Path | dict[str, Any]) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_or_path)

    from runtime.ledger_corruption import classify_ledger_corruption
    from runtime.ledger_drift import compare_trace_and_ledger, drift_detected
    from runtime.ledger_health import ledger_health_report
    from runtime.trace_compatibility import audit_trace_compatibility

    dry_run_report = evaluate_ledger_default_readiness(run_dir)
    health_report = ledger_health_report(run_dir)
    drift_report = compare_trace_and_ledger(run_dir, strict=False)
    corruption_report = classify_ledger_corruption(run_dir)
    trace_compat_report = audit_trace_compatibility()

    canary_enabled = ledger_canary_enabled()
    authoritative_effective = ledger_authoritative_enabled() or canary_enabled
    parity_required = ledger_parity_required() or (canary_enabled and ledger_canary_parity_required())

    categories: list[str] = []
    warnings: list[str] = []
    blocking_reasons: list[str] = []

    if not canary_enabled:
        categories.append("canary_disabled")
        warnings.append("ledger canary mode is disabled")

    if dry_run_report.get("drift_detected") or drift_detected(drift_report):
        categories.append("drift_detected")
        blocking_reasons.append("active ledger/trace drift detected")

    if dry_run_report.get("corruption_detected") or corruption_report.get("corruption_categories"):
        categories.append("corruption_detected")
        blocking_reasons.append("active ledger corruption categories detected")

    if not dry_run_report.get("parity_ok", False):
        categories.append("parity_failure")
        blocking_reasons.append("parity validation failed")

    if not dry_run_report.get("replay_ledger_ready", False):
        categories.append("replay_not_ready")
        blocking_reasons.append("replay ledger readiness failed")
    if not dry_run_report.get("eval_ledger_ready", False):
        categories.append("eval_not_ready")
        blocking_reasons.append("eval ledger readiness failed")
    if not dry_run_report.get("registry_ledger_ready", False):
        categories.append("registry_not_ready")
        blocking_reasons.append("registry ledger readiness failed")

    cutover_blockers = int(trace_compat_report.get("summary", {}).get("cutover_blocker_count", 0))
    if cutover_blockers > 0:
        categories.append("trace_blockers_present")
        blocking_reasons.append(f"trace cutover blockers present: {cutover_blockers}")

    if health_report.get("status") == "warning":
        warnings.append("ledger health has warning status")
    if health_report.get("status") in {"unhealthy", "error"}:
        blocking_reasons.append("ledger health is unhealthy")

    maintenance = health_report.get("maintenance", {})
    if not maintenance.get("maintenance_enabled", False) or maintenance.get("stale", False):
        categories.append("maintenance_warning")
        warnings.append("maintenance is disabled or stale")

    if dry_run_report.get("trace_compatibility_status") == "warning":
        categories.append("compatibility_warning")
        warnings.append("trace compatibility audit reports warnings")

    status = "ready"
    if blocking_reasons:
        status = "blocked"
    elif warnings:
        status = "warning"

    rollback = {
        "unset": [
            "RUNTIME_LEDGER_CANARY",
            "RUNTIME_LEDGER_AUTHORITATIVE",
            "RUNTIME_LEDGER_PARITY_REQUIRED",
            "RUNTIME_LEDGER_CANARY_PARITY_REQUIRED",
        ]
    }

    return {
        "status": status,
        "canary_enabled": canary_enabled,
        "authoritative_effective": authoritative_effective,
        "parity_required": parity_required,
        "trace_emission_preserved": True,
        "explicit_trace_override_supported": True,
        "categories": sorted(set(categories)),
        "warnings": sorted(set(warnings)),
        "blocking_reasons": sorted(set(blocking_reasons)),
        "rollback": rollback,
        "details": {
            "dry_run_readiness": dry_run_report,
            "ledger_health_report": health_report,
            "drift_report": drift_report,
            "corruption_report": corruption_report,
            "trace_compatibility_report": trace_compat_report,
            "run_path": str(run_dir),
            "cutover_blockers": cutover_blockers,
        },
    }
