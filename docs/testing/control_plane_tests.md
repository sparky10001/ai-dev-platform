# Control-Plane Tests (Stage 4)

Stage 4 tests are additive and isolated from `make validate`.

## Command

```bash
make control-plane-tests
```

## Suites

- DAG validation: `scripts/tests/control_plane_dag_tests.sh`
- Tool registry: `scripts/tests/control_plane_tool_registry_tests.sh`
- DAG executor: `scripts/tests/control_plane_dag_executor_tests.sh`
- Trace bridge: `scripts/tests/control_plane_trace_bridge_tests.sh`
- Planner: `scripts/tests/control_plane_planner_tests.sh`
- Orchestrator: `scripts/tests/control_plane_orchestrator_tests.sh`
- CLI: `scripts/tests/control_plane_cli_tests.sh`
- Policy layer: `scripts/tests/control_plane_policy_tests.sh`
- Scenario tests: `scripts/tests/control_plane_scenario_tests.sh`
- Replay/introspection: `scripts/tests/control_plane_replay_tests.sh`
- Eval/comparison: `scripts/tests/control_plane_eval_tests.sh`
- Experiments/datasets: `scripts/tests/control_plane_experiment_tests.sh`
- Benchmarks: `scripts/tests/control_plane_benchmark_tests.sh`
- Multi-strategy: `scripts/tests/control_plane_strategy_tests.sh`
- Adaptive heuristics: `scripts/tests/control_plane_heuristic_tests.sh`
- Memory/history: `scripts/tests/control_plane_memory_tests.sh`
- Knowledge/lineage: `scripts/tests/control_plane_knowledge_tests.sh`
- Orchestration Graph Analytics: `scripts/tests/control_plane_graph_analytics_tests.sh`
- Parallel DAG Execution: `scripts/tests/control_plane_parallel_executor_tests.sh`
