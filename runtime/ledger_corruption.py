#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.errors import EventLedgerError, NDJSONIntegrityError, TraceValidationError
from runtime.event_ledger import (
    build_ledger_index,
    load_ledger,
    load_ledger_index,
    validate_ledger_file,
    validate_trace_ledger_parity,
)
from runtime.evals import evaluate_run
from runtime.ledger_drift import compare_trace_and_ledger
from runtime.registry import summarize_runs
from runtime.replay import replay_trace


CORRUPTION_CATEGORIES = {
    "missing_ledger",
    "missing_trace",
    "malformed_ndjson",
    "empty_ledger",
    "mixed_run_id",
    "mixed_schema_version",
    "timestamp_regression",
    "duplicate_lifecycle_event",
    "missing_lifecycle_event",
    "event_after_session_end",
    "parity_mismatch",
    "index_mismatch",
    "replay_failure",
    "eval_failure",
    "registry_failure",
}


def _to_event_dict(event: Any) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    return dict(event)


def _resolve_run_dir(run_or_path: str | Path) -> Path:
    path = Path(run_or_path)
    if path.is_dir():
        return path
    if path.name in {"trace.jsonl", "ledger.jsonl", "result.json", "run.json", "ledger.index.json"}:
        return path.parent
    runs_candidate = Path(__file__).resolve().parent.parent / "runs" / str(run_or_path)
    if runs_candidate.exists():
        return runs_candidate
    return path


def _resolve_run_id(run_dir: Path, events: list[Any]) -> str | None:
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
    for evt in events:
        rid = _to_event_dict(evt).get("run_id")
        if isinstance(rid, str) and rid:
            return rid
    return run_dir.name if run_dir.name else None




def _can_evaluate_run(run_dir: Path, run_id: str | None) -> bool:
    if not run_id:
        return False
    root_runs = Path(__file__).resolve().parent.parent / "runs" / run_id
    return root_runs.resolve() == run_dir.resolve() and (run_dir / "run.json").exists() and (run_dir / "result.json").exists()


def recovery_guidance_for_categories(categories: list[str]) -> list[str]:
    guidance_map = {
        "missing_ledger": "Regenerate ledger from trace only if trace parity source is trusted; otherwise keep trace authority.",
        "missing_trace": "Keep compatibility mode and preserve trace-first recovery requirements before authority cutover.",
        "malformed_ndjson": "Do not enable ledger authority; inspect ledger writer and preserve trace fallback.",
        "empty_ledger": "Treat ledger as unusable and require regenerated dual-write artifacts before authority enablement.",
        "mixed_run_id": "Reject ledger authority and inspect run isolation/append path handling.",
        "mixed_schema_version": "Block authority enablement until schema-version consistency is restored.",
        "timestamp_regression": "Reject ledger for replay authority and inspect event ordering/write serialization.",
        "duplicate_lifecycle_event": "Validate lifecycle emitter sequencing before considering ledger authority.",
        "missing_lifecycle_event": "Require complete lifecycle traces before ledger authority cutover.",
        "event_after_session_end": "Reject ledger authority until lifecycle termination ordering is corrected.",
        "parity_mismatch": "Run ledger drift audit and compare event hashes before cutover.",
        "index_mismatch": "Regenerate ledger.index.json from ledger.jsonl after validating ledger integrity.",
        "replay_failure": "Keep replay source on trace until ledger replay succeeds deterministically.",
        "eval_failure": "Keep evaluation source on trace until ledger evaluation succeeds deterministically.",
        "registry_failure": "Keep registry source on trace until ledger-backed summaries succeed deterministically.",
    }

    ordered = sorted({cat for cat in categories if cat in guidance_map})
    return [guidance_map[cat] for cat in ordered]


def _lifecycle_categories(events: list[Any]) -> list[str]:
    names = [str(getattr(evt, "event", _to_event_dict(evt).get("event"))) for evt in events]
    categories: list[str] = []

    if names.count("session_start") > 1 or names.count("session_end") > 1 or names.count("agent_output") > 1:
        categories.append("duplicate_lifecycle_event")

    if "session_end" not in names or "agent_output" not in names:
        categories.append("missing_lifecycle_event")

    seen_end = False
    for name in names:
        if name == "session_end":
            seen_end = True
            continue
        if seen_end:
            categories.append("event_after_session_end")
            break

    return categories


def ledger_corruption_detected(report: dict[str, Any]) -> bool:
    return bool(report.get("corruption_categories", []))


