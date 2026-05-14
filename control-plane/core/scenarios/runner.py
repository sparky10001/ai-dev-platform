#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.orchestrator.orchestrator import orchestrate_task
from core.policy.defaults import DEFAULT_POLICY
from core.policy.defaults import SAFE_READONLY_POLICY
from core.scenarios.evaluator import evaluate_scenario
from core.scenarios.models import ControlPlaneScenario
from core.scenarios.models import ControlPlaneScenarioResult


def load_scenario(path: str | Path) -> ControlPlaneScenario:
    scenario_path = Path(path)
    payload = json.loads(scenario_path.read_text(encoding='utf-8'))
    return ControlPlaneScenario.model_validate(payload)


def _resolve_policy(policy_name: str | None):
    if policy_name is None:
        return None
    if policy_name == 'default':
        return DEFAULT_POLICY.model_dump(mode='json')
    if policy_name == 'safe-readonly':
        return SAFE_READONLY_POLICY.model_dump(mode='json')
    raise ValueError(f'unsupported scenario policy: {policy_name}')


def run_scenario(path: str | Path) -> ControlPlaneScenarioResult:
    scenario = load_scenario(path)

    orchestration = orchestrate_task(
        {
            'task': scenario.task,
            'planner_strategy': scenario.strategy,
            'trace': scenario.trace,
            'policy': _resolve_policy(scenario.policy),
        }
    )

    return evaluate_scenario(scenario, orchestration)
