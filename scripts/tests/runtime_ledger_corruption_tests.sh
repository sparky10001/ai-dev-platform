#!/usr/bin/env bash
###################################################################
# runtime_ledger_corruption_tests.sh
#
# Phase 3.7D Runtime Ledger Corruption Validation Suite
#
# Validates:
# - deterministic ledger corruption classification
# - strict corruption enforcement behavior
# - corruption recovery guidance mapping
# - corruption audit CLI behavior
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Corruption Validation"
echo "======================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_corruption_test.py; then
  echo "✅ Runtime ledger corruption test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger corruption test"
  FAILED=$((FAILED + 1))
fi

echo
echo "======================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger corruption validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger corruption validation passed"
