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
* compatibility-preserving EventLedger migration
* operational auditability
* replay-safe observability

The runtime is event-driven and persists canonical NDJSON traces for all execution activity. 

The runtime is intentionally designed as:

```text id="ij89eh"
event-sourced deterministic execution infrastructure
```

—not merely a command wrapper or orchestration shell.

---

# Runtime Layer Model

The runtime is intentionally layered:

```text id="zwshha"
contracts / schemas / validator
                ↓
trace_pipeline + event_ledger
                ↓
adapter_gateway + run_lifecycle
                ↓
engine
                ↓
replay / evals / registry / datasets
                ↓
audit + observability systems
```

The runtime preserves one-way dependency direction toward lower-level infrastructure layers.

Replay, evals, registry, datasets, and audit systems are treated as derived systems and must remain replay-safe and compatibility-preserving.

---

# Execution vs Derived Systems

## Execution Systems

Execution systems coordinate canonical runtime behavior and persistence.

Execution systems include:

* `runtime.engine`
* `runtime.adapter_gateway`
* `runtime.run_lifecycle`
* `runtime.trace_pipeline`
* `runtime.event_ledger`

Execution systems:

* produce canonical runtime artifacts
* coordinate runtime execution
* validate runtime contracts
* preserve lifecycle guarantees
* maintain replay-safe persistence

---

## Derived Systems

Derived systems consume runtime artifacts and remain replay-safe projections.

Derived systems include:

* `runtime.replay`
* `runtime.evals`
* `runtime.registry`
* `runtime.datasets`
* audit and observability tooling

Derived systems must remain:

* replay-safe
* read-oriented
* compatibility-preserving
* deterministic

Derived systems must never mutate canonical runtime history.

---

# Core Principles

## Deterministic Execution

Runtime behavior should be reproducible from persisted runtime artifacts.

The runtime avoids:

* hidden mutable state
* implicit side effects
* non-replayable execution paths
* implicit background mutation

---

## Schema-First Contracts

All external runtime contracts use JSON.

All internal validation uses:

* Pydantic v2
* `runtime.contracts`
* `runtime.schemas`
* `runtime.validator`

No adapter output is trusted without validation.

---

## Replay Safety

All traces and ledger artifacts must remain:

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
* implicit schedulers

The runtime remains single-process and deterministic by design.

---

# EventLedger Compatibility Model

The runtime currently operates in compatibility mode.

Current behavior:

* `trace.jsonl` remains canonical
* `ledger.jsonl` remains additive
* replay/eval/registry support dual-source operation
* authoritative ledger mode remains opt-in
* operational audits remain observational-only

EventLedger provides:

* deterministic parity validation
* migration readiness
* operational observability
* future ledger-authoritative support
* replay-safe cutover tooling

---

# Runtime Governance & Authority Model

The runtime now includes a governance-oriented authority transition framework designed to support future ledger-authoritative operation without compromising replay safety or rollback guarantees.

Governance systems are intentionally:

* observational-first
* deterministic
* replay-safe
* compatibility-preserving
* rollback-oriented

Governance systems must never:

* implicitly switch runtime authority
* mutate runtime history
* disable trace emission
* bypass replay validation
* weaken compatibility guarantees

---

## Current Authority State

Current operational behavior:

* `trace.jsonl` remains the active runtime default
* `ledger.jsonl` remains additive unless explicitly enabled
* authoritative ledger mode remains opt-in
* canary mode remains opt-in
* explicit trace override behavior remains supported
* rollback remains immediate and deterministic

No default authority cutover has been performed.

---

## Governance Layers

The governance stack is intentionally layered:

```text
authority_policy
        ↓
authority_matrix
        ↓
dual_authority_validation
        ↓
default_authority_simulation
        ↓
cutover_decision_gate
```

Responsibilities:

| Layer                             | Responsibility                    |
| --------------------------------- | --------------------------------- |
| `authority_policy.py`             | canonical authority semantics     |
| `ledger_authority_matrix.py`      | readiness aggregation             |
| `dual_authority_validation.py`    | continuous parity validation      |
| `default_authority_simulation.py` | simulated ledger-default analysis |
| `ledger_cutover_decision_gate.py` | governance eligibility evaluation |

