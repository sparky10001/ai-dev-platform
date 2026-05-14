#!/usr/bin/env python3
from __future__ import annotations

from core.strategies.models import StrategyVariant


def build_strategy_variants(
    task: str,
    planner_strategies: list[str],
    policies: list[str] | None = None,
) -> list[StrategyVariant]:

    unique_planners = sorted({p for p in planner_strategies if isinstance(p, str) and p})
    unique_policies = sorted({p for p in (policies or ['none']) if isinstance(p, str) and p})
    if not unique_policies:
        unique_policies = ['none']

    variants: list[StrategyVariant] = []
    for planner in unique_planners:
        for policy in unique_policies:
            policy_id = None if policy == 'none' else policy
            sid = f"{planner}__{policy}"
            variants.append(
                StrategyVariant(
                    strategy_id=sid,
                    planner_strategy=planner,
                    policy_id=policy_id,
                    metadata={'task': task},
                )
            )

    return variants