def classify_ledger_corruption(run_or_path: str | Path) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_or_path)
    trace_path = run_dir / "trace.jsonl"
    ledger_path = run_dir / "ledger.jsonl"
    index_path = run_dir / "ledger.index.json"

    trace_exists = trace_path.exists()
    ledger_exists = ledger_path.exists()
    index_exists = index_path.exists()

    categories: list[str] = []
    details: dict[str, Any] = {}
    strict_validation: dict[str, Any] = {
        "ledger_valid": False,
        "ledger_error": None,
        "parity_valid": False,
        "parity_error": None,
    }

    events: list[Any] = []

    if not trace_exists:
        categories.append("missing_trace")
    if not ledger_exists:
        categories.append("missing_ledger")

    if ledger_exists:
        try:
            events = load_ledger(ledger_path, strict=True)
            try:
                validate_ledger_file(ledger_path, strict=True)
                strict_validation["ledger_valid"] = True
            except TraceValidationError as exc:
                msg = str(exc)
                strict_validation["ledger_error"] = msg
                if "empty" in msg.lower():
                    categories.append("empty_ledger")
                elif "run_id" in msg.lower():
                    categories.append("mixed_run_id")
                elif "schema_version" in msg.lower():
                    categories.append("mixed_schema_version")
                elif "monotonic" in msg.lower() or "timestamp" in msg.lower():
                    categories.append("timestamp_regression")
                else:
                    categories.append("malformed_ndjson")
        except NDJSONIntegrityError as exc:
            strict_validation["ledger_error"] = str(exc)
            categories.append("malformed_ndjson")
        except Exception as exc:
            strict_validation["ledger_error"] = str(exc)
            categories.append("malformed_ndjson")

    if events:
        categories.extend(_lifecycle_categories(events))

    try:
        parity = validate_trace_ledger_parity(run_dir, strict=False)
        strict_validation["parity_valid"] = parity.get("status") == "success"
        details["parity_report"] = parity
        if parity.get("status") != "success":
            categories.append("parity_mismatch")
    except Exception as exc:
        strict_validation["parity_error"] = str(exc)
        categories.append("parity_mismatch")

    drift_report: dict[str, Any]
    try:
        drift_report = compare_trace_and_ledger(run_dir, strict=False)
        details["drift_report"] = drift_report
    except Exception as exc:
        drift_report = {"status": "error", "reason": str(exc)}
        details["drift_report"] = drift_report

    if index_exists and ledger_exists:
        try:
            recorded = load_ledger_index(run_dir)
            built = build_ledger_index(run_dir)
            if recorded != built:
                categories.append("index_mismatch")
                details["index_mismatch"] = {
                    "recorded_event_count": recorded.get("event_count"),
                    "built_event_count": built.get("event_count"),
                    "recorded_ledger_hash": recorded.get("ledger_hash"),
                    "built_ledger_hash": built.get("ledger_hash"),
                }
        except Exception as exc:
            categories.append("index_mismatch")
            details["index_error"] = str(exc)

    run_id = _resolve_run_id(run_dir, events)

    if ledger_exists:
        try:
            replay_trace(trace_path if trace_exists else ledger_path, strict=True, source="ledger")
        except Exception as exc:
            categories.append("replay_failure")
            details["replay_error"] = str(exc)

        if _can_evaluate_run(run_dir, run_id):
            try:
                evaluate_run(run_id, source="ledger")
            except Exception as exc:
                categories.append("eval_failure")
                details["eval_error"] = str(exc)

            try:
                summarize_runs(limit=1, source="ledger")
            except Exception as exc:
                categories.append("registry_failure")
                details["registry_error"] = str(exc)

    normalized_categories = sorted({cat for cat in categories if cat in CORRUPTION_CATEGORIES})

    status = "ok"
    if not trace_exists or not ledger_exists:
        status = "missing"
    if normalized_categories:
        status = "corrupt" if status != "missing" else "missing"

    report = {
        "status": status,
        "run_id": run_id,
        "trace_exists": trace_exists,
        "ledger_exists": ledger_exists,
        "index_exists": index_exists,
        "corruption_categories": normalized_categories,
        "strict_validation": strict_validation,
        "drift_report": details.get("drift_report", {}),
        "recovery_guidance": recovery_guidance_for_categories(normalized_categories),
        "details": details,
    }
    return report


def validate_ledger_recovery_readiness(run_or_path: str | Path) -> dict[str, Any]:
    report = classify_ledger_corruption(run_or_path)
    report["recovery_ready"] = not ledger_corruption_detected(report)
    return report


def validate_no_ledger_corruption(run_or_path: str | Path) -> None:
    report = classify_ledger_corruption(run_or_path)
    if ledger_corruption_detected(report):
        categories = ", ".join(report.get("corruption_categories", []))
        raise EventLedgerError(
            f"Ledger corruption detected for {report.get('run_id') or run_or_path}: {categories}"
        )
