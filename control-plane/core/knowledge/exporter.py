#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.corpora import build_relationship_corpus
from core.knowledge.models import KnowledgeGraph
from core.knowledge.models import LineageResult
from core.knowledge.traversal import summarize_knowledge_graph


def export_knowledge_graph_json(graph: KnowledgeGraph, path: str | Path) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(graph.model_dump(mode='json'), f, indent=2, sort_keys=True)
        f.write('\n')
    return str(out)


def export_knowledge_graph_markdown(graph: KnowledgeGraph, path: str | Path) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    summary = summarize_knowledge_graph(graph)
    corpus = build_relationship_corpus(graph)

    lines: list[str] = []
    lines.append(f'# Knowledge Graph: {graph.graph_id}')
    lines.append('')
    lines.append(f'- Total Nodes: {graph.total_nodes}')
    lines.append(f'- Total Edges: {graph.total_edges}')
    lines.append('')
    lines.append('## Relationship Frequencies')
    lines.append('')
    for key, value in corpus.get('relationship_frequencies', {}).items():
        lines.append(f'- {key}: {value}')
    lines.append('')
    lines.append('## Node Relationship Table')
    lines.append('')
    lines.append('| Node ID | Planner | Policy | Outgoing Edges |')
    lines.append('|---|---|---|---|')

    edge_map: dict[str, int] = {}
    for edge in graph.edges:
        edge_map[edge.source_id] = edge_map.get(edge.source_id, 0) + 1

    for node in graph.nodes:
        lines.append(
            f'| {node.node_id} | {node.planner_strategy or ""} | {node.policy_id or ""} | {edge_map.get(node.node_id, 0)} |'
        )

    lines.append('')
    lines.append('## Graph Summary')
    lines.append('')
    lines.append('```json')
    lines.append(json.dumps(summary, indent=2, sort_keys=True))
    lines.append('```')
    lines.append('')

    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return str(out)


def export_lineage_markdown(lineage: LineageResult, path: str | Path) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f'# Lineage: {lineage.lineage_id}')
    lines.append('')
    lines.append(f'- Root Node: {lineage.root_node_id}')
    lines.append(f'- Ancestors: {len(lineage.ancestor_ids)}')
    lines.append(f'- Descendants: {len(lineage.descendant_ids)}')
    lines.append('')
    lines.append('## Ancestors')
    lines.append('')
    for node_id in lineage.ancestor_ids:
        lines.append(f'- {node_id}')
    lines.append('')
    lines.append('## Descendants')
    lines.append('')
    for node_id in lineage.descendant_ids:
        lines.append(f'- {node_id}')
    lines.append('')

    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return str(out)
