#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from runtime.validator import validate_response


def execute_adapter_command(
    command: list[str],
    timeout: int | float | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    runtime_env = os.environ.copy()
    if env:
        runtime_env.update(env)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=runtime_env,
    )


def parse_adapter_output(stdout: str) -> dict[str, Any]:
    raw = (stdout or '').strip()
    try:
        return json.loads(raw)
    except Exception as exc:
        raise ValueError('Invalid runtime JSON') from exc


def normalize_adapter_response(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return dict(payload)


def validate_adapter_response(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_response(payload).model_dump(mode='json')
    except Exception as exc:
        raise ValueError(f'Invalid adapter contract: {exc}') from exc


def invoke_adapter(
    command: list[str],
    timeout: int | float | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    proc = execute_adapter_command(
        command=command,
        timeout=timeout,
        env=env,
    )
    parsed = parse_adapter_output(proc.stdout or '')
    normalized = normalize_adapter_response(parsed)
    return validate_adapter_response(normalized)