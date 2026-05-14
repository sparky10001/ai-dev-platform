#!/usr/bin/env python3
from __future__ import annotations

from core.policy.models import PolicySpec


DEFAULT_POLICY = PolicySpec(
    policy_id='default',
    allow_tools=[],
    deny_tools=[],
    allow_llm_nodes=False,
    max_nodes=25,
    max_dependencies_per_node=10,
    workspace_boundary=['/workspace'],
)

SAFE_READONLY_POLICY = PolicySpec(
    policy_id='safe-readonly',
    allow_tools=[
        'read_file',
        'list_files',
    ],
    deny_tools=[
        'write_file',
        'run_bash',
    ],
    allow_llm_nodes=False,
    max_nodes=10,
    max_dependencies_per_node=5,
    workspace_boundary=['/workspace'],
)
