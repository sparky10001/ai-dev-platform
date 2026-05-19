# AI Runtime Platform — Repository Instructions

# Runtime Architecture Philosophy

The runtime is treated as:

```text id="v7m3qc"
event-sourced deterministic infrastructure
```

—not merely a command wrapper.

Core runtime guarantees:

* replayability
* deterministic behavior
* append-only persistence
* schema durability
* crash survivability
* backward compatibility
* deterministic exports
* replay-safe evolution
* additive migration compatibility

All runtime systems must preserve these guarantees.

---

# Runtime Architecture

Canonical runtime architecture:

```text id="8zjlwm"
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
* audit tooling

Derived systems must remain:

* replay-safe
* deterministic
* compatibility-preserving
* read-oriented
* append-safe

Derived systems must never introduce hidden runtime mutation behavior.

---

# Runtime Layer Responsibilities

| Layer              | Responsibility                      |
| ------------------ | ----------------------------------- |
| contracts.py       | canonical contract enforcement      |
| schemas.py         | typed Pydantic models               |
| validator.py       | validation entrypoints              |
| trace_pipeline.py  | canonical trace persistence         |
| event_ledger.py    | deterministic ledger persistence    |
| adapter_gateway.py | provider integration                |
| run_lifecycle.py   | runtime lifecycle coordination      |
| engine.py          | runtime orchestration coordinator   |
| replay.py          | replay-safe reconstruction          |
| evals.py           | replay-derived evaluations          |
| registry.py        | filesystem-native querying          |
| datasets.py        | deterministic NDJSON exports        |
| audit systems      | deterministic operational reporting |

Do not bypass architectural layers.

---

# Schema-First Rules

Runtime is schema-first.

External contracts use:

* JSON
* NDJSON

Internal validation uses:

* Pydantic v2

Validation entrypoints:

```python id="y0g3kt"
validate_response()
validate_event()
validate_dataset_record()
validate_eval_record()
validate_ledger_file()
validate_trace_ledger_parity()
```

No runtime component may bypass validation.

---

# Contract Rules

Canonical contracts are defined in:

```text id="k3n2ut"
runtime/contracts.py
```

Contract guarantees:

* deterministic serialization
* replay-safe compatibility
* append-only evolution
* additive migrations
* backward compatibility

Compatibility helpers:

```python id="f2px91"
assert_backward_compatible()
assert_no_breaking_changes()
```

Never introduce breaking schema changes without explicit migration support.

---

# Runtime Event Rules

Every runtime event MUST contain:

* schema_version
* timestamp
* run_id
* event
* data

Optional additive fields:

* step
* meta
* error

Canonical trace persistence:

```text id="j2xv8q"
runs/<run_id>/trace.jsonl
```

Canonical ledger persistence:

```text id="p9jlwm"
runs/<run_id>/ledger.jsonl
```

Trace + ledger guarantees:

* NDJSON only
* append-only
* one JSON object per line
* replay-safe
* truncation-safe
* deterministic ordering
* schema-validated

Never emit malformed JSON lines.

---

# EventLedger Compatibility Rules

Current runtime behavior:

* `trace.jsonl` remains canonical by default
* `ledger.jsonl` operates in additive compatibility mode
* replay/eval/registry support dual-source operation
* authoritative ledger mode remains opt-in

Do NOT:

* remove trace compatibility
* bypass parity validation
* mutate historical ledger artifacts
* introduce non-deterministic ledger hashing
* auto-switch runtime authority
* break replay compatibility

Ledger migration must remain:

* additive
* replay-safe
* rollback-safe
* compatibility-preserving

---

# Response Contract Rules

All adapter responses MUST validate against:

```python id="r8h0ma"
runtime.schemas.ResponseSchema
```

All responses must contain:

* schema_version
* status
* output
* meta

Never bypass:

```python id="t1q6py"
validate_response()
```

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
* support crash-recovered traces
* preserve compatibility semantics

Replay entrypoints:

```python id="b4d7sk"
replay_trace()
load_trace()
load_full_run()
```

Do not introduce replay-breaking behavior.

---

# Evaluation Rules

Evaluations are replay-derived.

Never compute eval metrics from transient runtime state.

Evaluation guarantees:

* deterministic reconstruction
* replay-derived metrics
* schema validation
* compatibility with older runs

Evaluation APIs:

```python id="e5f8zx"
evaluate_run()
compare_runs()
```

Evaluation systems must remain deterministic and replay-safe.

---

# Registry Rules

Runtime registry is filesystem-native.

Do not introduce databases.

Registry guarantees:

* deterministic ordering
* replay-derived metadata
* malformed run isolation
* append-only compatibility

Registry APIs:

```python id="q0n5yu"
list_runs()
get_run()
query_runs()
summarize_runs()
```

---

# Dataset Rules

Dataset exports must remain deterministic.

Dataset guarantees:

* replay compatibility
* canonical serialization
* NDJSON validity
* stable ordering
* append-safe exports

Dataset APIs:

```python id="m9u4be"
export_run()
export_runs()
export_query()
build_eval_dataset()
build_trace_dataset()
```

Canonical serialization helper:

```python id="p3x1rt"
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