---

## Authority Modes

Supported authority modes:

| Mode            | Behavior                                |
| --------------- | --------------------------------------- |
| `trace`         | trace-first default runtime mode        |
| `canary`        | ledger-backed compatibility validation  |
| `authoritative` | explicit ledger-authoritative operation |

Authority mode selection remains explicit and environment-controlled.

The runtime never performs implicit authority transitions.

---

## Governance & Validation Systems

Governance validation includes:

* ledger readiness validation
* parity validation
* corruption detection
* drift auditing
* compatibility auditing
* deprecation inventory analysis
* rollback validation
* control-plane compatibility auditing

Core governance modules include:

```text
runtime/authority_policy.py
runtime/ledger_authority_matrix.py
runtime/dual_authority_validation.py
runtime/default_authority_simulation.py
runtime/ledger_cutover_decision_gate.py
runtime/trace_deprecation_inventory.py
```

These systems are intentionally:

* read-only
* deterministic
* replay-safe
* compatibility-preserving
* governance-oriented

---

## Simulation & Decision Layers

The runtime supports simulation-only governance analysis.

Simulation systems evaluate:

```text
"What would happen if ledger became the default authority?"
```

without:

* changing runtime defaults
* switching authority
* mutating runtime artifacts
* disabling trace compatibility

Decision-gate systems evaluate:

```text
"Would future ledger-default cutover be operationally safe?"
```

without approving or performing cutover automatically.

---

## Rollback Guarantees

Rollback safety is treated as a core runtime invariant.

Governance systems must preserve:

* immediate authority rollback
* explicit trace override behavior
* dual-source compatibility
* replay-safe recovery
* deterministic authority semantics

Rollback remains environment-controlled and non-destructive.

---

## Governance Testing

Governance-oriented validation is intentionally separated from the primary runtime correctness ladder.

Primary runtime ladder:

```bash
make runtime-tests
```

Governance/runtime-readiness ladder:

```bash
make runtime-governance-tests
```

Governance suites aggregate broader operational state and may perform bounded historical scans, authority simulations, compatibility analysis, and cutover readiness evaluation.

These suites are intentionally heavier and are typically run before:

* release tagging
* governance review
* cutover planning
* operational readiness evaluation

---

# Runtime Lifecycle

Canonical lifecycle:

```text id="mglv5s"
session_start
  → tool_call
  → tool_result
  → agent_output
  → session_end
```

Lifecycle ordering is validated by:

* `event_ordering_tests.sh`
* `replayability_smoke_test.sh`
* `resume_from_trace_tests.sh`

---

# Runtime Flow

## 1. Runtime Coordination

Entrypoint:

```text id="9nmbhh"
scripts/runtime.sh
```

Primary coordinator:

```text id="v3h5jg"
runtime/engine.py
```

Delegated execution systems:

* `runtime/adapter_gateway.py`
* `runtime/run_lifecycle.py`
* `runtime/trace_pipeline.py`
* `runtime/event_ledger.py`

Responsibilities:

* create runs
* coordinate lifecycle orchestration
* invoke adapters
* validate responses
* persist canonical runtime artifacts
* finalize runtime state

The engine remains coordinator-only infrastructure.

---

## 2. Run Creation

Module:

```text id="ffm76z"
runtime/run.py
```

Responsibilities:

* generate `run_id`
* create canonical run directory
* initialize runtime metadata
* persist `run.json`

Canonical structure:

```text id="votfuk"
runs/<run_id>/
  run.json
  trace.jsonl
  ledger.jsonl
  result.json
  ledger.index.json
```

---

## 3. Adapter Execution

Primary module:

```text id="6x6r6e"
runtime/adapter_gateway.py
```

Legacy execution helper:

```text id="xdv5p3"
runtime/runner.py
```

Responsibilities:

* invoke adapters
* normalize adapter behavior
* enforce timeout boundaries
* capture stdout/stderr
* preserve deterministic execution
* validate adapter responses

