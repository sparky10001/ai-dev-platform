#!/usr/bin/env bash
###################################################################
# runtime_ledger_health_tests.sh
#
# Phase 3.7E Runtime Ledger Health Observability Validation Suite
#
# Validates:
# - deterministic ledger health reporting
# - aggregate health metrics
# - maintenance visibility
# - strict CLI/validation semantics
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Health Observability"
echo "======================================"

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_health_test.py; then
  echo "✅ Runtime ledger health tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger health tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "======================================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger health validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger health validation passed"
