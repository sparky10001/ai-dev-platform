#!/usr/bin/env python3
from __future__ import annotations

import re

from core.dag.models import DagSpec
from core.dag.validator import validate_dag
from core.planner.models import PlannerRequest
from core.planner.models import PlannerResult
from tools.registry import validate_tool_node

_WRITE_PATTERN = re.compile(
    r"create\s+(?:a\s+)?file\s+called\s+(?P<path>[^\s]+)\s+with\s+content\s+(?P<quote>['\"])(?P<content>.*?)(?P=quote)",
    re.IGNORECASE,
)
_READ_PATTERN = re.compile(
    r"read\s+(?:file\s+)?(?P<path>[^\s]+)",
    re.IGNORECASE,
)


def noop_dag(task: str, reason: str | None = None) -> DagSpec:
    return validate_dag(
        {
            "dag_id": "plan_noop",
            "version": "1.0",
            "entry": "noop",
            "nodes": [
                {
                    "id": "noop",
                    "type": "noop",
                    "metadata": {"task": task, "reason": reason},
                }
            ],
        }
    )


def _build_write_list(task: str, path: str, content: str) -> DagSpec:
    write_args = {"path": path, "content": content}
    list_args = {"path": "."}
    if not validate_tool_node("write_file", write_args):
        return noop_dag(task, "write_file argument validation failed")
    if not validate_tool_node("list_files", list_args):
        return noop_dag(task, "list_files argument validation failed")
    return validate_dag(
        {
            "dag_id": "plan_write_list",
            "version": "1.0",
            "entry": "write",
            "nodes": [
                {"id": "write", "type": "tool", "tool": "write_file", "args": write_args},
                {
                    "id": "list",
                    "type": "tool",
                    "tool": "list_files",
                    "depends_on": ["write"],
                    "args": list_args,
                },
            ],
        }
    )


def _build_list_files(task: str) -> DagSpec:
    args = {"path": "."}
    if not validate_tool_node("list_files", args):
        return noop_dag(task, "list_files argument validation failed")
    return validate_dag(
        {
            "dag_id": "plan_list_files",
            "version": "1.0",
            "entry": "list",
            "nodes": [{"id": "list", "type": "tool", "tool": "list_files", "args": args}],
        }
    )


def _build_read_file(task: str, path: str) -> DagSpec:
    args = {"path": path}
    if not validate_tool_node("read_file", args):
        return noop_dag(task, "read_file argument validation failed")
    return validate_dag(
        {
            "dag_id": "plan_read_file",
            "version": "1.0",
            "entry": "read",
            "nodes": [{"id": "read", "type": "tool", "tool": "read_file", "args": args}],
        }
    )


def deterministic_plan(task: str) -> DagSpec:
    normalized = task.strip()
    lowered = normalized.lower()

    write_match = _WRITE_PATTERN.search(normalized)
    if write_match and ("list files" in lowered or "show files" in lowered):
        return _build_write_list(
            task=task,
            path=write_match.group("path"),
            content=write_match.group("content"),
        )

    if lowered in {"list files", "show files"}:
        return _build_list_files(task)

    read_match = _READ_PATTERN.fullmatch(normalized)
    if read_match:
        return _build_read_file(task, read_match.group("path"))

    return noop_dag(task, "unsupported deterministic task")


def plan_task(request: PlannerRequest | dict | str) -> PlannerResult:
    try:
        if isinstance(request, PlannerRequest):
            req = request
        elif isinstance(request, dict):
            req = PlannerRequest.model_validate(request)
        elif isinstance(request, str):
            req = PlannerRequest(task=request)
        else:
            return PlannerResult(
                status="error",
                strategy="deterministic",
                error="unsupported planner request type",
            )

        if req.strategy == "noop":
            return PlannerResult(
                status="success",
                strategy=req.strategy,
                dag=noop_dag(req.task, "noop strategy selected"),
                metadata=req.metadata,
            )

        if req.strategy == "deterministic":
            return PlannerResult(
                status="success",
                strategy=req.strategy,
                dag=deterministic_plan(req.task),
                metadata=req.metadata,
            )

        return PlannerResult(
            status="error",
            strategy=req.strategy,
            error=f"unsupported strategy: {req.strategy}",
            metadata=req.metadata,
        )
    except Exception as exc:
        return PlannerResult(status="error", strategy="deterministic", error=str(exc))
