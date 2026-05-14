#!/usr/bin/env python3
###################################################################
# runtime/run.py
#
# Phase 3 Run Management
#
# Responsibilities:
# - canonical run creation
# - deterministic run metadata
# - schema versioning
# - replay-safe persistence
# - result finalization
#
###################################################################

from __future__ import annotations

import json
import time

from pathlib import Path
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from runtime.schemas import SCHEMA_VERSION


# ================================================================
# 📁 Root
# ================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

RUNS_DIR = ROOT_DIR / "runs"

RUNS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ================================================================
# 🧾 Run Schema
# ================================================================

class RunSchema(BaseModel):

    model_config = ConfigDict(
        extra="allow"
    )

    schema_version: int = SCHEMA_VERSION

    id: str

    task: str

    command: str

    model: str

    status: Literal[
        "running",
        "done",
        "error"
    ] = "running"

    created_at: float

    completed_at: Optional[float] = None

    run_path: str

    trace_path: str

    result_path: str


# ================================================================
# 🆔 Run ID
# ================================================================

def generate_run_id() -> str:

    return f"run_{int(time.time() * 1000)}"


# ================================================================
# 🚀 Create Run
# ================================================================

def create_run(
    task: str,
    command: str,
    model: str,
):

    run_id = generate_run_id()

    run_dir = RUNS_DIR / run_id

    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    run = RunSchema(
        id=run_id,
        task=task,
        command=command,
        model=model,
        status="running",
        created_at=time.time(),
        run_path=str(run_dir),
        trace_path=str(run_dir / "trace.jsonl"),
        result_path=str(run_dir / "result.json"),
    )

    # ------------------------------------------------------------
    # Persist canonical run metadata
    # ------------------------------------------------------------

    (run_dir / "run.json").write_text(
        run.model_dump_json(indent=2),
        encoding="utf-8"
    )

    return run.model_dump()


# ================================================================
# 🏁 Finalize Run
# ================================================================

def finalize_run(
    run: dict,
    result: dict
):

    run_dir = Path(run["run_path"])

    # ------------------------------------------------------------
    # Update run state
    # ------------------------------------------------------------

    updated = RunSchema(
        **{
            **run,
            "status": result.get(
                "status",
                "done"
            ),
            "completed_at": time.time(),
        }
    )

    # ------------------------------------------------------------
    # Persist updated run metadata
    # ------------------------------------------------------------

    (run_dir / "run.json").write_text(
        updated.model_dump_json(indent=2),
        encoding="utf-8"
    )

    # ------------------------------------------------------------
    # Persist final result
    # ------------------------------------------------------------

    (run_dir / "result.json").write_text(
        json.dumps(
            result,
            indent=2
        ),
        encoding="utf-8"
    )