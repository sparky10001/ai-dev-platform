#!/usr/bin/env python3
###################################################################
# runtime/runner.py
#
# Phase 3 Adapter Runner
#
# Responsibilities:
# - deterministic adapter execution
# - timeout enforcement
# - subprocess isolation
# - normalized execution envelopes
# - replay-safe execution metadata
#
###################################################################

from __future__ import annotations

import os
import subprocess
import time

from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


# ================================================================
# 📦 Execution Result Schema
# ================================================================

class AdapterExecutionResult(BaseModel):

    model_config = ConfigDict(
        extra="allow"
    )

    stdout: str

    stderr: str

    returncode: int

    duration_seconds: float

    timed_out: bool = False

    crashed: bool = False


# ================================================================
# 🚀 Execute Adapter
# ================================================================

def execute_adapter(
    adapter: Path,
    command: str,
    user_input: str,
    model: str,
    env: Optional[dict] = None,
) -> dict:

    timeout = int(
        os.getenv(
            "AI_TIMEOUT",
            "120"
        )
    )

    start = time.time()

    # ------------------------------------------------------------
    # Environment Isolation
    # ------------------------------------------------------------

    runtime_env = os.environ.copy()

    if env:
        runtime_env.update(env)

    # ------------------------------------------------------------
    # Build Command
    # ------------------------------------------------------------

    cmd = [
        str(adapter),
        command,
        user_input,
        f"--model={model}",
    ]

    try:

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=runtime_env,
        )

        result = AdapterExecutionResult(
            stdout=(proc.stdout or "").strip(),
            stderr=(proc.stderr or "").strip(),
            returncode=proc.returncode,
            duration_seconds=(
                time.time() - start
            ),
            timed_out=False,
            crashed=(proc.returncode != 0),
        )

        return result.model_dump()

    # ============================================================
    # ⏰ Timeout Handling
    # ============================================================

    except subprocess.TimeoutExpired as e:

        result = AdapterExecutionResult(
            stdout=(e.stdout or "").strip()
            if e.stdout else "",
            stderr=(e.stderr or "").strip()
            if e.stderr else "",
            returncode=124,
            duration_seconds=(
                time.time() - start
            ),
            timed_out=True,
            crashed=False,
        )

        return result.model_dump()

    # ============================================================
    # 💥 Runtime Failure
    # ============================================================

    except Exception as e:

        result = AdapterExecutionResult(
            stdout="",
            stderr=str(e),
            returncode=1,
            duration_seconds=(
                time.time() - start
            ),
            timed_out=False,
            crashed=True,
        )

        return result.model_dump()