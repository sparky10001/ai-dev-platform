#!/usr/bin/env python3
###################################################################
# runtime/evals.py
#
# Phase 3B Runtime Evaluation Layer
#
# Responsibilities:
# - replay-derived run evaluation
# - schema-typed evaluation summaries
# - deterministic run comparison
# - loader/replay integration
#
###################################################################

from __future__ import annotations

from runtime.loader import get_run_path
from runtime.loader import load_result
from runtime.loader import load_run
from runtime.replay import replay_trace
from runtime.schemas import EvalComparison
from runtime.schemas import EvalSummary


# ================================================================
# Helpers
# ================================================================

def _runtime_seconds(run: dict, trace) -> float | None:

    created_at = run.get("created_at")
    completed_at = run.get("completed_at")

    if isinstance(created_at, (int, float)) and isinstance(completed_at, (int, float)):
        return max(0.0, completed_at - created_at)

    if trace.events:
        first = trace.events[0].timestamp
        last = trace.events[-1].timestamp
        return max(0.0, last - first)

    return None


def _status(run: dict, result: dict, trace) -> str | None:

    return (
        trace.status
        or result.get("status")
        or run.get("status")
    )


# ================================================================
# Evaluate Run
# ================================================================

def evaluate_run(run_id: str) -> EvalSummary:

    run = load_run(run_id)
    result = load_result(run_id)

    trace_path = get_run_path(run_id) / "trace.jsonl"

    replay = replay_trace(
        trace_path,
        strict=True,
    )

    return EvalSummary(
        run_id=run_id,
        status=_status(run, result, replay),
        total_events=replay.event_count,
        tool_calls=replay.tool_calls,
        tool_results=replay.tool_results,
        runtime_seconds=_runtime_seconds(run, replay),
        completed=replay.completed,
        replay_valid=True,
        schema_valid=True,
    )


# ================================================================
# Compare Runs
# ================================================================

def compare_runs(run_a: str, run_b: str) -> EvalComparison:

    eval_a = evaluate_run(run_a)
    eval_b = evaluate_run(run_b)

    delta_runtime_seconds = None

    if (
        eval_a.runtime_seconds is not None
        and eval_b.runtime_seconds is not None
    ):
        delta_runtime_seconds = (
            eval_b.runtime_seconds
            - eval_a.runtime_seconds
        )

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
