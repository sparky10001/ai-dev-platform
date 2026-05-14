#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import AliasChoices
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class ToolParameter(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    name: str

    schema_: dict[str, Any] = Field(
        validation_alias=AliasChoices('schema'),
        serialization_alias='schema',
    )

    required: bool = False

    description: str | None = None


class ToolContract(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    name: str

    description: str | None = None

    parameters_schema: dict[str, Any] = Field(default_factory=dict)

    required: list[str] = Field(default_factory=list)

    source: str = 'tool_executor'

    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def _non_empty_name(cls, value: str) -> str:

        if not value or not value.strip():
            raise ValueError('tool name must be non-empty')

        return value


class ToolRegistrySnapshot(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    tools: dict[str, ToolContract] = Field(default_factory=dict)

    count: int

    @model_validator(mode='after')
    def _validate_count(self) -> 'ToolRegistrySnapshot':

        if self.count != len(self.tools):
            raise ValueError('count must match number of tools')

        return self
