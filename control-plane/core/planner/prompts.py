#!/usr/bin/env python3
from __future__ import annotations

DAG_PLANNER_SYSTEM_PROMPT = (
    "You are a deterministic DAG planner. Build a minimal, valid DAG specification "
    "from a task using known tools only."
)

DETERMINISTIC_PLANNER_PROMPT = (
    "Convert task text into a static DAG with deterministic node ordering. "
    "Do not execute tools and do not call external models."
)
