#!/usr/bin/env bash
###################################################################
# runtime_projection_purity_tests.sh
#
# Phase 3.8C Projection Purity Validation Suite
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Projection Purity Validation"
echo "========================================"

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_projection_purity_test.py; then
  echo "✅ Runtime projection purity tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime projection purity tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "========================================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime projection purity validation failed"
  exit 1
fi

echo
echo "🎉 Runtime projection purity validation passed"
