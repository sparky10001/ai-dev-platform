# Runtime Testing

## Philosophy

The runtime test suite validates deterministic runtime guarantees, not merely functional correctness.

The runtime is treated as:

```text
event-sourced deterministic infrastructure
````

—not merely a command wrapper.

The test system validates:

* replay safety
* crash durability
* schema consistency
* lifecycle ordering
* NDJSON integrity
* parallel isolation
* deterministic contracts
* dataset determinism
* registry correctness
* replay-derived evaluation correctness
* backward compatibility guarantees
* snapshot regression stability
* adapter gateway boundary correctness

---

# Runtime Validation Model

The runtime validation ladder is intentionally layered:

```text
contracts
  ↓
schemas
  ↓
validator
  ↓
adapter gateway
  ↓
runtime engine
  ↓
replay
  ↓
evals
  ↓
registry
  ↓
datasets
```

Tests verify each layer independently and together.

---

# Core Runtime Test Suites

## runtime_tests.sh

Validates:

* response contract
* schema_version propagation
* lifecycle integrity
* replay compatibility
* tool trace emission
* deterministic response envelopes

Expected result:

```text
9 passed / 0 failed
```

---

## failure_tests.sh

Validates:

* runtime failure handling
* error envelope consistency
* lifecycle failure persistence
* trace durability during errors
* deterministic failure contracts

Expected result:

```text
6 passed / 0 failed
```

---

## ndjson_integrity_tests.sh

Validates:

* NDJSON correctness
* one-object-per-line guarantees
* malformed line prevention
* append-only formatting
* crash-safe persistence

Expected result:

```text
9 passed / 0 failed
```

---

## event_ordering_tests.sh

Validates:

* lifecycle ordering
* deterministic event sequencing
* session_start/session_end correctness
* replay-safe ordering guarantees

Expected result:

```text
11 passed / 0 failed
```

---

## replayability_smoke_test.sh

Validates:

* replay parsing
* replay loading
* replay-safe persistence
* deterministic reconstruction

Expected result:

```text
11 passed / 0 failed
```

---

## run_structure_test.sh

Validates:

* canonical run directory layout
* required runtime artifacts
* trace/result persistence
* filesystem-native guarantees

Expected result:

```text
6 passed / 0 failed
```

---

## trace_schema_consistency_test.sh

Validates:

* schema_version consistency
* event schema uniformity
* replay-safe contracts
* deterministic event structure

Expected result:

```text
12 passed / 0 failed
```

---

## parallel_run_isolation_test.sh

Validates:

* concurrent run isolation
* unique trace separation
* independent lifecycle persistence
* deterministic multi-run safety

Expected result:

```text
8 passed / 0 failed
```

---

## resume_from_trace_tests.sh

Validates:

* replay reconstruction
* terminal status reconstruction
* lifecycle reconstruction
* truncation survivability
* replay ordering
* incomplete run detection

Expected result:

```text
13 passed / 0 failed
```

---

# Phase 3 Runtime Test Suites

## loader_replay_tests.sh

Validates:

* replay loader correctness
* strict schema replay validation
* full run reconstruction
* malformed trace rejection
* replay ordering preservation
* backward-compatible loader aliases

Expected result:

```text
6 passed / 0 failed
```

---

## runtime_eval_tests.sh

Validates:

* replay-derived evaluation metrics
* runtime duration calculation
* tool call/result counting
* run comparison correctness
* malformed trace evaluation handling
* evaluation schema integrity

Expected result:

```text
6 passed / 0 failed
```

---

## runtime_registry_tests.sh

Validates:

* run enumeration
* deterministic sorting
* metadata querying
* filtering correctness
* malformed run isolation
* summary generation
* latest run resolution

Expected result:

```text
7 passed / 0 failed
```

---

## runtime_dataset_tests.sh

Validates:

* deterministic dataset exports
* NDJSON export integrity
* replay-safe dataset generation
* trace corpus generation
* evaluation dataset generation
* malformed trace handling
* canonical serialization

Expected result:

```text
7 passed / 0 failed
```

---

## runtime_contract_tests.sh

Validates:

* contract model integrity
* validator delegation correctness
* compatibility helper behavior
* canonical serialization determinism
* dataset/eval contract validation

Expected result:

```text
5 passed / 0 failed
```

---

## runtime_snapshot_tests.sh

Validates:

* deterministic runtime replay structure
* normalized trace stability
* normalized result stability
* optional run.json consistency
* lifecycle replay consistency
* replay-safe deterministic hashing
* volatile metadata normalization
* cross-run structural equivalence

Normalized fields include:

* run_id
* run_path
* trace_path
* timestamp
* timestamps
* duration_ms
* created_at
* completed_at
* started_at
* ended_at
* absolute run directory paths

The snapshot suite validates:

```text
same logical execution
→ same normalized runtime structure
→ same replay-safe hashes
```

Expected result:

```text
1 passed / 0 failed
```

This suite is intentionally lightweight and exists to lock runtime behavior prior to runtime substrate refactors.

It serves as a regression guard for:

* runtime decomposition
* lifecycle extraction
* adapter gateway extraction
* replay pipeline refactors
* trace persistence changes
* deterministic serialization guarantees

---

## runtime_adapter_gateway_tests.sh

Validates:

* adapter execution normalization
* adapter contract validation
* timeout handling
* invalid JSON handling
* deterministic adapter payload handling
* validation delegation through existing runtime contracts

Expected result:

```text
7 passed / 0 failed
```

This suite validates the Phase 3.5 Step 1 adapter gateway extraction boundary.

It serves as a regression guard for:

* adapter subprocess execution
* adapter stdout parsing
* adapter contract validation
* adapter timeout behavior
* adapter gateway refactors

---

# Running Tests

Run all runtime suites individually:

```bash
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
./scripts/tests/runtime_snapshot_tests.sh
./scripts/tests/runtime_adapter_gateway_tests.sh
```

Run the full runtime ladder:

```bash
make runtime-tests
```

Run the full provider/runtime validation ladder:

```bash
make validate
```

---

# Validation Coverage Matrix

| Capability                 | Covered By                       |
| -------------------------- | -------------------------------- |
| response contracts         | runtime_tests.sh                 |
| replay safety              | replayability_smoke_test.sh      |
| lifecycle ordering         | event_ordering_tests.sh          |
| crash durability           | failure_tests.sh                 |
| NDJSON integrity           | ndjson_integrity_tests.sh        |
| replay reconstruction      | resume_from_trace_tests.sh       |
| loader correctness         | loader_replay_tests.sh           |
| evaluation correctness     | runtime_eval_tests.sh            |
| registry correctness       | runtime_registry_tests.sh        |
| dataset determinism        | runtime_dataset_tests.sh         |
| contract enforcement       | runtime_contract_tests.sh        |
| isolation guarantees       | parallel_run_isolation_test.sh   |
| runtime snapshot stability | runtime_snapshot_tests.sh        |
| adapter gateway boundary   | runtime_adapter_gateway_tests.sh |

---

# CI Expectations

All runtime suites must pass before merge.

Minimum requirement:

```text
0 failed
```

No schema-breaking changes should be merged without:

* replay validation
* backward compatibility verification
* lifecycle validation
* dataset validation
* registry validation
* contract compatibility validation
* snapshot regression validation
* adapter gateway validation

---

# Deterministic Runtime Guarantees

The runtime guarantees:

* append-only traces
* deterministic ordering
* replay-safe persistence
* canonical serialization
* schema-validated contracts
* crash-safe writes
* filesystem-native querying
* deterministic adapter response normalization
* snapshot-stable runtime structure

Tests are designed to continuously validate these guarantees.

---

# Adding New Tests

New tests should validate deterministic guarantees whenever possible.

Preferred categories:

* replay correctness
* crash recovery
* schema migration
* lifecycle integrity
* concurrency isolation
* malformed input handling
* dataset determinism
* contract compatibility
* replay-derived evaluation correctness
* snapshot regression stability
* adapter gateway boundary behavior

Avoid:

* brittle timing assumptions
* non-deterministic assertions
* environment-specific dependencies
* hidden external state

---

# Replay-Centric Testing

Replay is considered foundational infrastructure.

Replay tests must validate:

* partial trace recovery
* truncation survivability
* deterministic reconstruction
* lifecycle restoration
* schema compatibility
* ordering guarantees

Replay correctness is a hard runtime invariant.

---

# Contract Validation Philosophy

The runtime treats schemas and contracts as:

```text
deterministic infrastructure guarantees
```

—not optional serialization helpers.

Validation is mandatory for:

* events
* responses
* adapter payloads
* datasets
* evals
* registry results
* replay loading

No runtime component may bypass validation.

---

# Common Failure Signatures

## Missing session_end

Likely causes:

* runtime crash
* failure path regression
* trace truncation
* interrupted persistence

---

## Invalid schema_version

Likely causes:

* schema migration drift
* bypassed validation layer
* malformed adapter output
* contract regression

---

## Replay reconstruction failure

Likely causes:

* malformed NDJSON
* missing lifecycle events
* event ordering corruption
* invalid schema migration

---

## Parallel isolation failure

Likely causes:

* shared mutable state
* non-unique run directories
* trace collision
* nondeterministic persistence

---

## Dataset determinism failure

Likely causes:

* unstable serialization ordering
* replay inconsistency
* nondeterministic export logic

---

## Contract validation failure

Likely causes:

* incompatible schema changes
* validator bypasses
* contract drift
* malformed replay structures

---

## Snapshot regression failure

Likely causes:

* runtime output drift
* trace structure drift
* unnormalized volatile metadata
* lifecycle event sequence changes
* result artifact changes

---

## Adapter gateway failure

Likely causes:

* invalid adapter JSON
* subprocess timeout drift
* adapter response contract drift
* validation delegation regression
* stdout/stderr handling changes

---

# Verification Requirements

Before completing runtime changes:

* run all runtime suites
* verify replay compatibility
* verify schema consistency
* verify imports
* verify backward compatibility
* verify deterministic serialization
* verify dataset exports
* verify replay reconstruction
* verify contract compatibility
* verify snapshot stability
* verify adapter gateway behavior

No runtime refactor should bypass the validation layer.

---

# Runtime Testing Philosophy

The runtime prioritizes:

* persistence guarantees
* replay correctness
* schema durability
* deterministic reconstruction
* contract stability
* crash survivability
* adapter boundary correctness
* snapshot-stable behavior

over simple output assertions.

The runtime test system exists to guarantee that every run remains:

* replayable
* queryable
* evaluatable
* exportable
* deterministic
* backward compatible
* contract validated

```
```
