#!/usr/bin/env python3
from __future__ import annotations

import time

from core.experiments.models import ExperimentManifest
from core.experiments.models import ExperimentRun


def create_experiment_manifest(
    experiment_id: str,
    runs: list[ExperimentRun],
    tags: list[str] | None = None,
) -> ExperimentManifest:

    ordered_runs = sorted(runs, key=lambda r: r.run_id)
    scored = [r.score for r in ordered_runs if isinstance(r.score, (int, float))]
    average_score = (sum(float(s) for s in scored) / len(scored)) if scored else 0.0

    return ExperimentManifest(
        experiment_id=experiment_id,
        created_at=time.time(),
        total_runs=len(ordered_runs),
        average_score=average_score,
        tags=sorted(tags) if tags else [],
        runs=ordered_runs,
        metadata={},
    )
