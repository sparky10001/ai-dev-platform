# Maintenance Operations

This document describes operational maintenance, cleanup, health auditing, and ledger-readiness observability for the runtime system.

Maintenance tooling is intentionally:

* non-destructive by default
* replay-safe
* compatibility-preserving
* operationally observable

---

## Operational Philosophy

Maintenance tooling must never:

* mutate runtime history unexpectedly
* bypass replay guarantees
* invalidate EventLedger parity
* remove trace compatibility automatically

Audit and dry-run systems are intentionally:

* observational-first
* warning-oriented
* deterministic
* non-authoritative

---

## Manual Commands

Run cleanup:

```bash
make log-maintenance
```

Dry-run cleanup:

```bash
make log-maintenance-dry-run
```

Run maintenance test suite:

```bash
make log-maintenance-tests
```

Run ledger health summary:

```bash
python3 scripts/maintenance/ledger_health_report.py --summary
```

Run ledger-default dry-run readiness summary:

```bash
python3 scripts/maintenance/ledger_default_dry_run.py --summary --recent 50
```

Run strict trace compatibility readiness audit:

```bash
python3 scripts/maintenance/trace_compatibility_audit.py --strict
```

---

## Safety Model

* Cleanup is explicit and operator-driven by default.
* Cleanup uses a nonblocking lock file to prevent concurrent runs.
* If maintenance is already running, subsequent invocations exit cleanly.
* Path safety checks prevent deletion outside configured trace/run directories.
* Audit tooling is read-only and does not mutate runtime artifacts.
* Dry-run readiness tooling never changes runtime authority behavior.

---

## Runtime Safety Guarantees

Maintenance tooling preserves:

* append-only runtime history
* replay compatibility
* EventLedger parity guarantees
* deterministic audit behavior
* trace compatibility during migration phases

---

## Exit Code Semantics

Maintenance and audit CLIs generally use:

* `0` — success / ready / warning-only
* `1` — strict-mode failure or blocking condition
* `2` — operational or usage error

---

## Lock Behavior

Lock file path default:

```text
tmp/log_manager.lock
```

Override via:

```text
AI_LOG_LOCK_FILE
```

Locking uses:

```text
fcntl.flock (nonblocking)
```

on Linux.

If the lock is already held:

* maintenance exits cleanly
* no cleanup overlap occurs
* verbose mode reports:

  ```text
  maintenance already running
  ```

---

## Opportunistic Maintenance Gate

The gate helper is available at:

```text
scripts/maintenance/maintenance_gate.py
```

Defaults:

* disabled unless:

  ```text
  AI_MAINTENANCE_ENABLED=1
  ```
* interval:

  ```text
  AI_MAINTENANCE_INTERVAL_SEC=300
  ```
* timeout:

  ```text
  AI_MAINTENANCE_TIMEOUT_SEC=30
  ```
* stamp path:

  ```text
  tmp/.last_log_maintenance
  ```

`maybe_run_maintenance(...)`:

* never raises by default
* returns JSON-safe status payloads
* remains nonblocking and compatibility-safe

---

## Environment Variables

### Log Manager

* `AI_LOG_MAX_FILES`
* `AI_LOG_MAX_SIZE_MB`
* `AI_LOG_TRUNCATE_LINES`
* `AI_LOG_MIN_AGE_SEC`
* `AI_MAX_RUN_DIRS`
* `AI_RUN_RETENTION_SEC`
* `AI_LOG_DRY_RUN`
* `AI_LOG_VERBOSE`
* `AI_LOG_LOCK_FILE`

### Maintenance Gate

* `AI_MAINTENANCE_ENABLED`
* `AI_MAINTENANCE_INTERVAL_SEC`
* `AI_MAINTENANCE_TIMEOUT_SEC`
* `AI_MAINTENANCE_STAMP_PATH`

### Ledger Dry-Run Readiness

* `RUNTIME_LEDGER_DRY_RUN_DEFAULT`

---

## Ledger Health Observability

Operational ledger health reporting is available via:

```bash
python3 scripts/maintenance/ledger_health_report.py --latest
```

```bash
python3 scripts/maintenance/ledger_health_report.py --summary
```

```bash
python3 scripts/maintenance/ledger_health_report.py --latest --strict
```

This reporting is:

* read-only
* non-authoritative
* non-mutating
* replay-safe

Large installations should prefer bounded scans where supported (for example `--recent N`) to distinguish current operational health from historical backlog conditions.

---

## Ledger-Default Dry-Run Readiness

Operational dry-run readiness reporting is available via:

```bash
python3 scripts/maintenance/ledger_default_dry_run.py --latest
```

```bash
python3 scripts/maintenance/ledger_default_dry_run.py --summary --recent 50
```

```bash
python3 scripts/maintenance/ledger_default_dry_run.py --json
```

```bash
python3 scripts/maintenance/ledger_default_dry_run.py --strict
```

Flag:

```text
RUNTIME_LEDGER_DRY_RUN_DEFAULT=1
```

enables dry-run signaling only.

Dry-run mode:

* does not switch runtime authority
* does not change replay/eval/registry defaults
* does not mutate runtime artifacts
* does not remove trace compatibility

Dry-run mode is intentionally:

* observational-only
* warning-oriented
* replay-safe
* compatibility-preserving

---

## Recommended Operational Commands

Current runtime health:

```bash
python3 scripts/maintenance/ledger_health_report.py --latest
```

Recent readiness snapshot:

```bash
python3 scripts/maintenance/ledger_default_dry_run.py --summary --recent 50
```

Strict compatibility readiness audit:

```bash
python3 scripts/maintenance/trace_compatibility_audit.py --strict
```

Strict corruption audit:

```bash
python3 scripts/maintenance/ledger_corruption_audit.py --latest --strict
```

Strict drift audit:

```bash
python3 scripts/maintenance/ledger_drift_audit.py --latest --strict
```

---

## Operational Expectations

Operational maintenance systems are designed to support:

* deterministic replay infrastructure
* additive EventLedger migration
* compatibility-safe runtime evolution
* operational cutover readiness validation
* long-term runtime observability

Maintenance systems intentionally prioritize:

* auditability
* replay integrity
* deterministic behavior
* operational safety

over aggressive cleanup or automatic remediation.
