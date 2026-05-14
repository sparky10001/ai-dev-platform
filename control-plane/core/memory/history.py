#!/usr/bin/env python3
from __future__ import annotations

import time

from core.evals.models import OrchestrationEvaluation
from core.memory.models import MemoryRecord
from core.memory.models import MemoryTimeline
from core.replay.models import ReplayDag


def replay_to_memory_record(
    replay: ReplayDag,
    evaluation: OrchestrationEvaluation | None = None,
) -> MemoryRecord:

    md = replay.summary.metadata if isinstance(replay.summary.metadata, dict) else {}
    planner = md.get('planner_strategy') if isinstance(md.get('planner_strategy'), str) else None
    policy = md.get('policy_id') if isinstance(md.get('policy_id'), str) else None
    task = md.get('task') if isinstance(md.get('task'), str) else None

    return MemoryRecord(
        memory_id=f"mem_{replay.summary.run_id}",
        run_id=replay.summary.run_id,
        task=task,
        planner_strategy=planner,
        policy_id=policy,
        score=(evaluation.score if evaluation else None),
        status=(evaluation.status if evaluation else replay.summary.status),
        created_at=replay.summary.started_at,
        metadata={'run_path': replay.summary.run_path, 'dag_id': replay.summary.dag_id},
    )


def build_memory_timeline(
    records: list[MemoryRecord],
    timeline_id: str = 'timeline',
) -> MemoryTimeline:

    ordered = sorted(records, key=lambda r: ((r.created_at if r.created_at is not None else float('inf')), (r.run_id or '')))
    return MemoryTimeline(
        timeline_id=timeline_id,
        created_at=time.time(),
        total_records=len(ordered),
        records=ordered,
        metadata={},
    )
