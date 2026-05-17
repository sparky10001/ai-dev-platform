#!/usr/bin/env python3
###################################################################
# runtime/replay.py
#
# Phase 3 Replay Engine
#
# Responsibilities:
# - NDJSON trace loading
# - schema validation
# - replay-safe parsing
# - lifecycle reconstruction
# - run recovery
# - partial trace tolerance
# - deterministic ordering
#
###################################################################

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
import os
import re

from runtime.event_ledger import load_ledger
from runtime.trace_pipeline import load_trace as load_trace_events

from runtime.schemas import (
    TraceEvent,
)

ReplaySource = Literal["trace", "ledger"]


# ================================================================
# 📦 Replay State
# ================================================================

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

    # ------------------------------------------------------------
    # Derived State
    # ------------------------------------------------------------

    @property
    def incomplete(self) -> bool:

        return (
            self.started
            and not self.completed
        )

    @property
    def successful(self) -> bool:

        return self.status == "done"


# ================================================================
# 🔧 Replay Source Resolution
# ================================================================

def replay_source(default: ReplaySource = "trace") -> ReplaySource:
    raw = os.getenv("RUNTIME_REPLAY_SOURCE")
    if not raw:
        return default
    normalized = raw.strip().lower()
    if normalized in ("trace", "ledger"):
        return normalized  # type: ignore[return-value]
    return default


def _source_path_for_replay(path_or_run: str | Path, source: ReplaySource) -> Path:
    path = Path(path_or_run)

    if path.is_dir():
        return path / ("trace.jsonl" if source == "trace" else "ledger.jsonl")

    if source == "trace":
        return path

    if path.name == "trace.jsonl":
        return path.with_name("ledger.jsonl")

    return path


def load_replay_events(
    path_or_run: str | Path,
    *,
    strict: bool = False,
    source: ReplaySource = "trace",
) -> list[TraceEvent]:
    resolved_path = _source_path_for_replay(path_or_run, source)

    if source == "ledger" and not resolved_path.exists():
        raise RuntimeError(f"Replay source ledger missing file: {resolved_path}")

    if source == "ledger":
        return load_ledger(resolved_path, strict=strict)

    try:
        return load_trace_events(resolved_path, strict=strict)
    except Exception as e:
        if strict:
            msg = str(e)
            line_no = "1"
            matches = re.findall(r":(\d+):", msg)
            if matches:
                line_no = matches[0]
            raise RuntimeError(
                f"Replay failed at line {line_no}: {e}"
            ) from e
        return []


# ================================================================
# 📥 Load Trace
# ================================================================

def load_trace(
    trace_path: str | Path,
    *,
    strict: bool = False,
    source: ReplaySource = "trace",
) -> list[TraceEvent]:
    selected_source = source if source != "trace" else replay_source(default="trace")
    return load_replay_events(
        trace_path,
        strict=strict,
        source=selected_source,
    )


# ================================================================
# 🔁 Replay Trace
# ================================================================

def replay_trace(
    trace_path: str | Path,
    *,
    strict: bool = False,
    source: ReplaySource = "trace",
) -> ReplayState:

    state = ReplayState()

    events = load_trace(
        trace_path,
        strict=strict,
        source=source,
    )

    state.events = events

    for evt in events:

        state.event_count += 1

        # --------------------------------------------------------
        # Run Identity
        # --------------------------------------------------------

        if not state.run_id:
            state.run_id = evt.run_id

        # --------------------------------------------------------
        # Lifecycle
        # --------------------------------------------------------

        if evt.event == "session_start":
            state.started = True

        elif evt.event == "session_end":

            state.completed = True

            if isinstance(evt.data, dict):

                state.status = (
                    evt.data.get("status")
                )

        # --------------------------------------------------------
        # Tool Accounting
        # --------------------------------------------------------

        elif evt.event == "tool_call":
            state.tool_calls += 1

        elif evt.event == "tool_result":
            state.tool_results += 1

        # --------------------------------------------------------
        # Final Output
        # --------------------------------------------------------

        elif evt.event == "agent_output":

            if isinstance(evt.data, dict):

                state.status = (
                    evt.data.get("status")
                )

                state.output = (
                    evt.data.get("output")
                )

    return state


# ================================================================
# 📊 Replay Summary
# ================================================================

def summarize_trace(
    trace_path: str | Path,
    *,
    source: ReplaySource = "trace",
) -> dict:

    replay = replay_trace(trace_path, source=source)

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
