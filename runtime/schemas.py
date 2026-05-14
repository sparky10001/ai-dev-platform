#!/usr/bin/env python3
###################################################################
# runtime/schemas.py
#
# Phase 3E Runtime Schema Layer
#
# Canonical typed runtime contracts.
#
# Responsibilities:
# ✅ schema versioning
# ✅ runtime validation
# ✅ replay typing
# ✅ deterministic serialization
# ✅ external response contracts
# ✅ metadata normalization
# ✅ avoids nested schema_version drift
#
###################################################################

from __future__ import annotations

from typing import Any
from typing import Literal
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

# ================================================================
# 🔖 Schema Version
# ================================================================

SCHEMA_VERSION = 1

# ================================================================
# 📦 Base Schema
# ================================================================

class RuntimeSchema(BaseModel):

    """
    Shared top-level runtime schema base.

    IMPORTANT:
    Only top-level contracts should inherit from RuntimeSchema.

    Nested metadata/data helper models should inherit from
    RuntimeNestedModel so they do not emit their own schema_version.
    """

    model_config = ConfigDict(
        extra="allow",
        frozen=False
    )

    schema_version: int = SCHEMA_VERSION


class RuntimeNestedModel(BaseModel):

    """
    Shared nested model base.

    Nested metadata/data objects must NOT include schema_version.
    The parent envelope owns schema versioning.
    """

    model_config = ConfigDict(
        extra="allow",
        frozen=False
    )

# ================================================================
# 🧾 Metadata Models
# ================================================================

class RuntimeMeta(RuntimeNestedModel):

    adapter: Optional[str] = None

    run_id: str

    run_path: Optional[str] = None

    steps: Optional[int] = 0

    mode: Optional[str] = None

    error: bool = False

    trace: list[Any] = Field(default_factory=list)

# ================================================================
# 🌐 External Runtime Response
# ================================================================

class ResponseModel(RuntimeSchema):

    """
    Canonical external runtime response contract.
    """

    status: Literal["done", "error"]

    output: Any

    meta: RuntimeMeta


# Backward-compatible alias used by validators/contracts.
ResponseSchema = ResponseModel

# ================================================================
# 📦 Base Runtime Event
# ================================================================

class RuntimeEvent(RuntimeSchema):

    """
    Base NDJSON trace event.
    """

    timestamp: float

    run_id: str

    event: str

# ================================================================
# 🚀 Session Lifecycle
# ================================================================

class SessionStartData(RuntimeNestedModel):

    command: Optional[str] = None

    input: Optional[str] = None

    model: Optional[str] = None

    adapter: Optional[str] = None


class SessionStartEvent(RuntimeEvent):

    event: Literal["session_start"]

    data: SessionStartData = Field(
        default_factory=SessionStartData
    )


class SessionEndData(RuntimeNestedModel):

    status: Optional[str] = None

    duration_ms: Optional[float] = None


class SessionEndEvent(RuntimeEvent):

    event: Literal["session_end"]

    data: SessionEndData = Field(
        default_factory=SessionEndData
    )

# ================================================================
# 🧰 Tool Lifecycle
# ================================================================

class ToolCallMeta(RuntimeNestedModel):

    input: dict[str, Any] = Field(default_factory=dict)


class ToolCallEvent(RuntimeEvent):

    event: Literal["tool_call"]

    data: str

    step: int

    meta: ToolCallMeta = Field(
        default_factory=ToolCallMeta
    )


class ToolResultMeta(RuntimeNestedModel):

    result: dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(RuntimeEvent):

    event: Literal["tool_result"]

    data: str

    step: int

    meta: ToolResultMeta = Field(
        default_factory=ToolResultMeta
    )

# ================================================================
# 🤖 Agent Output
# ================================================================

class AgentOutputData(RuntimeNestedModel):

    status: str

    output: Any

    meta: dict[str, Any] = Field(default_factory=dict)


