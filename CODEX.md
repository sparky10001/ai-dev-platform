# Codex Execution Guidelines

# Preferred Change Style

Always prefer:

* minimal surgical changes
* backward-compatible refactors
* preserving stable interfaces
* additive schema evolution
* deterministic behavior

Avoid:

* large rewrites
* architecture drift
* unnecessary abstractions
* introducing new frameworks
* changing stable runtime semantics

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

```text id="n2v7qs"
Make the minimal change required.
```

Avoid:

```text id="f8u3pk"
Rewrite the runtime.
```

---

# Runtime Architecture

Canonical runtime stack:

```text id="w4p1rx"
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

Core runtime modules:

* runtime/contracts.py
* runtime/schemas.py
* runtime/validator.py
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

---

# Runtime Philosophy

The runtime is treated as:

```text id="x5r8bv"
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

All changes must preserve these guarantees.

---

# Validation Boundary

All external JSON must pass through validation.

Validation entrypoints:

```python id="d6m2yt"
validate_response()
validate_event()
validate_dataset_record()
validate_eval_record()
```

Validation delegation flow:

```text id="u1h4qf"
validator.py
  → contracts.py
  → schemas.py
```

Never trust adapter output directly.

Never bypass validation.

---

# Contract Rules

Canonical contracts are defined in:

```text id="j9w3pc"
runtime/contracts.py
```

Contracts guarantee:

* deterministic serialization
* replay-safe persistence
* additive compatibility
* append-only evolution

Compatibility helpers:

```python id="v0n8xe"
assert_backward_compatible()
assert_no_breaking_changes()
```

Never introduce breaking schema changes without explicit migration support.

---

# Trace Lifecycle

Canonical lifecycle ordering:

```text id="q4t6ka"
session_start
→ tool_call
→ tool_result
→ agent_output
→ session_end
```

Ordering must remain deterministic and replay-safe.

Do not change lifecycle semantics.

---

# Trace Persistence

Trace files:

```text id="s7f9rm"
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

Replay entrypoints:

```python id="m1z4hw"
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

```python id="r5p0yu"
evaluate_run()
compare_runs()
```

Evaluation guarantees:

* deterministic reconstruction
* replay-derived metrics
* schema validation
* compatibility with older runs

---

# Registry Rules

Registry is filesystem-native.

Do not introduce databases.

Registry APIs:

```python id="k8v3sa"
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

```python id="h6x2cf"
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

```python id="e4m7zd"
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
* mutate replayed traces
* rewrite stable modules unnecessarily
* change NDJSON semantics
* change lifecycle ordering semantics
* change deterministic guarantees

---

# Preferred Refactor Pattern

Good:

```text id="y3q8wr"
Make the minimal additive change required.
```

Good:

```text id="t2u6bf"
Implement this using existing runtime patterns.
```

Bad:

```text id="n7p4ks"
Rewrite the runtime.
```

Bad:

```text id="b5m1zx"
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

```text id="p9d2ev"
Implement this similar to:
runtime/replay.py
runtime/validator.py
```

Bad:

```text id="a0r5hn"
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

Always run relevant runtime suites.

---

# Testing Commands

Core runtime validation:

```bash id="v4k7tc"
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

```bash id="g8m3ps"
./scripts/tests/loader_replay_tests.sh
./scripts/tests/runtime_eval_tests.sh
./scripts/tests/runtime_registry_tests.sh
./scripts/tests/runtime_dataset_tests.sh
./scripts/tests/runtime_contract_tests.sh
```

Minimum acceptable result:

```text id="u7r1xf"
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

over simple output assertions.

Tests validate infrastructure guarantees, not merely functionality.

---

# Migration Rules

Schema migrations must:

* be additive first
* preserve replay compatibility
* preserve deterministic exports
* preserve lifecycle semantics

Migration validation must include:

* replay validation
* crash recovery validation
* schema consistency validation
* dataset validation
* contract compatibility validation

Never introduce silent contract drift.

---

# Deterministic Runtime Guarantees

The runtime guarantees:

* replay-safe persistence
* append-only traces
* deterministic contracts
* deterministic exports
* replay-derived evaluation
* filesystem-native querying
* backward-compatible evolution

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

# Runtime Validation Philosophy

Schemas and contracts are treated as:

```text id="m0q4zw"
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
