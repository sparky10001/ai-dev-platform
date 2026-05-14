#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.evals.models import BenchmarkResult
from core.evals.models import OrchestrationEvaluation
from core.evals.models import ReplayComparison


def export_evaluation_json(evaluation: OrchestrationEvaluation, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(evaluation.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_comparison_json(comparison: ReplayComparison, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(comparison.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_benchmark_markdown(benchmark: BenchmarkResult, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        '# Orchestration Benchmark',
        '',
        f"- benchmark id: `{benchmark.benchmark_id}`",
        f"- total runs: `{benchmark.total_runs}`",
        f"- average score: `{benchmark.average_score}`",
        '',
        '| run_id | dag_id | status | score |',
        '|---|---|---|---|',
    ]

    for ev in benchmark.evaluations:
        lines.append(f"| {ev.run_id or ''} | {ev.dag_id or ''} | {ev.status} | {ev.score} |")

    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(p)
