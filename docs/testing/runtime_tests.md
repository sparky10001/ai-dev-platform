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
* lifecycle orchestration boundary correctness
* trace pipeline correctness

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
run lifecycle
  ↓
trace pipeline
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

# Phase 3.5 Runtime Refactor Guard Suites

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

## runtime_run_lifecycle_tests.sh

Validates:

* lifecycle initialization delegation
* session_start lifecycle transition orchestration
* agent_output lifecycle event orchestration
* terminal session_end sequencing
* failure lifecycle handling
* deterministic response envelope construction
* lifecycle contract stability

Expected result:

```text
6 passed / 0 failed
```

This suite validates the Phase 3.5 Step 2 lifecycle extraction boundary.

It serves as a regression guard for:

* lifecycle transition sequencing
* session_start/session_end ordering
* failure lifecycle behavior
* response envelope construction
* lifecycle orchestration refactors

---

## runtime_trace_pipeline_tests.sh

Validates:

* trace event append normalization
* schema-validated event persistence
* NDJSON append integrity
* replay-safe trace ingestion
* strict/tolerant trace handling
* trace file validation
* lifecycle ordering validation
* mixed run_id detection
* monotonic timestamp validation in strict mode
* schema_version consistency validation in strict mode
* duplicate lifecycle event detection in strict mode
* no events after session_end enforcement in strict mode
* malformed NDJSON rejection in strict mode
* replay reconstruction guarantees

Expected result:

```text
unit test pass / 0 failed
```

This suite validates the Phase 3.5 Step 3 trace pipeline extraction boundary.

It serves as a regression guard for:

* append-only NDJSON persistence
* event normalization and validation
* replay loading behavior
* strict trace validation behavior
* tolerant runtime ingestion behavior
* lifecycle ordering checks
* trace corruption detection
* trace pipeline refactors

Default behavior remains tolerant for runtime compatibility.

Tolerant ingestion now returns deterministic corruption diagnostics for invalid ingested fragments.
Strict ingestion raises typed trace errors for invalid fragments.

Strict validation is opt-in via:

```bash
RUNTIME_TRACE_STRICT=1
```

---
## runtime_event_ledger_tests.sh

Validates:

* additive ledger writes
* ledger NDJSON integrity
* strict ledger validation hardening
* trace/ledger dual-write parity
* trace/ledger parity mismatch detection
* checksum/index validation
* deterministic event hashing

Expected result:

unit test pass / 0 failed

This suite validates Phase 3.6B additive EventLedger validation/index/parity behavior.

## runtime_replay_ledger_tests.sh

Validates:

* trace replay remains default
* optional ledger replay
* trace/ledger replay parity
* deterministic missing-ledger handling

Expected result:

unit test pass / 0 failed

This suite validates Phase 3.6C replay-from-ledger behavior behind opt-in source selection.

## runtime_eval_ledger_tests.sh

Validates:

* default trace-based evaluation
* optional ledger-based evaluation
* trace/ledger evaluation parity
* deterministic missing-ledger behavior

Expected result:

unit test pass / 0 failed

This suite validates Phase 3.6D eval-from-ledger behavior behind opt-in source selection.

## runtime_registry_ledger_tests.sh

Validates:

* default trace-based registry behavior
* optional ledger-based registry loading
* trace/ledger registry parity
* deterministic missing-ledger handling

Expected result:

unit test pass / 0 failed

This suite validates Phase 3.6E registry-from-ledger behavior behind opt-in source selection.


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
./scripts/tests/runtime_run_lifecycle_tests.sh
./scripts/tests/runtime_trace_pipeline_tests.sh
./scripts/tests/runtime_event_ledger_tests.sh
./scripts/tests/runtime_replay_ledger_tests.sh
./scripts/tests/runtime_eval_ledger_tests.sh
./scripts/tests/runtime_registry_ledger_tests.sh
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

| Capability                       | Covered By                       |
| -------------------------------- | -------------------------------- |
| response contracts               | runtime_tests.sh                 |
| replay safety                    | replayability_smoke_test.sh      |
| lifecycle ordering               | event_ordering_tests.sh          |
| crash durability                 | failure_tests.sh                 |
| NDJSON integrity                 | ndjson_integrity_tests.sh        |
| replay reconstruction            | resume_from_trace_tests.sh       |
| loader correctness               | loader_replay_tests.sh           |
| evaluation correctness           | runtime_eval_tests.sh            |
| registry correctness             | runtime_registry_tests.sh        |
| dataset determinism              | runtime_dataset_tests.sh         |
| contract enforcement             | runtime_contract_tests.sh        |
| isolation guarantees             | parallel_run_isolation_test.sh   |
| runtime snapshot stability       | runtime_snapshot_tests.sh        |
| adapter gateway boundary         | runtime_adapter_gateway_tests.sh |
| lifecycle orchestration boundary | runtime_run_lifecycle_tests.sh   |
| trace pipeline boundary          | runtime_trace_pipeline_tests.sh  |
| event ledger boundary            | runtime_event_ledger_tests.sh    |
| replay ledger boundary           | runtime_replay_ledger_tests.sh   |
| eval ledger boundary             | runtime_eval_ledger_tests.sh     |
| registry ledger boundary         | runtime_registry_ledger_tests.sh |

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
* lifecycle orchestration validation
* trace pipeline validation
* event ledger dual-write validation
* replay source selection validation
* eval source selection validation
* registry source selection validation

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
* deterministic lifecycle transition orchestration
* validated trace pipeline behavior
* additive event ledger dual-write parity

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
* lifecycle orchestration boundary behavior
* trace pipeline boundary behavior

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
* trace pipeline persistence

No runtime component may bypass validation.

---

# Common Failure Signatures

## Missing session_end

Likely causes:

* runtime crash
* failure path regression
* trace truncation
* interrupted persistence
* lifecycle orchestration regression

---

## Invalid schema_version

Likely causes:

* schema migration drift
* bypassed validation layer
* malformed adapter output
* contract regression
* trace pipeline validation drift

---

## Replay reconstruction failure

Likely causes:

* malformed NDJSON
* missing lifecycle events
* event ordering corruption
* invalid schema migration
* trace pipeline ingestion regression

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

## Lifecycle orchestration failure

Likely causes:

* lifecycle ordering drift
* missing session_start/session_end
* response envelope regression
* failure transition regression
* lifecycle extraction drift

---

## Trace pipeline failure

Likely causes:

* malformed NDJSON append behavior
* event normalization drift
* strict/tolerant behavior regression
* schema validation bypass
* mixed run_id trace corruption
* lifecycle validation regression
* replay loading drift

---

## EventLedger dual-write failure

Likely causes:

* ledger append write error
* ledger strict-mode regression
* trace/ledger parity drift

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
* verify lifecycle orchestration behavior
* verify trace pipeline behavior
* verify event ledger dual-write behavior
* verify replay source selection behavior
* verify eval source selection behavior
* verify registry source selection behavior

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
* lifecycle transition correctness
* trace pipeline correctness
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
