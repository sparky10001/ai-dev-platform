#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.errors import EventLedgerError
from runtime.event_ledger import event_hash, load_ledger
from runtime.evals import evaluate_run
from runtime.registry import summarize_runs
from runtime.replay import summarize_trace
from runtime.trace_pipeline import load_trace


DRIFT_CATEGORIES = {
    "missing_trace",
    "missing_ledger",
    "event_count_mismatch",
    "event_sequence_mismatch",
    "event_hash_mismatch",
    "lifecycle_mismatch",
    "replay_summary_mismatch",
    "eval_summary_mismatch",
    "registry_summary_mismatch",
    "parse_error",
}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key in sorted(value.keys()):
            if key in {
                "timestamp",
                "timestamps",
                "duration_ms",
                "runtime_seconds",
                "created_at",
                "completed_at",
                "started_at",
                "ended_at",
                "run_path",
                "trace_path",
                "ledger_path",
            }:
                continue
            out[key] = _normalize_value(value[key])
        return out
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _to_event_dict(evt: Any) -> dict[str, Any]:
    if hasattr(evt, "model_dump"):
        return evt.model_dump(mode="json")
    if isinstance(evt, dict):
        return evt
    return dict(evt)


def _resolve_run_dir(run_or_path: str | Path) -> Path:
    path = Path(run_or_path)
    if path.is_dir():
        return path
    if path.name in {"trace.jsonl", "ledger.jsonl", "result.json", "run.json"}:
        return path.parent
    runs_candidate = Path(__file__).resolve().parent.parent / "runs" / str(run_or_path)
    if runs_candidate.exists():
        return runs_candidate
    return path


