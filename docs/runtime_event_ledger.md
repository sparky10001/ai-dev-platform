# Runtime EventLedger (Phase 3.6A)

Phase 3.6A introduces an additive EventLedger stream.

## Current State

- trace.jsonl remains the authoritative runtime event source.
- ledger.jsonl is a dual-written mirror stored per run directory.
- Replay, evals, and registry continue to read existing sources.

## Phase 3.6A Scope

- Add runtime/event_ledger.py.
- Dual-write validated runtime events to ledger.jsonl.
- Keep runtime behavior and response contracts unchanged.

## Strictness

- Default: ledger failures are non-fatal to preserve compatibility.
- RUNTIME_LEDGER_STRICT=1: ledger write failures raise typed errors.

## Migration Path

- 3.6B: validation and checksum guards
- 3.6C: replay-from-ledger behind feature flag
- 3.6D: eval-from-ledger behind feature flag
- 3.6E: registry-from-ledger behind feature flag
- 3.6F: ledger-authoritative cutover