Adapters communicate strictly through validated JSON contracts.

---

## 4. Lifecycle Orchestration

Module:

```text id="ucxxkg"
runtime/run_lifecycle.py
```

Responsibilities:

* lifecycle orchestration
* canonical event sequencing
* terminal lifecycle handling
* failure lifecycle handling
* deterministic response envelopes

Lifecycle ordering is replay-critical infrastructure.

---

## 5. Schema Validation

Modules:

```text id="rmtbfx"
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
* audit system outputs

Validation boundary includes:

* all external JSON
* all replayed events
* all persisted traces
* all exported datasets
* all eval summaries
* all ledger-derived artifacts

Validation delegation flow:

```text id="9g79j3"
validator.py
  → contracts.py
  → schemas.py
```

Compatibility helpers:

```text id="gq17vh"
assert_backward_compatible()
assert_no_breaking_changes()
```

Canonical serialization helper:

```text id="w9q1r4"
to_canonical_json()
```

---

## 6. Trace Persistence

Primary module:

```text id="u1ibzq"
runtime/trace_pipeline.py
```

Legacy compatibility helper:

```text id="p2wr2y"
runtime/events.py
```

Responsibilities:

* canonical event normalization
* schema validation
* append-only NDJSON persistence
* replay-safe ingestion
* strict/tolerant validation behavior

Trace format:

```text id="m63uq9"
runs/<run_id>/trace.jsonl
```

Requirements:

* append-only
* one JSON object per line
* replay-safe
* crash-safe
* schema-validated

---

## 7. EventLedger Persistence

Module:

```text id="ajv8av"
runtime/event_ledger.py
```

Responsibilities:

* additive ledger persistence
* deterministic event hashing
* parity validation
* migration readiness
* ledger indexing
* future authority support

Ledger artifacts:

```text id="pw6gse"
runs/<run_id>/ledger.jsonl
runs/<run_id>/ledger.index.json
```

EventLedger remains additive unless authoritative mode is explicitly enabled.

---

## 8. Replay System

Modules:

```text id="x3mf80"
runtime/replay.py
runtime/loader.py
```

Responsibilities:

* replay trace loading
* ledger replay loading
* schema-safe event reconstruction
* lifecycle reconstruction
* incomplete run detection

Replay guarantees:

* survives truncation
* preserves ordering
* preserves timestamps
* reconstructs terminal state
* preserves compatibility behavior

Replay remains authoritative runtime infrastructure.

---

# Evaluation System

Module:

```text id="tij8l5"
runtime/evals.py
```

Responsibilities:

* replay-derived runtime metrics
* run evaluation
* run comparison
* deterministic evaluation summaries

Core APIs:

```text id="1u7mev"
evaluate_run(run_id)
compare_runs(run_a, run_b)
```

Evaluation metrics include:

* `runtime_seconds`
* `total_events`
* `tool_calls`
* `tool_results`
* `replay_valid`
* `schema_valid`
* `completed`

Evaluation remains replay-derived infrastructure.

---

# Registry System

Module:

```text id="7o6czn"
runtime/registry.py
```

Responsibilities:

* enumerate runs
* query runtime history
* summarize execution metadata
* deterministic run ordering

Core APIs:

```text id="0j1c2r"
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

Registry behavior remains compatibility-preserving.

---

# Dataset Export System

Module:

```text id="u8h6z0"
runtime/datasets.py
```

Responsibilities:

* export replay-safe datasets
* export evaluation corpora
* export normalized traces
* deterministic NDJSON serialization

Supported exports:

