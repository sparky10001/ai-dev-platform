#!/usr/bin/env python3
from __future__ import annotations

import time

from core.heuristics.models import HeuristicSignal
from core.heuristics.models import StrategyRanking
from core.strategies.models import StrategyVariant


def rank_strategy_variants(
    variants: list[StrategyVariant],
    ranking_id: str = 'ranking',
) -> StrategyRanking:

    def score_of(v: StrategyVariant) -> float:
        return float(v.score) if isinstance(v.score, (int, float)) else float('-inf')

    ordered = sorted(variants, key=lambda v: (-score_of(v), v.strategy_id))
    ranked_ids = [v.strategy_id for v in ordered]

    scored = [float(v.score) for v in ordered if isinstance(v.score, (int, float))]
    avg = (sum(scored) / len(scored)) if scored else 0.0

    return StrategyRanking(
        ranking_id=ranking_id,
        created_at=time.time(),
        total_variants=len(ordered),
        ranked_strategy_ids=ranked_ids,
        average_score=avg,
        metadata={},
    )


def generate_heuristic_signals(
    variants: list[StrategyVariant],
) -> list[HeuristicSignal]:

    ordered = sorted(variants, key=lambda v: v.strategy_id)
    signals: list[HeuristicSignal] = []

    for idx, v in enumerate(ordered):
        signals.append(
            HeuristicSignal(
                signal_id=f'signal_{idx:04d}_{v.strategy_id}',
                strategy_id=v.strategy_id,
                planner_strategy=v.planner_strategy,
                policy_id=v.policy_id,
                score=v.score,
                weight=1.0,
                metadata=dict(v.metadata),
            )
        )

    return signals
