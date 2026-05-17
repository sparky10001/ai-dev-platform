# Runtime EventLedger (Phase 3.6C)

Phase 3.6B extends the additive EventLedger with deterministic hashing, index generation, and parity validation.

## Authoritative Source

- `trace.jsonl` remains the authoritative runtime event source of truth.
- `ledger.jsonl` remains an additive mirror only.
- Default replay behavior, evals, and registry behavior remain unchanged.

## Phase 3.6B Scope

- Deterministic event canonicalization via `canonical_event_payload(...)`.
- Deterministic event hashing via `event_hash(...)`.
- Per-event index records via `ledger_event_record(...)`.
- `ledger.index.json` sidecar generation and loading.
- Trace/Ledger parity validation via `validate_trace_ledger_parity(..., strict=False)`.
- Hardened strict ledger validation in `validate_ledger_file(..., strict=True)`.

## ledger.index.json Sidecar

`ledger.index.json` is generated from `ledger.jsonl` and includes:

- `schema_version`
- `run_id`
- `event_count`
- `ledger_hash`
- deterministic `events` entries (`index`, `event_hash`, canonical `event`)

The sidecar is deterministic and reproducible from the same ledger input.

## Deterministic Event Hashing

Event hashing is based on canonical payload fields:

- `schema_version`
- `run_id`
- `event`
- `timestamp`
- `data`

Equivalent event content yields identical hashes regardless of dict key ordering.

## Trace/Ledger Parity Validation

`validate_trace_ledger_parity(...)` compares `trace.jsonl` and `ledger.jsonl` for:

- event count parity
- event sequence parity
- event hash sequence parity

Default mode returns a structured report. `strict=True` raises `EventLedgerError` on mismatch.

## Strict Ledger Validation

In strict mode, `validate_ledger_file(...)` rejects:

- empty ledgers
- mixed `run_id`
- mixed `schema_version`
- timestamp regression
- events that cannot be canonicalized/hashed

## Compatibility

- No response contract changes.
- No NDJSON trace format changes.
- `trace.jsonl` remains source of truth.
- `ledger.jsonl` remains additive mirror only.
- Default replay behavior remains trace-based; eval/registry layers remain unchanged.

## Phase 3.6C Replay Flag

Phase 3.6C adds optional replay-from-ledger behind a flag.

- Default replay source remains `trace.jsonl`.
- Set `RUNTIME_REPLAY_SOURCE=ledger` (or pass `source="ledger"`) to replay from `ledger.jsonl`.
- Ledger replay is opt-in and non-authoritative.
- Missing `ledger.jsonl` in ledger mode fails deterministically; no implicit fallback is performed.
- `evals.py` and `registry.py` remain trace-based in this phase.

## Migration Path

- 3.6D: eval-from-ledger behind feature flag
- 3.6E: registry-from-ledger behind feature flag
- 3.6F: ledger-authoritative cutover
