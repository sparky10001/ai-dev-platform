#!/usr/bin/env bash
###################################################################
# runtime_registry_ledger_tests.sh
#
# Phase 3.6E Runtime Registry-from-Ledger Validation Suite
#
# Validates:
# - default trace-based registry behavior
# - optional ledger-based registry loading
# - trace/ledger registry parity
# - deterministic missing-ledger behavior
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Registry Ledger Validation"
echo "======================================"

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_registry_ledger_test.py; then
  echo "✅ Runtime registry-ledger test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime registry-ledger test"
  FAILED=$((FAILED + 1))
fi

echo
echo "======================================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime registry-ledger validation failed"
  exit 1
fi

echo
echo "🎉 Runtime registry-ledger validation passed"
