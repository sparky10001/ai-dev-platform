#!/usr/bin/env python3
from __future__ import annotations

from core.heuristics.models import HeuristicSignal
from core.heuristics.models import RecommendationResult


def _weighted_avg(signals: list[HeuristicSignal], key: str):
    buckets: dict[str, tuple[float, float]] = {}
    for s in signals:
        label = getattr(s, key)
        if not isinstance(label, str) or not label:
            continue
        score = float(s.score) if isinstance(s.score, (int, float)) else 0.0
        w = float(s.weight) if isinstance(s.weight, (int, float)) else 1.0
        total, weight = buckets.get(label, (0.0, 0.0))
        buckets[label] = (total + score * w, weight + w)

    avgs: dict[str, float] = {}
    for k, (total, weight) in buckets.items():
        avgs[k] = (total / weight) if weight else 0.0
    return avgs


def recommend_strategy(
    task: str,
    signals: list[HeuristicSignal],
) -> RecommendationResult:

    ordered_signals = sorted(signals, key=lambda s: s.signal_id)
    planner_avgs = _weighted_avg(ordered_signals, 'planner_strategy')
    policy_avgs = _weighted_avg(ordered_signals, 'policy_id')

    recommended_planner = None
    if planner_avgs:
        recommended_planner = sorted(planner_avgs.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    recommended_policy = None
    if policy_avgs:
        recommended_policy = sorted(policy_avgs.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    confidence = 0.0
    if planner_avgs:
        vals = sorted(planner_avgs.values(), reverse=True)
        if len(vals) == 1:
            confidence = 1.0
        else:
            gap = vals[0] - vals[1]
            confidence = max(0.0, min(1.0, gap))

    return RecommendationResult(
        recommendation_id=f'rec_{abs(hash(task)) % 1000000}',
        task=task,
        recommended_planner=recommended_planner,
        recommended_policy=recommended_policy,
        confidence=confidence,
        supporting_signals=ordered_signals,
        metadata={
            'planner_averages': planner_avgs,
            'policy_averages': policy_avgs,
        },
    )
