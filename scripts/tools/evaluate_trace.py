#!/usr/bin/env python3
###################################################################
# evaluate_trace.py — Trace evaluator (production v5.0)
#
# Guarantees:
# - Fully normalized deterministic tool extraction
# - Single source of truth for tool parsing
# - Safe recursive trace flattening
# - Stable evaluation scoring
# - No divergence between tool_set and tool_calls
###################################################################

import json
from typing import Any, Dict, List

Event = Dict[str, Any]
Criteria = List[Dict[str, Any]]


# ============================================================
# 🧪 Normalization
# ============================================================

def normalize_events(events: Any) -> List[Event]:
    if not isinstance(events, list):
        return []

    out: List[Event] = []

    for e in events:
        if isinstance(e, str):
            try:
                e = json.loads(e)
            except Exception:
                continue

        if isinstance(e, dict):
            out.append(e)

    return out


def normalize_criteria(criteria: Any) -> Criteria:
    return criteria if isinstance(criteria, list) else []


def validate_criteria(criteria: Criteria) -> Criteria:
    return [c for c in criteria if isinstance(c, dict) and "type" in c]


# ============================================================
# 🔥 Trace Flattening (safe recursion)
# ============================================================

def flatten_events(events: List[Event]) -> List[Event]:
    out: List[Event] = []

    def extract(e: Any):
        # 🔥 Normalize string → dict
        if isinstance(e, str):
            try:
                e = json.loads(e)
            except Exception:
                return

        if not isinstance(e, dict):
            return

        out.append(e)

        # --------------------------------------------------
        # 🔍 Traverse data.meta.trace
        # --------------------------------------------------
        data = e.get("data")
        if isinstance(data, dict):
            meta = data.get("meta")
            if isinstance(meta, dict):
                trace = meta.get("trace")
                if isinstance(trace, list):
                    for sub in trace:
                        extract(sub)

        # --------------------------------------------------
        # 🔍 Traverse meta.trace
        # --------------------------------------------------
        meta = e.get("meta")
        if isinstance(meta, dict):
            trace = meta.get("trace")
            if isinstance(trace, list):
                for sub in trace:
                    extract(sub)

    for e in events:
        extract(e)

    return out


# ============================================================
# 🔍 SINGLE SOURCE OF TRUTH: TOOL EXTRACTION
# ============================================================

def _normalize_tool(t: Any) -> str | None:
    if not isinstance(t, str):
        return None
    t = t.strip().lower()
    return t if t else None


def extract_tool(event: Event) -> str | None:
    if event.get("event") != "tool_call":
        return None

    meta = event.get("meta", {})
    data = event.get("data")

    candidates = []

    # data string
    if isinstance(data, str):
        candidates.append(data)

    # data dict
    if isinstance(data, dict):
        candidates.append(data.get("tool"))
        candidates.append(data.get("name"))

    # meta.tool
    if isinstance(meta, dict):
        candidates.append(meta.get("tool"))

        output = meta.get("output", {})
        if isinstance(output, dict):
            inner_meta = output.get("meta", {})
            if isinstance(inner_meta, dict):
                candidates.append(inner_meta.get("tool"))

    for c in candidates:
        tool = _normalize_tool(c)
        if tool:
            return tool

    return None


def tool_calls(events: List[Event]) -> List[str]:
    return [t for t in (extract_tool(e) for e in events) if t]


def tool_call_set(events: List[Event]) -> set:
    # SINGLE SOURCE OF TRUTH (no divergence possible)
    return set(tool_calls(events))


def has_tool(events: List[Event], tool: str) -> bool:
    tool = _normalize_tool(tool)
    if not tool:
        return False
    return tool in tool_call_set(events)


# ============================================================
# 🧪 Criteria evaluation
# ============================================================

def eval_tool_used(events: List[Event], c: Dict[str, Any]) -> bool:
    return has_tool(events, c.get("tool") or c.get("name"))


def eval_no_errors(events: List[Event], _: Dict[str, Any]) -> bool:
    for e in events:
        if not isinstance(e, dict):
            continue

        if e.get("error"):
            return False

        meta = e.get("meta")
        if isinstance(meta, dict) and meta.get("error"):
            return False

    return True


# ============================================================
# 🧠 Evaluation engine
# ============================================================

def evaluate(events: List[Event], criteria: Criteria):
    results = []
    passed = 0

    tool_set = tool_call_set(events)

    for c in criteria:
        ctype = c.get("type")

        if ctype == "tool_used":
            tool = _normalize_tool(c.get("tool") or c.get("name"))
            ok = tool in tool_set if tool else False

        elif ctype == "no_errors":
            ok = eval_no_errors(events, c)

        else:
            ok = False

        results.append({
            "criteria": c,
            "passed": bool(ok)
        })

        passed += int(bool(ok))

    total = len(criteria)

    return {
        "score": passed / total if total else 0,
        "passed": passed,
        "total": total,
        "results": results
    }


# ============================================================
# 🚀 Entry point
# ============================================================

def run(input_data: Dict[str, Any]):
    try:
        events = flatten_events(normalize_events(input_data.get("events")))
        criteria = validate_criteria(normalize_criteria(input_data.get("criteria")))

        result = evaluate(events, criteria)

        return {
            "status": "success",
            "data": result,
            "error": None,
            "meta": {}
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": {"message": str(e)},
            "meta": {}
        }