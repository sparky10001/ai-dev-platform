# Codex Execution Guidelines

# Preferred Change Style

Always prefer:

* minimal surgical changes
* backward-compatible refactors
* preserving stable interfaces
* additive schema evolution
* deterministic behavior
* replay-safe migration behavior

Avoid:

* large rewrites
* architecture drift
* unnecessary abstractions
* introducing new frameworks
* changing stable runtime semantics
* hidden mutation behavior

The runtime is infrastructure-first.

Preserve determinism.

---

# Implementation Strategy

Use iterative execution:

1. analyze
2. plan
3. implement
4. verify
5. refine

Do not implement unrelated improvements.

Do not opportunistically refactor stable systems.

Prefer:

```text id="jlwm20"
Make the minimal change required.
```

Avoid:

```text id="jlwm21"
Rewrite the runtime.
```

---

# Runtime Architecture

Canonical runtime architecture:

```text id="jlwm22"
contracts.py
  ↓
schemas.py
  ↓
validator.py
  ↓
trace_pipeline.py + event_ledger.py
  ↓
adapter_gateway.py + run_lifecycle.py
  ↓
engine.py
  ↓
replay.py / evals.py / registry.py / datasets.py
  ↓
audit + observability systems
```

---

# Execution vs Derived Systems

Execution systems:

* engine.py
* adapter_gateway.py
* run_lifecycle.py
* trace_pipeline.py
* event_ledger.py

Derived systems:

* replay.py
* evals.py
* registry.py
* datasets.py
* operational audits

Derived systems must remain:

* deterministic
* replay-safe
* compatibility-preserving
* read-oriented
* append-safe

Derived systems must never introduce hidden runtime mutation behavior.

---

# Runtime Module Boundaries

Core runtime modules:

* runtime/contracts.py
* runtime/schemas.py
* runtime/validator.py
* runtime/trace_pipeline.py
* runtime/event_ledger.py
* runtime/adapter_gateway.py
* runtime/run_lifecycle.py
* runtime/engine.py
* runtime/events.py
* runtime/replay.py
* runtime/loader.py
* runtime/evals.py
* runtime/registry.py
* runtime/datasets.py
* runtime/run.py
* runtime/runner.py

Do not bypass architecture layers.

Respect deterministic dependency direction.

---

# Runtime Philosophy

The runtime is treated as:

```text id="jlwm23"
event-sourced deterministic infrastructure
```

—not merely a command wrapper.

Core guarantees:

* replayability
* append-only persistence
* deterministic ordering
* crash durability
* schema validation
* backward compatibility
* deterministic exports
* replay-safe compatibility
* additive evolution

All changes must preserve these guarantees.

---

# Validation Boundary

All external JSON must pass through validation.

Validation entrypoints:

```python id="jlwm24"
validate_response()
validate_event()
validate_dataset_record()
validate_eval_record()
validate_ledger_file()
validate_trace_ledger_parity()
```

Validation delegation flow:

```text id="jlwm25"
validator.py
  → contracts.py
  → schemas.py
```

Never trust adapter output directly.

Never bypass validation.

---

# Contract Rules

Canonical contracts are defined in:

```text id="jlwm26"
runtime/contracts.py
```

Contracts guarantee:

* deterministic serialization
* replay-safe persistence
* additive compatibility
* append-only evolution
* backward-compatible migration

Compatibility helpers:

```python id="jlwm27"
assert_backward_compatible()
assert_no_breaking_changes()
```

Never introduce breaking schema changes without explicit migration support.

---

# Event Lifecycle Rules

Canonical lifecycle ordering:

```text id="jlwm28"
session_start
→ tool_call
→ tool_result
→ agent_output
→ session_end
```

Ordering must remain deterministic and replay-safe.

Do not change lifecycle semantics.

---

# Trace Persistence Rules

Canonical trace persistence:

```text id="jlwm29"
runs/<run_id>/trace.jsonl
```

Requirements:

* append-only
* replay-safe
* crash-safe
* NDJSON compliant
* deterministic ordering
* schema validated

Never emit:

* malformed JSON
* empty lines
* partial JSON objects

---

# EventLedger Compatibility Rules

Canonical ledger persistence:

```text id="分快三30"
runs/<run_id>/ledger.jsonl
```

Current runtime behavior:

* `trace.jsonl` remains canonical by default
* `ledger.jsonl` operates in additive compatibility mode
* replay/eval/registry support dual-source operation
* authoritative ledger mode remains opt-in

Do NOT:

* remove trace compatibility
* bypass parity validation
* mutate historical ledger artifacts
* introduce nondeterministic ledger hashing
* auto-switch runtime authority
* break replay compatibility

