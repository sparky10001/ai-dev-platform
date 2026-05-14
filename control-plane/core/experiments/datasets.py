#!/usr/bin/env python3
from __future__ import annotations

import time

from core.evals.models import OrchestrationEvaluation
from core.experiments.models import ReplayDataset
from core.experiments.models import ReplayDatasetEntry
from core.replay.models import ReplayDag


def replay_to_dataset_entry(
    replay: ReplayDag,
    evaluation: OrchestrationEvaluation | None = None,
) -> ReplayDatasetEntry:

    return ReplayDatasetEntry(
        run_id=replay.summary.run_id,
        dag_id=replay.summary.dag_id,
        task=(replay.summary.metadata.get('task') if isinstance(replay.summary.metadata, dict) else None),
        status=(evaluation.status if evaluation else replay.summary.status),
        tools_used=list(sorted(set(replay.summary.tools_used))),
        score=(evaluation.score if evaluation else None),
        metadata={'run_path': replay.summary.run_path},
    )


def build_replay_dataset(
    replays: list[ReplayDag],
    evaluations: list[OrchestrationEvaluation] | None = None,
    dataset_id: str = 'dataset',
) -> ReplayDataset:

    eval_map = {}
    if evaluations:
        for ev in evaluations:
            if ev.run_id:
                eval_map[ev.run_id] = ev

    ordered = sorted(replays, key=lambda r: r.summary.run_id)
    entries = [
        replay_to_dataset_entry(r, evaluation=eval_map.get(r.summary.run_id))
        for r in ordered
    ]

    return ReplayDataset(
        dataset_id=dataset_id,
        created_at=time.time(),
        total_entries=len(entries),
        entries=entries,
        metadata={},
    )
