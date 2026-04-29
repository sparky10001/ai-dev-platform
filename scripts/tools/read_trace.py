###################################################################
# read_trace.py — Execution trace reader (MCP-compliant v2.0)
###################################################################

import json
import os

name = "read_trace"
description = "Read and analyze the AI execution trace log"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_TRACE = os.path.join(BASE_DIR, ".ai_trace.log")

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Trace log path",
            "default": ".ai_trace.log"
        },
        "last_n": {
            "type": "integer",
            "description": "Number of recent events to return",
            "default": 50
        },
        "event_filter": {
            "type": "string",
            "description": "Filter by event type"
        },
        "session_id": {
            "type": "string",
            "description": "Filter by session ID"
        },
        "summarize": {
            "type": "boolean",
            "description": "Return summary instead of raw events",
            "default": False
        },
        "since_step": {
            "type": "integer",
            "description": "Only return events from this step onward"
        }
    }
}

# ================================================================
# 🧱 RESPONSE HELPERS
# ================================================================

def success(data, meta=None):
    return {
        "status": "success",
        "data": data,
        "error": None,
        "meta": meta or {}
    }

def failure(message, error_type="tool_error", meta=None):
    return {
        "status": "error",
        "data": None,
        "error": {
            "message": message,
            "type": error_type
        },
        "meta": meta or {}
    }

# ================================================================
# 🔐 PATH SAFETY
# ================================================================

def resolve_path(path):
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not path.startswith(BASE_DIR):
        return None
    return path

# ================================================================
# 📄 PARSING
# ================================================================

def parse_events(path):
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

# ================================================================
# 📊 SUMMARY
# ================================================================

def summarize_events(events):
    if not events:
        return {"total_events": 0}

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
        "errors": errors[:10],
        "first_step": min(steps) if steps else None,
        "last_step": max(steps) if steps else None,
    }

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    path = input_data.get("path", ".ai_trace.log")
    last_n = int(input_data.get("last_n", 50))
    event_filter = input_data.get("event_filter")
    session_id = input_data.get("session_id")
    do_summarize = bool(input_data.get("summarize", False))
    since_step = input_data.get("since_step")

    # ---- Resolve path ----
    full_path = resolve_path(path)
    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    if not os.path.exists(full_path):
        return failure(
            f"Trace log not found: {path}",
            "not_found",
            meta={"hint": "Run with --trace to generate logs"}
        )

    try:
        events = parse_events(full_path)

        # ---- Filters ----
        if event_filter:
            events = [e for e in events if e.get("event") == event_filter]

        if session_id:
            events = [
                e for e in events
                if str(e.get("session_id", "")) == str(session_id)
            ]

        if since_step is not None:
            since_step = int(since_step)
            events = [e for e in events if e.get("step", -1) >= since_step]

        # ---- Summarize ----
        if do_summarize:
            return success(
                summarize_events(events),
                meta={"path": full_path, "mode": "summary"}
            )

        # ---- Return last N ----
        total = len(events)
        recent = events[-last_n:]

        return success(
            recent,
            meta={
                "path": full_path,
                "mode": "events",
                "total_events": total,
                "returned": len(recent)
            }
        )

    except Exception as e:
        return failure(f"Failed to read trace: {str(e)}", "execution_error")