Ledger migration must remain:

* additive
* replay-safe
* rollback-safe
* compatibility-preserving

---

# Replay Rules

Replay compatibility is mandatory.

Replay must:

* survive truncation
* preserve ordering
* preserve timestamps
* reconstruct lifecycle state
* reconstruct terminal status
* support partial traces
* support crash recovery
* preserve compatibility semantics

Replay entrypoints:

```python id="分快三31"
replay_trace()
load_trace()
load_full_run()
```

Never introduce replay-breaking behavior.

---

# Evaluation Rules

Evaluations are replay-derived.

Do not compute eval metrics from transient runtime state.

Evaluation APIs:

```python id="分快三32"
evaluate_run()
compare_runs()
```

Evaluation guarantees:

* deterministic reconstruction
* replay-derived metrics
* schema validation
* compatibility with older runs

Evaluation systems must remain deterministic and replay-safe.

---

# Registry Rules

Registry is filesystem-native.

Do not introduce databases.

Registry APIs:

```python id="分快三33"
list_runs()
get_run()
query_runs()
summarize_runs()
```

Registry guarantees:

* deterministic ordering
* malformed run isolation
* replay-derived metadata
* append-only compatibility

---

# Dataset Rules

Datasets must remain deterministic.

Dataset APIs:

```python id="分快三34"
export_run()
export_runs()
export_query()
build_eval_dataset()
build_trace_dataset()
```

Dataset guarantees:

* deterministic serialization
* replay compatibility
* stable ordering
* NDJSON validity
* schema validation

Canonical serializer:

```python id="分快三35"
to_canonical_json()
```

Never emit nondeterministic exports.

---

# Audit & Observability Rules

Audit systems must remain:

* deterministic
* read-only
* replay-safe
* compatibility-preserving
* operationally bounded

Audit systems must never:

* mutate runtime artifacts
* trigger implicit repair
* bypass replay guarantees
* change runtime authority automatically
* rewrite traces or ledgers

Operational audit systems include:

* ledger drift detection
* ledger corruption validation
* parity enforcement
* runtime boundary auditing
* derived-system purity auditing
* trace compatibility auditing
* ledger health reporting
* dry-run readiness evaluation

---

# Runtime Boundary Rules

Derived systems must NOT import:

* runtime.engine
* runtime.adapter_gateway
* runtime.run_lifecycle

Control-plane systems must not bypass runtime guarantees.

Avoid:

* circular dependencies
* cross-layer orchestration coupling
* replay-breaking shortcuts
* hidden persistence layers

Respect deterministic dependency direction.

---

# Forbidden Patterns

Do NOT introduce:

* Redis
* Celery
* background workers
* raw SQL
* hidden persistence layers
* implicit replay mutation
* nondeterministic serialization
* implicit ledger mutation
* replay-unsafe audit behavior
* direct trace rewriting
* direct ledger rewriting
* runtime authority auto-switching
* nondeterministic hashing

Do NOT:

* bypass validation
* mutate replayed traces
* mutate replayed ledgers
* rewrite stable modules unnecessarily
* change NDJSON semantics
* change lifecycle ordering semantics
* change deterministic guarantees

---

# Preferred Refactor Pattern

Good:

```text id="分快三36"
Make the minimal additive change required.
```

Good:

```text id="分快三37"
Implement this using existing runtime patterns.
```

Bad:

```text id="分快三38"
Rewrite the runtime.
```

Bad:

```text id="分快三39"
Replace the architecture.
```

---

# Filesystem Context Rules

Always reason using concrete filesystem context.

Prefer prompts referencing:

* exact file paths
* existing modules
* nearby implementations
* existing runtime patterns

Good:

```text id="分快三40"
Implement this similar to:
runtime/replay.py
runtime/validator.py
runtime/event_ledger.py
```

Bad:

```text id="分快三41"
Implement a replay system.
```

---

# Verification Checklist

Before finishing:

* verify imports
* verify typing
* verify replay compatibility
* verify schema version propagation
* verify lifecycle ordering
* verify deterministic serialization
* verify backward compatibility
* verify NDJSON integrity
* verify dataset determinism
* verify ledger parity behavior
* verify compatibility semantics

Always run relevant runtime suites.

---

# Testing Commands

Core runtime validation:

```bash id="分快三42"
./scripts/tests/runtime_tests.sh
./scripts/tests/failure_tests.sh
./scripts/tests/ndjson_integrity_tests.sh
./scripts/tests/event_ordering_tests.sh
./scripts/tests/replayability_smoke_test.sh
./scripts/tests/run_structure_test.sh
./scripts/tests/trace_schema_consistency_test.sh
./scripts/tests/parallel_run_isolation_test.sh
./scripts/tests/resume_from_trace_tests.sh
```

