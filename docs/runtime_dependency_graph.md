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
