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
from typing import Any
import re

from runtime.trace_pipeline import load_trace as load_trace_events

from runtime.schemas import (
    TraceEvent,
)


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
# 📥 Load Trace
# ================================================================

def load_trace(
    trace_path: str | Path,
    *,
    strict: bool = False,
) -> list[TraceEvent]:

    path = Path(trace_path)

    try:
        events = load_trace_events(path, strict=strict)
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

    return events


# ================================================================
# 🔁 Replay Trace
# ================================================================

def replay_trace(
    trace_path: str | Path,
    *,
    strict: bool = False,
) -> ReplayState:

    state = ReplayState()

    events = load_trace(
        trace_path,
        strict=strict,
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
) -> dict:

    replay = replay_trace(trace_path)

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