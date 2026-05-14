#!/usr/bin/env python3
from __future__ import annotations

from core.memory.models import MemoryRecord
from core.memory.models import MemoryRetrievalResult


def _contains(hay: str | None, needle: str) -> bool:
    return isinstance(hay, str) and needle in hay.lower()


def retrieve_memory_records(
    records: list[MemoryRecord],
    query: str,
    limit: int = 10,
) -> MemoryRetrievalResult:

    q = query.lower().strip()

    scored: list[tuple[int, MemoryRecord]] = []
    for r in records:
        rank = 100
        task = r.task.lower() if isinstance(r.task, str) else ''
        planner = r.planner_strategy.lower() if isinstance(r.planner_strategy, str) else ''
        policy = r.policy_id.lower() if isinstance(r.policy_id, str) else ''
        status = r.status.lower() if isinstance(r.status, str) else ''

        if q and task == q:
            rank = 0
        elif q and q in planner:
            rank = 1
        elif q and q in policy:
            rank = 2
        elif q and q in status:
            rank = 3
        elif q and q in task:
            rank = 4

        if rank < 100:
            scored.append((rank, r))

    scored.sort(key=lambda x: (x[0], x[1].run_id or ''))
    matched = [r for _, r in scored[: max(0, limit)]]

    return MemoryRetrievalResult(
        retrieval_id=f"retrieval_{abs(hash(query)) % 1000000}",
        query=query,
        matched_records=matched,
        total_matches=len(matched),
        metadata={'limit': limit},
    )
