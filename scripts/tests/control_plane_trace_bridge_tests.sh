#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

run_check() {
  local name="$1"
  shift

  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

echo ""
echo "🧪 Control Plane Trace Bridge Validation"
echo "========================================"
echo ""

run_check "Python trace bridge tests" python3 -m unittest discover -s "${ROOT_DIR}/control-plane/tests" -p 'test_execution_trace_bridge.py'

run_check "Import check" python3 - <<'PY'
from pathlib import Path
import sys

cp = Path('/workspace/control-plane')
if str(cp) not in sys.path:
    sys.path.insert(0, str(cp))

from core.observability.trace import create_control_plane_run
from core.dag.executor import execute_dag

assert callable(create_control_plane_run)
assert callable(execute_dag)
PY

run_check "Execute and replay traced DAG" python3 - <<'PY'
from pathlib import Path
import json
import sys

cp = Path('/workspace/control-plane')
ws = cp.parent
if str(cp) not in sys.path:
    sys.path.insert(0, str(cp))
if str(ws) not in sys.path:
    sys.path.insert(0, str(ws))

from core.dag.executor import execute_dag
from runtime.replay import replay_trace

result = execute_dag(cp / 'dags' / 'examples' / 'file_write_flow.json', trace=True)
assert result.status == 'success'

runs = sorted((ws / 'runs').glob('run_*/run.json'), key=lambda p: p.stat().st_mtime, reverse=True)
run_id = None
for run_json in runs:
    payload = json.loads(run_json.read_text(encoding='utf-8'))
    if payload.get('command') == 'dag' and payload.get('task') == 'file_write_flow':
        run_id = payload.get('id')
        break
assert run_id

trace_path = ws / 'runs' / run_id / 'trace.jsonl'
replay = replay_trace(trace_path, strict=True)
assert replay.event_count > 0
PY

echo ""
echo "========================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Control-plane trace bridge tests FAILED"
  exit 1
fi

echo "🎉 Control-plane trace bridge tests passed"
