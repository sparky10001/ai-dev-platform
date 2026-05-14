#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class ControlPlaneScenarioExpectation(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    status: str | None = None
    planner_status: str | None = None
    execution_status: str | None = None
    dag_id: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    nodes_executed: list[str] = Field(default_factory=list)
    nodes_skipped: list[str] = Field(default_factory=list)
    requires_run_artifact: bool = False
    output_contains: list[str] = Field(default_factory=list)
    policy_violation_codes: list[str] = Field(default_factory=list)


class ControlPlaneScenario(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    scenario_id: str
    task: str
    strategy: str = 'deterministic'
    policy: str | None = None
    trace: bool = False
    expect: ControlPlaneScenarioExpectation

    @field_validator('scenario_id', 'task')
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError('scenario_id/task must be non-empty')
        return value


class ControlPlaneScenarioResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    scenario_id: str
    status: Literal['passed', 'failed']
    score: float
    passed: int
    total: int
    checks: list[dict[str, Any]] = Field(default_factory=list)
    orchestration_result: dict[str, Any] = Field(default_factory=dict)
