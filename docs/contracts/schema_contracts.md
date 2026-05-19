# Runtime Schema Contracts

## Overview

The runtime uses schema-versioned JSON contracts for all external interfaces. 

Internal validation is enforced using:

* Pydantic v2
* `runtime.contracts`
* `runtime.schemas`
* `runtime.validator`

Contracts are designed to remain:

* deterministic
* replay-safe
* backward compatible
* append-only friendly
* crash-safe
* NDJSON compatible
* compatibility-preserving

The runtime treats schemas as deterministic infrastructure contracts rather than serialization helpers.

---

# Contract Architecture

The contract stack is intentionally layered:

```text id="qq0z4m"
contracts.py
  ↓
schemas.py
  ↓
validator.py
  ↓
engine / trace_pipeline / event_ledger / replay / evals / registry / datasets / audits
```

Responsibilities:

| Layer               | Responsibility                         |
| ------------------- | -------------------------------------- |
| `contracts.py`      | canonical contract definitions         |
| `schemas.py`        | typed Pydantic runtime models          |
| `validator.py`      | validation entrypoints                 |
| `trace_pipeline.py` | canonical event persistence validation |
| `event_ledger.py`   | deterministic ledger validation        |
| `replay.py`         | replay-safe reconstruction             |
| `evals.py`          | replay-derived evaluation validation   |
| `registry.py`       | replay-derived metadata validation     |
| `datasets.py`       | deterministic export validation        |
| audit systems       | deterministic operational reporting    |

---

# Schema Versioning

Current schema version:

```text id="h2m8qe"
1
```

Current contract version:

```text id="5r8hva"
1
```

Constants:

```python id="jnh5pa"
SCHEMA_VERSION = 1
CONTRACT_VERSION = 1
```

All runtime responses and events must include:

```json id="40vdbd"
{
  "schema_version": 1
}
```

---

# Canonical Validation Entry Points

All runtime JSON must pass through canonical validation helpers:

```python id="ru8jqk"
validate_response()
validate_event()
validate_dataset_record()
validate_eval_record()
validate_ledger_file()
validate_trace_ledger_parity()
```

Validation delegation flow:

```text id="q07m6g"
validator.py
  → contracts.py
  → schemas.py
```

No runtime component may bypass validation.

---

# Response Contract

Canonical runtime response:

```json id="2v84hs"
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

| Field            | Type          | Required |
| ---------------- | ------------- | -------- |
| `schema_version` | integer       | yes      |
| `status`         | string        | yes      |
| `output`         | string/object | yes      |
| `meta`           | object        | yes      |

---

# Supported Status Values

| Status  | Meaning              |
| ------- | -------------------- |
| `done`  | successful execution |
| `error` | runtime failure      |

Additional status values must evolve additively.

---

# Meta Contract

Canonical metadata fields:

```json id="0zv7bz"
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

Canonical runtime event:

```json id="09e0pr"
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

| Field            | Type          | Required |
| ---------------- | ------------- | -------- |
| `schema_version` | integer       | yes      |
| `timestamp`      | float         | yes      |
| `run_id`         | string        | yes      |
| `event`          | string        | yes      |
| `data`           | object/string | yes      |

Additional optional fields:

| Field   | Purpose                |
| ------- | ---------------------- |
| `step`  | deterministic ordering |
| `meta`  | tool metadata          |
| `error` | failure metadata       |

---

# Supported Event Types

| Event           | Purpose              |
| --------------- | -------------------- |
| `session_start` | lifecycle start      |
| `tool_call`     | tool invocation      |
| `tool_result`   | tool result          |
| `agent_output`  | final runtime output |
| `session_end`   | lifecycle end        |

Additional event types may be added additively.

---

# EventLedger Contract

EventLedger persists deterministic additive runtime event mirrors.

Canonical ledger location:

```text id="64bl9n"
runs/<run_id>/ledger.jsonl
```

Ledger guarantees:

* NDJSON only
* append-only
* deterministic ordering
* replay-safe persistence
* schema-validated events
* deterministic event hashing
* parity-safe compatibility

EventLedger uses the same canonical runtime event schema as `trace.jsonl`.

---

# Ledger Index Contract

Canonical ledger index:

```text id="b1u8s7"
runs/<run_id>/ledger.index.json
```

Ledger index guarantees:

* deterministic serialization
* deterministic event hashes
* stable event ordering
* replay-safe reconstruction
* compatibility-safe regeneration

Canonical index fields:

```json id="srzvjn"
{
  "schema_version": 1,
  "run_id": "run_123",
  "event_count": 5,
  "ledger_hash": "..."
}
```

Event entries include:

* `index`
* `event_hash`
* canonical event payload

---

# Trace/Ledger Compatibility Contract

Current compatibility behavior:

* `trace.jsonl` remains canonical by default
* `ledger.jsonl` mirrors validated runtime events
* replay/eval/registry support dual-source operation
* ledger becomes default source only under authoritative mode

Compatibility guarantees:

* no runtime response contract changes
* no runtime event contract changes
* no NDJSON format changes
* no replay semantic changes
* no eval/registry output semantic changes

Ledger features remain additive unless explicitly gated by opt-in flags.

---

# Source Selection Contract

Replay/eval/registry support source selection via:

* explicit `source="trace"`
* explicit `source="ledger"`
* environment configuration

Default behavior:

```text id="d90mkq"
trace
```

Supported values:

```text id="33o8bp"
trace
ledger
```

Invalid source values must fall back deterministically to trace-safe behavior unless strict authoritative mode is explicitly enabled.

Explicit source arguments override environment defaults.

---

# Authoritative & Dry-Run Flag Contracts

## Authoritative Mode

Enable:

```text id="3c7x9z"
RUNTIME_LEDGER_AUTHORITATIVE=1
```

Authoritative mode:

* changes replay/eval/registry defaults to ledger
* preserves trace compatibility
* preserves runtime response contracts
* preserves runtime event contracts

Authoritative mode does NOT:

* remove trace artifacts
* bypass parity validation
* mutate historical runtime artifacts

---

## Parity Enforcement

Enable:

```text id="vvjlwm"
RUNTIME_LEDGER_PARITY_REQUIRED=1
```

Parity enforcement:

* raises deterministic errors on mismatch
* preserves replay safety
* preserves rollback safety

---

## Dry-Run Readiness Mode

Enable:

```text id="lf6v2f"
RUNTIME_LEDGER_DRY_RUN_DEFAULT=1
```

Dry-run mode:

* is observational-only
* does not change authority
* does not mutate artifacts
* does not change runtime defaults
* does not remove compatibility behavior

---

# Typed Contract Models

The runtime exposes typed Pydantic models for:

```text id="e8dk66"
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

