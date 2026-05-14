#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-scenarios] Running scenario unit tests"
python3 -m unittest control-plane/tests/test_control_plane_scenarios.py

echo "[control-plane-scenarios] Running import check"
python3 - <<'PY'
from pathlib import Path
import sys

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.scenarios.runner import run_scenario
print('[control-plane-scenarios] Import check passed')
PY

echo "[control-plane-scenarios] Running scenario files"
python3 - <<'PY'
from pathlib import Path
import sys

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.scenarios.runner import run_scenario

scenario_dir = Path('/workspace/control-plane/scenarios/tests')
for path in sorted(scenario_dir.glob('*.json')):
    result = run_scenario(path)
    if result.status != 'passed':
        raise SystemExit(f'scenario failed: {path.name}')
print('[control-plane-scenarios] Scenario smoke checks passed')
PY

echo "[control-plane-scenarios] PASS"