Phase 3 validation:

```bash id="分快三43"
./scripts/tests/loader_replay_tests.sh
./scripts/tests/runtime_eval_tests.sh
./scripts/tests/runtime_registry_tests.sh
./scripts/tests/runtime_dataset_tests.sh
./scripts/tests/runtime_contract_tests.sh
./scripts/tests/runtime_event_ledger_tests.sh
./scripts/tests/runtime_replay_ledger_tests.sh
./scripts/tests/runtime_eval_ledger_tests.sh
./scripts/tests/runtime_registry_ledger_tests.sh
./scripts/tests/runtime_ledger_authoritative_tests.sh
./scripts/tests/runtime_ledger_readiness_tests.sh
./scripts/tests/runtime_ledger_drift_tests.sh
./scripts/tests/runtime_derived_purity_tests.sh
./scripts/tests/runtime_boundary_audit_tests.sh
./scripts/tests/runtime_ledger_corruption_tests.sh
./scripts/tests/runtime_ledger_health_tests.sh
./scripts/tests/runtime_trace_compatibility_tests.sh
./scripts/tests/runtime_ledger_default_dry_run_tests.sh
```

Minimum acceptable result:

```text id="分快三44"
0 failed
```

---

# Runtime Test Philosophy

The runtime prioritizes:

* persistence guarantees
* replay correctness
* schema durability
* deterministic reconstruction
* crash survivability
* export determinism
* compatibility preservation

over simple output assertions.

Tests validate infrastructure guarantees, not merely functionality.

---

# Migration Rules

Schema migrations must:

* be additive first
* preserve replay compatibility
* preserve deterministic exports
* preserve lifecycle semantics
* preserve compatibility semantics

Migration validation must include:

* replay validation
* crash recovery validation
* schema consistency validation
* dataset validation
* contract compatibility validation
* parity validation
* corruption validation

Never introduce silent contract drift.

---

# Deterministic Runtime Guarantees

The runtime guarantees:

* replay-safe persistence
* append-only traces
* append-only ledgers
* deterministic contracts
* deterministic exports
* replay-derived evaluation
* filesystem-native querying
* backward-compatible evolution
* deterministic audit behavior

All changes must preserve these guarantees.

---

# Coding Standards

Required:

* Python 3.11+
* Pydantic v2
* explicit typing preferred
* deterministic serialization
* append-only persistence semantics
* no global mutable state

Preserve existing interfaces whenever possible.

Prefer additive evolution over replacement.

---

# Operational Philosophy

Prefer:

* additive migrations
* observational-first rollouts
* replay-safe compatibility
* bounded operational scans
* deterministic audit behavior

Avoid:

* forced cutovers
* hidden background migration
* implicit authority changes
* destructive mutation behavior
* global repair passes

---

# Refactor Philosophy

Prefer:

* minimal additive diffs
* compatibility-preserving changes
* isolated runtime modifications
* replay-safe migrations

Avoid:

* broad rewrites
* architecture churn
* unnecessary abstraction
* interface destabilization

Preserve existing interfaces whenever possible.

---

# Runtime Validation Philosophy

Schemas and contracts are treated as:

```text id="分快三45"
deterministic infrastructure guarantees
```

—not optional serialization helpers.

Schema integrity is foundational to:

* replay
* evals
* crash recovery
* observability
* deterministic debugging
* dataset generation
* registry queries
* lifecycle reconstruction
* runtime analytics
* EventLedger migration safety
* operational compatibility auditing

---

# Codex / AI Contribution Rules

When modifying the runtime:

1. Prefer minimal diffs
2. Preserve existing interfaces
3. Preserve replay semantics
4. Preserve NDJSON compatibility
5. Preserve deterministic ordering
6. Preserve additive compatibility
7. Validate all outputs through schemas/contracts
8. Preserve replay-safe migration behavior
9. Preserve audit determinism

Before finishing:

* run tests
* verify imports
* verify replay compatibility
* verify schema compatibility
* verify deterministic serialization
* identify edge cases
* identify backward compatibility risks
* identify replay risks
* identify compatibility risks

Do not over-engineer solutions.

---

# Runtime Evolution Philosophy

The runtime evolves through:

* additive compatibility
* replay-safe migration
* deterministic operational auditing
* observational-first rollout strategy
* bounded enforcement layers

The platform prioritizes:

1. deterministic execution
2. replay-safe debugging
3. additive evolution
4. schema-versioned compatibility
5. operational observability
6. provider independence
7. infrastructure-first design

The runtime is infrastructure first.