class AgentOutputEvent(RuntimeEvent):

    event: Literal["agent_output"]

    data: AgentOutputData

# ================================================================
# 📊 Runtime Evaluation
# ================================================================

class EvalSummary(RuntimeSchema):

    """
    Replay-derived runtime evaluation summary.
    """

    run_id: str

    status: Optional[str] = None

    total_events: int

    tool_calls: int

    tool_results: int

    runtime_seconds: Optional[float] = None

    completed: bool

    replay_valid: bool

    schema_valid: bool


class EvalComparison(RuntimeSchema):

    """
    Deterministic comparison between two runtime evaluations.
    """

    run_a: EvalSummary

    run_b: EvalSummary

    status_changed: bool

    delta_events: int

    delta_tool_calls: int

    delta_tool_results: int

    delta_runtime_seconds: Optional[float] = None

    both_completed: bool

    replay_valid: bool

    schema_valid: bool

# ================================================================
# 🗂️ Runtime Registry
# ================================================================

class RunQueryResult(RuntimeSchema):

    """
    Deterministic filesystem-backed run query result.
    """

    runs: list[dict[str, Any]] = Field(default_factory=list)

    total: int

    filters: dict[str, Any] = Field(default_factory=dict)

    sort_by: str

    descending: bool = False

    limit: Optional[int] = None


class RunSummary(RuntimeSchema):

    """
    Aggregate metrics for a deterministic set of runs.
    """

    total_runs: int

    completed_runs: int

    success_rate: float

    average_runtime: Optional[float] = None

    total_tool_calls: int

    replay_valid_runs: int

    schema_valid_runs: int

# ================================================================
# 📚 Runtime Datasets
# ================================================================

class DatasetRecord(RuntimeSchema):

    """
    Canonical dataset record for a complete runtime run export.
    """

    run_id: str

    run: dict[str, Any]

    result: dict[str, Any]

    eval: EvalSummary

    trace: list[dict[str, Any]] = Field(default_factory=list)


class EvalDatasetRecord(RuntimeSchema):

    """
    Canonical dataset record for replay-derived evaluation exports.
    """

    run_id: str

    eval: EvalSummary


class TraceDatasetRecord(RuntimeSchema):

    """
    Canonical dataset record for replay-safe trace corpus exports.
    """

    run_id: str

    event_index: int

    event: dict[str, Any]



# ================================================================
# 🧭 Control-Plane DAG Events
# ================================================================

class DagStartEvent(RuntimeEvent):

    event: Literal['dag_start']

    data: dict[str, Any] = Field(default_factory=dict)


class DagNodeStartEvent(RuntimeEvent):

    event: Literal['dag_node_start']

    data: dict[str, Any] = Field(default_factory=dict)


class DagNodeResultEvent(RuntimeEvent):

    event: Literal['dag_node_result']

    data: dict[str, Any] = Field(default_factory=dict)


class DagResultEvent(RuntimeEvent):

    event: Literal['dag_result']

    data: dict[str, Any] = Field(default_factory=dict)

# ================================================================
# 🔁 Replay/Event Union
# ================================================================

TraceEvent = Union[
    SessionStartEvent,
    ToolCallEvent,
    ToolResultEvent,
    AgentOutputEvent,
    SessionEndEvent,
    DagStartEvent,
    DagNodeStartEvent,
    DagNodeResultEvent,
    DagResultEvent,
]

# ================================================================
# 🗂️ Event Registry
# ================================================================

EVENT_MODELS = {
    "session_start": SessionStartEvent,
    "tool_call": ToolCallEvent,
    "tool_result": ToolResultEvent,
    "agent_output": AgentOutputEvent,
    "session_end": SessionEndEvent,
    "dag_start": DagStartEvent,
    "dag_node_start": DagNodeStartEvent,
    "dag_node_result": DagNodeResultEvent,
    "dag_result": DagResultEvent,
}