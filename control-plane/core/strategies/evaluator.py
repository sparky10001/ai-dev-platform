#!/usr/bin/env python3
from __future__ import annotations

from core.strategies.models import StrategyComparison
from core.strategies.models import StrategyExperiment
from core.strategies.models import StrategyVariant


def compare_strategy_variants(
    left: StrategyVariant,
    right: StrategyVariant,
) -> StrategyComparison:

    left_score = float(left.score) if isinstance(left.score, (int, float)) else 0.0
    right_score = float(right.score) if isinstance(right.score, (int, float)) else 0.0

    left_order = left.metadata.get('execution_order') if isinstance(left.metadata, dict) else None
    right_order = right.metadata.get('execution_order') if isinstance(right.metadata, dict) else None

    left_tools = sorted(set(left.metadata.get('tools_used', []))) if isinstance(left.metadata, dict) else []
    right_tools = sorted(set(right.metadata.get('tools_used', []))) if isinstance(right.metadata, dict) else []

    left_nodes = int(left.metadata.get('node_count', 0)) if isinstance(left.metadata, dict) else 0
    right_nodes = int(right.metadata.get('node_count', 0)) if isinstance(right.metadata, dict) else 0

    return StrategyComparison(
        comparison_id=f"cmp_{left.strategy_id}_vs_{right.strategy_id}",
        left_strategy_id=left.strategy_id,
        right_strategy_id=right.strategy_id,
        score_delta=right_score - left_score,
        execution_order_changed=(left_order != right_order),
        tool_usage_changed=(left_tools != right_tools),
        node_count_delta=(right_nodes - left_nodes),
        metadata={
            'left_status': left.status,
            'right_status': right.status,
            'left_tools': left_tools,
            'right_tools': right_tools,
        },
    )


def select_best_strategy(
    experiment: StrategyExperiment,
) -> str | None:

    if not experiment.variants:
        return None

    scored = []
    for v in experiment.variants:
        score = float(v.score) if isinstance(v.score, (int, float)) else float('-inf')
        scored.append((score, v.strategy_id))

    scored.sort(key=lambda x: (-x[0], x[1]))
    best = scored[0]
    if best[0] == float('-inf'):
        return None
    return best[1]
