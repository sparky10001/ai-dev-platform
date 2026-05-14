#!/usr/bin/env python3
from __future__ import annotations

from core.evals.models import OrchestrationEvaluation
from core.evals.models import OrchestrationMetric
from core.replay.models import ReplayDag


def evaluate_replay(replay: ReplayDag) -> OrchestrationEvaluation:
    total = replay.summary.total_nodes
    successful = replay.summary.successful_nodes
    failed = replay.summary.failed_nodes
    skipped = replay.summary.skipped_nodes
    executed = successful + failed
    tool_count = len(replay.summary.tools_used)
    trace_available = len(replay.events) > 0

    success_rate = (successful / total) if total else 0.0
    execution_completeness = (executed / total) if total else 0.0

    metrics = [
        OrchestrationMetric(name='duration_ms', value=replay.summary.duration_ms, passed=replay.summary.duration_ms is not None),
        OrchestrationMetric(name='execution_completeness', value=execution_completeness, passed=execution_completeness >= 0.5 if total else True),
        OrchestrationMetric(name='failure_count', value=failed, passed=failed == 0),
        OrchestrationMetric(name='skipped_count', value=skipped, passed=skipped == 0),
        OrchestrationMetric(name='success_rate', value=success_rate, passed=success_rate >= 0.5 if total else True),
        OrchestrationMetric(name='tool_count', value=tool_count, passed=True),
        OrchestrationMetric(name='trace_available', value=trace_available, passed=trace_available),
    ]

    # Deterministic weighted score in [0,1]:
    # 50% success_rate + 30% execution_completeness + 20% (1 if no failures else 0)
    score = (0.5 * success_rate) + (0.3 * execution_completeness) + (0.2 * (1.0 if failed == 0 else 0.0))
    score = max(0.0, min(1.0, float(score)))

    status = 'success' if replay.summary.status in {'success', 'done'} and failed == 0 else 'error'

    return OrchestrationEvaluation(
        evaluation_id=f"eval_{replay.summary.run_id}",
        run_id=replay.summary.run_id,
        dag_id=replay.summary.dag_id,
        status=status,
        score=score,
        metrics=metrics,
        metadata={'total_nodes': total},
    )
