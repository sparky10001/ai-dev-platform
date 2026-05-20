#!/usr/bin/env bash
###################################################################
# runtime_trace_deprecation_inventory_tests.sh
#
# Phase 3.9D Trace Compatibility Deprecation Inventory
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Trace Deprecation Inventory"
echo "========================================"

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_trace_deprecation_inventory_test.py; then
  echo "✅ Runtime trace deprecation inventory tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime trace deprecation inventory tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "========================================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime trace deprecation inventory validation failed"
  exit 1
fi

echo
echo "🎉 Runtime trace deprecation inventory validation passed"
