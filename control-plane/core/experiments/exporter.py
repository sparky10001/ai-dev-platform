#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.experiments.models import ExperimentManifest
from core.experiments.models import ReplayDataset


def export_manifest_json(manifest: ExperimentManifest, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_dataset_json(dataset: ReplayDataset, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dataset.model_dump(mode='json'), sort_keys=True, indent=2), encoding='utf-8')
    return str(p)


def export_manifest_markdown(manifest: ExperimentManifest, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        '# Experiment Manifest',
        '',
        f"- experiment id: `{manifest.experiment_id}`",
        f"- total runs: `{manifest.total_runs}`",
        f"- average score: `{manifest.average_score}`",
        f"- tags: `{manifest.tags}`",
        '',
        '| run_id | dag_id | status | score |',
        '|---|---|---|---|',
    ]

    for r in sorted(manifest.runs, key=lambda x: x.run_id):
        lines.append(f"| {r.run_id} | {r.dag_id or ''} | {r.status or ''} | {r.score if r.score is not None else ''} |")

    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return str(p)
