# Runtime Architecture

## Overview

The AI Runtime Platform is a deterministic, schema-first execution system designed for:

* replay-safe execution
* crash durability
* append-only trace persistence
* schema-validated contracts
* deterministic lifecycle reconstruction
* replay-derived evaluation
* filesystem-native runtime indexing
* deterministic dataset export
* parallel run isolation

The runtime is event-driven and persists canonical NDJSON traces for all execution activity.

---

# Core Principles

## Deterministic Execution

Runtime behavior should be reproducible from persisted traces.

The system avoids:

* hidden mutable state
* implicit side effects
* non-replayable execution paths

---

## Schema-First Contracts

All external runtime contracts use JSON.

All internal validation uses:

* Pydantic v2
* runtime.contracts
* runtime.schemas
* runtime.validator

No adapter output is trusted without validation.

---

## Replay Safety

All traces must remain:

* append-only
* truncation-safe
* replay-safe
* schema-validated
* NDJSON compliant

Replayability is a core architectural guarantee.

---

## Minimal Runtime Surface Area

The runtime intentionally avoids:

* Redis
* Celery
* distributed workers
* hidden queues
* external orchestration systems
* databases

The current runtime is single-process and deterministic by design.

---

# Runtime Lifecycle

Canonical lifecycle:

```text
session_start
  → tool_call
  → tool_result
  → agent_output
  → session_end
```

Lifecycle ordering is validated by:

* event_ordering_tests.sh
* replayability_smoke_test.sh
* resume_from_trace_tests.sh

---

# Runtime Flow

## 1. Runtime Entry

Entrypoint:

```text
scripts/runtime.sh
```

Primary orchestrator:

```text
runtime/engine.py
```

Responsibilities:

* create runs
* resolve adapters
* validate responses
* persist traces
* finalize runtime state

---

## 2. Run Creation

Module:

```text
runtime/run.py
```

Responsibilities:

* generate run_id
* create canonical run directory
* initialize run metadata
* persist run.json

Canonical structure:

```text
runs/<run_id>/
  run.json
  trace.jsonl
  result.json
```

---

## 3. Adapter Execution

Module:

```text
runtime/runner.py
```

Responsibilities:

* invoke adapters
* enforce timeout boundaries
* capture stdout/stderr
* preserve deterministic execution

Adapters communicate strictly through JSON.

---

## 4. Schema Validation

Modules:

```text
runtime/contracts.py
runtime/schemas.py
runtime/validator.py
```

Responsibilities:

* canonical runtime contracts
* schema versioning
* response validation
* event validation
* dataset validation
* eval validation
* compatibility enforcement
* typed runtime contracts

The contracts layer is the single source of truth for:

* runtime events
* runtime responses
* dataset exports
* evaluation records
* registry/query structures

Validation boundary:

* all external JSON
* all replayed events
* all persisted traces
* all exported datasets
* all eval summaries

Validation delegation flow:

```text
validator.py
  → contracts.py
  → schemas.py
```

Compatibility helpers:

```text
assert_backward_compatible()
assert_no_breaking_changes()
```

Canonical serialization helper:

```text
to_canonical_json()
```

---

## 5. Event Persistence

Module:

```text
runtime/events.py
```

Responsibilities:

* canonical event creation
* schema validation
* NDJSON persistence

Trace format:

```text
runs/<run_id>/trace.jsonl
```

Requirements:

* append-only
* one JSON object per line
* replay-safe
* crash-safe

---

## 6. Replay System

Modules:

```text
runtime/replay.py
runtime/loader.py
```

Responsibilities:

* replay trace loading
* schema-safe event reconstruction
* lifecycle reconstruction
* incomplete run detection

Replay guarantees:

* survives truncation
* preserves ordering
* preserves timestamps
* reconstructs terminal state

---

# Evaluation System

Module:

```text
runtime/evals.py
```

Responsibilities:

* replay-derived runtime metrics
* run evaluation
* run comparison
* deterministic evaluation summaries

Core APIs:

