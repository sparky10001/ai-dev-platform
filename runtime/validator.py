#!/usr/bin/env python3
###################################################################
# runtime/validator.py
#
# Centralized schema validation layer (Phase 3)
#
# Responsibilities:
# ✅ Validate runtime events
# ✅ Validate agent responses
# ✅ Validate replay payloads
# ✅ Enforce schema versioning
# ✅ Normalize all external contracts
#
# Used by:
# - runtime/events.py
# - scripts/agent.py
# - runtime/replay.py
# - future evaluator/replay systems
###################################################################

import json

from runtime.contracts import validate_event_contract
from runtime.contracts import validate_response_contract

# ================================================================
# Event Validation
# ================================================================

def validate_event(payload: dict):

    """
    Validate a runtime trace event.
    """

    return validate_event_contract(payload)


def validate_event_json(line: str):

    """
    Validate raw NDJSON event line.
    """

    payload = json.loads(line)

    return validate_event(payload)

# ================================================================
# Response Validation
# ================================================================

def validate_response(payload: dict):

    """
    Validate external runtime/agent response.

    This is now the canonical external contract.
    """

    return validate_response_contract(payload)


def validate_response_json(raw: str):

    """
    Validate serialized JSON response.
    """

    payload = json.loads(raw)

    return validate_response(payload)

# ================================================================
# Replay Validation
# ================================================================

def validate_trace_file(path):

    """
    Validate an entire NDJSON trace file.

    Returns:
        list[pydantic.BaseModel]
    """

    validated = []

    with open(path, "r", encoding="utf-8") as f:

        for line_no, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:

                validated.append(
                    validate_event_json(line)
                )

            except Exception as e:

                raise ValueError(
                    f"{path}:{line_no}: {e}"
                ) from e

    return validated

# ================================================================
# Safe Helpers
# ================================================================

def is_valid_event(payload):

    try:
        validate_event(payload)
        return True
    except Exception:
        return False


def is_valid_response(payload):

    try:
        validate_response(payload)
        return True
    except Exception:
        return False