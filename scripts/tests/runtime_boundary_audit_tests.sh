#!/usr/bin/env bash
###################################################################
# runtime_boundary_audit_tests.sh
#
# Phase 3.7C Runtime Boundary Enforcement Validation Suite
#
# Validates:
# - runtime import boundary guardrails
# - forbidden cross-layer import detection
# - control-plane runtime.engine import prohibition
# - boundary audit CLI strict/json behavior
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Boundary Audit Validation"
echo "===================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_boundary_audit_test.py; then
  echo "✅ Runtime boundary audit test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime boundary audit test"
  FAILED=$((FAILED + 1))
fi

echo
echo "===================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime boundary audit validation failed"
  exit 1
fi

echo
echo "🎉 Runtime boundary audit validation passed"
