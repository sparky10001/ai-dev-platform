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
echo "🧪 Control Plane DAG Validation"
echo "==============================="
echo ""

run_check "Python DAG tests" python3 -m unittest discover -s "${ROOT_DIR}/control-plane/tests" -p 'test_dag_validator.py'

run_check "Example DAG loads" python3 - <<'PY'
from pathlib import Path
import sys

root = Path('/workspace/control-plane')
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.dag.validator import load_dag

dag = load_dag(root / 'dags' / 'examples' / 'file_write_flow.json')
assert dag.dag_id == 'file_write_flow'
PY

echo ""
echo "==============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Control-plane DAG tests FAILED"
  exit 1
fi

echo "🎉 Control-plane DAG tests passed"
