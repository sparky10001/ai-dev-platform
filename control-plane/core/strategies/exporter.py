#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.strategies.models import StrategyExperiment


def export_strategy_experiment_json(experiment: StrategyExperiment, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(experiment.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_strategy_experiment_markdown(experiment: StrategyExperiment, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        '# Strategy Experiment',
        '',
        f"- experiment id: `{experiment.experiment_id}`",
        f"- task: `{experiment.task}`",
        f"- average score: `{experiment.average_score}`",
        f"- best strategy: `{experiment.best_strategy_id}`",
        '',
        '| strategy_id | planner | policy | status | score | run_id |',
        '|---|---|---|---|---|---|',
    ]

    for v in sorted(experiment.variants, key=lambda x: x.strategy_id):
        lines.append(
            f"| {v.strategy_id} | {v.planner_strategy} | {v.policy_id or 'none'} | {v.status or ''} | {v.score if v.score is not None else ''} | {v.run_id or ''} |"
        )

    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(p)
