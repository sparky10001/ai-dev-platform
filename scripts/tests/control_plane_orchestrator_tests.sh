#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

rm -f tmp/control_plane_orchestrator_*.txt tmp/hello.txt hello.txt

echo "[control-plane-orchestrator] Running orchestrator unit tests"
python3 -m unittest control-plane/tests/test_orchestrator.py

echo "[control-plane-orchestrator] Running import and smoke checks"
python3 - <<'PY'
from pathlib import Path
import os
import sys

control_plane_root = Path('/workspace/control-plane')
workspace = Path('/workspace')
if str(control_plane_root) not in sys.path:
    sys.path.insert(0, str(control_plane_root))

from core.orchestrator.orchestrator import orchestrate_task

result = orchestrate_task('list files')
if result.status not in {'success', 'error'}:
    raise SystemExit('orchestrator smoke test failed: invalid status')

rel_path = f"tmp/control_plane_orchestrator_{os.getpid()}.txt"
workspace.joinpath(rel_path).unlink(missing_ok=True)
try:
    traced = orchestrate_task({
        'task': f"Create a file called {rel_path} with content 'hi' and then list files",
        'trace': True,
    })
    if traced.status != 'success' or not traced.run_id or not traced.run_path:
        raise SystemExit('orchestrator traced smoke test failed')
finally:
    workspace.joinpath(rel_path).unlink(missing_ok=True)

print('[control-plane-orchestrator] Smoke tests passed')
PY

echo "[control-plane-orchestrator] PASS"
