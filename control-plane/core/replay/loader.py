#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from core.replay.models import ReplayDag
from core.replay.models import ReplayDagSummary
from core.replay.models import ReplayNodeResult
from core.runtime_events import load_control_plane_runtime_events


def _to_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def load_orchestration_trace(run_path: str | Path) -> ReplayDag:

    run_dir = Path(run_path)
    events: list[dict] = load_control_plane_runtime_events(run_dir, strict=False)

    run_id = run_dir.name
    for evt in events:
        rid = evt.get('run_id')
        if isinstance(rid, str) and rid:
            run_id = rid
            break

    nodes: dict[str, ReplayNodeResult] = {}
    dag_id: str | None = None
    status = 'unknown'
    execution_order: list[str] = []
    started_at = None
    completed_at = None

    for evt in events:
        et = evt.get('event')
        data = evt.get('data') if isinstance(evt.get('data'), dict) else {}
        ts = _to_float(evt.get('timestamp'))

        if et == 'session_start' and started_at is None:
            started_at = ts

        if et == 'session_end':
            completed_at = ts
            s = data.get('status')
            if isinstance(s, str) and s:
                status = s

        if et == 'dag_start':
            d = data.get('dag_id')
            if isinstance(d, str) and d:
                dag_id = d
            eo = data.get('execution_order')
            if isinstance(eo, list):
                execution_order = [str(x) for x in eo]

        if et == 'dag_node_start':
            nid = data.get('node_id')
            if not isinstance(nid, str) or not nid:
                continue
            tool = data.get('tool') if isinstance(data.get('tool'), str) else None
            if nid not in nodes:
                nodes[nid] = ReplayNodeResult(node_id=nid, status='unknown', tool=tool, started_at=ts, raw_event_count=1)
            else:
                node = nodes[nid]
                if node.started_at is None:
                    node.started_at = ts
                if node.tool is None and tool:
                    node.tool = tool
                node.raw_event_count += 1

        if et == 'dag_node_result':
            nid = data.get('node_id')
            if not isinstance(nid, str) or not nid:
                continue
            st = data.get('status') if isinstance(data.get('status'), str) else 'unknown'
            tool = data.get('tool') if isinstance(data.get('tool'), str) else None
            if nid not in nodes:
                nodes[nid] = ReplayNodeResult(node_id=nid, status=st, tool=tool, completed_at=ts, output=data.get('output'), raw_event_count=1, metadata={'error': data.get('error')})
            else:
                node = nodes[nid]
                node.status = st
                if node.tool is None and tool:
                    node.tool = tool
                node.completed_at = ts
                node.output = data.get('output')
                node.raw_event_count += 1
                node.metadata['error'] = data.get('error')

        if et == 'dag_result':
            d = data.get('dag_id')
            if isinstance(d, str) and d:
                dag_id = d
            s = data.get('status')
            if isinstance(s, str) and s:
                status = s
            eo = data.get('execution_order')
            if isinstance(eo, list):
                execution_order = [str(x) for x in eo]

    if status == 'unknown':
        statuses = [n.status for n in nodes.values()]
        if any(s == 'error' for s in statuses):
            status = 'error'
        elif statuses and all(s in {'success', 'skipped'} for s in statuses):
            status = 'success'

    success_count = sum(1 for n in nodes.values() if n.status == 'success')
    failed_count = sum(1 for n in nodes.values() if n.status == 'error')
    skipped_count = sum(1 for n in nodes.values() if n.status == 'skipped')

    tools = sorted({n.tool for n in nodes.values() if isinstance(n.tool, str) and n.tool})

    duration_ms = None
    if started_at is not None and completed_at is not None:
        duration_ms = (completed_at - started_at) * 1000.0

    summary = ReplayDagSummary(
        dag_id=dag_id,
        run_id=run_id,
        run_path=str(run_dir),
        status=status,
        total_nodes=len(nodes),
        successful_nodes=success_count,
        failed_nodes=failed_count,
        skipped_nodes=skipped_count,
        tools_used=tools,
        execution_order=execution_order,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        metadata={},
    )

    # deterministic node key order
    ordered_nodes = {k: nodes[k] for k in sorted(nodes.keys())}

    return ReplayDag(summary=summary, nodes=ordered_nodes, events=events)
