#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path

from core.benchmarks.evaluator import summarize_benchmark_suite
from core.benchmarks.models import BenchmarkMatrix
from core.benchmarks.models import BenchmarkScenarioResult
from core.benchmarks.models import BenchmarkSuiteResult
from core.evals.evaluator import evaluate_replay
from core.orchestrator.orchestrator import orchestrate_task
from core.policy.defaults import DEFAULT_POLICY
from core.policy.defaults import SAFE_READONLY_POLICY
from core.replay.loader import load_orchestration_trace
from core.scenarios.models import ControlPlaneScenario


def _resolve_policy(policy_name: str | None):
    if policy_name in (None, '', 'none'):
        return None
    if policy_name == 'default':
        return DEFAULT_POLICY.model_dump(mode='json')
    if policy_name == 'safe-readonly':
        return SAFE_READONLY_POLICY.model_dump(mode='json')
    return None


def run_benchmark_matrix(
    matrix: BenchmarkMatrix,
    scenario_dir: str | Path,
) -> BenchmarkSuiteResult:

    scenario_dir = Path(scenario_dir)
    policies = matrix.policies if matrix.policies else ['none']

    results: list[BenchmarkScenarioResult] = []

    for scenario_name in sorted(matrix.scenarios):
        scenario_path = scenario_dir / scenario_name
        payload = json.loads(scenario_path.read_text(encoding='utf-8'))
        scenario = ControlPlaneScenario.model_validate(payload)

        for strategy in sorted(matrix.planner_strategies):
            for policy_id in sorted(policies):
                policy_payload = _resolve_policy(policy_id)
                orch = orchestrate_task(
                    {
                        'task': scenario.task,
                        'planner_strategy': strategy,
                        'trace': bool(scenario.trace),
                        'policy': policy_payload,
                    }
                )

                run_id = orch.run_id
                score = None
                if orch.run_path:
                    try:
                        replay = load_orchestration_trace(orch.run_path)
                        ev = evaluate_replay(replay)
                        score = ev.score
                        if run_id is None:
                            run_id = replay.summary.run_id
                    except Exception:
                        score = None

                results.append(
                    BenchmarkScenarioResult(
                        scenario_id=scenario.scenario_id,
                        planner_strategy=strategy,
                        policy_id=(None if policy_id == 'none' else policy_id),
                        run_id=run_id,
                        status=orch.status,
                        score=score,
                        metadata={'dag_id': orch.dag_id},
                    )
                )

    suite = BenchmarkSuiteResult(
        benchmark_id=matrix.matrix_id,
        created_at=time.time(),
        total_runs=0,
        average_score=0.0,
        planner_scores={},
        policy_scores={},
        results=results,
        metadata={},
    )

    return summarize_benchmark_suite(suite)
