#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from runtime.events import log_event
from runtime.run import create_run
from runtime.run import finalize_run
from runtime.validator import validate_response


def create_control_plane_run(
    dag_id: str,
    task: str | None = None,
    model: str = 'control-plane',
) -> dict:

    return create_run(
        task=task or dag_id,
        command='dag',
        model=model,
    )


def log_dag_start(run: dict, dag_id: str, execution_order: list[str]) -> None:

    log_event(
        run,
        'dag_start',
        {
            'dag_id': dag_id,
            'execution_order': execution_order,
        },
    )


def log_node_start(
    run: dict,
    node_id: str,
    node_type: str,
    tool: str | None = None,
) -> None:

    log_event(
        run,
        'dag_node_start',
        {
            'node_id': node_id,
            'node_type': node_type,
            'tool': tool,
        },
    )


def log_node_result(run: dict, node_result) -> None:

    log_event(
        run,
        'dag_node_result',
        {
            'node_id': node_result.node_id,
            'node_type': node_result.node_type,
            'status': node_result.status,
            'output': node_result.output,
            'error': node_result.error,
            'duration_ms': node_result.duration_ms,
            'tool': node_result.tool,
            'raw_result': node_result.raw_result,
        },
    )


def log_dag_result(run: dict, result) -> None:

    log_event(
        run,
        'dag_result',
        {
            'dag_id': result.dag_id,
            'status': result.status,
            'execution_order': result.execution_order,
            'duration_ms': result.duration_ms,
            'error': result.error,
        },
    )


def finalize_control_plane_run(run: dict, result) -> dict:

    response_status = 'done' if result.status == 'success' else 'error'

    validated = validate_response(
        {
            'schema_version': 1,
            'status': response_status,
            'output': 'dag_completed' if result.status == 'success' else 'dag_failed',
            'meta': {
                'adapter': 'control-plane',
                'run_id': run['id'],
                'run_path': run['run_path'],
                'mode': 'dag',
                'error': result.status != 'success',
                'dag_id': result.dag_id,
                'execution_order': result.execution_order,
            },
        }
    )

    log_event(
        run,
        'agent_output',
        {
            'status': response_status,
            'output': validated.output,
            'meta': {
                'dag_id': result.dag_id,
                'execution_order': result.execution_order,
            },
        },
    )

    log_event(
        run,
        'session_end',
        {
            'status': response_status,
            'duration_ms': result.duration_ms,
        },
    )

    payload = validated.model_dump(mode='json')
    finalize_run(run, payload)

    return payload
