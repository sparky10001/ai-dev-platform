#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CONTROL_PLANE_ROOT.parent
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.dag.executor import execute_dag
from core.dag.validator import dag_to_execution_order
from core.dag.validator import load_dag
from core.orchestrator.orchestrator import orchestrate_task
from core.planner.planner import plan_task
from core.policy.defaults import DEFAULT_POLICY
from core.policy.defaults import SAFE_READONLY_POLICY
from core.replay.loader import load_orchestration_trace
from core.replay.introspection import summarize_replay
from core.replay.exporter import export_replay_markdown
from core.replay.exporter import export_replay_summary_json
from core.evals.evaluator import evaluate_replay
from core.evals.comparator import compare_replays
from core.evals.benchmarks import benchmark_replays


def _to_jsonable(obj: Any) -> Any:
    if hasattr(obj, 'model_dump'):
        return obj.model_dump(mode='json')
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, tuple):
        return [_to_jsonable(v) for v in obj]
    return obj


def _emit(payload: dict[str, Any], pretty: bool = False) -> None:
    kwargs: dict[str, Any] = {'sort_keys': True}
    if pretty:
        kwargs['indent'] = 2
    print(json.dumps(_to_jsonable(payload), **kwargs))


def _usage() -> str:
    return (
        'Usage:\n'
        '  ai-orchestrate run <task> [--trace] [--strategy=deterministic|noop] [--policy=default|safe-readonly] [--pretty]\n'
        '  ai-orchestrate plan <task> [--strategy=deterministic|noop] [--pretty]\n'
        '  ai-orchestrate validate-dag <path> [--pretty]\n'
        '  ai-orchestrate execute-dag <path> [--trace] [--pretty]\n'
        '  ai-orchestrate replay <run_path> [--pretty]\n'
        '  ai-orchestrate summarize-run <run_path> [--pretty]\n'
        '  ai-orchestrate export-run <run_path> <output.(md|json)> [--pretty]\n'
        '  ai-orchestrate evaluate-run <run_path> [--pretty]\n'
        '  ai-orchestrate compare-runs <run_path_a> <run_path_b> [--pretty]\n'
        '  ai-orchestrate benchmark-runs <run_path...> [--pretty]'
    )


def _resolve_policy(name: str) -> dict[str, Any]:
    if name == 'default':
        return DEFAULT_POLICY.model_dump(mode='json')
    if name == 'safe-readonly':
        return SAFE_READONLY_POLICY.model_dump(mode='json')
    raise ValueError(f'unsupported policy: {name}')


def _parse_flags(args: list[str], *, allow_trace: bool, allow_strategy: bool) -> tuple[list[str], bool, bool, str, str | None]:
    positional: list[str] = []
    pretty = False
    trace = False
    strategy = 'deterministic'
    policy_name: str | None = None

    for arg in args:
        if arg == '--pretty':
            pretty = True
        elif arg == '--trace':
            if not allow_trace:
                raise ValueError('--trace is not supported for this command')
            trace = True
        elif arg.startswith('--policy='):
            policy_name = arg.split('=', 1)[1]
        elif arg.startswith('--strategy='):
            if not allow_strategy:
                raise ValueError('--strategy is not supported for this command')
            strategy = arg.split('=', 1)[1]
        elif arg.startswith('--'):
            raise ValueError(f'unknown flag: {arg}')
        else:
            positional.append(arg)

    return positional, pretty, trace, strategy, policy_name


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        print(_usage(), file=sys.stderr)
        return 2

    command = args[0]
    raw = args[1:]

    try:
        if command == 'run':
            positional, pretty, trace, strategy, policy_name = _parse_flags(raw, allow_trace=True, allow_strategy=True)
            if not positional:
                print('error: missing task for run', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            task = ' '.join(positional)
            policy_payload = _resolve_policy(policy_name) if policy_name else None
            result = orchestrate_task({'task': task, 'planner_strategy': strategy, 'trace': trace, 'policy': policy_payload})
            _emit(result.model_dump(mode='json'), pretty=pretty)
            return 0

        if command == 'plan':
            positional, pretty, _trace, strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=True)
            if not positional:
                print('error: missing task for plan', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            task = ' '.join(positional)
            result = plan_task({'task': task, 'strategy': strategy})
            _emit(result.model_dump(mode='json'), pretty=pretty)
            return 0

        if command == 'validate-dag':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if not positional:
                print('error: missing path for validate-dag', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            path = positional[0]
            try:
                dag = load_dag(path)
                payload = {
                    'status': 'success',
                    'dag_id': dag.dag_id,
                    'execution_order': dag_to_execution_order(dag),
                }
            except Exception as exc:
                payload = {'status': 'error', 'error': str(exc)}
            _emit(payload, pretty=pretty)
            return 0

        if command == 'replay':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if not positional:
                print('error: missing run_path for replay', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replay = load_orchestration_trace(positional[0])
                _emit(replay.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'summarize-run':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if not positional:
                print('error: missing run_path for summarize-run', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replay = load_orchestration_trace(positional[0])
                summary = summarize_replay(replay)
                _emit(summary.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'evaluate-run':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if not positional:
                print('error: missing run_path for evaluate-run', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replay = load_orchestration_trace(positional[0])
                ev = evaluate_replay(replay)
                _emit(ev.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'compare-runs':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 2:
                print('error: compare-runs requires two run paths', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                left = load_orchestration_trace(positional[0])
                right = load_orchestration_trace(positional[1])
                cmp = compare_replays(left, right)
                _emit(cmp.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'benchmark-runs':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 1:
                print('error: benchmark-runs requires at least one run path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replays = [load_orchestration_trace(p) for p in positional]
                bench = benchmark_replays(replays, benchmark_id='benchmark_cli')
                _emit(bench.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-run':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 2:
                print('error: export-run requires run_path and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            run_path = positional[0]
            output_path = positional[1]
            try:
                replay = load_orchestration_trace(run_path)
                if output_path.lower().endswith('.md'):
                    written = export_replay_markdown(replay, output_path)
                else:
                    written = export_replay_summary_json(replay, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'execute-dag':
            positional, pretty, trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=True, allow_strategy=False)
            if not positional:
                print('error: missing path for execute-dag', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            path = positional[0]
            try:
                result = execute_dag(path, trace=trace)
                payload = result.model_dump(mode='json')
            except Exception as exc:
                payload = {'status': 'error', 'error': str(exc)}
            _emit(payload, pretty=pretty)
            return 0

        print(f'error: unknown command: {command}', file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    except ValueError as exc:
        print(f'error: {exc}', file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f'bootstrap error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