Structured report contracts additionally include:

* drift audit reports
* corruption audit reports
* ledger health reports
* trace compatibility reports
* boundary audit reports
* purity audit reports
* dry-run readiness reports

These contracts are deterministic and JSON-safe.

---

# Trace Contract

Canonical trace location:

```text id="63yjlwm"
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

Trace and ledger persistence guarantees:

* no empty lines
* valid JSON per line
* deterministic serialization
* replay-safe structure
* crash-safe append semantics

Validated by:

```text id="c9h7dg"
ndjson_integrity_tests.sh
trace_schema_consistency_test.sh
runtime_event_ledger_tests.sh
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

```python id="v4h4mt"
replay_trace()
load_trace()
load_full_run()
```

Replay remains authoritative runtime infrastructure.

---

# Evaluation Contracts

Evaluation models are replay-derived.

Canonical evaluation fields:

```json id="zh6v7e"
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

```python id="3eqlym"
evaluate_run()
compare_runs()
```

Evaluation behavior remains compatibility-preserving across trace and ledger sources.

---

# Dataset Contracts

Dataset exports are deterministic NDJSON.

Supported dataset types:

```text id="8u0tjk"
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

`runtime.datasets` is classified as a projection writer and must not mutate runtime source artifacts.

---

# Registry Contracts

Registry/query operations expose typed contracts for:

```text id="z4g0x0"
RunQueryResult
RunSummary
```

Registry guarantees:

* deterministic ordering
* replay-derived metadata
* malformed run isolation
* filesystem-native querying
* compatibility-safe source selection

---

# Audit Report Contracts

Operational audit systems emit deterministic structured reports.

Audit report guarantees:

* JSON-safe
* deterministic
* additive
* read-only
* compatibility-preserving

Audit systems include:

* drift reports
* corruption reports
* ledger health reports
* trace compatibility reports
* boundary audit reports
* purity audit reports
* dry-run readiness reports

Audit systems must never mutate runtime artifacts.

---

# Deterministic Serialization

Canonical serialization helper:

```python id="vxh6k3"
to_canonical_json()
```

Serialization guarantees:

* stable key ordering
* deterministic exports
* replay-safe persistence
* schema-consistent formatting

Dataset exports and ledger hashing rely on canonical serialization.

---

# Compatibility Enforcement

Compatibility helpers:

```python id="f1q3c4"
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
* additive audit report fields

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
* changing `schema_version` meaning
* breaking replay compatibility
* changing deterministic serialization guarantees

These changes can break:

* replay
* crash recovery
* datasets
* evals
* registry queries
* deterministic debugging
* operational observability

---

# Backward Compatibility Rules

New schema versions must:

* preserve replayability
* preserve NDJSON compatibility
* preserve lifecycle semantics
* preserve deterministic ordering
* preserve append-only persistence

Older traces and ledgers should remain parseable whenever possible.

---

# Contract Stability During Migration

EventLedger migration must not change:

* runtime response shape
* runtime event shape
* trace NDJSON format
* replay semantics
* eval/registry output semantics

Ledger features are additive unless explicitly gated by opt-in flags.

---

# Migration Rules

Schema migrations should:

* be additive first
* preserve replay compatibility
* preserve deterministic serialization
* preserve lifecycle reconstruction
* preserve dataset compatibility
* preserve audit compatibility

Migration validation should include:

* replay validation
* truncation recovery
* crash recovery
* schema consistency validation
* deterministic export validation
* eval reconstruction validation
* parity validation

---

# Validation Philosophy

The runtime treats schemas as:

```text id="tt7sl4"
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
* EventLedger migration safety

---

# Runtime Guarantees

The schema layer guarantees:

* deterministic contracts
* replay-safe persistence
* append-only traces
* append-only ledgers
* schema-versioned evolution
* crash durability
* deterministic exports
* filesystem-native querying
* replay-derived evaluations
* compatibility-preserving migration

These guarantees are validated continuously by the runtime test suites.

---

# Validation Coverage

Current validation coverage includes:

```text id="jpp7eq"
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
runtime_event_ledger_tests.sh
runtime_replay_ledger_tests.sh
runtime_eval_ledger_tests.sh
runtime_registry_ledger_tests.sh
runtime_ledger_authoritative_tests.sh
runtime_ledger_readiness_tests.sh
runtime_ledger_drift_tests.sh
runtime_derived_purity_tests.sh
runtime_boundary_audit_tests.sh
runtime_ledger_corruption_tests.sh
runtime_ledger_health_tests.sh
runtime_trace_compatibility_tests.sh
runtime_ledger_default_dry_run_tests.sh
```
