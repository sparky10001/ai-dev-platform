# Runtime EventLedger

The EventLedger system provides deterministic additive runtime event indexing, parity validation, migration readiness, and future ledger-authoritative support. 

The runtime currently operates in compatibility mode:

* `trace.jsonl` remains canonical
* `ledger.jsonl` remains additive
* replay/eval/registry support dual-source operation
* authoritative mode remains opt-in
* operational audits remain observational-only

EventLedger migration prioritizes:

* replay safety
* deterministic parity
* compatibility preservation
* audit-first cutover validation
* rollback safety

---

# Migration Model

The EventLedger migration proceeds through:

1. additive dual-write
2. deterministic parity validation
3. replay/eval/registry dual-source support
4. authoritative-mode opt-in
5. operational observability
6. cutover-readiness auditing
7. dry-run authority simulation
8. future controlled cutover

At every phase:

* trace compatibility is preserved
* replay guarantees remain authoritative
* rollback remains immediate

---

# Operational Safety Guarantees

EventLedger tooling must never:

* mutate runtime history implicitly
* bypass replay validation
* invalidate trace compatibility automatically
* perform automatic repair
* force authority changes

Operational audits are intentionally:

* read-only
* deterministic
* observational-first
* compatibility-preserving

---

# Current Runtime State

Current default runtime behavior:

* `trace.jsonl` remains canonical
* `ledger.jsonl` remains additive
* replay defaults to trace
* eval defaults to trace
* registry defaults to trace
* authoritative mode is opt-in
* dry-run mode is observational-only
* parity enforcement is optional

---

# Authoritative Source

* `trace.jsonl` remains the authoritative runtime event source of truth.
* `ledger.jsonl` remains an additive mirror only.
* Default replay behavior, evals, and registry behavior remain unchanged.

---

# Authoritative Mode

Authoritative mode means:

* replay/eval/registry default to ledger
* ledger parity may become enforcement-critical
* ledger readiness becomes operationally significant
* trace compatibility remains available unless explicitly retired later

Authoritative mode does NOT:

* remove trace artifacts
* disable replay fallback
* bypass parity validation
* mutate historical runtime artifacts

---

# Phase 3.6B Scope

Phase 3.6B extends the additive EventLedger with deterministic hashing, index generation, and parity validation.

Implemented capabilities:

* deterministic event canonicalization via `canonical_event_payload(...)`
* deterministic event hashing via `event_hash(...)`
* per-event index records via `ledger_event_record(...)`
* `ledger.index.json` sidecar generation and loading
* trace/ledger parity validation via `validate_trace_ledger_parity(..., strict=False)`
* hardened strict ledger validation in `validate_ledger_file(..., strict=True)`

---

# ledger.index.json Sidecar

`ledger.index.json` is generated from `ledger.jsonl` and includes:

* `schema_version`
* `run_id`
* `event_count`
* `ledger_hash`
* deterministic `events` entries:

  * `index`
  * `event_hash`
  * canonical `event`

The sidecar is deterministic and reproducible from identical ledger input.

---

# Deterministic Event Hashing

Event hashing is based on canonical payload fields:

* `schema_version`
* `run_id`
* `event`
* `timestamp`
* `data`

Equivalent event content yields identical hashes regardless of dict key ordering.

---

# Trace/Ledger Parity Validation

`validate_trace_ledger_parity(...)` compares `trace.jsonl` and `ledger.jsonl` for:

* event count parity
* event sequence parity
* event hash sequence parity

Default mode returns a structured report.

`strict=True` raises `EventLedgerError` on mismatch.

---

# Strict Ledger Validation

In strict mode, `validate_ledger_file(...)` rejects:

* empty ledgers
* mixed `run_id`
* mixed `schema_version`
* timestamp regression
* events that cannot be canonicalized or hashed

---

# Compatibility Guarantees

* No response contract changes.
* No NDJSON trace format changes.
* `trace.jsonl` remains source of truth.
* `ledger.jsonl` remains additive mirror only.
* Default replay behavior remains trace-based.
* Eval and registry behavior remain compatibility-preserving.

---

# Phase 3.6C Replay Flag

Phase 3.6C adds optional replay-from-ledger behind a flag.

* default replay source remains `trace.jsonl`
* set `RUNTIME_REPLAY_SOURCE=ledger` or pass `source="ledger"` to replay from `ledger.jsonl`
* ledger replay is opt-in and non-authoritative
* missing `ledger.jsonl` in ledger mode fails deterministically
* no implicit fallback is performed
* evals and registry remain trace-based in this phase

