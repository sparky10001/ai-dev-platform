#!/usr/bin/env python3
###################################################################
# runtime/events.py
#
# Phase 3 Runtime Event Writer
#
# Responsibilities:
# - canonical NDJSON persistence
# - schema validation
# - crash-safe flushing
# - deterministic serialization
#
###################################################################

from __future__ import annotations

import json
import os
import time
from typing import Any

from runtime.schemas import SCHEMA_VERSION
from runtime.validator import validate_event


# ================================================================
# 📡 Event Writer
# ================================================================

def log_event(
    run: dict,
    event: str,
    data: Any = None,
    **extra
):

    # ------------------------------------------------------------
    # Canonical payload
    # ------------------------------------------------------------

    payload = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": time.time(),
        "run_id": run["id"],
        "event": event,
        "data": data if data is not None else {},
        **extra
    }

    # ------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------

    validated = validate_event(payload)

    # ------------------------------------------------------------
    # Resolve trace path
    # ------------------------------------------------------------

    trace_path = run["trace_path"]

    # ------------------------------------------------------------
    # Persist NDJSON
    # ------------------------------------------------------------

    with open(trace_path, "a", encoding="utf-8") as f:

        f.write(
            json.dumps(validated.model_dump(mode="json")) + "\n"
        )

        # --------------------------------------------------------
        # Crash durability
        # --------------------------------------------------------

        f.flush()
        os.fsync(f.fileno())