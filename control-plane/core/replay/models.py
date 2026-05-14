#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ReplayNodeResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    node_id: str
    status: str
    tool: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    output: Any = None
    raw_event_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayDagSummary(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    dag_id: str | None = None
    run_id: str
    run_path: str
    status: str
    total_nodes: int = 0
    successful_nodes: int = 0
    failed_nodes: int = 0
    skipped_nodes: int = 0
    tools_used: list[str] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)
    started_at: float | None = None
    completed_at: float | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayDag(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    summary: ReplayDagSummary
    nodes: dict[str, ReplayNodeResult]
    events: list[dict[str, Any]] = Field(default_factory=list)
