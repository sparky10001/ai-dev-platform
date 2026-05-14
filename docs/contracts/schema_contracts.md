# Runtime Schema Contracts

## Overview

The runtime uses schema-versioned JSON contracts for all external interfaces.

Internal validation is enforced using:

* Pydantic v2
* runtime.contracts
* runtime.schemas
* runtime.validator

Contracts are designed to remain:

* deterministic
* replay-safe
* backward compatible
* append-only friendly
* crash-safe
* NDJSON compatible

The runtime treats schemas as infrastructure contracts rather than serialization helpers.

---

# Contract Architecture

The contract stack is layered intentionally:

```text
contracts.py
  ↓
schemas.py
  ↓
validator.py
  ↓
engine.py / replay.py / datasets.py
```

Responsibilities:

| Layer        | Responsibility                  |
| ------------ | ------------------------------- |
| contracts.py | canonical contract definitions  |
| schemas.py   | typed Pydantic runtime models   |
| validator.py | validation entrypoints          |
| replay.py    | replay-safe reconstruction      |
| datasets.py  | deterministic export validation |

---

# Schema Versioning

Current schema version:

```text
1
```

Current contract version:

```text
1
```

Constants:

```python
SCHEMA_VERSION = 1
CONTRACT_VERSION = 1
```

All runtime responses and events must include:

```json
{
  "schema_version": 1
}
```

---

# Canonical Validation Entry Points

All runtime JSON must pass through:

```python
validate_response()
validate_event()
validate_dataset_record()
validate_eval_record()
```

Validation delegation flow:

```text
validator.py
  → contracts.py
  → schemas.py
```

No runtime component may bypass validation.

---

# Response Contract

Canonical runtime response:

```json
{
  "schema_version": 1,
  "status": "done",
  "output": "completed",
  "meta": {
    "adapter": "agent.py",
    "run_id": "run_123",
    "run_path": "/workspace/runs/run_123",
    "error": false
  }
}
```

---

# Response Fields

| Field          | Type          | Required |
| -------------- | ------------- | -------- |
| schema_version | integer       | yes      |
| status         | string        | yes      |
| output         | string/object | yes      |
| meta           | object        | yes      |

---

# Supported Status Values

| Status | Meaning              |
| ------ | -------------------- |
| done   | successful execution |
| error  | runtime failure      |

---

# Meta Contract

Canonical metadata fields:

```json
{
  "adapter": "agent.py",
  "run_id": "run_123",
  "run_path": "/workspace/runs/run_123",
  "error": false
}
```

Additional metadata may be added additively.

---

# Runtime Event Contract

Canonical event:

```json
{
  "schema_version": 1,
  "timestamp": 1778367094.181,
  "run_id": "run_123",
  "event": "tool_call",
  "data": {}
}
```

---

# Event Fields

| Field          | Type          | Required |
| -------------- | ------------- | -------- |
| schema_version | integer       | yes      |
| timestamp      | float         | yes      |
| run_id         | string        | yes      |
| event          | string        | yes      |
| data           | object/string | yes      |

Additional optional fields:

| Field | Purpose                |
| ----- | ---------------------- |
| step  | deterministic ordering |
| meta  | tool metadata          |
| error | failure metadata       |

---

# Supported Event Types

| Event         | Purpose              |
| ------------- | -------------------- |
| session_start | lifecycle start      |
| tool_call     | tool invocation      |
| tool_result   | tool result          |
| agent_output  | final runtime output |
| session_end   | lifecycle end        |

Additional event types may be added additively.

---

# Typed Contract Models

The runtime exposes typed Pydantic models for:

```text
ResponseSchema
RuntimeEvent
SessionStartEvent
ToolCallEvent
ToolResultEvent
AgentOutputEvent
SessionEndEvent
EvalSummary
EvalComparison
RunQueryResult
RunSummary
DatasetRecord
EvalDatasetRecord
TraceDatasetRecord
```

These models are the canonical replay-safe contract layer.

---

# Trace Contract

Canonical trace location:

```text
runs/<run_id>/trace.jsonl
```

Trace requirements:

* NDJSON only
* append-only
* one JSON object per line
* replay-safe
* truncation-safe
* schema-validated
* deterministic ordering

---

# NDJSON Guarantees

