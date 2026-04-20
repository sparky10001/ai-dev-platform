###################################################################
# read_trace.py — Execution trace reader tool (v1.2 production)
#
# Reads and parses .ai_trace.log JSONL files
# Supports filtering, summarization, and session isolation
###################################################################

import json
import os
from datetime import datetime

name = "read_trace"
description = "Read and parse the AI execution trace log for debugging and evaluation"
input_schema = {
    "path": "string (optional) — trace log path (default: .ai_trace.log)",
    "last_n": "int (optional, default 50) — number of recent events to return",
    "event_filter": "string (optional) — filter by event type (e.g. 'tool_call')",
    "session_id": "string (optional) — filter by session ID",
    "summarize": "bool (optional, default false) — return summary stats instead of events",
    "since_step": "int (optional) — only return events from this step onward"
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_TRACE = os.path.join(BASE_DIR, ".ai_trace.log")


def parse_events(path):
    """Parse JSONL trace log into list of events."""
    events = []

    if not os.path.exists(path):
        return events

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                event["_line"] = line_num
                events.append(event)
            except json.JSONDecodeError:
                events.append({
                    "_line": line_num,
                    "event": "parse_error",
                    "data": line,
                    "step": -1
                })

    return events


def summarize_events(events):
    """Generate summary statistics from trace events."""
    if not events:
        return {"total": 0}

    event_types = {}
    tools_called = []
    errors = []
    steps = set()

    for e in events:
        etype = e.get("event", "unknown")
        event_types[etype] = event_types.get(etype, 0) + 1

        step = e.get("step", -1)
        if step >= 0:
            steps.add(step)

        if etype == "tool_call":
            tools_called.append(e.get("data", "unknown"))

        if "error" in etype:
            errors.append({
                "step": e.get("step"),
                "event": etype,
                "data": e.get("data", "")
            })

    return {
        "total_events": len(events),
        "total_steps": len(steps),
        "event_types": event_types,
        "tools_called": tools_called,
        "error_count": len(errors),
        "errors": errors[:10],  # cap at 10
        "first_step": min(steps) if steps else None,
        "last_step": max(steps) if steps else None,
    }


def run(input_data):
    path = input_data.get("path", DEFAULT_TRACE)
    last_n = input_data.get("last_n", 50)
    event_filter = input_data.get("event_filter", "")
    session_id = input_data.get("session_id", "")
    do_summarize = input_data.get("summarize", False)
    since_step = input_data.get("since_step", None)

    # ---- Resolve path ----
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(BASE_DIR, path))

    if not path.startswith(BASE_DIR):
        return {"status": "error", "output": "Access denied (path outside workspace)"}

    if not os.path.exists(path):
        return {
            "status": "error",
            "output": f"Trace log not found: {path}",
            "hint": "Run 'ai run --trace ...' to generate a trace log"
        }

    # ---- Parse ----
    try:
        events = parse_events(path)

        # ---- Filter by event type ----
        if event_filter:
            events = [e for e in events if e.get("event", "") == event_filter]

        # ---- Filter by session ----
        if session_id:
            events = [e for e in events
                     if str(e.get("session_id", "")) == str(session_id)]

        # ---- Filter by step ----
        if since_step is not None:
            events = [e for e in events
                     if e.get("step", -1) >= int(since_step)]

        # ---- Summarize mode ----
        if do_summarize:
            summary = summarize_events(events)
            return {
                "status": "done",
                "output": summary,
                "path": path
            }

        # ---- Return last N ----
        total = len(events)
        recent = events[-int(last_n):]

        return {
            "status": "done",
            "output": recent,
            "total_events": total,
            "returned": len(recent),
            "path": path
        }

    except Exception as e:
        return {"status": "error", "output": f"Failed to read trace: {str(e)}"}
