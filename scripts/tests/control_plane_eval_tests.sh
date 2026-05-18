#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

rm -f tmp/control_plane_eval_*.txt tmp/hello.txt hello.txt

echo "[control-plane-evals] Running eval unit tests"
python3 -m unittest control-plane/tests/test_orchestration_evals.py

echo "[control-plane-evals] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.evals.evaluator import evaluate_replay
from core.evals.comparator import compare_replays
from core.evals.benchmarks import benchmark_replays
print('[control-plane-evals] Import check passed')
PY

echo "[control-plane-evals] Running smoke flow"
python3 - <<'PY'
import json
import os
import subprocess
from pathlib import Path

rel_path = f"tmp/control_plane_eval_{os.getpid()}.txt"
Path('/workspace').joinpath(rel_path).unlink(missing_ok=True)
try:
    run1 = subprocess.run(['/workspace/ai-orchestrate', 'run', 'list files', '--trace'], capture_output=True, text=True, check=True)
    run2 = subprocess.run(['/workspace/ai-orchestrate', 'run', f"Create a file called {rel_path} with content 'hi' and then list files", '--trace'], capture_output=True, text=True, check=True)
    r1 = json.loads(run1.stdout)['run_path']
    r2 = json.loads(run2.stdout)['run_path']

    subprocess.run(['/workspace/ai-orchestrate', 'evaluate-run', r1], check=True, capture_output=True, text=True)
    subprocess.run(['/workspace/ai-orchestrate', 'compare-runs', r1, r2], check=True, capture_output=True, text=True)
    subprocess.run(['/workspace/ai-orchestrate', 'benchmark-runs', r1, r2], check=True, capture_output=True, text=True)

    out = Path('/workspace/tmp/control-plane-eval-export')
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(['/workspace/ai-orchestrate', 'export-run', r1, str(out / 'replay-summary.md')], check=True, capture_output=True, text=True)
finally:
    Path('/workspace').joinpath(rel_path).unlink(missing_ok=True)
print('[control-plane-evals] Smoke flow passed')
PY

echo "[control-plane-evals] PASS"
