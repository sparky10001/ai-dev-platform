#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.benchmarks.models import BenchmarkSuiteResult


def export_benchmark_suite_json(suite: BenchmarkSuiteResult, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(suite.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_benchmark_suite_markdown(suite: BenchmarkSuiteResult, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        '# Benchmark Suite',
        '',
        f"- benchmark id: `{suite.benchmark_id}`",
        f"- total runs: `{suite.total_runs}`",
        f"- average score: `{suite.average_score}`",
        '',
        '## Planner Scores',
        '',
        '| planner | score |',
        '|---|---|',
    ]

    for k in sorted(suite.planner_scores.keys()):
        lines.append(f"| {k} | {suite.planner_scores[k]} |")

    lines.extend([
        '',
        '## Policy Scores',
        '',
        '| policy | score |',
        '|---|---|',
    ])

    for k in sorted(suite.policy_scores.keys()):
        lines.append(f"| {k} | {suite.policy_scores[k]} |")

    lines.extend([
        '',
        '## Results',
        '',
        '| scenario | planner | policy | status | score | run_id |',
        '|---|---|---|---|---|---|',
    ])

    for r in suite.results:
        lines.append(
            f"| {r.scenario_id} | {r.planner_strategy} | {r.policy_id or 'none'} | {r.status or ''} | {r.score if r.score is not None else ''} | {r.run_id or ''} |"
        )

    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(p)