---

# Phase 3.6D Eval Flag

Phase 3.6D adds optional eval-from-ledger behind a flag.

* default evaluation source remains trace-based
* set `RUNTIME_EVAL_SOURCE=ledger` or pass `source="ledger"` to evaluate from `ledger.jsonl`
* replay and eval now support optional ledger mode
* registry remains trace-based in this phase
* ledger remains additive and non-authoritative

---

# Phase 3.6E Registry Flag

Phase 3.6E adds optional registry-from-ledger behind a flag.

* default registry source remains trace-based
* set `RUNTIME_REGISTRY_SOURCE=ledger` or pass `source="ledger"` to use ledger-backed registry summaries
* replay and eval already support optional ledger mode
* registry now supports optional ledger mode
* ledger remains additive and non-authoritative

---

# Phase 3.6F Authoritative Mode

Phase 3.6F adds opt-in ledger-authoritative mode behind feature flags.

Enable via:

```text
RUNTIME_LEDGER_AUTHORITATIVE=1
```

In authoritative mode:

* replay/eval/registry default sources become ledger
* explicit `source="trace"` overrides still force trace behavior
* trace artifacts are still emitted for compatibility
* optional parity enforcement is available

Optional parity enforcement:

```text
RUNTIME_LEDGER_PARITY_REQUIRED=1
```

With parity required:

* trace/ledger mismatch raises `EventLedgerError`

Ledger remains non-authoritative unless authoritative mode is explicitly enabled.

---

# Migration Path

Migration phases:

* 3.6B deterministic additive ledger foundation
* 3.6C replay dual-source support
* 3.6D eval dual-source support
* 3.6E registry dual-source support
* 3.6F authoritative-mode opt-in
* 3.6G cutover readiness auditing
* 3.7A–3.7I operational hardening and observability

---

# Phase 3.6G Cutover Readiness

Phase 3.6G focuses on cutover readiness auditing, migration clarity, and operational hardening.

Current readiness state:

* replay is ledger-capable and authoritative-aware
* eval is ledger-capable and authoritative-aware
* registry is ledger-capable and authoritative-aware
* trace artifacts remain emitted for compatibility
* parity enforcement is optional and gated

Authoritative operation flags:

* `RUNTIME_LEDGER_AUTHORITATIVE=1`
* `RUNTIME_LEDGER_PARITY_REQUIRED=1`

---

## Migration Matrix

| Component           | Ledger Ready | Default Source   | Authoritative Support |
| ------------------- | ------------ | ---------------- | --------------------- |
| replay              | yes          | trace            | yes                   |
| eval                | yes          | trace            | yes                   |
| registry            | yes          | trace            | yes                   |
| trace compatibility | required     | trace emitted    | retained              |
| parity enforcement  | yes          | off              | optional strict       |
| ledger index        | yes          | additive sidecar | available             |

---

## Operational Guidance

* keep default mode trace-first unless explicit operational cutover is required
* enable authoritative mode first in controlled environments
* enable parity enforcement after parity confidence is established
* treat parity failures as hard blockers for authoritative operation

---

## Cutover Checklist

1. validate dual-write parity across representative runs
2. run readiness audit helpers on recent runs
3. enable `RUNTIME_LEDGER_AUTHORITATIVE=1` in staging
4. optionally enable `RUNTIME_LEDGER_PARITY_REQUIRED=1`
5. validate replay/eval/registry equivalence and rollback readiness

---

## Rollback Strategy

Rollback is immediate:

```bash
unset RUNTIME_LEDGER_AUTHORITATIVE
unset RUNTIME_LEDGER_PARITY_REQUIRED
```

Trace-first defaults continue using unchanged artifacts.

---

## Operational Risks and Assumptions

Remaining operational assumptions:

* some scripts/docs still reference `trace.jsonl` as compatibility anchor
* authoritative mode depends on parity confidence and ledger presence
* compatibility tooling still expects trace artifact emission

Recovery expectations:

* ledger and trace remain available for replay-safe recovery
* parity checks identify divergence early
* rollback to trace-first mode remains immediate

---

# Audit System Inventory

