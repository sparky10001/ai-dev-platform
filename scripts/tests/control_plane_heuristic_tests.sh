#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-heuristics] Running heuristic unit tests"
python3 -m unittest control-plane/tests/test_adaptive_heuristics.py

echo "[control-plane-heuristics] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.heuristics.ranking import rank_strategy_variants
from core.heuristics.recommender import recommend_strategy
print('[control-plane-heuristics] Import check passed')
PY

echo "[control-plane-heuristics] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

r = subprocess.run(['/workspace/ai-orchestrate', 'recommend-strategy', 'list files'], capture_output=True, text=True, check=True)
json.loads(r.stdout)

rk = subprocess.run(['/workspace/ai-orchestrate', 'rank-strategies', 'list files', '--planner=deterministic', '--planner=noop'], capture_output=True, text=True, check=True)
json.loads(rk.stdout)

c = subprocess.run(['/workspace/ai-orchestrate', 'build-heuristic-corpus', 'list files'], capture_output=True, text=True, check=True)
json.loads(c.stdout)

out = Path('/workspace/tmp/control-plane-heuristic-export')
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-heuristic-corpus', 'list files', str(out / 'corpus.md')], capture_output=True, text=True, check=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-heuristic-corpus', 'list files', str(out / 'corpus.json')], capture_output=True, text=True, check=True)
print('[control-plane-heuristics] Smoke flow passed')
PY

echo "[control-plane-heuristics] PASS"
