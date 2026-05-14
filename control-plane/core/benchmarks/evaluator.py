#!/usr/bin/env python3
from __future__ import annotations

from core.benchmarks.models import BenchmarkSuiteResult


def _avg(vals: list[float]) -> float:
    return (sum(vals) / len(vals)) if vals else 0.0


def summarize_benchmark_suite(suite: BenchmarkSuiteResult) -> BenchmarkSuiteResult:
    results = sorted(
        suite.results,
        key=lambda r: (r.scenario_id, r.planner_strategy, r.policy_id or ''),
    )

    scored = [float(r.score) for r in results if isinstance(r.score, (int, float))]
    planner_scores: dict[str, float] = {}
    policy_scores: dict[str, float] = {}

    planners = sorted({r.planner_strategy for r in results})
    for p in planners:
        vals = [float(r.score) for r in results if r.planner_strategy == p and isinstance(r.score, (int, float))]
        planner_scores[p] = _avg(vals)

    policies = sorted({(r.policy_id or 'none') for r in results})
    for pol in policies:
        vals = [float(r.score) for r in results if (r.policy_id or 'none') == pol and isinstance(r.score, (int, float))]
        policy_scores[pol] = _avg(vals)

    suite.results = results
    suite.total_runs = len(results)
    suite.average_score = _avg(scored)
    suite.planner_scores = planner_scores
    suite.policy_scores = policy_scores
    return suite
