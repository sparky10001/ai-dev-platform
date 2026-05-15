#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class GraphMetric(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    name: str
    value: float | int | str | bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeMetric(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    node_id: str
    degree: int = 0
    incoming_edges: int = 0
    outgoing_edges: int = 0
    relationship_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphAnalyticsResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    analytics_id: str
    graph_id: str
    total_nodes: int = 0
    total_edges: int = 0
    relationship_frequencies: dict[str, int] = Field(default_factory=dict)
    isolated_nodes: list[str] = Field(default_factory=list)
    max_lineage_depth: int = 0
    node_metrics: list[NodeMetric] = Field(default_factory=list)
    metrics: list[GraphMetric] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
