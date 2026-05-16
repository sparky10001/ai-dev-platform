#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

from runtime.errors import NDJSONIntegrityError, TraceValidationError
from runtime.validator import validate_event


def _to_event_dict(event: dict[str, Any] | Any) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    return dict(event)


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


def append_event(run: dict[str, Any], event: dict[str, Any] | Any) -> None:
    payload = _to_event_dict(event)
    validated = validate_event(payload)
    ledger_path = ledger_path_for_run(run)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(validated.model_dump(mode="json")) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _resolve_ledger_path(path_or_run: str | Path | dict[str, Any]) -> Path:
    if isinstance(path_or_run, (str, Path)):
        p = Path(path_or_run)
        if p.is_dir():
            return p / "ledger.jsonl"
        return p
    return ledger_path_for_run(path_or_run)


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
    run_ids = {getattr(evt, "run_id", None) for evt in events}
    if len(run_ids) > 1:
        raise TraceValidationError("Inconsistent run_id values in ledger")
    versions = {getattr(evt, "schema_version", None) for evt in events}
    if len(versions) > 1:
        raise TraceValidationError("Inconsistent schema_version values in ledger")
    last_ts = None
    for evt in events:
        ts = getattr(evt, "timestamp", None)
        if not isinstance(ts, (int, float)):
            raise TraceValidationError("Ledger contains non-numeric timestamp")
        if last_ts is not None and ts < last_ts:
            raise TraceValidationError("Ledger timestamps are not monotonic")
        last_ts = float(ts)
    return events
