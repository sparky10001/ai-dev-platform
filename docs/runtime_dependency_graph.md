# Runtime Dependency Graph (Phase 3.5 Step 5)

This file records the runtime dependency boundary audit after extraction Steps 1 through 4.

## Allowed Direction

engine.py may coordinate lifecycle, adapter gateway, and trace pipeline modules.
Lower-level runtime modules should flow toward contracts, validator, and schemas layers.

## Verified Boundaries

- runtime.engine imports run_lifecycle, adapter_gateway, trace_pipeline, validator, and schemas.
- runtime.adapter_gateway imports stdlib plus runtime.validator only.
- runtime.run_lifecycle imports runtime.events, runtime.run, and runtime.validator only.
- runtime.trace_pipeline imports stdlib plus runtime.errors and runtime.validator only.
- runtime.replay imports runtime.trace_pipeline one-way.
- runtime.registry, runtime.datasets, and runtime.evals do not import runtime.engine.

## Forbidden Imports

- runtime.adapter_gateway must not import runtime.engine, runtime.run_lifecycle, or runtime.trace_pipeline.
- runtime.run_lifecycle must not import runtime.engine, runtime.adapter_gateway, runtime.replay, runtime.datasets, or runtime.evals.
- runtime.trace_pipeline must not import runtime.engine, runtime.adapter_gateway, runtime.run_lifecycle, runtime.replay, runtime.datasets, or runtime.evals.
- runtime.registry, runtime.datasets, and runtime.evals must not import runtime.engine.

## Step 6 and Step 7 Notes

Keep engine as a coordinator only, and keep dependency direction one-way into contracts and validation layers to avoid circular-import regressions.

## Phase 3.7C Boundary Enforcement

Phase 3.7C adds static runtime boundary enforcement to prevent cross-layer coupling regressions.

Boundary model:

- `runtime/engine.py` coordinates execution modules (`adapter_gateway`, `run_lifecycle`, `trace_pipeline`, `event_ledger`).
- `runtime/event_ledger.py` and `runtime/trace_pipeline.py` are persistence/validation layers and must not import replay/eval/registry or control-plane modules.
- `runtime/replay.py`, `runtime/evals.py`, `runtime/registry.py` are derived readers and must not import engine/adapter/lifecycle execution modules.
- `runtime/datasets.py` is a projection writer and must not import engine/adapter/lifecycle modules.
- control-plane must not import `runtime.engine`.

Audit command:

- `python3 scripts/maintenance/runtime_boundary_audit.py`
- `python3 scripts/maintenance/runtime_boundary_audit.py --json`
- `python3 scripts/maintenance/runtime_boundary_audit.py --strict`

Strict mode is enforcement-only for CI/staging and performs no runtime mutation or behavior cutover.

## Phase 3.7G Trace Compatibility Categories

Trace dependency inventory is now tracked with deterministic classifications:

- `compatibility_only`: temporary compatibility references for dual-source runtime operation
- `cutover_blocker`: trace assumptions that block default-ledger cutover
- `legacy_runtime_dependency`: legacy runtime modules with direct trace coupling
- `test_only`: trace usage limited to test coverage
- `documentation_only`: docs/examples mentioning trace compatibility
- `operational_tooling`: maintenance/audit scripts using trace intentionally

Audit command:

- `python3 scripts/maintenance/trace_compatibility_audit.py --summary`

Strict command (cutover-blocker gate only):

- `python3 scripts/maintenance/trace_compatibility_audit.py --strict`

## Phase 3.7H Blocker Semantics

`cutover_blocker` now means only a true runtime trace-only dependency that would break future trace retirement/cutover.

Not blockers:

- replay/eval/registry dual-source compatibility paths
- parity/drift/corruption/health audit helpers
- tests/docs/operational tooling references
- legacy-tracked runtime dependencies (`runtime/loader.py`, `runtime/run.py`)

Audit output includes `resolution_hint` for each blocker to keep mitigation steps deterministic and minimal.