Trace persistence guarantees:

* no empty lines
* valid JSON per line
* deterministic serialization
* replay-safe structure
* crash-safe append semantics

Validated by:

```text
ndjson_integrity_tests.sh
trace_schema_consistency_test.sh
```

---

# Replay Guarantees

Replay systems must support:

* partial traces
* truncated traces
* crash-recovered traces
* deterministic ordering
* lifecycle reconstruction
* schema validation
* incomplete run detection

Replay compatibility is a mandatory runtime guarantee.

Replay entrypoints:

```python
replay_trace()
load_trace()
load_full_run()
```

---

# Evaluation Contracts

Evaluation models are replay-derived.

Canonical evaluation fields:

```json
{
  "run_id": "run_123",
  "status": "done",
  "runtime_seconds": 1.23,
  "tool_calls": 2,
  "tool_results": 2,
  "completed": true,
  "replay_valid": true,
  "schema_valid": true
}
```

Evaluation APIs:

```python
evaluate_run()
compare_runs()
```

---

# Dataset Contracts

Dataset exports are deterministic NDJSON.

Supported dataset types:

```text
DatasetRecord
EvalDatasetRecord
TraceDatasetRecord
```

Dataset guarantees:

* deterministic ordering
* replay compatibility
* canonical serialization
* schema validation
* append-safe persistence

---

# Registry Contracts

Registry/query operations expose typed contracts for:

```text
RunQueryResult
RunSummary
```

Registry guarantees:

* deterministic ordering
* replay-derived metadata
* malformed run isolation
* filesystem-native querying

---

# Deterministic Serialization

Canonical serialization helper:

```python
to_canonical_json()
```

Serialization guarantees:

* stable key ordering
* deterministic exports
* replay-safe persistence
* schema-consistent formatting

Dataset exports rely on canonical serialization.

---

# Compatibility Enforcement

Compatibility helpers:

```python
assert_backward_compatible()
assert_no_breaking_changes()
```

The runtime enforces additive evolution.

---

# Allowed Schema Changes

Allowed:

* additive fields
* additive metadata
* additive event types
* optional metadata extensions
* additive dataset fields
* additive eval metrics

Preferred:

* backward-compatible additions only

---

# Forbidden Schema Changes

Forbidden:

* removing required fields
* renaming canonical fields
* changing event semantics
* changing NDJSON format
* changing lifecycle ordering semantics
* changing schema_version meaning
* breaking replay compatibility
* changing deterministic serialization guarantees

These changes can break:

* replay
* crash recovery
* datasets
* evals
* registry queries
* deterministic debugging

---

# Backward Compatibility Rules

New schema versions must:

* preserve replayability
* preserve NDJSON compatibility
* preserve lifecycle semantics
* preserve deterministic ordering
* preserve append-only persistence

Older traces should remain parseable whenever possible.

---

# Migration Rules

Schema migrations should:

* be additive first
* preserve replay compatibility
* preserve deterministic serialization
* preserve lifecycle reconstruction
* preserve dataset compatibility

Migration validation should include:

* replay validation
* truncation recovery
* crash recovery
* schema consistency validation
* deterministic export validation
* eval reconstruction validation

---

# Validation Philosophy

The runtime treats schemas as:

```text
deterministic infrastructure contracts
```

—not merely serialization helpers.

Schema integrity is foundational to:

* replay
* evals
* crash recovery
* observability
* deterministic debugging
* registry queries
* dataset generation
* lifecycle reconstruction
* runtime analytics

---

# Runtime Guarantees

The schema layer guarantees:

* deterministic contracts
* replay-safe persistence
* append-only traces
* schema-versioned evolution
* crash durability
* deterministic exports
* filesystem-native querying
* replay-derived evaluations

These guarantees are validated continuously by the runtime test suites.

---

# Validation Coverage

Current validation coverage includes:

```text
runtime_tests.sh
failure_tests.sh
ndjson_integrity_tests.sh
event_ordering_tests.sh
replayability_smoke_test.sh
trace_schema_consistency_test.sh
resume_from_trace_tests.sh
loader_replay_tests.sh
runtime_eval_tests.sh
runtime_registry_tests.sh
runtime_dataset_tests.sh
runtime_contract_tests.sh
```
