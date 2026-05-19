# Runtime EventLedger

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


## Phase 3.6D Eval Flag

Phase 3.6D adds optional eval-from-ledger behind a flag.

- Default evaluation source remains trace-based.
- Set `RUNTIME_EVAL_SOURCE=ledger` (or pass `source="ledger"`) to evaluate from `ledger.jsonl`.
- Replay and eval now both support optional ledger mode.
- Registry remains trace-based in this phase.
- Ledger remains non-authoritative and additive.


## Phase 3.6E Registry Flag

Phase 3.6E adds optional registry-from-ledger behind a flag.

- Default registry source remains trace-based.
- Set `RUNTIME_REGISTRY_SOURCE=ledger` (or pass `source="ledger"`) to use ledger-backed registry summaries.
- Replay and eval already support optional ledger mode.
- Registry now optionally supports ledger mode.
- Ledger remains non-authoritative and additive.


## Phase 3.6F Authoritative Mode

Phase 3.6F adds opt-in ledger-authoritative mode behind feature flags.

- Enable with `RUNTIME_LEDGER_AUTHORITATIVE=1`.
- In authoritative mode, replay/eval/registry default sources become ledger.
- Explicit `source="trace"` overrides still force trace behavior.
- Trace artifacts are still emitted for compatibility.
- Optional parity enforcement via `RUNTIME_LEDGER_PARITY_REQUIRED=1`.
- With parity required, trace/ledger mismatch raises `EventLedgerError`.

Ledger remains non-authoritative unless this mode is explicitly enabled.

## Migration Path

- 3.6F: ledger-authoritative cutover (implemented behind flag)


## Phase 3.6G Cutover Readiness

Phase 3.6G focuses on cutover readiness auditing, migration clarity, and operational hardening.

Current readiness state:

- replay is ledger-capable and authoritative-mode aware
- eval is ledger-capable and authoritative-mode aware
- registry is ledger-capable and authoritative-mode aware
- trace artifacts remain emitted for compatibility
- parity enforcement is optional and gated

Authoritative operation flags:

- `RUNTIME_LEDGER_AUTHORITATIVE=1`
- `RUNTIME_LEDGER_PARITY_REQUIRED=1`

Migration matrix:

| Component           | Ledger Ready | Default Source          | Authoritative Support |
|---------------------|--------------|-------------------------|-----------------------|
| replay              | yes          | trace                   | yes                   |
| eval                | yes          | trace                   | yes                   |
| registry            | yes          | trace                   | yes                   |
| trace compatibility | required     | trace artifacts emitted | retained              |
| parity enforcement  | yes          | off                     | optional strict       |
| ledger index        | yes          | additive sidecar        | available             |

Operational guidance:

- Keep default mode trace-first unless explicit operational cutover is required.
- Enable authoritative mode first in controlled environments.
- Enable parity enforcement after baseline parity confidence is established.
- Treat parity failures as hard blockers for authoritative operation.

Cutover checklist:

1. Validate dual-write parity across representative runs.
2. Run readiness audit helpers on recent runs.
3. Enable `RUNTIME_LEDGER_AUTHORITATIVE=1` in staging.
4. Optionally enable `RUNTIME_LEDGER_PARITY_REQUIRED=1`.
5. Validate replay/eval/registry equivalence and rollback readiness.

Rollback strategy:

- unset `RUNTIME_LEDGER_AUTHORITATIVE`
- unset `RUNTIME_LEDGER_PARITY_REQUIRED`
- continue with trace-first defaults using unchanged artifacts

Operational risks and remaining assumptions:

- some scripts/docs still reference `trace.jsonl` as compatibility anchor
- authoritative mode depends on dual-write parity and ledger presence
- compatibility tooling still expects trace artifact emission

Recovery expectations:

- ledger and trace both remain available for replay-safe recovery
- parity checks can identify divergence early
- rollback to trace-first mode is immediate via env flags

## Phase 3.7A Drift Detection

Phase 3.7A adds observational ledger/trace drift auditing and enforcement tooling without changing runtime behavior.

- Drift audit API: `runtime/ledger_drift.py`
- Operator CLI: `python3 scripts/maintenance/ledger_drift_audit.py --latest`
- Strict no-drift helper: `validate_no_drift(...)`

Drift categories:

- `missing_trace`
- `missing_ledger`
- `event_count_mismatch`
- `event_sequence_mismatch`
- `event_hash_mismatch`
- `lifecycle_mismatch`
- `replay_summary_mismatch`
- `eval_summary_mismatch`
- `registry_summary_mismatch`
- `parse_error`

Operational semantics:

- observational only; no automatic repair or mutation
- default runtime behavior remains unchanged
- strict mode can fail fast for CI/staging enforcement
- recommended before cutover: run `--all --strict` and resolve any drift categories

## Phase 3.7B Derived-System Purity Audit

Phase 3.7B adds static purity guardrails to verify derived systems are read-only projections over runtime artifacts.

Purity expectations:

- `runtime/replay.py` is projection-only.
- `runtime/evals.py` is replay-derived projection-only.
- `runtime/registry.py` is filesystem query projection-only.
- `runtime/ledger_drift.py` is observational audit-only.

