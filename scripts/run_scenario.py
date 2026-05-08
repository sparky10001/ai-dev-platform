#!/usr/bin/env python3
###################################################################
# run_scenario.py — Scenario Loader (v2)
###################################################################

import json
import os
import sys

ROOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

REQUIRED_FIELDS = [
    "scenario_id",
    "task",
    "success_criteria"
]


def success(data):
    return {
        "status": "success",
        "data": data
    }


def failure(message, error_type="scenario_error"):
    return {
        "status": "error",
        "error": {
            "message": message,
            "type": error_type
        }
    }


def validate(scenario):

    for field in REQUIRED_FIELDS:
        if field not in scenario:
            return False, f"Missing field: {field}"

    criteria = scenario.get("success_criteria")

    if not isinstance(criteria, list):
        return False, "success_criteria must be a list"

    return True, None


def load_scenario(path):

    full_path = os.path.abspath(path)

    if not os.path.exists(full_path):
        return failure(
            f"Scenario not found: {path}",
            "not_found"
        )

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            scenario = json.load(f)

    except Exception as e:
        return failure(str(e), "parse_error")

    ok, err = validate(scenario)

    if not ok:
        return failure(err, "validation_error")

    return success(scenario)


def main():

    if len(sys.argv) < 2:
        print(json.dumps(
            failure("Missing scenario path")
        ))
        return

    path = sys.argv[1]

    result = load_scenario(path)

    print(json.dumps(result))


if __name__ == "__main__":
    main()