```text id="w4w3o5"
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

`runtime.datasets` is classified as a projection writer and must not mutate runtime source artifacts.

---

# Audit & Observability Systems

Operational audit systems provide:

* drift detection
* corruption auditing
* ledger health reporting
* trace compatibility auditing
* runtime boundary auditing
* derived-system purity auditing
* ledger-default dry-run readiness

Core modules include:

```text id="ikq7f7"
runtime/ledger_drift.py
runtime/ledger_corruption.py
runtime/ledger_health.py
runtime/derived_purity.py
runtime/boundary_audit.py
runtime/trace_compatibility.py
```

Audit systems are intentionally:

* read-only
* deterministic
* observational-first
* compatibility-preserving

Audit systems must never:

* mutate runtime history
* bypass replay guarantees
* force authority changes
* perform implicit repair

---

# Core Runtime Modules

```text id="bh4av2"
runtime/
  engine.py
  run.py
  runner.py
  adapter_gateway.py
  run_lifecycle.py
  trace_pipeline.py
  event_ledger.py
  events.py
  replay.py
  loader.py
  evals.py
  registry.py
  datasets.py
  contracts.py
  validator.py
  schemas.py
  ledger_drift.py
  ledger_corruption.py
  ledger_health.py
  derived_purity.py
  boundary_audit.py
  trace_compatibility.py
```

---

# Event System

Canonical event fields:

```json id="t7o8j6"
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

| Event           | Purpose                  |
| --------------- | ------------------------ |
| `session_start` | lifecycle initialization |
| `tool_call`     | tool execution request   |
| `tool_result`   | tool execution result    |
| `agent_output`  | final runtime output     |
| `session_end`   | lifecycle completion     |

---

# Trace Persistence Model

Trace files are:

* append-only
* immutable after write
* line-oriented
* replay-derived
* compatibility-preserving

No event mutation is permitted after persistence.

---

# Failure Handling

Failure paths must still emit:

* valid JSON
* valid `schema_version`
* valid lifecycle termination
* replay-safe traces
* compatibility-safe artifacts

Failure guarantees are validated by:

```text id="az4uy8"
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
* independent ledger artifacts

Validated by:

```text id="1o9m4w"
parallel_run_isolation_test.sh
```

---

# Contract Architecture

The runtime uses a layered contract system:

```text id="yspkdp"
contracts.py
  ↓
schemas.py
  ↓
validator.py
  ↓
execution + replay + datasets + audit systems
```

Responsibilities:

| Layer          | Responsibility                 |
| -------------- | ------------------------------ |
| `contracts.py` | canonical contract definitions |
| `schemas.py`   | typed runtime schema layer     |
| `validator.py` | runtime validation entrypoints |
| `replay.py`    | replay-safe reconstruction     |
| `datasets.py`  | canonical export generation    |
| audit systems  | deterministic observability    |

Contract guarantees:

* deterministic serialization
* backward compatibility enforcement
* schema-versioned runtime contracts
* replay-safe persistence
* append-safe NDJSON traces

---

# Runtime Architectural Guarantees

The runtime guarantees:

* append-only persistence
* deterministic replay
* replay-safe reconstruction
* schema-validated contracts
* compatibility-preserving migration
* deterministic audit behavior
* additive EventLedger migration
* operational rollback safety
* replay-safe observability

These guarantees are considered core runtime invariants.

---

# Testing Guarantees

Current runtime guarantees are validated through:

```text id="a2hscm"
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
runtime_snapshot_tests.sh
runtime_adapter_gateway_tests.sh
runtime_run_lifecycle_tests.sh
runtime_trace_pipeline_tests.sh
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

---

# Current Operational Constraints

The runtime intentionally remains:

* single-process
* filesystem-native
* append-only
* replay-centric
* compatibility-preserving

The runtime intentionally avoids:

* distributed schedulers
* hidden queues
* implicit background mutation
* non-replayable orchestration
* distributed mutable state

These constraints are intentional architectural guarantees.

---

# Phase 4 Direction

Future runtime evolution areas include:

```text id="vrv4we"
runtime/state.py
runtime/reconstructor.py
runtime/observability.py
runtime/orchestrator.py
```

Future capabilities may include:

* deterministic state reconstruction
* replay-derived orchestration analytics
* resumable execution
* structured observability
* orchestration primitives
* multi-agent coordination
* evaluation pipelines
* runtime dashboards
* orchestration-aware replay tooling

Future phases must preserve:

* deterministic replay guarantees
* append-only persistence
* compatibility-safe migration
* replay-safe observability
* runtime contract validation
