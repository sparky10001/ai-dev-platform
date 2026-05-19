#!/usr/bin/env bash
###################################################################
# runtime_event_loader_tests.sh
#
# Phase 3.8B Canonical Runtime Event Loader Validation Suite
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Event Loader Validation"
echo "==================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_event_loader_test.py; then
  echo "✅ Runtime event loader tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime event loader tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "==================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime event loader validation failed"
  exit 1
fi

echo
echo "🎉 Runtime event loader validation passed"