Do not introduce:

* circular runtime dependencies
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
* noncanonical hashing
* runtime authority auto-switching
* direct trace rewriting
* direct ledger rewriting

Do NOT:

* bypass validation
* rewrite stable modules unnecessarily
* mutate replayed traces
* mutate replayed ledgers
* change NDJSON semantics
* change lifecycle ordering guarantees

---

# Runtime Philosophy

Prefer:

* minimal diffs
* deterministic behavior
* replayability
* append-only persistence
* backward compatibility
* additive schema evolution
* canonical serialization
* bounded operational scans
* replay-safe compatibility

Avoid:

* hidden side effects
* implicit state
* magic mutation
* over-engineering
* unnecessary abstractions
* architecture churn

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
* global mutation behavior
* destructive runtime rewrites

---

# Refactor Philosophy

Prefer:

* minimal additive diffs
* compatibility-preserving changes
* isolated runtime modifications
* replay-safe migrations

Avoid:

* broad rewrites
* unnecessary abstraction
* architecture destabilization
* interface churn

Preserve existing interfaces whenever possible.

---

# Migration Rules

Schema migrations must:

* be additive first
* preserve replay compatibility
* preserve deterministic exports
* preserve lifecycle reconstruction
* preserve compatibility semantics

Migration validation must include:

* replay validation
* crash recovery validation
* schema consistency validation
* dataset validation
* registry validation
* parity validation
* corruption validation

---

# Coding Standards

Required:

* Python 3.11+
* Pydantic v2
* explicit typing preferred
* deterministic serialization
* no global mutable state
* append-only trace semantics
* append-only ledger semantics

Preserve existing interfaces whenever possible.

Prefer minimal, additive refactors.

---

# Testing Requirements

Before finishing any runtime change:

Run:

```bash id="u8q4ac"
./scripts/tests/runtime_tests.sh
./scripts/tests/failure_tests.sh
./scripts/tests/ndjson_integrity_tests.sh
./scripts/tests/event_ordering_tests.sh
./scripts/tests/replayability_smoke_test.sh
./scripts/tests/run_structure_test.sh
./scripts/tests/trace_schema_consistency_test.sh
./scripts/tests/parallel_run_isolation_test.sh
./scripts/tests/resume_from_trace_tests.sh
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

Verify:

* replay compatibility
* schema compatibility
* deterministic serialization
* backward compatibility
* import correctness
* NDJSON integrity
* parity compatibility
* ledger compatibility
* audit determinism

Minimum acceptable result:

```text id="v1m8sx"
0 failed
```

---

# Runtime Guarantees

The runtime guarantees:

* deterministic contracts
* replay-safe persistence
* append-only traces
* append-only ledgers
* crash-safe writes
* deterministic exports
* replay-derived evaluation
* filesystem-native querying
* additive compatibility evolution
* deterministic audit behavior

All runtime changes must preserve these guarantees.

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

# Runtime Validation Philosophy

Schemas and contracts are treated as:

```text id="a6c7wb"
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
