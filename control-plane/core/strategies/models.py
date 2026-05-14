#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class StrategyVariant(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    strategy_id: str
    planner_strategy: str
    policy_id: str | None = None
    dag_id: str | None = None
    run_id: str | None = None
    score: float | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyExperiment(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    experiment_id: str
    task: str
    created_at: float
    variants: list[StrategyVariant] = Field(default_factory=list)
    best_strategy_id: str | None = None
    average_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyComparison(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    comparison_id: str
    left_strategy_id: str
    right_strategy_id: str
    score_delta: float = 0.0
    execution_order_changed: bool = False
    tool_usage_changed: bool = False
    node_count_delta: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
