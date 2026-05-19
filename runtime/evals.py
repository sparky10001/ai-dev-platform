#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Literal
import os

from runtime.event_loader import load_runtime_events, resolve_runtime_event_source, runtime_event_source
from runtime.loader import get_run_path, load_result, load_run
from runtime.replay import ReplayState, load_replay_events, replay_events
from runtime.schemas import EvalComparison, EvalSummary, TraceEvent

EvalSource = Literal["trace", "ledger"]


def eval_source(default: EvalSource = "trace") -> EvalSource:
    raw = os.getenv("RUNTIME_EVAL_SOURCE")
    if raw:
        return resolve_runtime_event_source(raw, default=default)  # type: ignore[return-value]
    return runtime_event_source(default=default)  # type: ignore[return-value]


def _eval_path_for_source(run_path: Path, source: EvalSource) -> Path:
    return run_path / ("ledger.jsonl" if source == "ledger" else "trace.jsonl")


def load_eval_events(run_or_path: str | Path, *, source: EvalSource = "trace") -> list[Any]:
    path = Path(run_or_path)
    if path.is_dir():
        event_path = _eval_path_for_source(path, source)
    elif source == "ledger" and path.name == "trace.jsonl":
        event_path = path.with_name("ledger.jsonl")
    else:
        event_path = path

    if source == "ledger" and not event_path.exists():
        raise RuntimeError(f"Eval source ledger missing file: {event_path}")

    if source == "ledger":
        return load_runtime_events(event_path, source=source, strict=True)

    # Preserve trace-mode replay error surface for existing callers/tests.
    return load_replay_events(event_path, strict=True, source="trace")


def _runtime_seconds(run: dict[str, Any] | None, replay: ReplayState) -> float | None:
    if isinstance(run, dict):
        created_at = run.get("created_at")
        completed_at = run.get("completed_at")
        if isinstance(created_at, (int, float)) and isinstance(completed_at, (int, float)):
            return max(0.0, completed_at - created_at)

    if replay.events:
        first = replay.events[0].timestamp
        last = replay.events[-1].timestamp
        return max(0.0, last - first)
    return None


def _status(run: dict[str, Any] | None, result: dict[str, Any] | None, replay: ReplayState) -> str | None:
    run_status = run.get("status") if isinstance(run, dict) else None
    result_status = result.get("status") if isinstance(result, dict) else None
    return replay.status or result_status or run_status


def evaluate_events(
    events: Iterable[TraceEvent],
    *,
    run_id: str | None = None,
    run: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> EvalSummary:
    replay = replay_events(events, run_id=run_id)
    effective_run_id = run_id or replay.run_id or "unknown"

    return EvalSummary(
        run_id=effective_run_id,
        status=_status(run, result, replay),
        total_events=replay.event_count,
        tool_calls=replay.tool_calls,
        tool_results=replay.tool_results,
        runtime_seconds=_runtime_seconds(run, replay),
        completed=replay.completed,
        replay_valid=True,
        schema_valid=True,
    )


def compare_event_sets(
    events_a: Iterable[TraceEvent],
    events_b: Iterable[TraceEvent],
    *,
    run_a: dict[str, Any] | None = None,
    run_b: dict[str, Any] | None = None,
    result_a: dict[str, Any] | None = None,
    result_b: dict[str, Any] | None = None,
    run_id_a: str | None = None,
    run_id_b: str | None = None,
) -> EvalComparison:
    eval_a = evaluate_events(events_a, run_id=run_id_a, run=run_a, result=result_a)
    eval_b = evaluate_events(events_b, run_id=run_id_b, run=run_b, result=result_b)

    delta_runtime_seconds = None
    if eval_a.runtime_seconds is not None and eval_b.runtime_seconds is not None:
        delta_runtime_seconds = eval_b.runtime_seconds - eval_a.runtime_seconds

    return EvalComparison(
        run_a=eval_a,
        run_b=eval_b,
        status_changed=(eval_a.status != eval_b.status),
        delta_events=(eval_b.total_events - eval_a.total_events),
        delta_tool_calls=(eval_b.tool_calls - eval_a.tool_calls),
        delta_tool_results=(eval_b.tool_results - eval_a.tool_results),
        delta_runtime_seconds=delta_runtime_seconds,
        both_completed=(eval_a.completed and eval_b.completed),
        replay_valid=(eval_a.replay_valid and eval_b.replay_valid),
        schema_valid=(eval_a.schema_valid and eval_b.schema_valid),
    )


def evaluate_run(run_id: str, *, source: EvalSource | None = None) -> EvalSummary:
    run = load_run(run_id)
    result = load_result(run_id)
    run_path = get_run_path(run_id)

    selected_source = eval_source(default="trace") if source is None else source
    events = load_eval_events(run_path, source=selected_source)
    return evaluate_events(events, run_id=run_id, run=run, result=result)


def compare_runs(run_a: str, run_b: str, *, source: EvalSource | None = None) -> EvalComparison:
    selected_source = eval_source(default="trace") if source is None else source

    run_a_payload = load_run(run_a)
    run_b_payload = load_run(run_b)
    result_a_payload = load_result(run_a)
    result_b_payload = load_result(run_b)

    events_a = load_eval_events(get_run_path(run_a), source=selected_source)
    events_b = load_eval_events(get_run_path(run_b), source=selected_source)

    return compare_event_sets(
        events_a,
        events_b,
        run_a=run_a_payload,
        run_b=run_b_payload,
        result_a=result_a_payload,
        result_b=result_b_payload,
        run_id_a=run_a,
        run_id_b=run_b,
    )
