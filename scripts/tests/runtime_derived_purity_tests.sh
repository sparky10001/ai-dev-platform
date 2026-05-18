#!/usr/bin/env bash
###################################################################
# runtime_derived_purity_tests.sh
#
# Phase 3.7B Runtime Derived-System Purity Validation Suite
#
# Validates:
# - derived module read-only purity constraints
# - forbidden write/import/subprocess detection
# - dataset projection-writer classification behavior
# - strict audit CLI behavior
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Derived Purity Validation"
echo "===================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_derived_purity_test.py; then
  echo "✅ Runtime derived purity test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime derived purity test"
  FAILED=$((FAILED + 1))
fi

echo
echo "===================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime derived purity validation failed"
  exit 1
fi

echo
echo "🎉 Runtime derived purity validation passed"
