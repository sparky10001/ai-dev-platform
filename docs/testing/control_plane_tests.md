# Control-Plane Tests

The control-plane test suite validates orchestration, planning, policy enforcement, DAG execution, replay introspection, adaptive strategy selection, orchestration analytics, and higher-level runtime coordination.

Unlike the runtime layer, which guarantees deterministic execution infrastructure, the control-plane validates:

* orchestration correctness
* DAG planning and execution behavior
* policy enforcement
* strategy selection
* replay introspection
* orchestration analytics
* memory and lineage systems
* multi-run experimentation
* adaptive orchestration heuristics

The control-plane is intentionally layered above the runtime and must preserve runtime replay and contract guarantees.

---

# Relationship to Runtime

The runtime is responsible for:

* deterministic execution
* append-only persistence
* replay guarantees
* contract validation
* lifecycle correctness

The control-plane is responsible for:

* orchestration
* planning
* DAG coordination
* experimentation
* policy enforcement
* orchestration analytics

Control-plane systems must never bypass runtime guarantees.

---

# Validation Scope

Control-plane tests are intentionally additive and are not part of the minimal runtime validation ladder:

```bash id="vyl10l"
make validate
```

This separation exists because:

* runtime validation protects deterministic infrastructure guarantees
* control-plane validation protects orchestration behavior
* runtime validation must remain lightweight and universally runnable
* control-plane validation may involve broader orchestration flows, datasets, heuristics, and experimental execution paths

Primary control-plane validation command:

```bash id="imj9gr"
make control-plane-tests
```

---

# Control-Plane Guarantees

The control-plane guarantees:

* deterministic DAG execution ordering
* replay-safe orchestration
* policy-aware execution
* orchestration traceability
* strategy isolation
* experiment reproducibility
* orchestration lineage visibility
* runtime contract preservation

---

# Testing Philosophy

Control-plane tests validate orchestration correctness while preserving:

* runtime replay guarantees
* runtime contract guarantees
* deterministic orchestration behavior
* isolation between orchestration runs
* compatibility-safe runtime integration

The control-plane must remain layered above runtime infrastructure.

---

# Core DAG & Orchestration Suites

## DAG Validation

Suite:

```text id="n6ix1z"
scripts/tests/control_plane_dag_tests.sh
```

Validates:

* DAG schema correctness
* node dependency validation
* cycle detection
* DAG metadata integrity
* deterministic DAG parsing

---

## Tool Registry

Suite:

```text id="pjlwmr"
scripts/tests/control_plane_tool_registry_tests.sh
```

Validates:

* tool registration
* tool lookup correctness
* tool metadata consistency
* registry determinism
* runtime compatibility guarantees

---

## DAG Executor

Suite:

```text id="0b6bci"
scripts/tests/control_plane_dag_executor_tests.sh
```

Validates:

* deterministic DAG execution ordering
* dependency resolution
* tool execution orchestration
* execution result propagation
* runtime-safe orchestration behavior

---

## Planner

Suite:

```text id="3zjpj0"
scripts/tests/control_plane_planner_tests.sh
```

Validates:

* deterministic task planning
* orchestration decomposition
* plan generation correctness
* DAG construction consistency

---

## Orchestrator

Suite:

```text id="1z6r3s"
scripts/tests/control_plane_orchestrator_tests.sh
```

Validates:

* end-to-end orchestration behavior
* planner/executor coordination
* orchestration lifecycle integrity
* replay-safe orchestration execution

---

## CLI

Suite:

```text id="9nk7a4"
scripts/tests/control_plane_cli_tests.sh
```

Validates:

* CLI orchestration entrypoints
* orchestration command behavior
* replay-safe CLI integration
* deterministic CLI response handling

---

# Replay & Introspection Suites

## Trace Bridge

Suite:

```text id="7l6q1r"
scripts/tests/control_plane_trace_bridge_tests.sh
```

Validates:

* runtime/control-plane trace interoperability
* orchestration replay visibility
* trace-safe orchestration integration

---

## Replay & Introspection

Suite:

```text id="1kq0dr"
scripts/tests/control_plane_replay_tests.sh
```

Validates:

* orchestration replay loading
* replay introspection correctness
* orchestration replay determinism
* runtime replay compatibility

---

## Eval & Comparison

Suite:

```text id="xyx3gf"
scripts/tests/control_plane_eval_tests.sh
```

Validates:

* orchestration evaluation correctness
* replay comparison behavior
* orchestration scoring consistency
* experiment comparison safety

---

## Experiments & Datasets

Suite:

```text id="8e8r14"
scripts/tests/control_plane_experiment_tests.sh
```

Validates:

* orchestration experiment execution
* dataset generation
* deterministic experiment tracking
* experiment reproducibility

---

# Adaptive Orchestration Suites

## Benchmarks

Suite:

```text id="4o3nlu"
scripts/tests/control_plane_benchmark_tests.sh
```

Validates:

* orchestration benchmarking
* deterministic benchmark execution
* runtime-safe benchmark flows

---

## Multi-Strategy

Suite:

```text id="0v84g7"
scripts/tests/control_plane_strategy_tests.sh
```

Validates:

* strategy selection
* orchestration isolation
* multi-strategy coordination
* deterministic strategy execution

---

## Adaptive Heuristics

Suite:

```text id="5r1k0z"
scripts/tests/control_plane_heuristic_tests.sh
```

Validates:

* heuristic selection behavior
* adaptive orchestration correctness
* deterministic heuristic evaluation

---

## Parallel DAG Execution

Suite:

```text id="e4s56j"
scripts/tests/control_plane_parallel_executor_tests.sh
```

Validates:

* parallel DAG execution safety
* deterministic dependency coordination
* orchestration concurrency guarantees
* replay-safe parallel execution

---

# Memory & Knowledge Suites

## Memory & History

Suite:

```text id="8h0uw7"
scripts/tests/control_plane_memory_tests.sh
```

Validates:

* orchestration memory behavior
* historical orchestration retrieval
* replay-safe memory integration
* orchestration continuity guarantees

---

## Knowledge & Lineage

Suite:

```text id="e6rjv2"
scripts/tests/control_plane_knowledge_tests.sh
```

Validates:

* orchestration lineage tracking
* knowledge graph integration
* replay-safe orchestration lineage
* orchestration provenance visibility

---

## Orchestration Graph Analytics

Suite:

```text id="f6mp44"
scripts/tests/control_plane_graph_analytics_tests.sh
```

Validates:

* orchestration graph analysis
* orchestration dependency visibility
* lineage graph correctness
* orchestration analytics determinism

---

# Scenario & Policy Suites

## Scenario Tests

Suite:

```text id="4jx0fr"
scripts/tests/control_plane_scenario_tests.sh
```

Validates:

* orchestration scenario execution
* runtime/control-plane integration behavior
* deterministic orchestration flows
* scenario replay safety

---

## Policy Layer

Suite:

```text id="1v0cfk"
scripts/tests/control_plane_policy_tests.sh
```

Validates:

* policy-aware orchestration
* orchestration restriction enforcement
* deterministic policy application
* runtime-safe policy coordination

---

# Runtime Event Bridge

Control-plane replay/introspection now consumes canonical runtime events via `control-plane/core/runtime_events.py`.

Bridge APIs:

* `control_plane_runtime_event_source(source=None, default="trace")`
* `load_control_plane_runtime_events(run_or_path, source=None, strict=False)`
* `iter_control_plane_runtime_events(run_or_path, source=None, strict=False)`

Behavior guarantees:

* trace-first default remains unchanged
* explicit `source="trace"` remains supported
* ledger/canary/authoritative source selection is supported through `runtime.event_loader`
* control-plane CLI outputs and schema behavior remain unchanged
* control-plane remains forbidden from importing `runtime.engine`

Validation suite:

```bash
./scripts/tests/control_plane_runtime_event_bridge_tests.sh
```

---

# Operational Expectations

Control-plane systems must:

* preserve runtime replay safety
* avoid bypassing runtime validation
* remain compatible with EventLedger migration
* preserve orchestration traceability
* maintain deterministic orchestration behavior

The control-plane must remain compatibility-safe with:

* runtime replay guarantees
* EventLedger migration phases
* runtime contract validation
* audit and observability systems

---

# Runtime Integration Constraints

Control-plane systems must not:

* mutate runtime history directly
* bypass runtime validation layers
* import forbidden runtime execution layers
* violate runtime dependency boundaries
* bypass EventLedger parity guarantees

Runtime remains the authoritative execution substrate.

The control-plane remains an orchestration and coordination layer only.

---

# Future Expansion

Future control-plane phases may expand:

* orchestration analytics
* adaptive planning
* experiment coordination
* lineage tracking
* multi-agent orchestration
* policy-aware execution routing

while preserving:

* runtime determinism
* replay guarantees
* contract validation
* compatibility-safe orchestration behavior

---

# Architectural Summary

The architecture intentionally separates:

```text id="v1h93t"
runtime = deterministic execution substrate
control-plane = orchestration and coordination layer
```

This separation preserves:

* replay safety
* deterministic runtime guarantees
* orchestration flexibility
* migration safety
* compatibility-safe evolution
* operational observability
