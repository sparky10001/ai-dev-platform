# Runtime Dependency Graph

This document records the runtime dependency model, execution boundaries, derived-system rules, and compatibility-safe migration constraints introduced through Phase 3.5–3.7.

The runtime is intentionally structured as deterministic, replay-safe infrastructure with strict dependency direction and operational audit guarantees.

---

# Runtime Layer Model

The runtime is intentionally layered:

```text
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
audit + observability tooling
```

Dependency direction must remain one-way toward lower-level infrastructure layers.

Replay, evals, registry, datasets, and audit systems are treated as derived systems and must not couple back into runtime execution layers.

---

# Runtime Execution vs Derived Systems

## Execution Systems

Execution systems coordinate and persist canonical runtime behavior.

Execution systems include:

* `runtime.engine`
* `runtime.adapter_gateway`
* `runtime.run_lifecycle`
* `runtime.trace_pipeline`
* `runtime.event_ledger`

Execution systems:

* produce canonical runtime artifacts
* coordinate runtime execution
* enforce lifecycle ordering
* validate runtime contracts
* preserve replay guarantees

---

## Derived Systems

Derived systems consume runtime artifacts and must remain replay-safe and compatibility-preserving.

Derived systems include:

* `runtime.replay`
* `runtime.evals`
* `runtime.registry`
* `runtime.datasets`
* audit and observability tooling

Derived systems:

* must remain read-oriented
* must not mutate runtime history
* must not couple into execution orchestration
* must remain deterministic and replay-safe

---

# Allowed Dependency Direction

`runtime.engine` is the top-level runtime coordinator.

Lower-level runtime modules must not import upward into execution orchestration layers.

Dependency direction must remain one-way toward:

* contracts
* schemas
* validator
* persistence infrastructure

Execution orchestration must remain centralized in `runtime.engine`.

---

# Verified Boundaries

## Execution Layer

* `runtime.engine` imports:

  * `runtime.run_lifecycle`
  * `runtime.adapter_gateway`
  * `runtime.trace_pipeline`
  * `runtime.event_ledger`
  * `runtime.validator`
  * `runtime.schemas`

* `runtime.adapter_gateway` imports stdlib plus:

  * `runtime.validator`

* `runtime.run_lifecycle` imports:

  * `runtime.events`
  * `runtime.run`
  * `runtime.validator`

* `runtime.trace_pipeline` imports stdlib plus:

  * `runtime.errors`
  * `runtime.validator`

* `runtime.event_ledger` imports persistence/validation infrastructure only and remains additive to trace infrastructure.

---

## Derived Layer

* `runtime.replay` imports `runtime.trace_pipeline` one-way.
* `runtime.registry`, `runtime.datasets`, and `runtime.evals` do not import `runtime.engine`.
* audit systems do not participate in runtime execution orchestration.

---

# EventLedger Positioning

`runtime.trace_pipeline.py` remains the canonical append-only runtime event stream layer.

`runtime.event_ledger.py` provides:

* additive deterministic ledger indexing
* parity validation
* migration readiness
* future authority support
* operational observability support

EventLedger remains compatibility-preserving unless authoritative mode is explicitly enabled.

---

# Forbidden Imports

## Adapter Gateway

`runtime.adapter_gateway` must not import:

* `runtime.engine`
* `runtime.run_lifecycle`
* `runtime.trace_pipeline`
* replay/eval/registry systems

---

## Run Lifecycle

`runtime.run_lifecycle` must not import:

* `runtime.engine`
* `runtime.adapter_gateway`
* `runtime.replay`
* `runtime.datasets`
* `runtime.evals`
* audit/observability systems

---

## Trace Pipeline

`runtime.trace_pipeline` must not import:

* `runtime.engine`
* `runtime.adapter_gateway`
* `runtime.run_lifecycle`
* `runtime.replay`
* `runtime.datasets`
* `runtime.evals`
* control-plane orchestration modules

---

## EventLedger

`runtime.event_ledger` must not import:

* `runtime.engine`
* execution orchestration modules
* control-plane orchestration systems

except through explicitly approved compatibility-safe helpers.

---

## Derived Systems

`runtime.replay`, `runtime.registry`, `runtime.datasets`, and `runtime.evals` must not import:

* `runtime.engine`
* `runtime.adapter_gateway`
* `runtime.run_lifecycle`

Derived systems must remain replay-safe and read-oriented.

---

## Control Plane

control-plane modules must not import:

* `runtime.engine`

directly.

---

# Architectural Guidance

The runtime intentionally preserves:

* coordinator-only engine orchestration
* one-way dependency flow
* replay-safe persistence
* deterministic reconstruction
* additive migration safety
* compatibility-preserving evolution

Circular runtime coupling is considered a critical architectural regression.

---

# Audit and Observability Systems

Audit systems are intentionally:

* read-only
* non-authoritative
* compatibility-preserving
* deterministic
* observational-first

Audit systems must never:

* mutate runtime history
* bypass replay guarantees
* alter runtime authority automatically
* perform implicit repair

Audit and observability systems include:

* drift auditing
* corruption auditing
* health observability
* trace compatibility auditing
* dry-run readiness evaluation
* cutover readiness auditing

---

# Phase 3.7C Boundary Enforcement

Phase 3.7C adds static runtime boundary enforcement to prevent cross-layer coupling regressions.

Boundary model:

