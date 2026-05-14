#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ExperimentRun(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    run_id: str
    dag_id: str | None = None
    scenario_id: str | None = None
    evaluation_id: str | None = None
    benchmark_id: str | None = None
    score: float | None = None
    status: str | None = None
    created_at: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentManifest(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    experiment_id: str
    created_at: float
    total_runs: int = 0
    average_score: float = 0.0
    tags: list[str] = Field(default_factory=list)
    runs: list[ExperimentRun] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayDatasetEntry(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    run_id: str
    dag_id: str | None = None
    task: str | None = None
    status: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayDataset(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    dataset_id: str
    created_at: float
    total_entries: int = 0
    entries: list[ReplayDatasetEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
