###################################################################
# run_scenario.py — Scenario loader & validator (MCP v2.0)
###################################################################

import json
import os
from datetime import datetime

name = "run_scenario"
description = "Load, validate, and prepare a scenario spec for execution"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to scenario JSON file"
        },
        "validate_only": {
            "type": "boolean",
            "description": "Only validate scenario",
            "default": False
        },
        "override": {
            "type": "object",
            "description": "Override scenario fields"
        }
    },
    "required": ["path"]
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
# 📋 SCHEMA RULES
# ================================================================

REQUIRED_FIELDS = ["scenario_id", "task", "success_criteria"]

DEFAULTS = {
    "name": "Unnamed Scenario",
    "project": "unknown",
    "agent": "default",
    "timeout": 60,
    "context": {},
    "initial_input": "",
    "tags": []
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
# ✅ VALIDATION
# ================================================================

def validate_scenario(scenario):
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in scenario:
            errors.append({
                "field": field,
                "message": f"Missing required field: '{field}'"
            })

    criteria = scenario.get("success_criteria")
    if criteria is not None:
        if not isinstance(criteria, list):
            errors.append({
                "field": "success_criteria",
                "message": "Must be a list"
            })
        elif len(criteria) == 0:
            errors.append({
                "field": "success_criteria",
                "message": "Must contain at least one item"
            })

    sid = scenario.get("scenario_id", "")
    if sid and not all(c.isalnum() or c in "-_" for c in sid):
        errors.append({
            "field": "scenario_id",
            "message": "Invalid format (alphanumeric, dash, underscore only)"
        })

    timeout = scenario.get("timeout")
    if timeout is not None:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append({
                "field": "timeout",
                "message": "Must be a positive number"
            })

    return len(errors) == 0, errors

# ================================================================
# 🛠️ PREPARATION
# ================================================================

def prepare_scenario(scenario, overrides=None):
    prepared = {**DEFAULTS, **scenario}

    if isinstance(overrides, dict):
        prepared.update(overrides)

    prepared["_prepared_at"] = datetime.utcnow().isoformat()
    prepared["_runtime"] = "ai-dev-platform"

    return prepared

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    path = input_data.get("path")
    validate_only = bool(input_data.get("validate_only", False))
    overrides = input_data.get("override", {})

    # ---- Validate input ----
    if not isinstance(path, str) or not path:
        return failure("Invalid or missing 'path'", "validation_error")

    full_path = resolve_path(path)
    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    if not os.path.exists(full_path):
        return failure(
            f"Scenario file not found: {path}",
            "not_found",
            meta={"hint": "Check scenarios/ directory"}
        )

    # ---- Load JSON ----
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            scenario = json.load(f)
    except json.JSONDecodeError as e:
        return failure(
            f"Invalid JSON: {str(e)}",
            "parse_error"
        )
    except Exception as e:
        return failure(
            f"Failed to read scenario: {str(e)}",
            "execution_error"
        )

    # ---- Validate ----
    is_valid, errors = validate_scenario(scenario)

    if not is_valid:
        return failure(
            "Invalid scenario spec",
            "validation_error",
            meta={
                "errors": errors,
                "path": path
            }
        )

    # ---- Validate-only mode ----
    if validate_only:
        return success(
            {
                "valid": True,
                "scenario_id": scenario.get("scenario_id"),
                "criteria_count": len(scenario.get("success_criteria", []))
            },
            meta={"path": path, "mode": "validate"}
        )

    # ---- Prepare ----
    prepared = prepare_scenario(scenario, overrides)

    return success(
        {
            "scenario": prepared,
            "scenario_id": prepared["scenario_id"],
            "task": prepared["task"],
            "criteria_count": len(prepared["success_criteria"])
        },
        meta={"path": path, "mode": "prepare"}
    )