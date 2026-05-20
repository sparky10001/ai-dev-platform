# Runtime Testing

## Philosophy

The runtime test suite validates deterministic runtime guarantees, not merely functional correctness.

The runtime is treated as:

```text
event-sourced deterministic infrastructure
```

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
* EventLedger parity guarantees
* audit and observability correctness
* cutover readiness behavior

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
trace pipeline + event loader
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
  ↓
audit + observability
```

Tests verify each layer independently and together.

---

# Runtime Audit & Observability Model

Beginning with Phase 3.7, the runtime includes operational audit and observability infrastructure in addition to deterministic replay guarantees.

The runtime now continuously validates:

* ledger/trace parity
* corruption detection
* drift detection
* runtime boundary enforcement
* derived-system purity
* ledger health observability
* trace compatibility readiness
* cutover readiness
* ledger-default dry-run simulation

These systems are intentionally:

* observational-first
* replay-centric
* compatibility-preserving
* non-destructive
* deterministic

No audit system may bypass runtime validation guarantees.

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

Default behavior remains tolerant for runtime compatibility.

Strict validation is opt-in via:

```bash
RUNTIME_TRACE_STRICT=1
```

---

# Phase 3.6 EventLedger Migration Suites

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

```text
unit test pass / 0 failed
```

This suite validates Phase 3.6B additive EventLedger validation/index/parity behavior.

---

## runtime_replay_ledger_tests.sh

Validates:

* trace replay remains default
* optional ledger replay
* trace/ledger replay parity
* deterministic missing-ledger handling

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.6C replay-from-ledger behavior behind opt-in source selection.

---

## runtime_eval_ledger_tests.sh

Validates:

* default trace-based evaluation
* optional ledger-based evaluation
* trace/ledger evaluation parity
* deterministic missing-ledger behavior

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.6D eval-from-ledger behavior behind opt-in source selection.

---

## runtime_registry_ledger_tests.sh

Validates:

* default trace-based registry behavior
* optional ledger-based registry loading
* trace/ledger registry parity
* deterministic missing-ledger handling

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.6E registry-from-ledger behavior behind opt-in source selection.

---

## runtime_ledger_authoritative_tests.sh

Validates:

* authoritative default switching
* explicit source override behavior
* parity enforcement
* trace compatibility preservation

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.6F ledger-authoritative cutover behind explicit flags.

---

## runtime_ledger_readiness_tests.sh

Validates:

* cutover readiness reporting
* parity readiness
* dependency audit structure
* authoritative readiness state

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.6G ledger cutover readiness auditing and migration-readiness reporting.

---

# Phase 3.7 Runtime Hardening & Audit Suites

## runtime_ledger_drift_tests.sh

Validates:

* cutover drift reporting
* parity drift category classification
* replay/eval/registry parity dimensions
* strict no-drift enforcement semantics
* audit CLI deterministic output and exit codes

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.7A ledger/trace drift detection as observational verification tooling.

---

## runtime_derived_purity_tests.sh

Validates:

* derived projection modules remain read-only
* forbidden write/import/subprocess detection
* dataset projection-writer classification
* strict derived purity audit behavior

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.7B derived-system purity audit guardrails.

---

## runtime_boundary_audit_tests.sh

Validates:

* runtime import-boundary model enforcement
* forbidden cross-layer import detection
* control-plane runtime.engine import prohibition
* boundary audit CLI strict/json behavior

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.7C runtime boundary enforcement guardrails.

---

## runtime_ledger_corruption_tests.sh

Validates:

* ledger corruption category detection
* strict vs tolerant corruption handling
* parity/index mismatch detection
* ledger-mode replay/eval/registry failure categorization
* corruption audit CLI strict/json behavior

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.7D ledger corruption and recovery-readiness guardrails.

---

## runtime_ledger_health_tests.sh

Validates:

* single-run ledger health classification
* aggregate ledger health metrics
* maintenance visibility + stale-stamp detection
* cutover-readiness integration
* health CLI strict/json/latest/summary behavior

Expected result:

```text
unit test pass / 0 failed