`runtime/datasets.py` classification:

- classified as `projection_writer`.
- allowed to write export outputs.
- not allowed to write runtime source artifacts (`trace.jsonl`, `ledger.jsonl`, `run.json`, `result.json`).

Audit commands:

- `python3 scripts/maintenance/derived_purity_audit.py`
- `python3 scripts/maintenance/derived_purity_audit.py --json`
- `python3 scripts/maintenance/derived_purity_audit.py --strict`

Strict mode:

- exits nonzero when purity violations are detected.
- intended for CI/staging guardrails.
- observational only; no auto-repair or behavior cutover.

## Phase 3.7C Runtime Boundary Enforcement

Phase 3.7C adds import-boundary guardrails that protect runtime layering around trace/ledger persistence and derived readers.

Key enforcement points:

- execution modules remain coordinator-directed (`engine` -> gateway/lifecycle/trace/ledger)
- derived modules (`replay`, `evals`, `registry`) remain read-side projections
- ledger/trace layers are protected from replay/eval/registry/control-plane coupling
- control-plane importing `runtime.engine` is treated as a boundary violation

Tooling:

- `python3 scripts/maintenance/runtime_boundary_audit.py`
- strict mode: `python3 scripts/maintenance/runtime_boundary_audit.py --strict`

This is observational guardrail enforcement only and does not modify runtime behavior.

## Phase 3.7D Ledger Corruption & Recovery Validation

Phase 3.7D adds deterministic corruption classification and recovery-readiness auditing for ledger artifacts before authority cutover.

Corruption categories:

- `missing_ledger`
- `missing_trace`
- `malformed_ndjson`
- `empty_ledger`
- `mixed_run_id`
- `mixed_schema_version`
- `timestamp_regression`
- `duplicate_lifecycle_event`
- `missing_lifecycle_event`
- `event_after_session_end`
- `parity_mismatch`
- `index_mismatch`
- `replay_failure`
- `eval_failure`
- `registry_failure`

Audit commands:

- `python3 scripts/maintenance/ledger_corruption_audit.py --latest`
- `python3 scripts/maintenance/ledger_corruption_audit.py --latest --json`
- `python3 scripts/maintenance/ledger_corruption_audit.py --latest --strict`

Operational guidance:

- corruption audit is observational only
- no automatic repair or mutation is performed
- trace fallback remains available for compatibility and recovery
- strict mode is intended for pre-cutover and CI enforcement

## Phase 3.7E Operational Observability

Phase 3.7E adds operator-facing ledger health reporting without changing runtime behavior.

Health coverage includes:

- parity visibility (`parity_ok`)
- drift visibility (from `runtime/ledger_drift.py`)
- corruption visibility (from `runtime/ledger_corruption.py`)
- replay/eval/registry ledger-read health checks
- maintenance stamp visibility (`AI_MAINTENANCE_*`)
- cutover-readiness integration (`ledger_cutover_readiness`)

Health status semantics:

- `healthy`: parity/corruption/replay-eval-registry checks pass
- `warning`: missing ledger/index, maintenance disabled/stale, cutover not ready, or drift with trace fallback intact
- `unhealthy`: corruption, parity failure, strict validation failure, replay/eval/registry ledger failures, or required trace missing

CLI usage:

- `python3 scripts/maintenance/ledger_health_report.py --latest`
- `python3 scripts/maintenance/ledger_health_report.py --summary`
- `python3 scripts/maintenance/ledger_health_report.py --latest --json`
- `python3 scripts/maintenance/ledger_health_report.py --latest --strict`

Operational notes:

- observability is read-only and does not mutate artifacts
- no auto-repair behavior is introduced
- default trace compatibility and default-authority behavior remain unchanged

## Phase 3.7G Trace Compatibility Audit

Phase 3.7G adds deterministic inventory and classification for remaining `trace.jsonl` dependencies.

Categories:

- `compatibility_only`
- `cutover_blocker`
- `legacy_runtime_dependency`
- `test_only`
- `documentation_only`
- `operational_tooling`

CLI:

- `python3 scripts/maintenance/trace_compatibility_audit.py`
- `python3 scripts/maintenance/trace_compatibility_audit.py --summary`
- `python3 scripts/maintenance/trace_compatibility_audit.py --json`
- `python3 scripts/maintenance/trace_compatibility_audit.py --strict`

Strict mode exits nonzero only when `cutover_blocker` dependencies are present.

This audit is observational-only and does not modify runtime behavior, schemas, or artifacts.

## Phase 3.7H Trace Cutover Blocker Resolution

Phase 3.7H refines trace compatibility blocker semantics to reduce false positives.

Cutover blocker definition (strict):

- only dependencies that would fail operationally if trace were retired/default-ledger cutover were attempted
- compatibility scaffolding, migration helpers, and dual-source readers are not blockers

Reporting improvements:

- audit output now includes `cutover_blockers` with:
  - `path`
  - `reason`
  - `resolution_hint`

Operational interpretation:

- `compatibility_only` references are allowed during migration
- `legacy_runtime_dependency` references are tracked but do not fail strict blocker gates
- strict mode fails only on true `cutover_blocker` items
