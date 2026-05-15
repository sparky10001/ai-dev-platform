#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-knowledge] Running knowledge unit tests"
python3 -m unittest control-plane/tests/test_orchestration_knowledge_graph.py

echo "[control-plane-knowledge] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.knowledge.lineage import build_knowledge_graph
from core.knowledge.traversal import compute_lineage

print('[control-plane-knowledge] Import check passed')
PY

echo "[control-plane-knowledge] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.evals.evaluator import evaluate_replay
from core.knowledge.exporter import export_knowledge_graph_json
from core.knowledge.exporter import export_knowledge_graph_markdown
from core.knowledge.exporter import export_lineage_markdown
from core.knowledge.lineage import build_knowledge_graph
from core.knowledge.traversal import compute_lineage
from core.memory.history import replay_to_memory_record
from core.orchestrator.orchestrator import orchestrate_task
from core.replay.loader import load_orchestration_trace

outputs = [
    orchestrate_task({'task': 'list files', 'trace': True}),
    orchestrate_task({'task': "Create a file called hello.txt with content 'hi' and then list files", 'trace': True}),
]
records = []
for output in outputs:
    replay = load_orchestration_trace(output.run_path)
    evaluation = evaluate_replay(replay)
    records.append(replay_to_memory_record(replay, evaluation))

graph = build_knowledge_graph(records, graph_id='knowledge_smoke')
lineage = compute_lineage(graph, graph.nodes[0].node_id)

out_dir = Path('/workspace/tmp/control-plane-knowledge-smoke')
out_dir.mkdir(parents=True, exist_ok=True)

export_knowledge_graph_json(graph, out_dir / 'graph.json')
export_knowledge_graph_markdown(graph, out_dir / 'graph.md')
export_lineage_markdown(lineage, out_dir / 'lineage.md')

kg = subprocess.run(['/workspace/ai-orchestrate', 'build-knowledge-graph', '/workspace/runs'], check=True, capture_output=True, text=True)
json.loads(kg.stdout)

graph_payload = json.loads(kg.stdout)
if graph_payload.get('nodes'):
    node_id = graph_payload['nodes'][0]['node_id']
    ln = subprocess.run(['/workspace/ai-orchestrate', 'compute-lineage', '/workspace/runs', node_id], check=True, capture_output=True, text=True)
    json.loads(ln.stdout)

exp = subprocess.run(['/workspace/ai-orchestrate', 'export-knowledge-graph', '/workspace/runs', str(out_dir / 'graph_cli.md')], check=True, capture_output=True, text=True)
json.loads(exp.stdout)

print('[control-plane-knowledge] Smoke flow passed')
PY

echo "[control-plane-knowledge] PASS"
