#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from pydantic import ConfigDict

from core.dag.models import DagNode
from core.dag.models import DagSpec
from core.dag.validator import dag_to_execution_order
from core.dag.validator import load_dag
from core.dag.validator import validate_dag
from core.observability.trace import create_control_plane_run
from core.observability.trace import finalize_control_plane_run
from core.observability.trace import log_dag_result
from core.observability.trace import log_dag_start
from core.observability.trace import log_node_result
from core.observability.trace import log_node_start
from runtime.events import log_event
from tools.registry import get_tool
from tools.registry import validate_tool_node


class NodeExecutionResult(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    node_id: str

    node_type: str

    status: Literal['success', 'error', 'skipped']

    output: Any = None

    error: str | None = None

    run_id: str | None = None

    run_path: str | None = None

    started_at: float

    finished_at: float

    duration_ms: float

    tool: str | None = None

    raw_result: dict[str, Any] | None = None


class DagExecutionResult(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    dag_id: str

    status: Literal['success', 'error']

    execution_order: list[str]

    results: dict[str, NodeExecutionResult]

    started_at: float

    finished_at: float

    duration_ms: float

    error: str | None = None

    run_id: str | None = None

    run_path: str | None = None


def _repo_root() -> Path:

    # control-plane/core/dag/executor.py -> /workspace
    return Path(__file__).resolve().parents[3]


def _load_dag_input(dag: DagSpec | dict | str | Path) -> DagSpec:

    if isinstance(dag, DagSpec):
        return dag

    if isinstance(dag, dict):
        return validate_dag(dag)

    if isinstance(dag, (str, Path)):
        return load_dag(dag)

    raise TypeError('dag must be DagSpec, dict, str, or Path')


def _run_tool_command(cmd: list[str], cwd: Path):

    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def execute_tool_node(node: DagNode) -> NodeExecutionResult:

    started_at = time.time()

    tool_name = node.tool or ''

    try:
        tool_contract = get_tool(tool_name)
    except KeyError:
        finished_at = time.time()
        return NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            status='error',
            output=None,
            error=f"unknown tool: {tool_name}",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at) * 1000.0,
            tool=tool_name,
            raw_result=None,
        )

    args = node.args or {}

    if not validate_tool_node(tool_contract.name, args):
        finished_at = time.time()
        return NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            status='error',
            output=None,
            error='tool args missing required fields',
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at) * 1000.0,
            tool=tool_contract.name,
            raw_result=None,
        )

    cmd = [
        'python3',
        'scripts/tool_executor.py',
        tool_contract.name,
        json.dumps(args, sort_keys=True, separators=(',', ':')),
    ]

    proc = _run_tool_command(cmd, _repo_root())

    if proc.returncode != 0:
        finished_at = time.time()
        message = proc.stderr.strip() or proc.stdout.strip() or 'tool executor failed'
        return NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            status='error',
            output=None,
            error=message,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at) * 1000.0,
            tool=tool_contract.name,
            raw_result=None,
        )

    try:
        payload = json.loads(proc.stdout)
    except Exception:
        finished_at = time.time()
        return NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            status='error',
            output=None,
            error='invalid JSON from tool executor',
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at) * 1000.0,
            tool=tool_contract.name,
            raw_result=None,
        )

    finished_at = time.time()

    if payload.get('status') != 'success':
        return NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            status='error',
            output=None,
            error='tool execution returned non-success status',
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(finished_at - started_at) * 1000.0,
            tool=tool_contract.name,
            raw_result=payload,
        )

    return NodeExecutionResult(
        node_id=node.id,
        node_type=node.type,
        status='success',
        output=payload.get('data'),
        error=None,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=(finished_at - started_at) * 1000.0,
        tool=tool_contract.name,
        raw_result=payload,
    )


def execute_noop_node(node: DagNode) -> NodeExecutionResult:

    started_at = time.time()
    finished_at = time.time()

    return NodeExecutionResult(
        node_id=node.id,
        node_type=node.type,
        status='success',
        output={'message': 'noop completed'},
        error=None,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=(finished_at - started_at) * 1000.0,
        tool=None,
        raw_result={'status': 'success', 'data': {'message': 'noop completed'}},
    )



def execute_dag(dag: DagSpec | dict | str | Path, trace: bool = False) -> DagExecutionResult:

    started_at = time.time()

    dag_spec = _load_dag_input(dag)
    execution_order = dag_to_execution_order(dag_spec)
    nodes_by_id = {node.id: node for node in dag_spec.nodes}

    run = None

    if trace:
        run = create_control_plane_run(
            dag_id=dag_spec.dag_id,
            task=dag_spec.dag_id,
            model='control-plane',
        )

        log_event(
            run,
            'session_start',
            {
                'command': 'dag',
                'input': dag_spec.dag_id,
                'adapter': 'control-plane',
            },
        )

        log_dag_start(
            run,
            dag_spec.dag_id,
            execution_order,
        )

    results: dict[str, NodeExecutionResult] = {}
    final_status: Literal['success', 'error'] = 'success'
    final_error: str | None = None

    try:
        for index, node_id in enumerate(execution_order):
            node = nodes_by_id[node_id]

            if run is not None:
                log_node_start(
                    run,
                    node.id,
                    node.type,
                    node.tool,
                )

            if node.type == 'noop':
                result = execute_noop_node(node)
            elif node.type == 'tool':
                result = execute_tool_node(node)
            elif node.type == 'llm':
                result = NodeExecutionResult(
                    node_id=node.id,
                    node_type=node.type,
                    status='error',
                    output=None,
                    error='llm nodes are not implemented in Stage 4C',
                    started_at=time.time(),
                    finished_at=time.time(),
                    duration_ms=0.0,
                    tool=None,
                    raw_result=None,
                )
            else:
                result = NodeExecutionResult(
                    node_id=node.id,
                    node_type=node.type,
                    status='error',
                    output=None,
                    error=f'unsupported node type: {node.type}',
                    started_at=time.time(),
                    finished_at=time.time(),
                    duration_ms=0.0,
                    tool=None,
                    raw_result=None,
                )

            results[node_id] = result

            if run is not None:
                log_node_result(run, result)

            if result.status != 'success':
                final_status = 'error'
                final_error = result.error

                for skipped_id in execution_order[index + 1:]:
                    skipped_time = time.time()
                    skipped_node = nodes_by_id[skipped_id]
                    skipped = NodeExecutionResult(
                        node_id=skipped_id,
                        node_type=skipped_node.type,
                        status='skipped',
                        output=None,
                        error='skipped due to upstream failure',
                        started_at=skipped_time,
                        finished_at=skipped_time,
                        duration_ms=0.0,
                        tool=skipped_node.tool,
                        raw_result=None,
                    )
                    results[skipped_id] = skipped

                    if run is not None:
                        log_node_result(run, skipped)

                break

    except Exception as exc:
        final_status = 'error'
        final_error = str(exc)

    finished_at = time.time()

    dag_result = DagExecutionResult(
        dag_id=dag_spec.dag_id,
        status=final_status,
        execution_order=execution_order,
        results=results,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=(finished_at - started_at) * 1000.0,
        error=final_error,
        run_id=(run.get('id') if run is not None else None),
        run_path=(run.get('run_path') if run is not None else None),
    )

    if run is not None:
        log_dag_result(run, dag_result)
        finalize_control_plane_run(run, dag_result)

    return dag_result