```text
evaluate_run(run_id)
compare_runs(run_a, run_b)
```

Evaluation metrics include:

* runtime_seconds
* total_events
* tool_calls
* tool_results
* replay_valid
* schema_valid
* completed

---

# Registry System

Module:

```text
runtime/registry.py
```

Responsibilities:

* enumerate runs
* query runtime history
* summarize execution metadata
* deterministic run ordering

Core APIs:

```text
list_runs()
get_run(run_id)
get_latest_run()
query_runs(...)
summarize_runs(...)
```

Supported query dimensions:

* status
* command
* model
* completion state
* timestamp ordering
* result limits

---

# Dataset Export System

Module:

```text
runtime/datasets.py
```

Responsibilities:

* export replay-safe datasets
* export evaluation corpora
* export normalized traces
* deterministic NDJSON serialization

Supported exports:

```text
export_run(...)
export_runs(...)
export_query(...)
build_eval_dataset(...)
build_trace_dataset(...)
```

Export guarantees:

* append-safe
* deterministic ordering
* replay-compatible
* schema-validated
* NDJSON compliant

---

# Core Runtime Modules

```text
runtime/
  engine.py
  run.py
  runner.py
  events.py
  replay.py
  loader.py
  evals.py
  registry.py
  datasets.py
  contracts.py
  validator.py
  schemas.py
```

---

# Event System

Canonical event fields:

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

# Supported Event Types

| Event         | Purpose                  |
| ------------- | ------------------------ |
| session_start | lifecycle initialization |
| tool_call     | tool execution request   |
| tool_result   | tool execution result    |
| agent_output  | final runtime output     |
| session_end   | lifecycle completion     |

---

# Trace Persistence Model

Trace files are:

* append-only
* immutable after write
* line-oriented
* replay-derived

No event mutation is permitted after persistence.

---

# Failure Handling

Failure paths must still emit:

* valid JSON
* valid schema_version
* valid lifecycle termination
* replay-safe traces

Failure guarantees are validated by:

```text
failure_tests.sh
crash_recovery_tests.sh
```

---

# Parallel Isolation

Concurrent runtime executions must remain isolated.

Isolation guarantees:

* unique run directories
* unique trace files
* independent lifecycle persistence

Validated by:

```text
parallel_run_isolation_test.sh
```

---

# Contract Architecture

The runtime uses a layered contract system:

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

| Layer        | Responsibility                 |
| ------------ | ------------------------------ |
| contracts.py | canonical contract definitions |
| schemas.py   | typed runtime schema layer     |
| validator.py | runtime validation entrypoints |
| replay.py    | replay-safe reconstruction     |
| datasets.py  | canonical export generation    |

Contract guarantees:

* deterministic serialization
* backward compatibility enforcement
* schema-versioned runtime contracts
* replay-safe persistence
* append-safe NDJSON traces

---

# Testing Guarantees

Current runtime guarantees are validated through:

```text
runtime_tests.sh
failure_tests.sh
ndjson_integrity_tests.sh
event_ordering_tests.sh
replayability_smoke_test.sh
run_structure_test.sh
trace_schema_consistency_test.sh
parallel_run_isolation_test.sh
resume_from_trace_tests.sh
loader_replay_tests.sh
runtime_eval_tests.sh
runtime_registry_tests.sh
runtime_dataset_tests.sh
runtime_contract_tests.sh
```

---

# Current Limitations

Current runtime intentionally avoids:

* distributed orchestration
* resumable execution continuation
* background scheduling
* cross-process coordination
* remote persistence
* distributed state management

These may be introduced in later phases.

---

# Phase 4 Direction

Planned evolution areas:

```text
runtime/state.py
runtime/reconstructor.py
runtime/observability.py
runtime/orchestrator.py
```

Future capabilities:

* deterministic state reconstruction
* replay-derived evals
* resumable execution
* runtime analytics
* trace inspection APIs
* structured observability
* orchestration primitives
* multi-agent execution
* evaluation pipelines
* runtime dashboards
