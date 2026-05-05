#!/usr/bin/env python3
###################################################################
# read_trace.py — Execution trace reader (v4.0)
#
# Updates:
# - Uses logs/traces directory (AI_TRACE_DIR aware)
# - Supports session-based trace files
# - Auto-resolves latest trace if no path provided
# - Maintains full backward compatibility
###################################################################

import json
import os
from typing import Any, Dict, List

name = "read_trace"
description = "Read and analyze the AI execution trace log"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

DEFAULT_TRACE_DIR = os.getenv(
    "AI_TRACE_DIR",
    os.path.join(BASE_DIR, "logs", "traces")
)


# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "last_n": {"type": "integer", "default": 50},
        "event_filter": {"type": "string"},
        "session_id": {"type": "string"},
        "summarize": {"type": "boolean", "default": False},
        "since_step": {"type": "integer"}
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
# 🔐 PATH RESOLUTION
# ================================================================

def resolve_path(path: str | None) -> str | None:
    """
    Resolves:
    - explicit path
    - relative path
    - latest trace fallback
    """

    # ---- Case 1: explicit path ----
    if path:
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(BASE_DIR, path))
        if not path.startswith(BASE_DIR):
            return None
        return path

    # ---- Case 2: auto-resolve latest trace ----
    if not os.path.exists(DEFAULT_TRACE_DIR):
        return None

    files = [
        f for f in os.listdir(DEFAULT_TRACE_DIR)
        if f.startswith("ai_trace.") and f.endswith(".log")
    ]

    if not files:
        return None

    files.sort(
        key=lambda f: os.path.getmtime(os.path.join(DEFAULT_TRACE_DIR, f)),
        reverse=True
    )

    return os.path.join(DEFAULT_TRACE_DIR, files[0])


# ================================================================
# 📄 PARSE NDJSON TRACE
# ================================================================

def parse_events(path: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []

    if not os.path.exists(path):
        return events

    buffer = ""

    def try_parse(chunk: str):
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                events.append(obj)
                return True
        except json.JSONDecodeError:
            return False
        return False

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("{") and line.endswith("}"):
                if try_parse(line):
                    continue

            buffer += line

            if try_parse(buffer):
                buffer = ""

    return events


# ================================================================
# 🔥 FLATTEN NESTED TRACE STRUCTURES
# ================================================================

def flatten_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def extract(e: Any):
        if not isinstance(e, dict):
            return

        out.append(e)

        data = e.get("data")
        if isinstance(data, dict):
            meta = data.get("meta", {})
            if isinstance(meta, dict):
                trace = meta.get("trace")
                if isinstance(trace, list):
                    for sub in trace:
                        extract(sub)

        meta = e.get("meta", {})
        if isinstance(meta, dict):
            trace = meta.get("trace")
            if isinstance(trace, list):
                for sub in trace:
                    extract(sub)

    for e in events:
        extract(e)

    return out


# ================================================================
# 📊 SUMMARY
# ================================================================

def summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        if isinstance(step, int) and step >= 0:
            steps.add(step)

        if etype == "tool_call":
            tool = e.get("data")
            if isinstance(tool, str):
                tools_called.append(tool)

        if "error" in etype:
            errors.append({
                "step": step,
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
    }


# ================================================================
# 🚀 MAIN ENTRY
# ================================================================

def run(input_data: Dict[str, Any]):
    path = input_data.get("path")
    last_n = int(input_data.get("last_n", 50))
    event_filter = input_data.get("event_filter")
    session_id = input_data.get("session_id")
    do_summarize = bool(input_data.get("summarize", False))
    since_step = input_data.get("since_step")

    full_path = resolve_path(path)

    if not full_path:
        return failure(
            "Trace file not found",
            "not_found",
            meta={"hint": "Ensure traces exist in logs/traces or pass explicit path"}
        )

    try:
        events = parse_events(full_path)
        events = flatten_events(events)

        if event_filter:
            events = [e for e in events if e.get("event") == event_filter]

        if since_step is not None:
            since_step = int(since_step)
            events = [
                e for e in events
                if isinstance(e.get("step"), int) and e.get("step") >= since_step
            ]

        if do_summarize:
            return success(
                summarize_events(events),
                meta={"path": full_path, "mode": "summary"}
            )

        total = len(events)

        if last_n > 0:
            tail = events[-last_n:]
            tool_events = [e for e in events if e.get("event") == "tool_call"]

            seen = set()
            merged = []

            for e in tail + tool_events:
                key = (e.get("event"), e.get("step"), str(e.get("data")))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(e)

            recent = merged
        else:
            recent = events

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