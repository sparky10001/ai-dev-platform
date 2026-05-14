#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class OrchestrationMetric(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    name: str
    value: float | int | str | bool | None = None
    passed: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestrationEvaluation(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    evaluation_id: str
    run_id: str | None = None
    dag_id: str | None = None
    status: Literal['success', 'error']
    score: float = 0.0
    metrics: list[OrchestrationMetric] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayComparison(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    comparison_id: str
    left_run_id: str
    right_run_id: str
    identical: bool = False
    score_delta: float = 0.0
    tool_delta: list[str] = Field(default_factory=list)
    execution_order_changed: bool = False
    node_count_delta: int = 0
    status_changed: bool = False
    differences: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    benchmark_id: str
    status: Literal['success', 'error']
    total_runs: int = 0
    average_score: float = 0.0
    successful_runs: int = 0
    failed_runs: int = 0
    evaluations: list[OrchestrationEvaluation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
