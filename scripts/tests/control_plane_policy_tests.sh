#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-policy] Running policy unit tests"
python3 -m unittest control-plane/tests/test_policy_layer.py

echo "[control-plane-policy] Running import check"
python3 - <<'PY'
from pathlib import Path
import sys

control_plane_root = Path('/workspace/control-plane')
if str(control_plane_root) not in sys.path:
    sys.path.insert(0, str(control_plane_root))

from core.orchestrator.orchestrator import orchestrate_task
from core.policy.defaults import SAFE_READONLY_POLICY

result = orchestrate_task({
    'task': "Create a file called tmp/hello.txt with content 'hi' and then list files",
    'policy': SAFE_READONLY_POLICY.model_dump(mode='json'),
})

if result.status != 'error' or result.execution_status != 'skipped':
    raise SystemExit('policy smoke test failed: write flow was not blocked')

print('[control-plane-policy] Import/smoke check passed')
PY

echo "[control-plane-policy] PASS"
