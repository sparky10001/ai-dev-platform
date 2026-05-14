#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class MemoryRecord(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    memory_id: str
    run_id: str | None = None
    task: str | None = None
    planner_strategy: str | None = None
    policy_id: str | None = None
    score: float | None = None
    status: str | None = None
    created_at: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryTimeline(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    timeline_id: str
    created_at: float
    total_records: int = 0
    records: list[MemoryRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRetrievalResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    retrieval_id: str
    query: str
    matched_records: list[MemoryRecord] = Field(default_factory=list)
    total_matches: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryCorpus(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    corpus_id: str
    created_at: float
    total_records: int = 0
    records: list[MemoryRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
