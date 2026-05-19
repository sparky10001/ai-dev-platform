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
echo "🧪 Control Plane Runtime Event Bridge Validation"
echo "================================================"
echo ""

run_check "Python runtime event bridge tests" python3 -m unittest discover -s "${ROOT_DIR}/control-plane/tests" -p 'test_runtime_event_bridge.py'

echo ""
echo "================================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Control-plane runtime event bridge tests FAILED"
  exit 1
fi

echo "🎉 Control-plane runtime event bridge tests passed"
