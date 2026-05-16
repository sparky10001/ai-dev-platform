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


def validate_trace_file(
    path: str | Path,
    *,
    strict: bool | None = None,
) -> list[Any]:
    strict_mode = _strict_enabled(strict)
    events = list(iter_trace_events(path, strict=strict_mode))

    if not strict_mode:
        return events

    run_ids = {evt.run_id for evt in events}
    if len(run_ids) > 1:
        raise TraceValidationError("Inconsistent run_id values in trace")

    names = [evt.event for evt in events]
    if names:
        if names[0] != "session_start":
            raise LifecycleOrderingError("First event must be session_start")
        if names[-1] != "session_end":
            raise LifecycleOrderingError("Last event must be session_end")
        if "agent_output" not in names:
            raise LifecycleOrderingError("Trace missing agent_output")

    seen_end = False
    for evt in names:
        if evt == "session_end":
            seen_end = True
        elif seen_end:
            raise LifecycleOrderingError("Events found after session_end")

    return events