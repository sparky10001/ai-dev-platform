#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class KnowledgeNode(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    node_id: str
    node_type: str
    run_id: str | None = None
    task: str | None = None
    planner_strategy: str | None = None
    policy_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdge(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    edge_id: str
    source_id: str
    target_id: str
    relationship_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    graph_id: str
    created_at: float
    total_nodes: int = 0
    total_edges: int = 0
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    lineage_id: str
    root_node_id: str
    ancestor_ids: list[str] = Field(default_factory=list)
    descendant_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
