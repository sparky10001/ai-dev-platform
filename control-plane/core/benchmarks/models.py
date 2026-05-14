#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class BenchmarkScenarioResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    scenario_id: str
    planner_strategy: str
    policy_id: str | None = None
    run_id: str | None = None
    status: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkMatrix(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    matrix_id: str
    scenarios: list[str] = Field(default_factory=list)
    planner_strategies: list[str] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkSuiteResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    benchmark_id: str
    created_at: float
    total_runs: int = 0
    average_score: float = 0.0
    planner_scores: dict[str, float] = Field(default_factory=dict)
    policy_scores: dict[str, float] = Field(default_factory=dict)
    results: list[BenchmarkScenarioResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
