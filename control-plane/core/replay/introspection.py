#!/usr/bin/env python3
from __future__ import annotations

from core.replay.models import ReplayDag
from core.replay.models import ReplayDagSummary


def summarize_replay(replay: ReplayDag) -> ReplayDagSummary:
    return replay.summary


def list_tools_used(replay: ReplayDag) -> list[str]:
    return sorted({n.tool for n in replay.nodes.values() if isinstance(n.tool, str) and n.tool})


def get_failed_nodes(replay: ReplayDag) -> list[str]:
    return sorted([nid for nid, n in replay.nodes.items() if n.status == 'error'])


def get_skipped_nodes(replay: ReplayDag) -> list[str]:
    return sorted([nid for nid, n in replay.nodes.items() if n.status == 'skipped'])


def get_execution_order(replay: ReplayDag) -> list[str]:
    if replay.summary.execution_order:
        return list(replay.summary.execution_order)
    return sorted(replay.nodes.keys())


def build_lineage_graph(replay: ReplayDag) -> dict[str, list[str]]:
    order = get_execution_order(replay)
    graph: dict[str, list[str]] = {nid: [] for nid in sorted(replay.nodes.keys())}
    for i in range(len(order) - 1):
        src = order[i]
        dst = order[i + 1]
        if src not in graph:
            graph[src] = []
        if dst not in graph:
            graph[dst] = []
        graph[src].append(dst)
    for k in sorted(graph.keys()):
        graph[k] = sorted(graph[k])
    return {k: graph[k] for k in sorted(graph.keys())}
