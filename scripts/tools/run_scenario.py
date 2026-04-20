###################################################################
# run_scenario.py — Scenario spec loader and validator (v1.2)
#
# Loads, validates, and prepares scenario specs for execution.
# Bridge between agent-sim scenario definitions and ai-dev-platform
# execution engine.
#
# Part of the Simulation-Driven CI pipeline:
#   scenario spec → run_scenario → execution → read_trace → evaluate
###################################################################

import json
import os
from datetime import datetime

name = "run_scenario"
description = (
    "Load, validate, and prepare a scenario spec for execution. "
    "Use before running agent evaluations to establish the task contract."
)
input_schema = {
    "path": "string (required) — path to scenario JSON file",
    "validate_only": "bool (optional, default false) — only validate, don't prepare",
    "override": "dict (optional) — override specific scenario fields"
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# ---- Required fields ----
REQUIRED_FIELDS = [
    "scenario_id",
    "task",
    "success_criteria"
]

# ---- Optional fields with defaults ----
DEFAULTS = {
    "name": "Unnamed Scenario",
    "project": "unknown",
    "agent": "default",
    "timeout": 60,
    "context": {},
    "initial_input": "",
    "tags": []
}


def validate_scenario(scenario):
    """
    Validate scenario spec against contract.
    Returns (is_valid, list_of_errors)
    """
    errors = []

    # ---- Required fields ----
    for field in REQUIRED_FIELDS:
        if field not in scenario:
            errors.append(f"Missing required field: '{field}'")

    # ---- success_criteria must be a non-empty list ----
    criteria = scenario.get("success_criteria")
    if criteria is not None:
        if not isinstance(criteria, list):
            errors.append("'success_criteria' must be a list")
        elif len(criteria) == 0:
            errors.append("'success_criteria' must have at least one item")

    # ---- scenario_id format ----
    sid = scenario.get("scenario_id", "")
    if sid and not all(c.isalnum() or c in "-_" for c in sid):
        errors.append(
            "'scenario_id' must contain only alphanumeric, dash, or underscore"
        )

    # ---- timeout must be positive int ----
    timeout = scenario.get("timeout")
    if timeout is not None:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append("'timeout' must be a positive number")

    return len(errors) == 0, errors


def prepare_scenario(scenario, overrides=None):
    """
    Apply defaults and overrides to scenario.
    Returns prepared scenario dict.
    """
    prepared = {**DEFAULTS, **scenario}

    if overrides and isinstance(overrides, dict):
        prepared.update(overrides)

    # ---- Inject runtime metadata ----
    prepared["_prepared_at"] = datetime.utcnow().isoformat()
    prepared["_runtime"] = "ai-dev-platform"

    return prepared


def run(input_data):
    path = input_data.get("path")
    validate_only = input_data.get("validate_only", False)
    overrides = input_data.get("override", {})

    # ---- Validate input ----
    if not path:
        return {"status": "error", "output": "Missing 'path'"}

    # ---- Resolve path ----
    if not os.path.isabs(path):
        full_path = os.path.abspath(os.path.join(BASE_DIR, path))
    else:
        full_path = os.path.abspath(path)

    if not full_path.startswith(BASE_DIR):
        return {"status": "error", "output": "Access denied (path outside workspace)"}

    if not os.path.exists(full_path):
        return {
            "status": "error",
            "output": f"Scenario file not found: {path}",
            "hint": "Check scenarios/ directory for available specs"
        }

    # ---- Load JSON ----
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            scenario = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "output": f"Invalid JSON in scenario file: {str(e)}"
        }
    except Exception as e:
        return {"status": "error", "output": f"Failed to read scenario: {str(e)}"}

    # ---- Validate ----
    is_valid, errors = validate_scenario(scenario)

    if not is_valid:
        return {
            "status": "error",
            "output": f"Invalid scenario spec: {'; '.join(errors)}",
            "errors": errors,
            "path": path
        }

    # ---- Validate only mode ----
    if validate_only:
        return {
            "status": "done",
            "output": f"Scenario valid: {scenario.get('scenario_id')}",
            "scenario_id": scenario.get("scenario_id"),
            "criteria_count": len(scenario.get("success_criteria", [])),
            "path": path
        }

    # ---- Prepare ----
    prepared = prepare_scenario(scenario, overrides)

    return {
        "status": "done",
        "output": prepared,
        "scenario_id": prepared["scenario_id"],
        "task": prepared["task"],
        "criteria_count": len(prepared["success_criteria"]),
        "path": path
    }
