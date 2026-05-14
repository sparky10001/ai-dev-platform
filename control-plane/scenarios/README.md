# Control-Plane Scenarios

Scenario tests validate the deterministic control-plane flow:

`task -> planner -> policy validation -> executor -> optional trace`

## Scenario Schema (minimal)

Each scenario JSON supports:

- `scenario_id` (string)
- `task` (string)
- `strategy` (string, default `deterministic`)
- `policy` (string or null, supported: `default`, `safe-readonly`)
- `trace` (bool)
- `expect` object with fields such as:
  - `status`, `planner_status`, `execution_status`, `dag_id`
  - `tools_used`, `nodes_executed`, `nodes_skipped`
  - `requires_run_artifact`, `output_contains`, `policy_violation_codes`

## Run

```bash
./scripts/tests/control_plane_scenario_tests.sh
make control-plane-tests
```
