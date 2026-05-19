#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator, Literal

from runtime.event_ledger import (
    enforce_trace_ledger_parity_if_required,
    iter_ledger_events,
    ledger_authoritative_enabled,
    ledger_canary_enabled,
    load_ledger,
)
from runtime.trace_pipeline import iter_trace_events, load_trace

RuntimeEventSource = Literal["trace", "ledger"]


def runtime_event_source(default: RuntimeEventSource = "trace") -> RuntimeEventSource:
    return resolve_runtime_event_source(source=None, default=default)


def resolve_runtime_event_source(
    source: RuntimeEventSource | str | None = None,
    default: RuntimeEventSource = "trace",
) -> RuntimeEventSource:
    fallback: RuntimeEventSource = "ledger" if (ledger_authoritative_enabled() or ledger_canary_enabled()) else default

    if source is not None:
        normalized = str(source).strip().lower()
        if normalized in ("trace", "ledger"):
            return normalized  # type: ignore[return-value]
        return fallback

    env = os.getenv("RUNTIME_EVENT_SOURCE")
    if env:
        normalized = env.strip().lower()
        if normalized in ("trace", "ledger"):
            return normalized  # type: ignore[return-value]

    return fallback


def _source_path(path_or_run: str | Path, source: RuntimeEventSource) -> Path:
    path = Path(path_or_run)
    if path.is_dir():
        return path / ("trace.jsonl" if source == "trace" else "ledger.jsonl")
    if source == "ledger" and path.name == "trace.jsonl":
        return path.with_name("ledger.jsonl")
    return path


def iter_runtime_events(
    run_or_path: str | Path,
    source: RuntimeEventSource | str | None = None,
    strict: bool = False,
) -> Iterator[Any]:
    resolved_source = resolve_runtime_event_source(source=source, default="trace")
    resolved_path = _source_path(run_or_path, resolved_source)

    if resolved_source == "ledger":
        if not resolved_path.exists():
            raise RuntimeError(f"Runtime source ledger missing file: {resolved_path}")
        enforce_trace_ledger_parity_if_required(run_or_path)
        return iter_ledger_events(resolved_path, strict=strict)

    return iter_trace_events(resolved_path, strict=strict)


def load_runtime_events(
    run_or_path: str | Path,
    source: RuntimeEventSource | str | None = None,
    strict: bool = False,
) -> list[Any]:
    resolved_source = resolve_runtime_event_source(source=source, default="trace")
    resolved_path = _source_path(run_or_path, resolved_source)

    if resolved_source == "ledger":
        if not resolved_path.exists():
            raise RuntimeError(f"Runtime source ledger missing file: {resolved_path}")
        enforce_trace_ledger_parity_if_required(run_or_path)
        return load_ledger(resolved_path, strict=strict)

    return load_trace(resolved_path, strict=strict)
