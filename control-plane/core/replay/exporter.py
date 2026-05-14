#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.replay.introspection import get_execution_order
from core.replay.introspection import list_tools_used
from core.replay.models import ReplayDag


def export_replay_summary_json(replay: ReplayDag, path: str | Path) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = replay.summary.model_dump(mode='json')
    target.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding='utf-8')
    return str(target)


def export_replay_markdown(replay: ReplayDag, path: str | Path) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append('# Replay Summary')
    lines.append('')
    lines.append(f"- run id: `{replay.summary.run_id}`")
    lines.append(f"- dag id: `{replay.summary.dag_id}`")
    lines.append(f"- status: `{replay.summary.status}`")
    lines.append(f"- execution order: `{get_execution_order(replay)}`")
    lines.append(f"- tools used: `{list_tools_used(replay)}`")
    lines.append('')
    lines.append('| node_id | status | tool |')
    lines.append('|---|---|---|')
    for nid in sorted(replay.nodes.keys()):
        n = replay.nodes[nid]
        lines.append(f"| {nid} | {n.status} | {n.tool or ''} |")

    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(target)
