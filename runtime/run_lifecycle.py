#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from runtime.events import log_event
from runtime.run import create_run
from runtime.run import finalize_run as finalize_run_record
from runtime.validator import validate_response


def build_response(
    message: Any,
    *,
    status: str = "error",
    run_id: str | None = None,
    run_path: str | None = None,
    adapter: str = "engine.py",
    error: bool = True,
):
    return validate_response({
        "status": status,
        "output": message,
        "meta": {
            "adapter": adapter,
            "error": error,
            "run_id": run_id or "no_run",
            "run_path": run_path or "",
        },
    })


def initialize_run(task: str, command: str, model: str) -> dict[str, Any]:
    return create_run(task=task, command=command, model=model)


def start_run(run: dict[str, Any], command: str, user_input: str, model: str) -> None:
    log_event(
        run,
        "session_start",
        {
            "command": command,
            "input": user_input,
            "model": model,
        },
    )


def record_agent_output(run: dict[str, Any], status: str, output: Any) -> None:
    log_event(
        run,
        "agent_output",
        {
            "status": status,
            "output": output,
        },
    )


def finalize_run(run: dict[str, Any], status: str, result: dict[str, Any]) -> None:
    log_event(
        run,
        "session_end",
        {
            "status": status,
        },
    )
    finalize_run_record(run, result)


def fail_run(run: dict[str, Any], message: str):
    result = build_response(
        message,
        status="error",
        run_id=run.get("id"),
        run_path=run.get("run_path"),
        adapter="engine.py",
        error=True,
    )

    try:
        record_agent_output(run, "error", message)
        log_event(
            run,
            "session_end",
            {
                "status": "error",
            },
        )
    except Exception:
        pass

    try:
        finalize_run_record(run, result.model_dump(mode="json"))
    except Exception:
        pass

    return result
