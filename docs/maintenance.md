# Maintenance Operations

## Manual Commands

- Run cleanup:
  - `make log-maintenance`
- Dry-run cleanup:
  - `make log-maintenance-dry-run`
- Run maintenance test suite:
  - `make log-maintenance-tests`

## Safety Model

- Cleanup is explicit and operator-driven by default.
- Cleanup uses a nonblocking lock file to prevent concurrent runs.
- If maintenance is already running, subsequent invocations exit cleanly.
- Path safety checks prevent deletion outside configured trace/run directories.

## Lock Behavior

- Lock file path default: `tmp/log_manager.lock`
- Override via: `AI_LOG_LOCK_FILE`
- Locking uses `fcntl.flock` (nonblocking) on Linux.

## Opportunistic Maintenance Gate

The gate helper is available at `scripts/maintenance/maintenance_gate.py`.

- Disabled by default unless `AI_MAINTENANCE_ENABLED=1`
- Interval default: `AI_MAINTENANCE_INTERVAL_SEC=300`
- Timeout default: `AI_MAINTENANCE_TIMEOUT_SEC=30`
- Stamp default: `tmp/.last_log_maintenance`

`maybe_run_maintenance(...)` never raises by default and returns a JSON-safe result payload describing skip/success/error.

## Environment Variables

Log manager:

- `AI_LOG_MAX_FILES`
- `AI_LOG_MAX_SIZE_MB`
- `AI_LOG_TRUNCATE_LINES`
- `AI_LOG_MIN_AGE_SEC`
- `AI_MAX_RUN_DIRS`
- `AI_RUN_RETENTION_SEC`
- `AI_LOG_DRY_RUN`
- `AI_LOG_VERBOSE`
- `AI_LOG_LOCK_FILE`

Maintenance gate:

- `AI_MAINTENANCE_ENABLED`
- `AI_MAINTENANCE_INTERVAL_SEC`
- `AI_MAINTENANCE_TIMEOUT_SEC`
- `AI_MAINTENANCE_STAMP_PATH`
