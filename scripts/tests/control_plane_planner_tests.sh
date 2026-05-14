#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-planner] Running planner unit tests"
python3 -m unittest control-plane/tests/test_dag_planner.py

echo "[control-plane-planner] Running import and smoke checks"
python3 - <<'PY'
from pathlib import Path
import sys

control_plane_root = Path('/workspace/control-plane')
if str(control_plane_root) not in sys.path:
    sys.path.insert(0, str(control_plane_root))

from core.planner.planner import plan_task
from core.dag.validator import validate_dag

result = plan_task('list files')
if result.status != 'success' or result.dag is None:
    raise SystemExit('planner smoke test failed: no DAG returned')

validate_dag(result.dag.model_dump())
print('[control-plane-planner] Smoke test passed')
PY

echo "[control-plane-planner] PASS"
