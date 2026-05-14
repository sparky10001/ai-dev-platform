#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from core.orchestrator.models import OrchestrationResult
from core.scenarios.models import ControlPlaneScenario
from core.scenarios.models import ControlPlaneScenarioResult


def _json_text(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def evaluate_scenario(
    scenario: ControlPlaneScenario,
    orchestration_result: OrchestrationResult,
) -> ControlPlaneScenarioResult:

    payload = orchestration_result.model_dump(mode='json')
    expect = scenario.expect
    checks: list[dict] = []

    def add_check(name: str, passed: bool, details: dict | None = None):
        checks.append({'name': name, 'passed': passed, 'details': details or {}})

    if expect.status is not None:
        add_check('status', payload.get('status') == expect.status, {'expected': expect.status, 'actual': payload.get('status')})

    if expect.planner_status is not None:
        add_check('planner_status', payload.get('planner_status') == expect.planner_status, {'expected': expect.planner_status, 'actual': payload.get('planner_status')})

    if expect.execution_status is not None:
        add_check('execution_status', payload.get('execution_status') == expect.execution_status, {'expected': expect.execution_status, 'actual': payload.get('execution_status')})

    if expect.dag_id is not None:
        add_check('dag_id', payload.get('dag_id') == expect.dag_id, {'expected': expect.dag_id, 'actual': payload.get('dag_id')})

    node_results = payload.get('node_results') or {}

    actual_tools: list[str] = []
    for _nid, nres in node_results.items():
        tool = nres.get('tool')
        if isinstance(tool, str) and tool:
            actual_tools.append(tool)
        else:
            raw = nres.get('raw_result')
            if isinstance(raw, dict):
                meta = raw.get('meta')
                if isinstance(meta, dict) and isinstance(meta.get('tool'), str):
                    actual_tools.append(meta['tool'])

    if expect.tools_used:
        ok = all(tool in actual_tools for tool in expect.tools_used)
        add_check('tools_used', ok, {'expected': expect.tools_used, 'actual': actual_tools})

    executed_nodes = [nid for nid, nres in node_results.items() if nres.get('status') in {'success', 'error'}]
    skipped_nodes = [nid for nid, nres in node_results.items() if nres.get('status') == 'skipped']

    if expect.nodes_executed:
        ok = all(node in executed_nodes for node in expect.nodes_executed)
        add_check('nodes_executed', ok, {'expected': expect.nodes_executed, 'actual': executed_nodes})

    if expect.nodes_skipped:
        ok = all(node in skipped_nodes for node in expect.nodes_skipped)
        add_check('nodes_skipped', ok, {'expected': expect.nodes_skipped, 'actual': skipped_nodes})

    if expect.requires_run_artifact:
        run_id = payload.get('run_id')
        run_path = payload.get('run_path')
        trace_exists = False
        if isinstance(run_path, str) and run_path:
            trace_exists = (Path(run_path) / 'trace.jsonl').exists()
        ok = bool(run_id) and bool(run_path) and trace_exists
        add_check('requires_run_artifact', ok, {'run_id': run_id, 'run_path': run_path, 'trace_exists': trace_exists})

    if expect.output_contains:
        full_text = _json_text(payload)
        ok = all(fragment in full_text for fragment in expect.output_contains)
        add_check('output_contains', ok, {'expected': expect.output_contains})

    if expect.policy_violation_codes:
        policy = ((payload.get('metadata') or {}).get('policy') or {})
        violations = policy.get('violations') or []
        actual_codes = [v.get('code') for v in violations if isinstance(v, dict)]
        ok = all(code in actual_codes for code in expect.policy_violation_codes)
        add_check('policy_violation_codes', ok, {'expected': expect.policy_violation_codes, 'actual': actual_codes})

    total = len(checks)
    passed = sum(1 for c in checks if c['passed'])
    # Chosen behavior: with zero configured checks, score is 1.0 (vacuous pass).
    score = 1.0 if total == 0 else (passed / total)
    status = 'passed' if passed == total else 'failed'

    return ControlPlaneScenarioResult(
        scenario_id=scenario.scenario_id,
        status=status,
        score=score,
        passed=passed,
        total=total,
        checks=checks,
        orchestration_result=payload,
    )
