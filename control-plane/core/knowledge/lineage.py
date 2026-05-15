#!/usr/bin/env python3
from __future__ import annotations

import time

from core.knowledge.models import KnowledgeEdge
from core.knowledge.models import KnowledgeGraph
from core.knowledge.models import KnowledgeNode
from core.memory.models import MemoryRecord


def memory_record_to_node(record: MemoryRecord) -> KnowledgeNode:
    return KnowledgeNode(
        node_id=record.memory_id,
        node_type='memory_record',
        run_id=record.run_id,
        task=record.task,
        planner_strategy=record.planner_strategy,
        policy_id=record.policy_id,
        metadata={
            'score': record.score,
            'status': record.status,
            'created_at': record.created_at,
            'memory_metadata': record.metadata,
        },
    )


def _task_family(task: str | None) -> str | None:
    if not isinstance(task, str) or not task.strip():
        return None
    t = task.lower().strip()
    if 'list files' in t or 'show files' in t:
        return 'list_files'
    if 'create a file' in t or 'write file' in t:
        return 'write_file'
    if 'read file' in t or t.startswith('read '):
        return 'read_file'
    return t


def build_knowledge_graph(
    records: list[MemoryRecord],
    graph_id: str = 'graph',
) -> KnowledgeGraph:
    ordered = sorted(records, key=lambda r: ((r.created_at if r.created_at is not None else float('inf')), (r.run_id or ''), r.memory_id))
    nodes = [memory_record_to_node(r) for r in ordered]

    edges: list[KnowledgeEdge] = []
    seen: set[tuple[str, str, str]] = set()

    def add_edge(source_id: str, target_id: str, rel: str) -> None:
        if source_id == target_id:
            return
        key = (source_id, target_id, rel)
        if key in seen:
            return
        seen.add(key)
        edges.append(
            KnowledgeEdge(
                edge_id=f'edge_{rel}_{source_id}_{target_id}',
                source_id=source_id,
                target_id=target_id,
                relationship_type=rel,
                metadata={},
            )
        )

    for i, left in enumerate(nodes):
        for right in nodes[i + 1:]:
            if left.planner_strategy and left.planner_strategy == right.planner_strategy:
                add_edge(left.node_id, right.node_id, 'same_planner')
            if left.policy_id and left.policy_id == right.policy_id:
                add_edge(left.node_id, right.node_id, 'same_policy')
            if _task_family(left.task) and _task_family(left.task) == _task_family(right.task):
                add_edge(left.node_id, right.node_id, 'same_task')

    for i in range(len(nodes) - 1):
        add_edge(nodes[i].node_id, nodes[i + 1].node_id, 'precedes')

    edges = sorted(edges, key=lambda e: (e.relationship_type, e.source_id, e.target_id, e.edge_id))

    return KnowledgeGraph(
        graph_id=graph_id,
        created_at=time.time(),
        total_nodes=len(nodes),
        total_edges=len(edges),
        nodes=nodes,
        edges=edges,
        metadata={},
    )
