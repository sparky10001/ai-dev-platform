#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-strategies] Running strategy unit tests"
python3 -m unittest control-plane/tests/test_multi_strategy_experiments.py

echo "[control-plane-strategies] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.strategies.branching import execute_strategy_experiment
from core.strategies.evaluator import compare_strategy_variants
print('[control-plane-strategies] Import check passed')
PY

echo "[control-plane-strategies] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

exp = subprocess.run([
    '/workspace/ai-orchestrate', 'strategy-experiment', 'list files',
    '--planner=deterministic', '--planner=noop', '--policy=default'
], capture_output=True, text=True, check=True)
json.loads(exp.stdout)

cmp_out = subprocess.run([
    '/workspace/ai-orchestrate', 'compare-strategies', 'list files',
    '--planner=deterministic', '--planner=noop'
], capture_output=True, text=True, check=True)
json.loads(cmp_out.stdout)

out = Path('/workspace/tmp/control-plane-strategy-export')
out.mkdir(parents=True, exist_ok=True)
subprocess.run([
    '/workspace/ai-orchestrate', 'export-strategy-experiment', 'list files', str(out / 'strategy.md')
], capture_output=True, text=True, check=True)
subprocess.run([
    '/workspace/ai-orchestrate', 'export-strategy-experiment', 'list files', str(out / 'strategy.json')
], capture_output=True, text=True, check=True)
print('[control-plane-strategies] Smoke flow passed')
PY

echo "[control-plane-strategies] PASS"
