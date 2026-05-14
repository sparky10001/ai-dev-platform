#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class PolicySpec(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    policy_id: str
    version: str = '1.0'
    allow_tools: list[str] = Field(default_factory=list)
    deny_tools: list[str] = Field(default_factory=list)
    allow_llm_nodes: bool = False
    max_nodes: int = 25
    max_dependencies_per_node: int = 10
    workspace_boundary: list[str] = Field(default_factory=lambda: ['/workspace'])
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('max_nodes')
    @classmethod
    def _validate_max_nodes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError('max_nodes must be > 0')
        return value

    @field_validator('max_dependencies_per_node')
    @classmethod
    def _validate_max_deps(cls, value: int) -> int:
        if value <= 0:
            raise ValueError('max_dependencies_per_node must be > 0')
        return value

    @field_validator('allow_tools', 'deny_tools')
    @classmethod
    def _validate_tool_names(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError('tool names must be non-empty strings')
        return value


class PolicyViolation(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    code: str
    message: str
    node_id: str | None = None
    tool: str | None = None


class PolicyValidationResult(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    status: Literal['success', 'error']
    violations: list[PolicyViolation] = Field(default_factory=list)
    policy_id: str
    dag_id: str | None = None
