#!/usr/bin/env python3
from __future__ import annotations

from core.evals.evaluator import evaluate_replay
from core.evals.models import BenchmarkResult
from core.replay.models import ReplayDag


def benchmark_replays(replays: list[ReplayDag], benchmark_id: str = 'benchmark') -> BenchmarkResult:
    evals = [evaluate_replay(r) for r in replays]
    evals = sorted(evals, key=lambda e: (e.run_id or '', e.evaluation_id))

    total_runs = len(evals)
    successful_runs = sum(1 for e in evals if e.status == 'success')
    failed_runs = sum(1 for e in evals if e.status == 'error')
    average_score = (sum(e.score for e in evals) / total_runs) if total_runs else 0.0

    status = 'success' if failed_runs == 0 else 'error'

    return BenchmarkResult(
        benchmark_id=benchmark_id,
        status=status,
        total_runs=total_runs,
        average_score=average_score,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        evaluations=evals,
        metadata={},
    )
