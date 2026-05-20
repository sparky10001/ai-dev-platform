#!/usr/bin/env bash
###################################################################
# runtime_ledger_authority_matrix_tests.sh
#
# Phase 3.9A Runtime Ledger Authority Readiness Matrix Validation
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Authority Matrix"
echo "==================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_authority_matrix_test.py; then
  echo "✅ Runtime ledger authority matrix tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger authority matrix tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "==================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger authority matrix validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger authority matrix validation passed"
