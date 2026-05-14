#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.heuristics.models import HeuristicCorpus
from core.heuristics.models import RecommendationResult
from core.heuristics.models import StrategyRanking


def export_ranking_json(ranking: StrategyRanking, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ranking.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_recommendation_json(rec: RecommendationResult, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_corpus_markdown(corpus: HeuristicCorpus, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    planner_freq: dict[str, int] = {}
    policy_freq: dict[str, int] = {}
    for s in corpus.signals:
        if s.planner_strategy:
            planner_freq[s.planner_strategy] = planner_freq.get(s.planner_strategy, 0) + 1
        if s.policy_id:
            policy_freq[s.policy_id] = policy_freq.get(s.policy_id, 0) + 1

    lines = [
        '# Heuristic Corpus',
        '',
        f"- corpus id: `{corpus.corpus_id}`",
        f"- total signals: `{corpus.total_signals}`",
        '',
        '## Planner Frequencies',
        '',
        '| planner | count |',
        '|---|---|',
    ]

    for k in sorted(planner_freq.keys()):
        lines.append(f"| {k} | {planner_freq[k]} |")

    lines.extend([
        '',
        '## Policy Frequencies',
        '',
        '| policy | count |',
        '|---|---|',
    ])

    for k in sorted(policy_freq.keys()):
        lines.append(f"| {k} | {policy_freq[k]} |")

    lines.extend([
        '',
        '## Signals',
        '',
        '| signal_id | strategy_id | planner | policy | score | weight |',
        '|---|---|---|---|---|---|',
    ])

    for s in sorted(corpus.signals, key=lambda x: x.signal_id):
        lines.append(
            f"| {s.signal_id} | {s.strategy_id or ''} | {s.planner_strategy or ''} | {s.policy_id or ''} | {s.score if s.score is not None else ''} | {s.weight} |"
        )

    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(p)
