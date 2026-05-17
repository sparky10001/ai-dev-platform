#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from runtime.evals import evaluate_run
from runtime.event_ledger import (
    enforce_trace_ledger_parity_if_required,
    ledger_authoritative_enabled,
    load_ledger,
)
from runtime.loader import get_run_path, list_runs as list_run_ids, load_run
from runtime.replay import load_replay_events
from runtime.schemas import RunQueryResult, RunSummary

RegistrySource = Literal["trace", "ledger"]


def registry_source(default: RegistrySource = "trace") -> RegistrySource:
    raw = os.getenv("RUNTIME_REGISTRY_SOURCE")
    if raw:
        normalized = raw.strip().lower()
        if normalized in ("trace", "ledger"):
            return normalized  # type: ignore[return-value]
    if ledger_authoritative_enabled():
        return "ledger"
    return default


def _registry_path_for_source(run_path: Path, source: RegistrySource) -> Path:
    return run_path / ("ledger.jsonl" if source == "ledger" else "trace.jsonl")


def load_registry_events(run_or_path: str | Path, *, source: RegistrySource = "trace") -> list[Any]:
    path = Path(run_or_path)
    if path.is_dir():
        event_path = _registry_path_for_source(path, source)
    elif source == "ledger" and path.name == "trace.jsonl":
        event_path = path.with_name("ledger.jsonl")
    else:
        event_path = path

    if source == "ledger":
        if not event_path.exists():
            raise RuntimeError(f"Registry source ledger missing file: {event_path}")
        enforce_trace_ledger_parity_if_required(run_or_path)
        return load_ledger(event_path, strict=True)

    return load_replay_events(event_path, strict=True, source="trace")


def list_runs() -> list[str]:
    return list_run_ids()


def get_run(run_id: str) -> dict[str, Any]:
    return load_run(run_id)


def get_latest_run() -> dict[str, Any] | None:
    result = query_runs(sort_by="created_at", descending=True, limit=1)
    if not result.runs:
        return None
    return result.runs[0]


def _safe_load_run(run_id: str) -> dict[str, Any] | None:
    try:
        return load_run(run_id)
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _is_completed(run: dict[str, Any]) -> bool:
    return run.get("completed_at") is not None or run.get("status") in {"done", "error"}


def _matches(run: dict[str, Any], *, status: str | None, command: str | None, model: str | None, completed: bool | None) -> bool:
    if status is not None and run.get("status") != status:
        return False
    if command is not None and run.get("command") != command:
        return False
    if model is not None and run.get("model") != model:
        return False
    if completed is not None and _is_completed(run) != completed:
        return False
    return True


def _sort_key(run: dict[str, Any], sort_by: str):
    value = run.get(sort_by)
    if isinstance(value, (int, float, str)):
        return (0, value, run.get("id", ""))
    return (1, "", run.get("id", ""))


def query_runs(
    *,
    status: str | None = None,
    command: str | None = None,
    model: str | None = None,
    completed: bool | None = None,
    sort_by: str = "created_at",
    descending: bool = False,
    limit: int | None = None,
) -> RunQueryResult:
    filters = {k: v for k, v in {"status": status, "command": command, "model": model, "completed": completed}.items() if v is not None}

    runs = []
    for run_id in list_runs():
        run = _safe_load_run(run_id)
        if run is None:
            continue
        if _matches(run, status=status, command=command, model=model, completed=completed):
            runs.append(run)

    runs = sorted(runs, key=lambda run: _sort_key(run, sort_by), reverse=descending)
    if limit is not None:
        runs = runs[:max(0, limit)]

    return RunQueryResult(runs=runs, total=len(runs), filters=filters, sort_by=sort_by, descending=descending, limit=limit)


def summarize_runs(
    *,
    status: str | None = None,
    command: str | None = None,
    model: str | None = None,
    completed: bool | None = None,
    sort_by: str = "created_at",
    descending: bool = False,
    limit: int | None = None,
    source: RegistrySource | None = None,
) -> RunSummary:
    selected_source = registry_source(default="trace") if source is None else source

    query = query_runs(
        status=status,
        command=command,
        model=model,
        completed=completed,
        sort_by=sort_by,
        descending=descending,
        limit=limit,
    )

    evals = []
    for run in query.runs:
        run_id = run.get("id")
        if not isinstance(run_id, str):
            continue
        try:
            if selected_source == "ledger":
                load_registry_events(get_run_path(run_id), source="ledger")
            evals.append(evaluate_run(run_id, source=selected_source))
        except (FileNotFoundError, RuntimeError, json.JSONDecodeError, TypeError, ValueError):
            continue

    total_runs = len(evals)
    completed_runs = sum(1 for item in evals if item.completed)
    successful_runs = sum(1 for item in evals if item.status == "done")
    runtimes = [item.runtime_seconds for item in evals if item.runtime_seconds is not None]

    average_runtime = (sum(runtimes) / len(runtimes)) if runtimes else None
    success_rate = (successful_runs / total_runs) if total_runs else 0.0

    return RunSummary(
        total_runs=total_runs,
        completed_runs=completed_runs,
        success_rate=success_rate,
        average_runtime=average_runtime,
        total_tool_calls=sum(item.tool_calls for item in evals),
        replay_valid_runs=sum(1 for item in evals if item.replay_valid),
        schema_valid_runs=sum(1 for item in evals if item.schema_valid),
    )
