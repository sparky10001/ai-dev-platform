#!/usr/bin/env bash
###################################################################
# runtime_ledger_drift_tests.sh
#
# Phase 3.7A Runtime Ledger/Trace Drift Detection Validation Suite
#
# Validates:
# - deterministic drift auditing
# - drift category classification
# - strict drift enforcement helper
# - audit CLI output and exit semantics
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Drift Detection"
echo "================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_drift_test.py; then
  echo "✅ Runtime ledger drift tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger drift tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger drift validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger drift validation passed"
