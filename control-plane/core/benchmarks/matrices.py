#!/usr/bin/env python3
from __future__ import annotations

from core.benchmarks.models import BenchmarkMatrix


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({v for v in values if isinstance(v, str) and v})


def build_benchmark_matrix(
    scenarios: list[str],
    planner_strategies: list[str],
    policies: list[str] | None = None,
    matrix_id: str = 'matrix',
) -> BenchmarkMatrix:

    return BenchmarkMatrix(
        matrix_id=matrix_id,
        scenarios=_sorted_unique(scenarios),
        planner_strategies=_sorted_unique(planner_strategies),
        policies=_sorted_unique(policies or []),
        metadata={},
    )
