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
from core.experiments.tracker import track_replay
from core.experiments.tracker import track_replays
from core.experiments.datasets import build_replay_dataset
from core.experiments.exporter import export_manifest_json
from core.experiments.exporter import export_manifest_markdown
from core.benchmarks.matrices import build_benchmark_matrix
from core.benchmarks.runner import run_benchmark_matrix
from core.benchmarks.exporter import export_benchmark_suite_json
from core.benchmarks.exporter import export_benchmark_suite_markdown
from core.strategies.branching import execute_strategy_experiment
from core.strategies.evaluator import compare_strategy_variants
from core.strategies.exporter import export_strategy_experiment_json
from core.strategies.exporter import export_strategy_experiment_markdown
from core.heuristics.ranking import rank_strategy_variants
from core.heuristics.ranking import generate_heuristic_signals
from core.heuristics.recommender import recommend_strategy
from core.heuristics.corpora import build_heuristic_corpus
from core.heuristics.exporter import export_ranking_json
from core.heuristics.exporter import export_recommendation_json
from core.heuristics.exporter import export_corpus_markdown
from core.memory.history import replay_to_memory_record
from core.memory.history import build_memory_timeline
from core.memory.retrieval import retrieve_memory_records
from core.memory.corpora import build_memory_corpus
from core.memory.exporter import export_memory_timeline_json
from core.memory.exporter import export_memory_timeline_markdown
from core.memory.exporter import export_memory_corpus_json
from core.knowledge.lineage import build_knowledge_graph
from core.knowledge.traversal import compute_lineage
from core.knowledge.exporter import export_knowledge_graph_json
from core.knowledge.exporter import export_knowledge_graph_markdown
from core.graph_analytics.analyzer import analyze_knowledge_graph
from core.graph_analytics.exporter import export_graph_analytics_json
from core.graph_analytics.exporter import export_graph_analytics_markdown


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
        '  ai-orchestrate benchmark-runs <run_path...> [--pretty]\n'
        '  ai-orchestrate track-run <run_path> [--pretty]\n'
        '  ai-orchestrate track-experiment <run_path...> [--pretty]\n'
        '  ai-orchestrate build-dataset <run_path...> [--pretty]\n'
        '  ai-orchestrate export-experiment <run_path...> <output.(md|json)> [--pretty]\n'
        '  ai-orchestrate benchmark-suite <scenario_dir> [--pretty]\n'
        '  ai-orchestrate benchmark-matrix <scenario_dir> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate export-benchmark-suite <scenario_dir> <output.(md|json)> [--pretty]\n'
        '  ai-orchestrate strategy-experiment <task> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate compare-strategies <task> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate export-strategy-experiment <task> <output.(md|json)> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate recommend-strategy <task> [--pretty]\n'
        '  ai-orchestrate rank-strategies <task> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate build-heuristic-corpus <task> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate export-heuristic-corpus <task> <output.(md|json)> [--planner=...] [--policy=...] [--pretty]\n'
        '  ai-orchestrate memory-timeline <runs_dir> [--pretty]\n'
        '  ai-orchestrate retrieve-memory <runs_dir> <query> [--pretty]\n'
        '  ai-orchestrate build-memory-corpus <runs_dir> [--pretty]\n'
        '  ai-orchestrate export-memory-timeline <runs_dir> <output.(md|json)> [--pretty]\n'
        '  ai-orchestrate build-knowledge-graph <runs_dir> [--max-records=N] [--pretty]\n'
        '  ai-orchestrate compute-lineage <runs_dir> <node_id> [--max-records=N] [--pretty]\n'
        '  ai-orchestrate export-knowledge-graph <runs_dir> <output.(md|json)> [--max-records=N] [--pretty]\n'
        '  ai-orchestrate analyze-knowledge-graph <runs_dir> [--max-records=N] [--pretty]\n'
        '  ai-orchestrate export-graph-analytics <runs_dir> <output.(md|json)> [--max-records=N] [--pretty]'
    )


def _resolve_policy(name: str) -> dict[str, Any]:
    if name == 'default':
        return DEFAULT_POLICY.model_dump(mode='json')
    if name == 'safe-readonly':
        return SAFE_READONLY_POLICY.model_dump(mode='json')
    raise ValueError(f'unsupported policy: {name}')


