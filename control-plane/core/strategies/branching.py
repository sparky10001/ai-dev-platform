#!/usr/bin/env python3
from __future__ import annotations

import time

from core.evals.evaluator import evaluate_replay
from core.orchestrator.orchestrator import orchestrate_task
from core.policy.defaults import DEFAULT_POLICY
from core.policy.defaults import SAFE_READONLY_POLICY
from core.replay.loader import load_orchestration_trace
from core.strategies.evaluator import select_best_strategy
from core.strategies.models import StrategyExperiment
from core.strategies.models import StrategyVariant
from core.strategies.planner_variants import build_strategy_variants


def _resolve_policy(policy_id: str | None):
    if policy_id in (None, '', 'none'):
        return None
    if policy_id == 'default':
        return DEFAULT_POLICY.model_dump(mode='json')
    if policy_id == 'safe-readonly':
        return SAFE_READONLY_POLICY.model_dump(mode='json')
    return None


def execute_strategy_experiment(
    task: str,
    planner_strategies: list[str],
    policies: list[str] | None = None,
    trace: bool = True,
) -> StrategyExperiment:

    variants = build_strategy_variants(task, planner_strategies, policies)
    executed: list[StrategyVariant] = []

    for variant in variants:
        orch = orchestrate_task(
            {
                'task': task,
                'planner_strategy': variant.planner_strategy,
                'trace': trace,
                'policy': _resolve_policy(variant.policy_id),
            }
        )

        updated = StrategyVariant.model_validate(variant.model_dump(mode='json'))
        updated.status = orch.status
        updated.run_id = orch.run_id
        updated.dag_id = orch.dag_id

        meta = dict(updated.metadata)
        meta['execution_order'] = orch.execution_order

        if orch.run_path:
            try:
                replay = load_orchestration_trace(orch.run_path)
                ev = evaluate_replay(replay)
                updated.score = ev.score
                if not updated.run_id:
                    updated.run_id = replay.summary.run_id
                meta['tools_used'] = replay.summary.tools_used
                meta['node_count'] = replay.summary.total_nodes
            except Exception:
                updated.score = None
        else:
            updated.score = None
            meta['tools_used'] = []
            meta['node_count'] = len(orch.node_results)

        updated.metadata = meta
        executed.append(updated)

    executed = sorted(executed, key=lambda v: v.strategy_id)
    scores = [float(v.score) for v in executed if isinstance(v.score, (int, float))]
    avg = (sum(scores) / len(scores)) if scores else 0.0

    exp = StrategyExperiment(
        experiment_id=f"strategy_exp_{int(time.time() * 1000)}",
        task=task,
        created_at=time.time(),
        variants=executed,
        best_strategy_id=None,
        average_score=avg,
        metadata={},
    )
    exp.best_strategy_id = select_best_strategy(exp)
    return exp
