#!/usr/bin/env bash
###################################################################
# runtime_ledger_default_dry_run_tests.sh
#
# Phase 3.7I Ledger-Default Dry-Run Validation Suite
#
# Validates:
# - dry-run mode enablement behavior
# - readiness aggregation and categories
# - strict CLI semantics
# - no authority/default switching side effects
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger-Default Dry-Run"
echo "=================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_default_dry_run_test.py; then
  echo "✅ Runtime ledger-default dry-run tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger-default dry-run tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "=================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger-default dry-run validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger-default dry-run validation passed"
