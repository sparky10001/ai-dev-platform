#!/usr/bin/env python3
###################################################################
# runtime/datasets.py
#
# Phase 3D Runtime Dataset + Export Layer
#
# Responsibilities:
# - canonical NDJSON run exports
# - replay-safe trace corpus exports
# - replay-derived evaluation datasets
# - deterministic filesystem-native serialization
#
###################################################################

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Iterable

from pydantic import BaseModel

from runtime.evals import evaluate_run
from runtime.loader import load_full_run
from runtime.registry import query_runs
from runtime.schemas import DatasetRecord
from runtime.schemas import EvalDatasetRecord
from runtime.schemas import TraceDatasetRecord


# ================================================================
# Serialization
# ================================================================

def _json_line(record: BaseModel) -> str:

    return json.dumps(
        record.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_jsonl(records: Iterable[BaseModel], output_path: str | Path) -> Path:

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(_json_line(record))
            f.write("\n")

    return path


def _event_dict(event) -> dict[str, Any]:

    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")

    return dict(event)


def _dataset_record(run_id: str) -> DatasetRecord:

    bundle = load_full_run(run_id)
    summary = evaluate_run(run_id)

    trace = [
        _event_dict(event)
        for event in bundle["trace"]
    ]

    return DatasetRecord(
        run_id=run_id,
        run=bundle["run"],
        result=bundle["result"],
        eval=summary,
        trace=trace,
    )


def _sorted_run_ids(run_ids: Iterable[str]) -> list[str]:

    return sorted(str(run_id) for run_id in run_ids)


# ================================================================
# Run Exports
# ================================================================

def export_run(run_id: str, output_path: str | Path) -> Path:

    return _write_jsonl(
        [_dataset_record(run_id)],
        output_path,
    )


def export_runs(run_ids: Iterable[str], output_path: str | Path) -> Path:

    records = [
        _dataset_record(run_id)
        for run_id in _sorted_run_ids(run_ids)
    ]

    return _write_jsonl(
        records,
        output_path,
    )


def export_query(query_filters: dict[str, Any] | None, output_path: str | Path) -> Path:

    filters = query_filters or {}
    query = query_runs(**filters)

    return export_runs(
        [run["id"] for run in query.runs if isinstance(run.get("id"), str)],
        output_path,
    )


# ================================================================
# Dataset Builders
# ================================================================

def build_eval_dataset(
    run_ids: Iterable[str] | None = None,
    output_path: str | Path | None = None,
    **query_filters,
) -> list[EvalDatasetRecord] | Path:

    if run_ids is None:
        query = query_runs(**query_filters)
        selected = [run["id"] for run in query.runs if isinstance(run.get("id"), str)]
    else:
        selected = _sorted_run_ids(run_ids)

    records = [
        EvalDatasetRecord(
            run_id=run_id,
            eval=evaluate_run(run_id),
        )
        for run_id in _sorted_run_ids(selected)
    ]

    if output_path is None:
        return records

    return _write_jsonl(records, output_path)


def build_trace_dataset(
    run_ids: Iterable[str] | None = None,
    output_path: str | Path | None = None,
    **query_filters,
) -> list[TraceDatasetRecord] | Path:

    if run_ids is None:
        query = query_runs(**query_filters)
        selected = [run["id"] for run in query.runs if isinstance(run.get("id"), str)]
    else:
        selected = _sorted_run_ids(run_ids)

    records: list[TraceDatasetRecord] = []

    for run_id in _sorted_run_ids(selected):
        bundle = load_full_run(run_id)

        for index, event in enumerate(bundle["trace"]):
            records.append(
                TraceDatasetRecord(
                    run_id=run_id,
                    event_index=index,
                    event=_event_dict(event),
                )
            )

    if output_path is None:
        return records

    return _write_jsonl(records, output_path)
