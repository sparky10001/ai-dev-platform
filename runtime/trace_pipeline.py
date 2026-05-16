#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Iterator

from runtime.errors import (
    LifecycleOrderingError,
    NDJSONIntegrityError,
    ReplayCorruptionError,
    TraceValidationError,
)
from runtime.validator import validate_event


def _strict_enabled(strict: bool | None = None) -> bool:
    if strict is not None:
        return strict
    return os.getenv("RUNTIME_TRACE_STRICT") == "1"


def normalize_trace_event(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return dict(payload)


def validate_trace_event(payload: dict[str, Any]):
    return validate_event(normalize_trace_event(payload))


def append_trace_event(
    run: dict[str, Any],
    event: str,
    data: Any = None,
    **extra,
) -> None:
    payload = {
        "schema_version": 1,
        "timestamp": time.time(),
        "run_id": run["id"],
        "event": event,
        "data": data if data is not None else {},
        **extra,
    }

    validated = validate_trace_event(payload)
    trace_path = run["trace_path"]

    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(validated.model_dump(mode="json")) + "\n")
        f.flush()
        os.fsync(f.fileno())


def iter_trace_events(
    trace_path: str | Path,
    *,
    strict: bool | None = None,
) -> Iterator[Any]:
    path = Path(trace_path)
    strict_mode = _strict_enabled(strict)

    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception as exc:
                if strict_mode:
                    raise NDJSONIntegrityError(
                        f"Malformed NDJSON at {path}:{lineno}: {exc}"
                    ) from exc
                continue

            try:
                yield validate_trace_event(payload)
            except Exception as exc:
                if strict_mode:
                    raise ReplayCorruptionError(
                        f"Invalid trace event at {path}:{lineno}: {exc}"
                    ) from exc
                continue


def load_trace(
    trace_path: str | Path,
    *,
    strict: bool | None = None,
) -> list[Any]:
    return list(iter_trace_events(trace_path, strict=strict))




def append_validated_trace_event(
    trace_path: str | Path,
    payload: dict[str, Any],
) -> None:
    validated = validate_trace_event(normalize_trace_event(payload))
    path = Path(trace_path)
    with open(path, "a", encoding="utf-8") as f:
        json.dump(validated.model_dump(mode="json"), f)
        f.write("\n")


def trace_diagnostic(index: int, exc: Exception) -> dict[str, Any]:
    return {
        "index": int(index),
        "error_type": type(exc).__name__,
        "message": str(exc),
    }


def ingest_trace_events(
    trace_path: str | Path,
    events: list[dict[str, Any]] | None,
    *,
    strict: bool | None = None,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    strict_mode = _strict_enabled(strict)
    if not isinstance(events, list):
        return diagnostics
    for index, evt in enumerate(events):
        try:
            append_validated_trace_event(trace_path, evt)
        except Exception as exc:
            diagnostics.append(trace_diagnostic(index, exc))
            if strict_mode:
                if isinstance(exc, (NDJSONIntegrityError, ReplayCorruptionError, TraceValidationError, LifecycleOrderingError)):
                    raise
                raise ReplayCorruptionError(
                    f"Invalid ingested trace fragment at index {index}: {exc}"
                ) from exc
            continue
    return diagnostics

def validate_monotonic_timestamps(events: list[Any]) -> None:
    last_ts: float | None = None
    for evt in events:
        ts = getattr(evt, "timestamp", None)
        if not isinstance(ts, (int, float)):
            raise TraceValidationError("Trace contains non-numeric timestamp")
        if last_ts is not None and ts < last_ts:
            raise TraceValidationError("Trace timestamps are not monotonic")
        last_ts = float(ts)


def validate_run_id_consistency(events: list[Any]) -> None:
    run_ids = {getattr(evt, "run_id", None) for evt in events}
    if len(run_ids) > 1:
        raise TraceValidationError("Inconsistent run_id values in trace")


def validate_schema_version_consistency(events: list[Any]) -> None:
    versions = {getattr(evt, "schema_version", None) for evt in events}
    if len(versions) > 1:
        raise TraceValidationError("Inconsistent schema_version values in trace")


def validate_lifecycle_ordering(events: list[Any]) -> None:
    names = [evt.event for evt in events]
    if not names:
        return

    if names.count("session_start") > 1:
        raise LifecycleOrderingError("Duplicate session_start events detected")
    if names.count("session_end") > 1:
        raise LifecycleOrderingError("Duplicate session_end events detected")
    if names.count("agent_output") > 1:
        raise LifecycleOrderingError("Duplicate agent_output events detected")

    if names[0] != "session_start":
        raise LifecycleOrderingError("First event must be session_start")

    seen_end = False
    for name in names:
        if name == "session_end":
            seen_end = True
        elif seen_end:
            raise LifecycleOrderingError("Events found after session_end")

    if "session_end" in names and names[-1] != "session_end":
        raise LifecycleOrderingError("Last event must be session_end")

    if "session_end" in names and "agent_output" not in names:
        raise LifecycleOrderingError("Trace missing agent_output")


def validate_deterministic_trace(events: list[Any]) -> None:
    validate_run_id_consistency(events)
    validate_schema_version_consistency(events)
    validate_monotonic_timestamps(events)
    validate_lifecycle_ordering(events)


def validate_trace_file(
    path: str | Path,
    *,
    strict: bool | None = None,
) -> list[Any]:
    strict_mode = _strict_enabled(strict)
    events = list(iter_trace_events(path, strict=strict_mode))

    if not strict_mode:
        return events

    validate_deterministic_trace(events)
    return events