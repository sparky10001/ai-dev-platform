#!/usr/bin/env python3
###################################################################
# runtime/loader.py
#
# Phase 3 Runtime Loader
#
# Responsibilities:
# - run discovery
# - trace loading
# - result loading
# - replay helpers
# - eval loading
#
###################################################################

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.replay import replay_trace


ROOT_DIR = Path(__file__).resolve().parent.parent

RUNS_DIR = ROOT_DIR / "runs"
EVALS_DIR = ROOT_DIR / "logs" / "evals"


# ================================================================
# 📦 Run Resolution
# ================================================================

def get_run_path(run_id: str) -> Path:

    return RUNS_DIR / run_id


# ================================================================
# 📄 Load run.json
# ================================================================

def load_run(run_id: str) -> dict[str, Any]:

    path = get_run_path(run_id) / "run.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ================================================================
# 📄 Load result.json
# ================================================================

def load_result(run_id: str) -> dict[str, Any]:

    path = get_run_path(run_id) / "result.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ================================================================
# 📡 Load replayable trace
# ================================================================

def load_trace(run_id: str):

    path = get_run_path(run_id) / "trace.jsonl"

    replay = replay_trace(
        path,
        strict=True,
    )

    return replay.events


def load_run_trace(run_id: str):

    return load_trace(run_id)


# ================================================================
# 📦 Load complete run bundle
# ================================================================

def load_full_run(run_id: str) -> dict[str, Any]:

    return {
        "run": load_run(run_id),
        "result": load_result(run_id),
        "trace": load_trace(run_id),
    }


# ================================================================
# 📊 Load eval record
# ================================================================

def load_eval(run_id: str) -> dict[str, Any]:

    path = EVALS_DIR / f"eval.{run_id}.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ================================================================
# 📚 List runs
# ================================================================

def list_runs():

    if not RUNS_DIR.exists():
        return []

    return sorted(
        [
            p.name
            for p in RUNS_DIR.iterdir()
            if p.is_dir()
        ]
    )


# ================================================================
# 📚 List evals
# ================================================================

def list_evals():

    if not EVALS_DIR.exists():
        return []

    return sorted(
        [
            p.name
            for p in EVALS_DIR.glob("eval.*.json")
        ]
    )