#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from core.dag.models import DagSpec


class PlannerRequest(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    task: str

    strategy: Literal['deterministic', 'noop'] = 'deterministic'

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('task')
    @classmethod
    def _task_non_empty(cls, value: str) -> str:

        if not isinstance(value, str) or not value.strip():
            raise ValueError('task must be non-empty')

        return value


class PlannerResult(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    status: Literal['success', 'error']

    dag: DagSpec | None = None

    error: str | None = None

    strategy: str

    metadata: dict[str, Any] = Field(default_factory=dict)
