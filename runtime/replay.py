#!/usr/bin/env python3
###################################################################
# runtime/replay.py
###################################################################

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Literal
import os
import re

from runtime.authority_policy import effective_runtime_event_source
from runtime.event_loader import load_runtime_events
from runtime.schemas import TraceEvent

ReplaySource = Literal["trace", "ledger"]


class ReplayState:
    def __init__(self):
        self.run_id: str | None = None
        self.events: list[TraceEvent] = []
        self.started: bool = False
        self.completed: bool = False
        self.status: str | None = None
        self.output: Any = None
        self.event_count: int = 0
        self.tool_calls: int = 0
        self.tool_results: int = 0
        self.errors: list[str] = []

    @property
    def incomplete(self) -> bool:
        return self.started and not self.completed

    @property
    def successful(self) -> bool:
        return self.status == "done"


def replay_source(default: ReplaySource = "trace") -> ReplaySource:
    raw = os.getenv("RUNTIME_REPLAY_SOURCE")
    return effective_runtime_event_source(source=raw, default=default)  # type: ignore[return-value]


def _source_path_for_replay(path_or_run: str | Path, source: ReplaySource) -> Path:
    path = Path(path_or_run)
    if path.is_dir():
        return path / ("trace.jsonl" if source == "trace" else "ledger.jsonl")
    if source == "trace":
        return path
    if path.name == "trace.jsonl":
        return path.with_name("ledger.jsonl")
    return path


def replay_events(events: Iterable[TraceEvent], *, run_id: str | None = None) -> ReplayState:
    state = ReplayState()
    if run_id:
        state.run_id = run_id

    for evt in events:
        state.events.append(evt)
        state.event_count += 1

        if not state.run_id:
            state.run_id = getattr(evt, "run_id", None)

        event_name = getattr(evt, "event", None)
        event_data = getattr(evt, "data", None)

        if event_name == "session_start":
            state.started = True
        elif event_name == "session_end":
            state.completed = True
            if isinstance(event_data, dict):
                state.status = event_data.get("status")
        elif event_name == "tool_call":
            state.tool_calls += 1
        elif event_name == "tool_result":
            state.tool_results += 1
        elif event_name == "agent_output":
            if isinstance(event_data, dict):
                state.status = event_data.get("status")
                state.output = event_data.get("output")

    return state


def summarize_events(events: Iterable[TraceEvent], *, run_id: str | None = None) -> dict[str, Any]:
    replay = replay_events(events, run_id=run_id)
    return {
        "run_id": replay.run_id,
        "events": replay.event_count,
        "tool_calls": replay.tool_calls,
        "tool_results": replay.tool_results,
        "started": replay.started,
        "completed": replay.completed,
        "incomplete": replay.incomplete,
        "status": replay.status,
        "successful": replay.successful,
        "output": replay.output,
    }


def load_replay_events(
    path_or_run: str | Path,
    *,
    strict: bool = False,
    source: ReplaySource = "trace",
) -> list[TraceEvent]:
    resolved_path = _source_path_for_replay(path_or_run, source)

    if source == "ledger" and not resolved_path.exists():
        raise RuntimeError(f"Replay source ledger missing file: {resolved_path}")

    try:
        return load_runtime_events(resolved_path, source=source, strict=strict)
    except Exception as e:
        if strict and source == "trace":
            msg = str(e)
            line_no = "1"
            matches = re.findall(r":(\d+):", msg)
            if matches:
                line_no = matches[0]
            raise RuntimeError(f"Replay failed at line {line_no}: {e}") from e
        if strict:
            raise
        return []


def load_trace(
    trace_path: str | Path,
    *,
    strict: bool = False,
    source: ReplaySource | None = None,
) -> list[TraceEvent]:
    selected_source = replay_source(default="trace") if source is None else source
    return load_replay_events(trace_path, strict=strict, source=selected_source)


def replay_trace(
    trace_path: str | Path,
    *,
    strict: bool = False,
    source: ReplaySource | None = None,
) -> ReplayState:
    events = load_trace(trace_path, strict=strict, source=source)
    return replay_events(events)


def summarize_trace(
    trace_path: str | Path,
    *,
    source: ReplaySource | None = None,
) -> dict:
    events = load_trace(trace_path, source=source)
    return summarize_events(events)
