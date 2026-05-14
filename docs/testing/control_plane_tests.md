# Control-Plane Tests (Stage 4)

Stage 4 tests are additive and currently isolated from the Phase 3E validation gate.

## Test Suites

- Stage 4A DAG validation:
  - `scripts/tests/control_plane_dag_tests.sh`
- Stage 4B tool registry bridge:
  - `scripts/tests/control_plane_tool_registry_tests.sh`
- Stage 4C DAG executor scaffold:
  - `scripts/tests/control_plane_dag_executor_tests.sh`
- Stage 4D trace bridge:
  - `scripts/tests/control_plane_trace_bridge_tests.sh`
- Stage 4F deterministic planner scaffold:
  - `scripts/tests/control_plane_planner_tests.sh`
- Stage 4G planner/executor orchestration:
  - `scripts/tests/control_plane_orchestrator_tests.sh`
- Stage 4H control-plane CLI:
  - `scripts/tests/control_plane_cli_tests.sh`
- Stage 4I deterministic policy layer:
  - `scripts/tests/control_plane_policy_tests.sh`
- Stage 4J control-plane scenario tests:
  - `scripts/tests/control_plane_scenario_tests.sh`
- Stage 4K orchestration replay + introspection:
  - `scripts/tests/control_plane_replay_tests.sh`

## Convenience Command

Run all control-plane tests:

```bash
make control-plane-tests
```

Note: these tests are intentionally not part of `make validate` yet.
