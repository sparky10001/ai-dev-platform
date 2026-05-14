#!/usr/bin/env python3
from __future__ import annotations

from core.dag.executor import execute_dag
from core.orchestrator.models import OrchestrationRequest
from core.orchestrator.models import OrchestrationResult
from core.planner.planner import plan_task


def orchestrate_task(request: OrchestrationRequest | dict | str) -> OrchestrationResult:

    try:
        if isinstance(request, OrchestrationRequest):
            req = request
        elif isinstance(request, dict):
            req = OrchestrationRequest.model_validate(request)
        elif isinstance(request, str):
            req = OrchestrationRequest(task=request)
        else:
            return OrchestrationResult(
                status='error',
                task='',
                planner_status='error',
                execution_status='skipped',
                planner_error='unsupported orchestration request type',
            )
    except Exception as exc:
        return OrchestrationResult(
            status='error',
            task=request if isinstance(request, str) else '',
            planner_status='error',
            execution_status='skipped',
            planner_error=str(exc),
        )

    plan = plan_task(
        {
            'task': req.task,
            'strategy': req.planner_strategy,
            'metadata': req.metadata,
        }
    )

    if plan.status != 'success':
        return OrchestrationResult(
            status='error',
            task=req.task,
            planner_status='error',
            execution_status='skipped',
            planner_error=plan.error,
            metadata=req.metadata,
        )

    if plan.dag is None:
        return OrchestrationResult(
            status='error',
            task=req.task,
            planner_status='error',
            execution_status='skipped',
            planner_error='planner returned no dag',
            metadata=req.metadata,
        )

    execution = execute_dag(plan.dag, trace=req.trace)

    node_results = {
        node_id: node_result.model_dump(mode='json')
        for node_id, node_result in execution.results.items()
    }

    success = execution.status == 'success'

    return OrchestrationResult(
        status='success' if success else 'error',
        task=req.task,
        planner_status='success',
        execution_status=execution.status,
        dag_id=execution.dag_id,
        run_id=getattr(execution, 'run_id', None),
        run_path=getattr(execution, 'run_path', None),
        planner_error=None,
        execution_error=execution.error,
        execution_order=list(execution.execution_order),
        node_results=node_results,
        metadata=req.metadata,
    )
