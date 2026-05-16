#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-parallel] Running parallel executor unit tests"
python3 -m unittest control-plane/tests/test_parallel_dag_executor.py

echo "[control-plane-parallel] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.dag.parallel_executor import execute_dag_parallel
from core.dag.parallel_executor import dag_to_execution_batches

print('[control-plane-parallel] Import check passed')
PY

echo "[control-plane-parallel] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.dag.parallel_executor import execute_dag_parallel

result = execute_dag_parallel(
    {
        'dag_id': 'smoke_parallel_noop',
        'version': '1.0.0',
        'entry': 'a',
        'nodes': [
            {'id': 'a', 'type': 'noop'},
            {'id': 'b', 'type': 'noop'},
            {'id': 'c', 'type': 'noop', 'depends_on': ['a', 'b']},
        ],
    },
    max_workers=2,
)
assert result.status == 'success'

dag_path = '/workspace/control-plane/dags/examples/file_write_flow.json'
proc = subprocess.run(
    ['/workspace/ai-orchestrate', 'execute-dag', dag_path, '--parallel', '--max-workers=2'],
    check=True,
    capture_output=True,
    text=True,
)
payload = json.loads(proc.stdout)
assert payload.get('execution_mode') == 'parallel'

print('[control-plane-parallel] Smoke flow passed')
PY

echo "[control-plane-parallel] PASS"
