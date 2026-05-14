#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tools.contracts import ToolContract
from tools.contracts import ToolRegistrySnapshot


def _repo_root() -> Path:

    # control-plane/tools/registry.py -> /workspace
    return Path(__file__).resolve().parents[2]


def load_openai_tools() -> list[dict[str, Any]]:

    root = _repo_root()

    cmd = ['python3', 'scripts/tool_executor.py', '--list-tools-openai']

    proc = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            f"tool executor command failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )

    try:
        payload = json.loads(proc.stdout)
    except Exception as exc:
        raise RuntimeError('invalid JSON from tool executor') from exc

    tools = payload.get('tools') if isinstance(payload, dict) else None

    if not isinstance(tools, list):
        raise RuntimeError("tool executor output missing '.tools' list")

    return tools


def normalize_openai_tool(tool: dict[str, Any]) -> ToolContract:

    if not isinstance(tool, dict):
        raise ValueError('OpenAI tool payload must be dict')

    if tool.get('type') != 'function':
        raise ValueError("OpenAI tool payload must have type='function'")

    function = tool.get('function')

    if not isinstance(function, dict):
        raise ValueError("OpenAI tool payload missing 'function' object")

    name = function.get('name')
    description = function.get('description')
    parameters = function.get('parameters')

    if not isinstance(name, str) or not name.strip():
        raise ValueError('OpenAI tool function.name must be a non-empty string')

    if parameters is None:
        parameters = {}

    if not isinstance(parameters, dict):
        raise ValueError('OpenAI tool function.parameters must be an object')

    required = parameters.get('required', [])

    if not isinstance(required, list):
        raise ValueError('OpenAI tool function.parameters.required must be a list')

    return ToolContract(
        name=name,
        description=description if isinstance(description, str) else None,
        parameters_schema=parameters,
        required=[str(item) for item in required],
        source='tool_executor',
        raw=tool,
    )


def build_registry() -> ToolRegistrySnapshot:

    tools = load_openai_tools()
    normalized: dict[str, ToolContract] = {}

    for item in tools:
        contract = normalize_openai_tool(item)

        if contract.name in normalized:
            raise ValueError(f"duplicate tool name: {contract.name}")

        normalized[contract.name] = contract

    return ToolRegistrySnapshot(
        tools=normalized,
        count=len(normalized),
    )


def get_tool(name: str) -> ToolContract:

    registry = build_registry()

    if name not in registry.tools:
        raise KeyError(name)

    return registry.tools[name]


def validate_tool_args(tool: ToolContract, args: dict[str, Any]) -> bool:

    if not isinstance(args, dict):
        return False

    for field in tool.required:
        if field not in args:
            return False

    return True


def validate_tool_node(tool_name: str, args: dict[str, Any]) -> bool:

    tool = get_tool(tool_name)
    return validate_tool_args(tool, args)
