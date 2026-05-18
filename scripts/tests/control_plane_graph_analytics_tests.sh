#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

rm -f tmp/control_plane_graph_analytics_*.txt tmp/hello.txt hello.txt

echo "[control-plane-graph-analytics] Running graph analytics unit tests"
python3 -m unittest control-plane/tests/test_orchestration_graph_analytics.py

echo "[control-plane-graph-analytics] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.graph_analytics.analyzer import analyze_knowledge_graph
from core.graph_analytics.metrics import compute_relationship_frequencies

print('[control-plane-graph-analytics] Import check passed')
PY

echo "[control-plane-graph-analytics] Running smoke flow"
python3 - <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.evals.evaluator import evaluate_replay
from core.graph_analytics.analyzer import analyze_knowledge_graph
from core.graph_analytics.exporter import export_graph_analytics_json
from core.graph_analytics.exporter import export_graph_analytics_markdown
from core.knowledge.lineage import build_knowledge_graph
from core.memory.history import replay_to_memory_record
from core.orchestrator.orchestrator import orchestrate_task
from core.replay.loader import load_orchestration_trace

rel_path = f"tmp/control_plane_graph_analytics_{os.getpid()}.txt"
Path('/workspace').joinpath(rel_path).unlink(missing_ok=True)
try:
    outs = [
        orchestrate_task({'task': 'list files', 'trace': True}),
        orchestrate_task({'task': f"Create a file called {rel_path} with content 'hi' and then list files", 'trace': True}),
    ]
    records = []
    for out in outs:
        replay = load_orchestration_trace(out.run_path)
        evaluation = evaluate_replay(replay)
        records.append(replay_to_memory_record(replay, evaluation))

    graph = build_knowledge_graph(records, graph_id='graph_analytics_smoke')
    result = analyze_knowledge_graph(graph, analytics_id='graph_analytics_smoke')

    out_dir = Path('/workspace/tmp/control-plane-graph-analytics-smoke')
    out_dir.mkdir(parents=True, exist_ok=True)
    export_graph_analytics_json(result, out_dir / 'report.json')
    export_graph_analytics_markdown(result, out_dir / 'report.md')

    an = subprocess.run(['/workspace/ai-orchestrate', 'analyze-knowledge-graph', '/workspace/runs', '--max-records=25'], check=True, capture_output=True, text=True)
    json.loads(an.stdout)
    ex = subprocess.run(['/workspace/ai-orchestrate', 'export-graph-analytics', '/workspace/runs', str(out_dir / 'report_cli.md'), '--max-records=25'], check=True, capture_output=True, text=True)
    json.loads(ex.stdout)
finally:
    Path('/workspace').joinpath(rel_path).unlink(missing_ok=True)

print('[control-plane-graph-analytics] Smoke flow passed')
PY

echo "[control-plane-graph-analytics] PASS"