Operational recommendation: use `python3 scripts/maintenance/ledger_health_report.py --summary --recent 50` for bounded recent health visibility.```

This suite validates Phase 3.7E operational observability for ledger health.

---

## runtime_trace_compatibility_tests.sh

Validates:

* deterministic trace dependency inventory
* compatibility/blocker/legacy/test/docs/tooling classification
* cutover blocker readiness validator semantics
* trace compatibility audit CLI strict/json behavior

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.7G trace compatibility audit guardrails.

---

## runtime_ledger_default_dry_run_tests.sh

Validates:

* dry-run mode enablement and default-disabled behavior
* ledger-default readiness aggregation and categories
* strict CLI behavior and deterministic summary output
* no authority/default switching side effects

Expected result:

```text
unit test pass / 0 failed
```

This suite validates Phase 3.7I ledger-default dry-run observability without changing runtime authority.

---

## runtime_ledger_canary_tests.sh

Validates:

* explicit canary flag behavior
* canary source-default switching (replay/eval/registry)
* explicit trace source override safety
* canary readiness status aggregation
* canary CLI strict/json/print-env/recent behavior

Expected result:

unit test pass / 0 failed

Make targets:

* `make runtime-ledger-canary-tests`
* `make ledger-canary`
* `make ledger-canary-summary`
* `make ledger-canary-env`

Canary mode remains explicit opt-in and does not change global runtime defaults.

---

## runtime_event_loader_tests.sh

Validates:

* canonical source resolution (`trace` / `ledger`)
* authoritative/canary default switching behavior
* explicit source override behavior
* trace and ledger loading/iteration parity
* deterministic missing-ledger failure semantics
* replay/eval/registry helper consistency against the shared loader

Run:

* `./scripts/tests/runtime_event_loader_tests.sh`
* `make runtime-event-loader-tests`

---

## runtime_projection_purity_tests.sh

Validates:

* replay/eval/registry projection helpers over in-memory events
* projection helpers remain file-I/O free
* projection outputs match run-based public APIs on fixture runs
* public APIs continue loading via canonical event loader
* source behavior remains unchanged under trace/ledger/canary/authoritative paths

Run:

* `./scripts/tests/runtime_projection_purity_tests.sh`
* `make runtime-projection-purity-tests`

---

## runtime_ledger_authority_matrix_tests.sh

Validates:

* ready/warning/blocked matrix paths
* deterministic blocker ordering
* rollback payload determinism
* compatibility/boundary/purity propagation
* corruption/drift propagation
* control-plane compatibility propagation
* summary recent limiting
* CLI json/strict behavior
* no runtime mutation behavior

Suite:

```bash
./scripts/tests/runtime_ledger_authority_matrix_tests.sh
```

---

## runtime_authority_policy_tests.sh

Validates:

* default/canary/authoritative authority modes
* authoritative precedence over canary
* dry-run policy flag behavior
* explicit source override and deterministic invalid-source fallback
* transition/policy payload determinism
* replay/eval/registry and control-plane bridge source consistency
* no runtime mutation and no default cutover behavior

Run:

* `./scripts/tests/runtime_authority_policy_tests.sh`
* `make runtime-authority-policy-tests`

---

## runtime_dual_authority_validation_tests.sh

Validates:

* dual-validation activation by authority mode (`trace`/`canary`/`authoritative`)
* drift/corruption/parity/compatibility/rollback blocker propagation
* deterministic blocker ordering
* summary recent limiting
* CLI json/strict behavior
* no runtime mutation and no authority auto-switch

Run:

* `./scripts/tests/runtime_dual_authority_validation_tests.sh`
* `make runtime-dual-authority-validation-tests`

---

## runtime_trace_deprecation_inventory_tests.sh

Validates:

* deterministic trace deprecation inventory generation
* retained/operational/candidate classification paths
* documentation/test/historical classification
* informational strict behavior (no candidate-based failure)
* CLI summary/json/candidates/retained/operational behavior
* deterministic ordering and no runtime mutation

Run:

* `./scripts/tests/runtime_trace_deprecation_inventory_tests.sh`
* `make runtime-trace-deprecation-inventory-tests`

---

## runtime_default_authority_simulation_tests.sh

Validates:

* default-authority simulation ready/warning/blocked states
* deterministic blocker ordering
* propagation from authority matrix and dual-authority validation
* compatibility and deprecation inventory propagation
* CLI json/strict behavior
* no runtime mutation and no authority switch

Run:

* `./scripts/tests/runtime_default_authority_simulation_tests.sh`
* `make runtime-default-authority-simulation-tests`

---

## runtime_ledger_cutover_decision_gate_tests.sh

Validates:

* eligible / conditional / blocked decision-gate semantics
* deterministic blocker and condition ordering
* governance propagation from matrix, dual validation, simulation, compatibility, and deprecation inventory
* CLI json/strict behavior
* no authority mutation and no runtime mutation

Run:

* `./scripts/tests/runtime_ledger_cutover_decision_gate_tests.sh`
* `make runtime-ledger-cutover-decision-gate-tests`

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
./scripts/tests/runtime_run_lifecycle_tests.sh
./scripts/tests/runtime_trace_pipeline_tests.sh
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
./scripts/tests/runtime_ledger_canary_tests.sh
./scripts/tests/runtime_event_loader_tests.sh
./scripts/tests/runtime_projection_purity_tests.sh
./scripts/tests/runtime_ledger_authority_matrix_tests.sh
./scripts/tests/runtime_authority_policy_tests.sh
./scripts/tests/runtime_dual_authority_validation_tests.sh
./scripts/tests/runtime_trace_deprecation_inventory_tests.sh
./scripts/tests/runtime_default_authority_simulation_tests.sh
./scripts/tests/runtime_ledger_cutover_decision_gate_tests.sh
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

| Capability                        | Covered By                                    |
| --------------------------------- | --------------------------------------------- |
| response contracts                | runtime_tests.sh                              |
| replay safety                     | replayability_smoke_test.sh                   |
| lifecycle ordering                | event_ordering_tests.sh                       |
| crash durability                  | failure_tests.sh                              |
| NDJSON integrity                  | ndjson_integrity_tests.sh                     |
| replay reconstruction             | resume_from_trace_tests.sh                    |
| loader correctness                | loader_replay_tests.sh                        |
| evaluation correctness            | runtime_eval_tests.sh                         |
| registry correctness              | runtime_registry_tests.sh                     |
| dataset determinism               | runtime_dataset_tests.sh                      |
| contract enforcement              | runtime_contract_tests.sh                     |
| isolation guarantees              | parallel_run_isolation_test.sh                |
| runtime snapshot stability        | runtime_snapshot_tests.sh                     |
| adapter gateway boundary          | runtime_adapter_gateway_tests.sh              |
| lifecycle orchestration boundary  | runtime_run_lifecycle_tests.sh                |
| trace pipeline boundary           | runtime_trace_pipeline_tests.sh               |
| event ledger boundary             | runtime_event_ledger_tests.sh                 |
| replay ledger boundary            | runtime_replay_ledger_tests.sh                |
| eval ledger boundary              | runtime_eval_ledger_tests.sh                  |
| registry ledger boundary          | runtime_registry_ledger_tests.sh              |
| ledger authoritative boundary     | runtime_ledger_authoritative_tests.sh         |    
| ledger readiness boundary         | runtime_ledger_readiness_tests.sh             |
| ledger/trace drift auditing       | runtime_ledger_drift_tests.sh                 |
| derived-system purity             | runtime_derived_purity_tests.sh               |
| runtime boundary enforcement      | runtime_boundary_audit_tests.sh               |
| ledger corruption detection       | runtime_ledger_corruption_tests.sh            |
| ledger health observability       | runtime_ledger_health_tests.sh                |
| trace compatibility auditing      | runtime_trace_compatibility_tests.sh          |
| ledger-default dry-run readiness  | runtime_ledger_default_dry_run_tests.sh       |
| ledger authoritative canary       | runtime_ledger_canary_tests.sh                |
| canonical runtime event loader    | runtime_event_loader_tests.sh                 |
| runtime projection purity         | runtime_projection_purity_tests.sh            |
| ledger authority readiness matrix | runtime_ledger_authority_matrix_tests.sh      |
| runtime authority policy          | runtime_authority_policy_tests.sh             |
| dual-authority validation window  | runtime_dual_authority_validation_tests.sh    |
| trace deprecation inventory       | runtime_trace_deprecation_inventory_tests.sh  |
| default authority simulation      | runtime_default_authority_simulation_tests.sh |
| ledger cutover decision gate      | runtime_ledger_cutover_decision_gate_tests.sh |
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
* ledger authoritative mode validation
* ledger cutover readiness audit validation
* ledger drift audit validation
* ledger corruption validation
* runtime boundary audit validation
* derived purity audit validation
* ledger health observability validation
* trace compatibility validation
* ledger-default dry-run validation
* canonical runtime event loader validation

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
* canonical runtime event source resolution
* additive event ledger dual-write parity
* deterministic audit and observability reporting

Tests are designed to continuously validate these guarantees.

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
* verify ledger authoritative mode behavior
* verify ledger cutover readiness behavior
* verify ledger drift auditing
* verify ledger corruption auditing
* verify ledger health reporting
* verify trace compatibility auditing
* verify ledger-default dry-run readiness
* verify runtime boundary audit behavior
* verify derived purity audit behavior

No runtime refactor should bypass the validation layer.

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
* EventLedger parity behavior
* audit and observability outputs

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

## Ledger drift audit failure

Likely causes:

* trace/ledger divergence
* replay/eval/registry projection mismatch
* lifecycle parity corruption
* incompatible ledger reconstruction

---

## Ledger corruption audit failure

Likely causes:

* malformed ledger NDJSON
* mixed run_id ledger corruption
* timestamp regression
* duplicate lifecycle events
* parity/index mismatch

---

## Ledger health degradation

Likely causes:

* stale maintenance state
* missing ledger/index artifacts
* historical corruption backlog
* parity instability
* incomplete cutover readiness

---

## Trace compatibility blocker

Likely causes:

* trace-only runtime assumptions
* hardcoded replay dependencies
* legacy runtime coupling
* incomplete compatibility abstraction

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
* operational observability
* migration safety
* cutover readiness validation

over simple output assertions.

The runtime test system exists to guarantee that every run remains:

* replayable
* queryable
* evaluatable
* exportable
* deterministic
* backward compatible
* contract validated
* operationally observable
* migration-safe
