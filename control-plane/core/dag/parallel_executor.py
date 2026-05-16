#!/usr/bin/env python3
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from core.dag.executor import execute_noop_node
from core.dag.executor import execute_tool_node
from core.dag.executor import NodeExecutionResult
from core.dag.models import DagSpec
from core.dag.validator import load_dag
from core.dag.validator import validate_dag


class ParallelExecutionBatch(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    batch_index: int
    node_ids: list[str] = Field(default_factory=list)


class ParallelDagExecutionResult(BaseModel):

    model_config = ConfigDict(extra='allow', frozen=False)

    status: Literal['success', 'error']
    dag_id: str | None = None
    execution_mode: str = 'parallel'
    batches: list[ParallelExecutionBatch] = Field(default_factory=list)
    node_results: dict[str, Any] = Field(default_factory=dict)
    execution_order: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _load_dag_input(dag: DagSpec | dict | str | Path) -> DagSpec:
    if isinstance(dag, DagSpec):
        return dag
    if isinstance(dag, dict):
        return validate_dag(dag)
    if isinstance(dag, (str, Path)):
        return load_dag(dag)
    raise TypeError('dag must be DagSpec, dict, str, or Path')


def dag_to_execution_batches(dag: DagSpec) -> list[list[str]]:
    node_ids = sorted([n.id for n in dag.nodes])
    indegree = {node_id: 0 for node_id in node_ids}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}

    for node in dag.nodes:
        for dep in node.depends_on:
            outgoing[dep].append(node.id)
            indegree[node.id] += 1

    for k in outgoing:
        outgoing[k] = sorted(outgoing[k])

    ready = sorted([nid for nid in node_ids if indegree[nid] == 0])
    batches: list[list[str]] = []
    visited = 0

    while ready:
        batch = sorted(ready)
        batches.append(batch)
        visited += len(batch)

        next_ready_set: set[str] = set()
        for current in batch:
            for nxt in outgoing.get(current, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    next_ready_set.add(nxt)
        ready = sorted(next_ready_set)

    if visited != len(node_ids):
        raise ValueError('dependency cycle detected in DAG')

    return batches


def _execute_node(node):
    if node.type == 'noop':
        return execute_noop_node(node)
    if node.type == 'tool':
        return execute_tool_node(node)
    if node.type == 'llm':
        now = time.time()
        return NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            status='error',
            output=None,
            error='llm nodes are not implemented in Stage 4T parallel execution',
            started_at=now,
            finished_at=now,
            duration_ms=0.0,
            tool=None,
            raw_result=None,
        )
    now = time.time()
    return NodeExecutionResult(
        node_id=node.id,
        node_type=node.type,
        status='error',
        output=None,
        error=f'unsupported node type: {node.type}',
        started_at=now,
        finished_at=now,
        duration_ms=0.0,
        tool=None,
        raw_result=None,
    )


def execute_dag_parallel(
    dag: DagSpec | dict | str | Path,
    max_workers: int = 4,
    trace: bool = False,
) -> ParallelDagExecutionResult:
    if max_workers < 1:
        raise ValueError('max_workers must be >= 1')

    dag_spec = _load_dag_input(dag)
    batches = dag_to_execution_batches(dag_spec)
    batch_models = [ParallelExecutionBatch(batch_index=i, node_ids=b) for i, b in enumerate(batches)]
    execution_order = [nid for b in batches for nid in b]
    nodes_by_id = {n.id: n for n in dag_spec.nodes}

    if trace:
        return ParallelDagExecutionResult(
            status='error',
            dag_id=dag_spec.dag_id,
            execution_mode='parallel',
            batches=batch_models,
            node_results={},
            execution_order=execution_order,
            metadata={
                'error': 'trace=True is not implemented for parallel executor in Stage 4T',
                'max_workers': max_workers,
            },
        )

    results: dict[str, NodeExecutionResult] = {}
    status: Literal['success', 'error'] = 'success'
    error_message: str | None = None

    for bi, batch in enumerate(batches):
        workers = min(max_workers, len(batch))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {node_id: pool.submit(_execute_node, nodes_by_id[node_id]) for node_id in batch}

            ordered_batch_results: list[tuple[str, NodeExecutionResult]] = []
            for node_id in sorted(batch):
                ordered_batch_results.append((node_id, futures[node_id].result()))

        for node_id, result in ordered_batch_results:
            results[node_id] = result
            if result.status != 'success' and status == 'success':
                status = 'error'
                error_message = result.error or 'parallel node execution failed'

        if status == 'error':
            skipped_nodes = [nid for later_batch in batches[bi + 1:] for nid in later_batch]
            for skipped_id in skipped_nodes:
                now = time.time()
                skipped_node = nodes_by_id[skipped_id]
                results[skipped_id] = NodeExecutionResult(
                    node_id=skipped_id,
                    node_type=skipped_node.type,
                    status='skipped',
                    output=None,
                    error='skipped due to upstream failure',
                    started_at=now,
                    finished_at=now,
                    duration_ms=0.0,
                    tool=skipped_node.tool,
                    raw_result=None,
                )
            break

    ordered_node_results = {nid: results[nid].model_dump(mode='json') for nid in sorted(results.keys())}

    return ParallelDagExecutionResult(
        status=status,
        dag_id=dag_spec.dag_id,
        execution_mode='parallel',
        batches=batch_models,
        node_results=ordered_node_results,
        execution_order=execution_order,
        metadata={
            'max_workers': max_workers,
            'error': error_message,
        },
    )