| Audit System             | Purpose                                |
| ------------------------ | -------------------------------------- |
| `ledger_drift`           | parity divergence detection            |
| `ledger_corruption`      | corruption classification              |
| `ledger_health`          | operational readiness visibility       |
| `trace_compatibility`    | cutover dependency inventory           |
| `derived_purity`         | replay-safe derived-system enforcement |
| `runtime_boundary`       | import-layer enforcement               |
| `ledger_default_dry_run` | simulated ledger-default readiness     |

---

# Phase 3.7A Drift Detection

Phase 3.7A adds observational ledger/trace drift auditing and enforcement tooling.

Drift categories:

* `missing_trace`
* `missing_ledger`
* `event_count_mismatch`
* `event_sequence_mismatch`
* `event_hash_mismatch`
* `lifecycle_mismatch`
* `replay_summary_mismatch`
* `eval_summary_mismatch`
* `registry_summary_mismatch`
* `parse_error`

Tooling:

* `runtime/ledger_drift.py`
* `python3 scripts/maintenance/ledger_drift_audit.py --latest`

Strict helper:

```text
validate_no_drift(...)
```

Operational semantics follow the standard observational safety model.

---

# Phase 3.7B Derived-System Purity Audit

Phase 3.7B adds static purity guardrails verifying that derived systems remain replay-safe projections.

Purity expectations:

* `runtime/replay.py` is projection-only
* `runtime/evals.py` is replay-derived projection-only
* `runtime/registry.py` is filesystem-query projection-only
* `runtime/ledger_drift.py` is observational-only

`runtime/datasets.py` classification:

* classified as `projection_writer`
* allowed to write export outputs
* forbidden from mutating runtime source artifacts

Audit commands:

* `python3 scripts/maintenance/derived_purity_audit.py`
* `python3 scripts/maintenance/derived_purity_audit.py --json`
* `python3 scripts/maintenance/derived_purity_audit.py --strict`

This audit follows the standard observational safety model.

---

# Phase 3.7C Runtime Boundary Enforcement

Phase 3.7C adds import-boundary guardrails protecting runtime layering around trace/ledger persistence and derived readers.

Key enforcement points:

* execution modules remain coordinator-directed
* derived modules remain read-side projections
* ledger/trace layers remain protected from replay/eval/registry coupling
* control-plane importing `runtime.engine` is treated as a boundary violation

Tooling:

* `python3 scripts/maintenance/runtime_boundary_audit.py`
* `python3 scripts/maintenance/runtime_boundary_audit.py --strict`

This audit follows the standard observational safety model.

---

# Phase 3.7D Ledger Corruption & Recovery Validation

Phase 3.7D adds deterministic corruption classification and recovery-readiness auditing.

Corruption categories:

* `missing_ledger`
* `missing_trace`
* `malformed_ndjson`
* `empty_ledger`
* `mixed_run_id`
* `mixed_schema_version`
* `timestamp_regression`
* `duplicate_lifecycle_event`
* `missing_lifecycle_event`
* `event_after_session_end`
* `parity_mismatch`
* `index_mismatch`
* `replay_failure`
* `eval_failure`
* `registry_failure`

Audit commands:

* `python3 scripts/maintenance/ledger_corruption_audit.py --latest`
* `python3 scripts/maintenance/ledger_corruption_audit.py --latest --json`
* `python3 scripts/maintenance/ledger_corruption_audit.py --latest --strict`

Operational guidance:

* trace fallback remains available for compatibility and recovery
* strict mode is intended for CI/staging enforcement
* no automatic repair is performed

This audit follows the standard observational safety model.

---

# Phase 3.7E Operational Observability

Phase 3.7E adds operator-facing ledger health reporting.

Health coverage includes:

* parity visibility
* drift visibility
* corruption visibility
* replay/eval/registry ledger-read health checks
* maintenance stamp visibility
* cutover-readiness integration

Health status semantics:

| Status      | Meaning                                                     |
| ----------- | ----------------------------------------------------------- |
| `healthy`   | parity/corruption/replay/eval/registry checks pass          |
| `warning`   | compatibility-safe issues exist with replay fallback intact |
| `unhealthy` | corruption/parity/strict runtime failures detected          |

CLI usage:

* `python3 scripts/maintenance/ledger_health_report.py --latest`
* `python3 scripts/maintenance/ledger_health_report.py --summary --recent 50`
* `python3 scripts/maintenance/ledger_health_report.py --latest --json`
* `python3 scripts/maintenance/ledger_health_report.py --latest --strict`

This observability layer follows the standard observational safety model.

---

# Phase 3.7G Trace Compatibility Audit

Phase 3.7G adds deterministic inventory and classification for remaining `trace.jsonl` dependencies.