def _collect_memory_records_from_runs(runs_dir: str, max_records: int = 250) -> list:
    run_paths = sorted([p for p in Path(runs_dir).glob('run_*') if p.is_dir()])[: max_records]
    records = []
    for rp in run_paths:
        try:
            replay = load_orchestration_trace(rp)
            ev = evaluate_replay(replay)
            records.append(replay_to_memory_record(replay, ev))
        except Exception:
            continue
    return records


def _parse_max_records(args: list[str], default: int = 250) -> int:
    max_records = default
    for arg in args:
        if arg.startswith('--max-records='):
            raw = arg.split('=', 1)[1]
            try:
                value = int(raw)
            except ValueError as exc:
                raise ValueError('--max-records must be an integer') from exc
            if value <= 0:
                raise ValueError('--max-records must be > 0')
            max_records = value
    return max_records


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

        if command == 'memory-timeline':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: memory-timeline requires runs directory', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            try:
                run_paths = sorted([p for p in __import__('pathlib').Path(runs_dir).glob('run_*') if p.is_dir()])
                records = []
                for rp in run_paths:
                    try:
                        replay = load_orchestration_trace(rp)
                        ev = evaluate_replay(replay)
                        records.append(replay_to_memory_record(replay, ev))
                    except Exception:
                        continue
                timeline = build_memory_timeline(records, timeline_id='timeline_cli')
                _emit(timeline.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'retrieve-memory':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 2:
                print('error: retrieve-memory requires runs directory and query', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            query = ' '.join(positional[1:])
            try:
                run_paths = sorted([p for p in __import__('pathlib').Path(runs_dir).glob('run_*') if p.is_dir()])
                records = []
                for rp in run_paths:
                    try:
                        replay = load_orchestration_trace(rp)
                        ev = evaluate_replay(replay)
                        records.append(replay_to_memory_record(replay, ev))
                    except Exception:
                        continue
                result = retrieve_memory_records(records, query)
                _emit(result.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'build-memory-corpus':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: build-memory-corpus requires runs directory', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            try:
                run_paths = sorted([p for p in __import__('pathlib').Path(runs_dir).glob('run_*') if p.is_dir()])
                records = []
                for rp in run_paths:
                    try:
                        replay = load_orchestration_trace(rp)
                        ev = evaluate_replay(replay)
                        records.append(replay_to_memory_record(replay, ev))
                    except Exception:
                        continue
                corpus = build_memory_corpus(records, corpus_id='memory_corpus_cli')
                _emit(corpus.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-memory-timeline':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 2:
                print('error: export-memory-timeline requires runs directory and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            output_path = positional[1]
            try:
                run_paths = sorted([p for p in __import__('pathlib').Path(runs_dir).glob('run_*') if p.is_dir()])
                records = []
                for rp in run_paths:
                    try:
                        replay = load_orchestration_trace(rp)
                        ev = evaluate_replay(replay)
                        records.append(replay_to_memory_record(replay, ev))
                    except Exception:
                        continue
                timeline = build_memory_timeline(records, timeline_id='timeline_cli')
                if output_path.lower().endswith('.md'):
                    written = export_memory_timeline_markdown(timeline, output_path)
                elif output_path.lower().endswith('.json'):
                    written = export_memory_timeline_json(timeline, output_path)
                else:
                    written = export_memory_timeline_markdown(timeline, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'build-knowledge-graph':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: build-knowledge-graph requires runs directory', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            try:
                max_records = _parse_max_records(raw)
                records = _collect_memory_records_from_runs(runs_dir, max_records=max_records)
                graph = build_knowledge_graph(records, graph_id='knowledge_graph_cli')
                _emit(graph.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'compute-lineage':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 2:
                print('error: compute-lineage requires runs directory and node_id', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            node_id = positional[1]
            try:
                max_records = _parse_max_records(raw)
                records = _collect_memory_records_from_runs(runs_dir, max_records=max_records)
                graph = build_knowledge_graph(records, graph_id='knowledge_graph_cli')
                lineage = compute_lineage(graph, node_id)
                _emit(lineage.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-knowledge-graph':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 2:
                print('error: export-knowledge-graph requires runs directory and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            output_path = positional[1]
            try:
                max_records = _parse_max_records(raw)
                records = _collect_memory_records_from_runs(runs_dir, max_records=max_records)
                graph = build_knowledge_graph(records, graph_id='knowledge_graph_cli')
                if output_path.lower().endswith('.json'):
                    written = export_knowledge_graph_json(graph, output_path)
                else:
                    written = export_knowledge_graph_markdown(graph, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'analyze-knowledge-graph':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: analyze-knowledge-graph requires runs directory', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            try:
                max_records = _parse_max_records(raw)
                records = _collect_memory_records_from_runs(runs_dir, max_records=max_records)
                graph = build_knowledge_graph(records, graph_id='knowledge_graph_cli')
                result = analyze_knowledge_graph(graph, analytics_id='graph_analytics_cli')
                _emit(result.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-graph-analytics':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 2:
                print('error: export-graph-analytics requires runs directory and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            runs_dir = positional[0]
            output_path = positional[1]
            try:
                max_records = _parse_max_records(raw)
                records = _collect_memory_records_from_runs(runs_dir, max_records=max_records)
                graph = build_knowledge_graph(records, graph_id='knowledge_graph_cli')
                result = analyze_knowledge_graph(graph, analytics_id='graph_analytics_cli')
                if output_path.lower().endswith('.json'):
                    written = export_graph_analytics_json(result, output_path)
                else:
                    written = export_graph_analytics_markdown(result, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'recommend-strategy':
            pretty = '--pretty' in raw
            task = ' '.join([arg for arg in raw if not arg.startswith('--')])
            if not task:
                print('error: recommend-strategy requires task text', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=['deterministic', 'noop'],
                    policies=['default', 'safe-readonly'],
                    trace=True,
                )
                signals = generate_heuristic_signals(exp.variants)
                rec = recommend_strategy(task, signals)
                _emit(rec.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'rank-strategies':
            pretty = '--pretty' in raw
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            task = ' '.join([arg for arg in raw if not arg.startswith('--')])
            if not task:
                print('error: rank-strategies requires task text', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=(planners or ['deterministic', 'noop']),
                    policies=(policies or ['default']),
                    trace=True,
                )
                ranking = rank_strategy_variants(exp.variants, ranking_id='ranking_cli')
                _emit(ranking.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'build-heuristic-corpus':
            pretty = '--pretty' in raw
            task = ' '.join([arg for arg in raw if not arg.startswith('--')])
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            if not task:
                print('error: build-heuristic-corpus requires task text', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=(planners or ['deterministic', 'noop']),
                    policies=(policies or ['default']),
                    trace=True,
                )
                signals = generate_heuristic_signals(exp.variants)
                corpus = build_heuristic_corpus(signals, corpus_id='corpus_cli')
                _emit(corpus.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-heuristic-corpus':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            if len(positional) < 2:
                print('error: export-heuristic-corpus requires task text and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            output_path = positional[-1]
            task = ' '.join(positional[:-1])
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=(planners or ['deterministic', 'noop']),
                    policies=(policies or ['default']),
                    trace=True,
                )
                signals = generate_heuristic_signals(exp.variants)
                corpus = build_heuristic_corpus(signals, corpus_id='corpus_cli')
                if output_path.lower().endswith('.md'):
                    written = export_corpus_markdown(corpus, output_path)
                elif output_path.lower().endswith('.json'):
                    # reuse generic JSON exporter style by writing recommendation/ranking pattern
                    written = export_recommendation_json(
                        recommend_strategy(task, signals),
                        output_path,
                    )
                else:
                    written = export_corpus_markdown(corpus, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'strategy-experiment':
            pretty = '--pretty' in raw
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: strategy-experiment requires task text', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            task = ' '.join(positional)
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=(planners or ['deterministic']),
                    policies=(policies or ['default']),
                    trace=True,
                )
                _emit(exp.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'compare-strategies':
            pretty = '--pretty' in raw
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: compare-strategies requires task text', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            task = ' '.join(positional)
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=(planners or ['deterministic', 'noop']),
                    policies=(policies or ['default']),
                    trace=True,
                )
                variants = sorted(exp.variants, key=lambda v: v.strategy_id)
                comparisons = []
                for i in range(len(variants) - 1):
                    comparisons.append(compare_strategy_variants(variants[i], variants[i + 1]).model_dump(mode='json'))
                _emit(comparisons, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-strategy-experiment':
            pretty = '--pretty' in raw
            positional = [arg for arg in raw if not arg.startswith('--')]
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            if len(positional) < 2:
                print('error: export-strategy-experiment requires task text and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            output_path = positional[-1]
            task = ' '.join(positional[:-1])
            try:
                exp = execute_strategy_experiment(
                    task=task,
                    planner_strategies=(planners or ['deterministic', 'noop']),
                    policies=(policies or ['default']),
                    trace=True,
                )
                if output_path.lower().endswith('.md'):
                    written = export_strategy_experiment_markdown(exp, output_path)
                else:
                    written = export_strategy_experiment_json(exp, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'track-run':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 1:
                print('error: track-run requires run_path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replay = load_orchestration_trace(positional[0])
                ev = evaluate_replay(replay)
                tracked = track_replay(replay, evaluation=ev)
                _emit(tracked.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'track-experiment':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 1:
                print('error: track-experiment requires run paths', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replays = [load_orchestration_trace(p) for p in positional]
                evals = [evaluate_replay(r) for r in replays]
                manifest = track_replays(replays, evaluations=evals, experiment_id='experiment_cli')
                _emit(manifest.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'build-dataset':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 1:
                print('error: build-dataset requires run paths', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                replays = [load_orchestration_trace(p) for p in positional]
                evals = [evaluate_replay(r) for r in replays]
                dataset = build_replay_dataset(replays, evaluations=evals, dataset_id='dataset_cli')
                _emit(dataset.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-experiment':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 3:
                print('error: export-experiment requires run paths plus output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                output_path = positional[-1]
                run_paths = positional[:-1]
                replays = [load_orchestration_trace(p) for p in run_paths]
                evals = [evaluate_replay(r) for r in replays]
                manifest = track_replays(replays, evaluations=evals, experiment_id='experiment_cli')
                if output_path.lower().endswith('.md'):
                    written = export_manifest_markdown(manifest, output_path)
                else:
                    written = export_manifest_json(manifest, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
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

        if command == 'benchmark-suite':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 1:
                print('error: benchmark-suite requires scenario directory', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            try:
                scenario_dir = positional[0]
                scenarios = sorted([p.name for p in __import__('pathlib').Path(scenario_dir).glob('*.json')])
                matrix = build_benchmark_matrix(
                    scenarios=scenarios,
                    planner_strategies=['deterministic', 'noop'],
                    policies=['default', 'safe-readonly'],
                    matrix_id='benchmark_suite_cli',
                )
                suite = run_benchmark_matrix(matrix, scenario_dir)
                _emit(suite.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'benchmark-matrix':
            pretty = '--pretty' in raw
            planners = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--planner=')]
            policies = [arg.split('=', 1)[1] for arg in raw if arg.startswith('--policy=')]
            positional = [arg for arg in raw if not arg.startswith('--')]
            if len(positional) < 1:
                print('error: benchmark-matrix requires scenario directory', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            scenario_dir = positional[0]
            try:
                scenarios = sorted([p.name for p in __import__('pathlib').Path(scenario_dir).glob('*.json')])
                matrix = build_benchmark_matrix(
                    scenarios=scenarios,
                    planner_strategies=(planners or ['deterministic']),
                    policies=(policies or ['default']),
                    matrix_id='benchmark_matrix_cli',
                )
                suite = run_benchmark_matrix(matrix, scenario_dir)
                _emit(suite.model_dump(mode='json'), pretty=pretty)
            except Exception as exc:
                _emit({'status': 'error', 'error': str(exc)}, pretty=pretty)
            return 0

        if command == 'export-benchmark-suite':
            positional, pretty, _trace, _strategy, _policy_name = _parse_flags(raw, allow_trace=False, allow_strategy=False)
            if len(positional) < 2:
                print('error: export-benchmark-suite requires scenario_dir and output path', file=sys.stderr)
                print(_usage(), file=sys.stderr)
                return 2
            scenario_dir = positional[0]
            output_path = positional[1]
            try:
                scenarios = sorted([p.name for p in __import__('pathlib').Path(scenario_dir).glob('*.json')])
                matrix = build_benchmark_matrix(
                    scenarios=scenarios,
                    planner_strategies=['deterministic', 'noop'],
                    policies=['default', 'safe-readonly'],
                    matrix_id='benchmark_suite_cli',
                )
                suite = run_benchmark_matrix(matrix, scenario_dir)
                if output_path.lower().endswith('.md'):
                    written = export_benchmark_suite_markdown(suite, output_path)
                else:
                    written = export_benchmark_suite_json(suite, output_path)
                _emit({'status': 'success', 'path': written}, pretty=pretty)
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
