#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-benchmarks] Running benchmark unit tests"
python3 -m unittest control-plane/tests/test_policy_planner_benchmarks.py

echo "[control-plane-benchmarks] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.benchmarks.matrices import build_benchmark_matrix
from core.benchmarks.runner import run_benchmark_matrix
print('[control-plane-benchmarks] Import check passed')
PY

echo "[control-plane-benchmarks] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

scenario_dir = '/workspace/control-plane/scenarios/tests'

suite = subprocess.run(['/workspace/ai-orchestrate', 'benchmark-suite', scenario_dir], capture_output=True, text=True, check=True)
json.loads(suite.stdout)

out = Path('/workspace/tmp/control-plane-benchmark-export')
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-benchmark-suite', scenario_dir, str(out / 'suite.md')], capture_output=True, text=True, check=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-benchmark-suite', scenario_dir, str(out / 'suite.json')], capture_output=True, text=True, check=True)
print('[control-plane-benchmarks] Smoke flow passed')
PY

echo "[control-plane-benchmarks] PASS"
