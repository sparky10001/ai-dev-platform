#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.graph_analytics.models import GraphAnalyticsResult


def export_graph_analytics_json(result: GraphAnalyticsResult, path: str | Path) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(mode='json'), f, indent=2, sort_keys=True)
        f.write('\n')
    return str(out)


def export_graph_analytics_markdown(result: GraphAnalyticsResult, path: str | Path) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f'# Graph Analytics: {result.analytics_id}')
    lines.append('')
    lines.append(f'- Graph ID: {result.graph_id}')
    lines.append(f'- Total Nodes: {result.total_nodes}')
    lines.append(f'- Total Edges: {result.total_edges}')
    lines.append(f'- Max Lineage Depth: {result.max_lineage_depth}')
    lines.append('')

    lines.append('## Relationship Frequencies')
    lines.append('')
    for k in sorted(result.relationship_frequencies):
        lines.append(f'- {k}: {result.relationship_frequencies[k]}')
    lines.append('')

    lines.append('## Isolated Nodes')
    lines.append('')
    if result.isolated_nodes:
        for node_id in result.isolated_nodes:
            lines.append(f'- {node_id}')
    else:
        lines.append('- none')
    lines.append('')

    lines.append('## Node Metrics')
    lines.append('')
    lines.append('| Node ID | Degree | Incoming | Outgoing | Relationship Types |')
    lines.append('|---|---:|---:|---:|---|')
    for nm in result.node_metrics:
        rel_types = ', '.join(nm.relationship_types)
        lines.append(f'| {nm.node_id} | {nm.degree} | {nm.incoming_edges} | {nm.outgoing_edges} | {rel_types} |')

    lines.append('')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return str(out)