Categories:

* `compatibility_only`
* `cutover_blocker`
* `legacy_runtime_dependency`
* `test_only`
* `documentation_only`
* `operational_tooling`

CLI:

* `python3 scripts/maintenance/trace_compatibility_audit.py`
* `python3 scripts/maintenance/trace_compatibility_audit.py --summary`
* `python3 scripts/maintenance/trace_compatibility_audit.py --json`
* `python3 scripts/maintenance/trace_compatibility_audit.py --strict`

Strict mode exits nonzero only when true `cutover_blocker` dependencies exist.

This audit follows the standard observational safety model.

---

# Phase 3.7H Trace Cutover Blocker Resolution

Phase 3.7H refines blocker semantics to reduce compatibility false positives.

`cutover_blocker` means only:

```text
a runtime dependency that would operationally fail if trace were retired or ledger-default cutover were attempted
```

Not blockers:

* compatibility scaffolding
* migration helpers
* replay/eval/registry dual-source readers
* audit systems
* docs/tests/tooling references
* legacy tracked runtime dependencies

Audit output includes:

* `path`
* `reason`
* `resolution_hint`

for deterministic remediation guidance.

---

# Phase 3.7I Ledger-Default Dry-Run Mode

Phase 3.7I adds observational ledger-default readiness simulation.

Enable signaling:

```text
RUNTIME_LEDGER_DRY_RUN_DEFAULT=1
```

Dry-run readiness aggregates:

* parity state
* drift state
* corruption state
* replay/eval/registry readiness
* cutover blocker inventory
* compatibility warnings
* maintenance warnings

Dry-run categories:

* `drift_detected`
* `corruption_detected`
* `parity_failure`
* `replay_not_ready`
* `eval_not_ready`
* `registry_not_ready`
* `trace_blockers_present`
* `compatibility_warning`
* `maintenance_warning`

CLI:

* `python3 scripts/maintenance/ledger_default_dry_run.py --latest`
* `python3 scripts/maintenance/ledger_default_dry_run.py --summary --recent 50`
* `python3 scripts/maintenance/ledger_default_dry_run.py --json`
* `python3 scripts/maintenance/ledger_default_dry_run.py --strict`

Dry-run mode:

* does not switch authority
* does not mutate artifacts
* does not remove trace compatibility
* does not change replay/eval/registry defaults

Dry-run mode follows the standard observational safety model.

---

## Phase 3.8A Controlled Ledger-Authoritative Canary

Phase 3.8A adds explicit canary mode for authoritative-ledger operation without changing global defaults.

Flags:

* `RUNTIME_LEDGER_CANARY=1`
* `RUNTIME_LEDGER_CANARY_PARITY_REQUIRED=1` (optional strict parity in canary)

Canary semantics:

* opt-in only
* replay/eval/registry default to ledger during canary
* trace emission remains preserved
* explicit `source="trace"` remains supported
* rollback is immediate by unsetting canary/authoritative/parity flags

Canary readiness helper:

* `evaluate_ledger_canary_readiness(...)`

CLI:

* `python3 scripts/maintenance/ledger_canary.py --latest`
* `python3 scripts/maintenance/ledger_canary.py --summary --recent 50`
* `python3 scripts/maintenance/ledger_canary.py --print-env`
* `python3 scripts/maintenance/ledger_canary.py --latest --strict`

This phase is operational guardrail work only and does not perform default cutover.

---

## Phase 3.8B Canonical Runtime Event Loader

Phase 3.8B centralizes runtime event source resolution and event loading into `runtime/event_loader.py`.

Canonical APIs:

* `resolve_runtime_event_source(source=None, default="trace")`
* `runtime_event_source(default="trace")`
* `iter_runtime_events(run_or_path, source=None, strict=False)`
* `load_runtime_events(run_or_path, source=None, strict=False)`

Semantics remain unchanged:

* default remains trace-first unless authoritative/canary flags are enabled
* explicit `source="trace"` still overrides canary/authoritative defaults
* missing `ledger.jsonl` in ledger mode still fails deterministically
* trace emission and compatibility remain preserved

This is an internal deduplication step only and does not change contracts or NDJSON formats.

---

## Phase 3.8C Projection Purity Refactor

Phase 3.8C keeps runtime behavior unchanged while clarifying boundaries:

* `runtime/event_loader.py` remains the canonical source resolver/loader
* replay/eval/registry now expose pure event-projection helpers over in-memory event sequences
* public run-based APIs remain backward-compatible and source-aware
* no default cutover, no trace removal, no schema changes

Projection helpers are file-I/O free and consume already-loaded canonical events.

---

# Phase 3.8D Control-Plane Runtime Event Bridge

Control-plane consumers now load canonical runtime events through a bridge layer that delegates to `runtime.event_loader`.

Bridge APIs:

* `control_plane_runtime_event_source(...)`
* `load_control_plane_runtime_events(...)`
* `iter_control_plane_runtime_events(...)`

Compatibility guarantees remain unchanged:

* default source remains trace
* canary/authoritative behavior remains opt-in
* explicit trace source override remains supported
* trace artifacts continue to be emitted for compatibility
* no NDJSON/EventLedger schema changes were introduced

---

# Phase 3.9A Ledger Authority Readiness Matrix

Ledger default-authority governance is now formalized via:

* `runtime/ledger_authority_matrix.py`
* `scripts/maintenance/ledger_authority_matrix.py`

Matrix goals:

* deterministic readiness assessment
* explicit cutover blockers
* structured warnings/recommendations
* rollback guarantee visibility

Operational usage:

* `python3 scripts/maintenance/ledger_authority_matrix.py --latest`
* `python3 scripts/maintenance/ledger_authority_matrix.py --summary --recent 50`

This layer is observational-only:

* no runtime default changes
* no authority auto-switching
* no trace removal
* no schema changes

---

## Phase 3.9B Authority Policy Layer

Runtime authority semantics are centralized in `runtime/authority_policy.py`.

Canonical APIs:

* `runtime_authority_mode()` -> `trace|canary|authoritative`
* `effective_runtime_event_source(source=None, default="trace")`
* `runtime_authority_policy()`
* `runtime_authority_transition_state()`

Rules are deterministic and unchanged:

* trace-first remains default
* canary remains explicit opt-in
* authoritative remains explicit opt-in
* authoritative overrides canary
* explicit source override still wins

No default authority cutover is performed in this phase.

---

## Phase 3.9C Dual-Authority Validation Window

`runtime/dual_authority_validation.py` adds a deterministic, read-only validation window for ledger-backed authority modes.

It aggregates:

* drift state
* corruption state
* replay/eval/registry parity state
* compatibility blockers
* rollback readiness
* authority transition state

Activation semantics:

* active only when authority mode is `canary` or `authoritative`
* available but inactive in `trace` mode

This phase is observational only and does not change runtime defaults or authority behavior.

---

## Phase 3.9D Trace Deprecation Inventory

`runtime/trace_deprecation_inventory.py` provides an informational-only inventory for remaining trace references.

It classifies references into retained compatibility, operational dependencies, legacy runtime paths, and future deprecation/removal candidates.

This inventory does not remove trace support, does not alter runtime authority, and does not change EventLedger behavior.

---

## Phase 3.9E Default Authority Simulation

`runtime/default_authority_simulation.py` adds an observational simulation layer for "what if ledger were the global default authority now?"

It is simulation-only and deterministic:

* actual default remains `trace`
* simulated default is reported as `ledger`
* no authority switch is performed
* trace emission remains preserved
* rollback semantics are carried through unchanged

It aggregates authority matrix, dual-authority validation, trace compatibility, and trace deprecation inventory for governance planning without runtime mutation.

---

## Phase 3.9F Ledger Cutover Decision Gate

`runtime/ledger_cutover_decision_gate.py` adds a governance-only operational decision gate.

It evaluates readiness, validation, simulation, compatibility, deprecation inventory, and rollback confidence to produce:

* `eligible`
* `conditional`
* `blocked`

This gate is observational only: no cutover is performed, authority is not switched, trace emission remains preserved, and runtime artifacts are not mutated.

---

# Future Cutover Direction

Future cutover phases may:

* enable controlled ledger-authoritative rollout
* reduce operational trace dependence
* preserve replay compatibility guarantees
* retain audit and observability enforcement

No automatic trace retirement is currently performed.

---

# Architectural Guarantees

The EventLedger architecture guarantees:

* deterministic replay compatibility
* additive migration safety
* append-only runtime history
* operational rollback safety
* compatibility-preserving evolution
* deterministic parity validation
* audit-safe operational observability
* replay-safe recovery behavior

EventLedger is intentionally designed as:

```text
deterministic runtime migration and operational reliability infrastructure
```

—not merely a secondary trace format.
