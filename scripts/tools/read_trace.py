#!/usr/bin/env python3
###################################################################
# read_trace.py — Execution trace reader (MCP-compliant v3.0)
#
# Guarantees:
# - NDJSON-safe parsing
# - Canonical event structure
# - Nested trace flattening (CRITICAL)
# - Stable output for evaluators
###################################################################

import json
import os
from typing import Any, Dict, List

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
            "default": ".ai_trace.log"
        },
        "last_n": {
            "type": "integer",
            "default": 50
        },
        "event_filter": {
            "type": "string"
        },
        "session_id": {
            "type": "string"
        },
        "summarize": {
            "type": "boolean",
            "default": False
        },
        "since_step": {
            "type": "integer"
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

def resolve_path(path: str) -> str | None:
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not path.startswith(BASE_DIR):
        return None
    return path


# ================================================================
# 📄 PARSE NDJSON TRACE
# ================================================================

def parse_events(path: str) -> List[Dict[str, Any]]:
    """
    Robust parser that supports:
    - NDJSON (one JSON object per line)
    - Pretty-printed multi-line JSON objects
    - Mixed formats (CRITICAL FIX)
    """
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

            # Case 1: clean single-line JSON
            if line.startswith("{") and line.endswith("}"):
                if try_parse(line):
                    continue

            # Case 2: multi-line JSON accumulation
            buffer += line

            if try_parse(buffer):
                buffer = ""  # reset after successful parse

    return events


# ================================================================
# 🔥 FLATTEN NESTED TRACE STRUCTURES (CRITICAL FIX)
# ================================================================

def flatten_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def extract(e: Any):
        if not isinstance(e, dict):
            return

        out.append(e)

        # Case 1: agent_output → data.meta.trace
        data = e.get("data")
        if isinstance(data, dict):
            meta = data.get("meta", {})
            if isinstance(meta, dict):
                trace = meta.get("trace")
                if isinstance(trace, list):
                    for sub in trace:
                        extract(sub)

        # Case 2: direct meta.trace
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
            tool = (
                e.get("data")
                or e.get("meta", {}).get("tool")
                or e.get("meta", {}).get("output", {}).get("meta", {}).get("tool")
            )
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
        "first_step": min(steps) if steps else None,
        "last_step": max(steps) if steps else None,
    }


# ================================================================
# 🚀 MAIN ENTRY
# ================================================================

def run(input_data: Dict[str, Any]):
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
        # ---- Parse + Normalize ----
        events = parse_events(full_path)

        # 🔥 CRITICAL: flatten nested traces
        events = flatten_events(events)

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
            events = [
                e for e in events
                if isinstance(e.get("step"), int) and e.get("step") >= since_step
            ]

        # ---- Summarize ----
        if do_summarize:
            return success(
                summarize_events(events),
                meta={"path": full_path, "mode": "summary"}
            )

        # ---- Return last N ----
        total = len(events)
        # 🔥 Always include ALL tool_call events
        if last_n > 0:
            tail = events[-last_n:]

            # Extract ALL tool_calls globally
            tool_events = [e for e in events if e.get("event") == "tool_call"]

            # Merge + dedupe
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