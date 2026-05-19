#!/usr/bin/env bash
###################################################################
# runtime_trace_compatibility_tests.sh
#
# Phase 3.7G Runtime Trace Compatibility Audit Validation Suite
#
# Validates:
# - deterministic trace dependency inventory
# - trace dependency classification categories
# - cutover blocker detection semantics
# - audit CLI strict/json behavior
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Trace Compatibility Audit"
echo "===================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_trace_compatibility_test.py; then
  echo "✅ Runtime trace compatibility tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime trace compatibility tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "===================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime trace compatibility validation failed"
  exit 1
fi

echo
echo "🎉 Runtime trace compatibility validation passed"
