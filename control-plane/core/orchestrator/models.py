#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class OrchestrationRequest(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    task: str
    planner_strategy: Literal['deterministic', 'noop'] = 'deterministic'
    trace: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('task')
    @classmethod
    def _task_non_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError('task must be non-empty')
        return value


class OrchestrationResult(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    status: Literal['success', 'error']
    task: str
    planner_status: Literal['success', 'error']
    execution_status: Literal['success', 'error', 'skipped']
    dag_id: str | None = None
    run_id: str | None = None
    run_path: str | None = None
    planner_error: str | None = None
    execution_error: str | None = None
    execution_order: list[str] = Field(default_factory=list)
    node_results: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
