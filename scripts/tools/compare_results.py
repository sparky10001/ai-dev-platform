###################################################################
# compare_results.py — v8 Tool (Strict Contract + Robust Eval)
#
# Guarantees:
# - Strict input_schema (required by tool_executor v8)
# - Deterministic structured output
# - Defensive against malformed eval files
# - Stable comparison (no index-based assumptions)
###################################################################

import json
import os

name = "compare_results"
description = "Compare two evaluation result files"

input_schema = {
    "type": "object",
    "properties": {
        "baseline": {
            "type": "string",
            "description": "Path to baseline result JSON file"
        },
        "current": {
            "type": "string",
            "description": "Path to current result JSON file"
        }
    },
    "required": ["baseline", "current"]
}


# ================================================================
# 📦 Helpers
# ================================================================
def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r") as f:
        return json.load(f)


def normalize_results(results):
    """
    Convert results into dict keyed by criteria for stable comparison
    """
    out = {}

    for r in results:
        key = r.get("criteria") or str(r)
        out[key] = {
            "passed": bool(r.get("passed", False)),
            "raw": r
        }

    return out


# ================================================================
# 🚀 Main Tool
# ================================================================
def run(input_data):
    baseline_path = input_data.get("baseline")
    current_path = input_data.get("current")

    # ------------------------------------------------------------
    # ❌ Input validation
    # ------------------------------------------------------------
    if not baseline_path or not current_path:
        return {
            "status": "error",
            "error": {
                "message": "Missing required fields: baseline, current",
                "type": "validation_error"
            }
        }

    # ------------------------------------------------------------
    # 📥 Load files
    # ------------------------------------------------------------
    try:
        base = load_json(baseline_path)
        curr = load_json(current_path)
    except Exception as e:
        return {
            "status": "error",
            "error": {
                "message": str(e),
                "type": "file_error"
            }
        }

    # ------------------------------------------------------------
    # 🧠 Extract scores safely
    # ------------------------------------------------------------
    base_score = float(base.get("score", 0))
    curr_score = float(curr.get("score", 0))
    score_diff = curr_score - base_score

    # ------------------------------------------------------------
    # 🔍 Normalize results (NO index assumptions)
    # ------------------------------------------------------------
    base_results = normalize_results(base.get("results", []))
    curr_results = normalize_results(curr.get("results", []))

    regressions = []
    improvements = []
    unchanged = []

    all_keys = set(base_results.keys()) | set(curr_results.keys())

    for key in all_keys:
        b = base_results.get(key, {"passed": False})
        c = curr_results.get(key, {"passed": False})

        if b["passed"] and not c["passed"]:
            regressions.append(key)
        elif not b["passed"] and c["passed"]:
            improvements.append(key)
        else:
            unchanged.append(key)

    # ------------------------------------------------------------
    # 📊 Final structured output
    # ------------------------------------------------------------
    return {
        "status": "success",
        "data": {
            "baseline_score": base_score,
            "current_score": curr_score,
            "score_diff": score_diff,

            "regressed": score_diff < 0,
            "improved": score_diff > 0,

            "summary": {
                "total": len(all_keys),
                "regressions": len(regressions),
                "improvements": len(improvements),
                "unchanged": len(unchanged)
            },

            "regressions": regressions,
            "improvements": improvements,
            "unchanged": unchanged
        },
        "meta": {
            "tool": "compare_results",
            "version": "v8"
        }
    }