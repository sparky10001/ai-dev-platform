#!/usr/bin/env python3
from __future__ import annotations

from core.evals.models import OrchestrationEvaluation
from core.experiments.manifests import create_experiment_manifest
from core.experiments.models import ExperimentManifest
from core.experiments.models import ExperimentRun
from core.replay.models import ReplayDag


def track_replay(
    replay: ReplayDag,
    evaluation: OrchestrationEvaluation | None = None,
    scenario_id: str | None = None,
    benchmark_id: str | None = None,
) -> ExperimentRun:

    return ExperimentRun(
        run_id=replay.summary.run_id,
        dag_id=replay.summary.dag_id,
        scenario_id=scenario_id,
        evaluation_id=(evaluation.evaluation_id if evaluation else None),
        benchmark_id=benchmark_id,
        score=(evaluation.score if evaluation else None),
        status=(evaluation.status if evaluation else replay.summary.status),
        created_at=replay.summary.started_at,
        metadata={'run_path': replay.summary.run_path},
    )


def track_replays(
    replays: list[ReplayDag],
    evaluations: list[OrchestrationEvaluation] | None = None,
    experiment_id: str = 'experiment',
    tags: list[str] | None = None,
) -> ExperimentManifest:

    eval_map = {}
    if evaluations:
        for ev in evaluations:
            if ev.run_id:
                eval_map[ev.run_id] = ev

    runs = [
        track_replay(r, evaluation=eval_map.get(r.summary.run_id))
        for r in sorted(replays, key=lambda x: x.summary.run_id)
    ]

    return create_experiment_manifest(experiment_id=experiment_id, runs=runs, tags=tags)
