#!/usr/bin/env python3
from __future__ import annotations

from core.evals.evaluator import evaluate_replay
from core.evals.models import ReplayComparison
from core.replay.models import ReplayDag


def compare_replays(left: ReplayDag, right: ReplayDag) -> ReplayComparison:
    left_eval = evaluate_replay(left)
    right_eval = evaluate_replay(right)

    differences: list[dict] = []

    status_changed = left.summary.status != right.summary.status
    if status_changed:
        differences.append({'field': 'status', 'left': left.summary.status, 'right': right.summary.status})

    left_tools = sorted(left.summary.tools_used)
    right_tools = sorted(right.summary.tools_used)
    tool_delta = sorted(set(left_tools).symmetric_difference(set(right_tools)))
    if tool_delta:
        differences.append({'field': 'tools_used', 'left': left_tools, 'right': right_tools, 'delta': tool_delta})

    execution_order_changed = list(left.summary.execution_order) != list(right.summary.execution_order)
    if execution_order_changed:
        differences.append({'field': 'execution_order', 'left': left.summary.execution_order, 'right': right.summary.execution_order})

    node_count_delta = left.summary.total_nodes - right.summary.total_nodes
    if node_count_delta != 0:
        differences.append({'field': 'node_count', 'left': left.summary.total_nodes, 'right': right.summary.total_nodes, 'delta': node_count_delta})

    left_failed = sorted([nid for nid, n in left.nodes.items() if n.status == 'error'])
    right_failed = sorted([nid for nid, n in right.nodes.items() if n.status == 'error'])
    if left_failed != right_failed:
        differences.append({'field': 'failed_nodes', 'left': left_failed, 'right': right_failed})

    left_skipped = sorted([nid for nid, n in left.nodes.items() if n.status == 'skipped'])
    right_skipped = sorted([nid for nid, n in right.nodes.items() if n.status == 'skipped'])
    if left_skipped != right_skipped:
        differences.append({'field': 'skipped_nodes', 'left': left_skipped, 'right': right_skipped})

    score_delta = right_eval.score - left_eval.score
    if abs(score_delta) > 1e-12:
        differences.append({'field': 'score', 'left': left_eval.score, 'right': right_eval.score, 'delta': score_delta})

    identical = len(differences) == 0

    return ReplayComparison(
        comparison_id=f"cmp_{left.summary.run_id}_vs_{right.summary.run_id}",
        left_run_id=left.summary.run_id,
        right_run_id=right.summary.run_id,
        identical=identical,
        score_delta=score_delta,
        tool_delta=tool_delta,
        execution_order_changed=execution_order_changed,
        node_count_delta=node_count_delta,
        status_changed=status_changed,
        differences=differences,
        metadata={},
    )