def _load_run_json(run_dir: Path) -> dict[str, Any]:
    run_json = run_dir / "run.json"
    if not run_json.exists():
        return {}
    try:
        payload = json.loads(run_json.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _resolve_run_id(run_dir: Path, trace_events: list[Any], ledger_events: list[Any], run_payload: dict[str, Any]) -> str | None:
    rid = run_payload.get("id")
    if isinstance(rid, str) and rid:
        return rid
    for evt in trace_events + ledger_events:
        run_id = _to_event_dict(evt).get("run_id")
        if isinstance(run_id, str) and run_id:
            return run_id
    return run_dir.name if run_dir.name else None


def _event_projection(events: list[Any]) -> tuple[list[str], list[str]]:
    payloads = [_to_event_dict(evt) for evt in events]
    sequence = [str(payload.get("event")) for payload in payloads]
    hashes = [event_hash(payload) for payload in payloads]
    return sequence, hashes


def compare_trace_and_ledger(run_or_path: str | Path, *, strict: bool = False) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_or_path)
    trace_path = run_dir / "trace.jsonl"
    ledger_path = run_dir / "ledger.jsonl"
    run_payload = _load_run_json(run_dir)

    report: dict[str, Any] = {
        "status": "ok",
        "run_id": None,
        "trace_exists": trace_path.exists(),
        "ledger_exists": ledger_path.exists(),
        "event_count_match": False,
        "event_sequence_match": False,
        "event_hash_match": False,
        "lifecycle_match": False,
        "replay_summary_match": False,
        "eval_summary_match": False,
        "registry_summary_match": False,
        "trace_event_count": 0,
        "ledger_event_count": 0,
        "drift_categories": [],
        "details": {},
    }

    categories: list[str] = []
    details: dict[str, Any] = {}

    if not trace_path.exists():
        categories.append("missing_trace")
    if not ledger_path.exists():
        categories.append("missing_ledger")

    trace_events: list[Any] = []
    ledger_events: list[Any] = []

    if report["trace_exists"]:
        try:
            trace_events = load_trace(trace_path, strict=True)
        except Exception as exc:
            categories.append("parse_error")
            details["trace_error"] = str(exc)
    if report["ledger_exists"]:
        try:
            ledger_events = load_ledger(ledger_path, strict=True)
        except Exception as exc:
            categories.append("parse_error")
            details["ledger_error"] = str(exc)

    report["run_id"] = _resolve_run_id(run_dir, trace_events, ledger_events, run_payload)
    report["trace_event_count"] = len(trace_events)
    report["ledger_event_count"] = len(ledger_events)

    if trace_events and ledger_events:
        try:
            seq_trace, hash_trace = _event_projection(trace_events)
            seq_ledger, hash_ledger = _event_projection(ledger_events)

            report["event_count_match"] = len(trace_events) == len(ledger_events)
            report["event_sequence_match"] = seq_trace == seq_ledger
            report["event_hash_match"] = hash_trace == hash_ledger

            if not report["event_count_match"]:
                categories.append("event_count_mismatch")
            if not report["event_sequence_match"]:
                categories.append("event_sequence_mismatch")
            if not report["event_hash_match"]:
                categories.append("event_hash_mismatch")

            lifecycle_trace = {
                "first_event": seq_trace[0] if seq_trace else None,
                "last_event": seq_trace[-1] if seq_trace else None,
                "started": "session_start" in seq_trace,
                "completed": "session_end" in seq_trace,
            }
            lifecycle_ledger = {
                "first_event": seq_ledger[0] if seq_ledger else None,
                "last_event": seq_ledger[-1] if seq_ledger else None,
                "started": "session_start" in seq_ledger,
                "completed": "session_end" in seq_ledger,
            }
            report["lifecycle_match"] = lifecycle_trace == lifecycle_ledger
            if not report["lifecycle_match"]:
                categories.append("lifecycle_mismatch")
            details["lifecycle"] = {"trace": lifecycle_trace, "ledger": lifecycle_ledger}

            replay_trace_summary = _normalize_value(summarize_trace(trace_path, source="trace"))
            replay_ledger_summary = _normalize_value(summarize_trace(trace_path, source="ledger"))
            report["replay_summary_match"] = replay_trace_summary == replay_ledger_summary
            if not report["replay_summary_match"]:
                categories.append("replay_summary_mismatch")
            details["replay_summary"] = {"trace": replay_trace_summary, "ledger": replay_ledger_summary}

            run_id = report["run_id"]
            if isinstance(run_id, str) and run_id:
                try:
                    eval_trace = _normalize_value(evaluate_run(run_id, source="trace").model_dump(mode="json"))
                    eval_ledger = _normalize_value(evaluate_run(run_id, source="ledger").model_dump(mode="json"))
                    report["eval_summary_match"] = eval_trace == eval_ledger
                    if not report["eval_summary_match"]:
                        categories.append("eval_summary_mismatch")
                    details["eval_summary"] = {"trace": eval_trace, "ledger": eval_ledger}
                except Exception as exc:
                    categories.append("parse_error")
                    details["eval_error"] = str(exc)

                try:
                    command = run_payload.get("command") if isinstance(run_payload.get("command"), str) else None
                    model = run_payload.get("model") if isinstance(run_payload.get("model"), str) else None
                    registry_trace = _normalize_value(
                        summarize_runs(
                            command=command,
                            model=model,
                            sort_by="created_at",
                            descending=False,
                            source="trace",
                        ).model_dump(mode="json")
                    )
                    registry_ledger = _normalize_value(
                        summarize_runs(
                            command=command,
                            model=model,
                            sort_by="created_at",
                            descending=False,
                            source="ledger",
                        ).model_dump(mode="json")
                    )
                    report["registry_summary_match"] = registry_trace == registry_ledger
                    if not report["registry_summary_match"]:
                        categories.append("registry_summary_mismatch")
                    details["registry_summary"] = {"trace": registry_trace, "ledger": registry_ledger}
                except Exception as exc:
                    categories.append("parse_error")
                    details["registry_error"] = str(exc)
            else:
                categories.append("parse_error")
                details["run_id_error"] = "Unable to resolve run_id for eval/registry parity"

        except Exception as exc:
            categories.append("parse_error")
            details["comparison_error"] = str(exc)

    if not report["trace_exists"] or not report["ledger_exists"]:
        details.setdefault("missing_artifacts", True)

    normalized_categories = sorted({cat for cat in categories if cat in DRIFT_CATEGORIES})
    report["drift_categories"] = normalized_categories
    report["details"] = details
    report["status"] = "drift" if normalized_categories else "ok"

    if strict and normalized_categories:
        raise EventLedgerError(
            f"Ledger/trace drift detected for {report.get('run_id') or run_dir}: {', '.join(normalized_categories)}"
        )

    return report


def summarize_drift(report: dict[str, Any]) -> dict[str, Any]:
    categories = sorted(set(report.get("drift_categories", [])))
    return {
        "status": report.get("status", "error"),
        "run_id": report.get("run_id"),
        "drift_detected": bool(categories),
        "drift_categories": categories,
        "trace_event_count": report.get("trace_event_count", 0),
        "ledger_event_count": report.get("ledger_event_count", 0),
    }


def drift_detected(report: dict[str, Any]) -> bool:
    return bool(report.get("drift_categories", []))


def validate_no_drift(run_or_path: str | Path) -> None:
    compare_trace_and_ledger(run_or_path, strict=True)
