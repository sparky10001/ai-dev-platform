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

All runtime systems must preserve these guarantees.

---

# Runtime Architecture

Canonical architecture stack:

```text id="s8p4an"
contracts.py
  ↓
schemas.py
  ↓
validator.py
  ↓
engine.py
  ↓
replay.py
  ↓
evals.py
  ↓
registry.py
  ↓
datasets.py
```

Responsibilities:

| Layer        | Responsibility                  |
| ------------ | ------------------------------- |
| contracts.py | canonical contract enforcement  |
| schemas.py   | typed Pydantic models           |
| validator.py | validation entrypoints          |
| engine.py    | runtime lifecycle orchestration |
| replay.py    | replay-safe reconstruction      |
| evals.py     | replay-derived evaluations      |
| registry.py  | filesystem-native querying      |
| datasets.py  | deterministic NDJSON exports    |

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

Canonical event persistence:

```text id="j2xv8q"
runs/<run_id>/trace.jsonl
```

Trace guarantees:

* NDJSON only
* append-only
* one JSON object per line
* replay-safe
* truncation-safe
* deterministic ordering

Never emit malformed JSON lines.

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

# Forbidden Patterns

Do NOT introduce:

* Redis
* Celery
* background workers
* raw SQL
* hidden persistence layers
* implicit replay mutation
* nondeterministic serialization

Do NOT:

* bypass validation
* rewrite stable modules unnecessarily
* mutate replayed traces
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

Avoid:

* hidden side effects
* implicit state
* magic mutation
* over-engineering
* unnecessary abstractions

---

# Migration Rules

Schema migrations must:

* be additive first
* preserve replay compatibility
* preserve deterministic exports
* preserve lifecycle reconstruction

Migration validation must include:

* replay validation
* crash recovery validation
* schema consistency validation
* dataset validation
* registry validation

---

# Coding Standards

Required:

* Python 3.11+
* Pydantic v2
* explicit typing preferred
* deterministic serialization
* no global mutable state
* append-only trace semantics

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
```

Verify:

* replay compatibility
* schema compatibility
* deterministic serialization
* backward compatibility
* import correctness
* NDJSON integrity

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
* crash-safe writes
* deterministic exports
* replay-derived evaluation
* filesystem-native querying
* additive compatibility evolution

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

Before finishing:

* run tests
* verify imports
* verify replay compatibility
* verify schema compatibility
* verify deterministic serialization
* identify edge cases
* identify backward compatibility risks

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
