#!/usr/bin/env python3
from __future__ import annotations

from core.memory.models import MemoryRecord
from core.memory.models import MemoryTimeline


def reconstruct_execution_timeline(
    records: list[MemoryRecord],
) -> list[MemoryRecord]:

    return sorted(records, key=lambda r: ((r.created_at if r.created_at is not None else float('inf')), (r.run_id or '')))


def summarize_memory_timeline(
    timeline: MemoryTimeline,
) -> dict:

    planner_freq: dict[str, int] = {}
    policy_freq: dict[str, int] = {}

    successful = 0
    failed = 0

    for r in timeline.records:
        if r.status in {'success', 'done'}:
            successful += 1
        elif r.status == 'error':
            failed += 1

        if r.planner_strategy:
            planner_freq[r.planner_strategy] = planner_freq.get(r.planner_strategy, 0) + 1
        if r.policy_id:
            policy_freq[r.policy_id] = policy_freq.get(r.policy_id, 0) + 1

    return {
        'total_records': timeline.total_records,
        'successful_records': successful,
        'failed_records': failed,
        'planner_frequencies': {k: planner_freq[k] for k in sorted(planner_freq.keys())},
        'policy_frequencies': {k: policy_freq[k] for k in sorted(policy_freq.keys())},
    }
