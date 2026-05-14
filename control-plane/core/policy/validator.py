#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from core.dag.models import DagSpec
from core.policy.defaults import DEFAULT_POLICY
from core.policy.models import PolicySpec
from core.policy.models import PolicyValidationResult
from core.policy.models import PolicyViolation


def validate_policy(policy: PolicySpec | dict | None) -> PolicySpec:
    if policy is None:
        return DEFAULT_POLICY
    if isinstance(policy, PolicySpec):
        return policy
    if isinstance(policy, dict):
        return PolicySpec.model_validate(policy)
    raise TypeError('policy must be PolicySpec, dict, or None')


def _is_path_within_boundary(raw_path: str, boundaries: list[str]) -> bool:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = Path('/workspace') / candidate

    normalized = candidate.resolve(strict=False)

    for root in boundaries:
        root_path = Path(root).resolve(strict=False)
        try:
            normalized.relative_to(root_path)
            return True
        except Exception:
            continue

    return False


def validate_dag_against_policy(
    dag: DagSpec,
    policy: PolicySpec | dict | None = None,
) -> PolicyValidationResult:

    spec = validate_policy(policy)
    violations: list[PolicyViolation] = []

    if len(dag.nodes) > spec.max_nodes:
        violations.append(
            PolicyViolation(
                code='max_nodes_exceeded',
                message=f'dag node count {len(dag.nodes)} exceeds max_nodes {spec.max_nodes}',
            )
        )

    for node in dag.nodes:
        if len(node.depends_on) > spec.max_dependencies_per_node:
            violations.append(
                PolicyViolation(
                    code='max_dependencies_exceeded',
                    message=(
                        f"node '{node.id}' dependency count {len(node.depends_on)} exceeds "
                        f"max_dependencies_per_node {spec.max_dependencies_per_node}"
                    ),
                    node_id=node.id,
                    tool=node.tool,
                )
            )

        if node.type == 'llm' and not spec.allow_llm_nodes:
            violations.append(
                PolicyViolation(
                    code='llm_nodes_not_allowed',
                    message='llm nodes are not allowed by policy',
                    node_id=node.id,
                )
            )

        if node.type == 'tool':
            tool_name = node.tool or ''

            if spec.allow_tools and tool_name not in spec.allow_tools:
                violations.append(
                    PolicyViolation(
                        code='tool_not_allowlisted',
                        message=f"tool '{tool_name}' is not in allow_tools",
                        node_id=node.id,
                        tool=tool_name,
                    )
                )

            if tool_name in spec.deny_tools:
                violations.append(
                    PolicyViolation(
                        code='tool_denied',
                        message=f"tool '{tool_name}' is denied by policy",
                        node_id=node.id,
                        tool=tool_name,
                    )
                )

            if isinstance(node.args, dict) and 'path' in node.args:
                path_value = node.args.get('path')
                if isinstance(path_value, str):
                    if not _is_path_within_boundary(path_value, spec.workspace_boundary):
                        violations.append(
                            PolicyViolation(
                                code='path_outside_workspace_boundary',
                                message=f"path '{path_value}' is outside workspace boundary",
                                node_id=node.id,
                                tool=tool_name,
                            )
                        )
                else:
                    violations.append(
                        PolicyViolation(
                            code='invalid_path_argument',
                            message='path argument must be a string when provided',
                            node_id=node.id,
                            tool=tool_name,
                        )
                    )

    status = 'success' if not violations else 'error'

    return PolicyValidationResult(
        status=status,
        violations=violations,
        policy_id=spec.policy_id,
        dag_id=dag.dag_id,
    )
