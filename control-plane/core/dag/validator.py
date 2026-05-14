#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from core.dag.models import DagSpec


def validate_dag(data: dict) -> DagSpec:

    return DagSpec.model_validate(data)


def load_dag(path: str | Path) -> DagSpec:

    dag_path = Path(path)

    with open(dag_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    return validate_dag(payload)


def dag_to_execution_order(dag: DagSpec) -> list[str]:

    node_ids = [node.id for node in dag.nodes]
    indegree = {node_id: 0 for node_id in node_ids}
    outgoing: dict[str, list[str]] = defaultdict(list)

    for node in dag.nodes:
        for dep in node.depends_on:
            outgoing[dep].append(node.id)
            indegree[node.id] += 1

    # Deterministic: resolve ready nodes in declared DAG order.
    ready = [node_id for node_id in node_ids if indegree[node_id] == 0]
    order: list[str] = []

    while ready:
        current = ready.pop(0)
        order.append(current)

        for nxt in node_ids:
            if nxt in outgoing[current]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)

    if len(order) != len(node_ids):
        raise ValueError('dependency cycle detected in DAG')

    if dag.entry not in order:
        raise ValueError('entry node must be part of execution order')

    return order
