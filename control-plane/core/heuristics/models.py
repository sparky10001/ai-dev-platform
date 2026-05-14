#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class HeuristicSignal(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    signal_id: str
    strategy_id: str | None = None
    planner_strategy: str | None = None
    policy_id: str | None = None
    score: float | None = None
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyRanking(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    ranking_id: str
    created_at: float
    total_variants: int = 0
    ranked_strategy_ids: list[str] = Field(default_factory=list)
    average_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    recommendation_id: str
    task: str
    recommended_planner: str | None = None
    recommended_policy: str | None = None
    confidence: float = 0.0
    supporting_signals: list[HeuristicSignal] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HeuristicCorpus(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    corpus_id: str
    created_at: float
    total_signals: int = 0
    signals: list[HeuristicSignal] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
