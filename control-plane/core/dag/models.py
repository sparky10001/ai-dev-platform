#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class DagNode(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    id: str

    type: Literal['tool', 'llm', 'noop']

    depends_on: list[str] = Field(default_factory=list)

    tool: str | None = None

    args: dict[str, Any] = Field(default_factory=dict)

    prompt: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def _validate_node_contract(self) -> 'DagNode':

        if self.type == 'tool' and not self.tool:
            raise ValueError('tool nodes must include tool')

        if self.type == 'llm' and not self.prompt:
            raise ValueError('llm nodes must include prompt')

        return self


class DagSpec(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    dag_id: str

    version: str

    entry: str

    nodes: list[DagNode]

    @model_validator(mode='after')
    def _validate_graph_contract(self) -> 'DagSpec':

        ids = [node.id for node in self.nodes]

        if len(ids) != len(set(ids)):
            raise ValueError('node ids must be unique')

        if self.entry not in ids:
            raise ValueError('entry node must exist in nodes')

        id_set = set(ids)

        for node in self.nodes:
            missing = [dep for dep in node.depends_on if dep not in id_set]
            if missing:
                raise ValueError(
                    f"node '{node.id}' has missing dependencies: {', '.join(missing)}"
                )

        return self
