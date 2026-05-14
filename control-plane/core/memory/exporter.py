#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.memory.models import MemoryCorpus
from core.memory.models import MemoryTimeline
from core.memory.timelines import summarize_memory_timeline


def export_memory_timeline_json(timeline: MemoryTimeline, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(timeline.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_memory_corpus_json(corpus: MemoryCorpus, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(corpus.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_memory_timeline_markdown(timeline: MemoryTimeline, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    summary = summarize_memory_timeline(timeline)

    lines = [
        '# Memory Timeline',
        '',
        f"- timeline id: `{timeline.timeline_id}`",
        f"- total records: `{timeline.total_records}`",
        '',
        '## Planner Frequencies',
        '',
        '| planner | count |',
        '|---|---|',
    ]
    for k, v in summary['planner_frequencies'].items():
        lines.append(f"| {k} | {v} |")

    lines.extend([
        '',
        '## Policy Frequencies',
        '',
        '| policy | count |',
        '|---|---|',
    ])
    for k, v in summary['policy_frequencies'].items():
        lines.append(f"| {k} | {v} |")

    lines.extend([
        '',
        '## Execution History',
        '',
        '| run_id | task | planner | policy | status | score | created_at |',
        '|---|---|---|---|---|---|---|',
    ])
    for r in timeline.records:
        lines.append(
            f"| {r.run_id or ''} | {r.task or ''} | {r.planner_strategy or ''} | {r.policy_id or ''} | {r.status or ''} | {r.score if r.score is not None else ''} | {r.created_at if r.created_at is not None else ''} |"
        )

    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(p)