* `runtime.engine` coordinates execution modules:

  * `adapter_gateway`
  * `run_lifecycle`
  * `trace_pipeline`
  * `event_ledger`

* `runtime.event_ledger` and `runtime.trace_pipeline` are persistence/validation layers and must not import replay/eval/registry or control-plane orchestration systems.

* `runtime.replay`, `runtime.evals`, and `runtime.registry` are derived readers and must not import execution orchestration systems.

* `runtime.datasets` is classified as a projection writer and must not import execution orchestration modules.

* control-plane modules must not import `runtime.engine`.

Audit commands:

```bash
python3 scripts/maintenance/runtime_boundary_audit.py
```

```bash
python3 scripts/maintenance/runtime_boundary_audit.py --json
```

```bash
python3 scripts/maintenance/runtime_boundary_audit.py --strict
```

Strict mode is enforcement-only for CI/staging and performs no runtime mutation or behavior cutover.

---

# Phase 3.7G Trace Compatibility Categories

Trace dependency inventory is tracked with deterministic classifications.

## Compatibility Categories

### compatibility_only

Temporary compatibility references required for dual-source runtime operation.

### cutover_blocker

True trace-only runtime dependencies that would block future default-ledger cutover.

### legacy_runtime_dependency

Legacy runtime modules with direct trace coupling retained temporarily for compatibility.

### test_only

Trace references limited to runtime or control-plane test coverage.

### documentation_only

Documentation/examples mentioning trace compatibility behavior.

### operational_tooling

Maintenance/audit scripts intentionally operating on trace artifacts.

---

## Audit Commands

Summary:

```bash
python3 scripts/maintenance/trace_compatibility_audit.py --summary
```

Structured JSON:

```bash
python3 scripts/maintenance/trace_compatibility_audit.py --json
```

Strict cutover-blocker gate:

```bash
python3 scripts/maintenance/trace_compatibility_audit.py --strict
```

---

# Phase 3.7H Blocker Semantics

`cutover_blocker` means only:

```text
a true runtime trace-only dependency that would break future trace retirement or ledger-default cutover
```

The following are NOT blockers:

* replay/eval/registry dual-source compatibility paths
* parity/drift/corruption/health audit helpers
* tests/docs/tooling references
* compatibility scaffolding
* operational observability systems
* legacy-tracked runtime dependencies:

  * `runtime.loader`
  * `runtime.run`

Audit output includes deterministic:

* `reason`
* `resolution_hint`

for each blocker entry.

---

# Phase 3.7I Dry-Run Readiness Layer

An observational dry-run layer evaluates whether ledger-default mode would be safe without changing runtime authority.

Helper:

```text
runtime.event_ledger.evaluate_ledger_default_readiness(...)
```

CLI:

```bash
python3 scripts/maintenance/ledger_default_dry_run.py
```

Dry-run readiness aggregates:

* parity validation
* drift detection
* corruption auditing
* ledger health
* trace compatibility readiness
* cutover readiness
* replay/eval/registry ledger readiness

Dry-run mode is intentionally:

* observational-only
* warning-oriented
* non-authoritative
* replay-safe
* compatibility-preserving

Dry-run mode does NOT:

* switch replay/eval/registry defaults
* change runtime authority
* mutate runtime artifacts
* remove trace compatibility

unless authoritative mode is explicitly enabled separately.

---

## Phase 3.8A Canary Layer

Canary helpers are layered as operational wrappers around existing replay/eval/registry source-selection behavior.

- canary flag enables ledger-default behavior in derived readers
- explicit trace source overrides continue to bypass canary defaults
- trace/ledger artifact emission boundaries remain unchanged
- canary readiness is observational aggregation (health/drift/corruption/compatibility)

---

## Phase 3.8B Canonical Event Loader Layer

`runtime/event_loader.py` is the canonical projection loader used by replay/eval/registry source-aware reads.

Layering intent:

- `event_loader` depends on trace and ledger read paths
- replay/eval/registry depend on `event_loader` for source resolution and dispatch
- source default behavior remains trace-first unless authoritative/canary flags are enabled
- explicit trace overrides remain supported

This layer reduces duplicated source-selection logic and preserves compatibility behavior.

---

# Future Cutover Model

The runtime currently operates in compatibility mode.

Current behavior:

* `trace.jsonl` remains emitted
* EventLedger remains additive
* replay/eval/registry support dual-source operation
* authoritative mode remains opt-in
* dry-run readiness remains observational-only

Future cutover phases may:

* enable ledger-authoritative defaults
* reduce operational trace dependence
* preserve replay compatibility guarantees
* retain audit and observability safety checks

---

# CI Boundary Enforcement Expectations

Boundary audits are considered CI-critical runtime safety checks.

New runtime modules must preserve:

* dependency direction
* execution/derived separation
* replay-safe boundaries
* compatibility-safe migration behavior
* deterministic audit behavior

Boundary regressions must fail CI validation.

---

# Runtime Architectural Guarantees

The runtime architecture guarantees:

* deterministic replay
* append-only runtime history
* one-way dependency flow
* replay-safe persistence
* additive migration safety
* compatibility-preserving evolution
* audit-safe operational observability
* deterministic reconstruction
* schema-validated runtime behavior

The runtime is intentionally designed as:

```text
event-sourced deterministic execution infrastructure
```

—not merely a command wrapper or orchestration shell.
