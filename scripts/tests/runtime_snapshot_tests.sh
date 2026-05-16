#!/usr/bin/env bash
###################################################################
# runtime_snapshot_tests.sh
#
# Phase 3.5 Runtime Snapshot Regression Suite
#
# Validates:
# - deterministic runtime snapshot stability
# - normalized result.json consistency
# - normalized trace.jsonl consistency
# - optional run.json consistency
# - lifecycle event sequence stability
# - volatile metadata normalization
# - replay-safe structural equivalence across repeated runs
#
# Purpose:
# - locks current runtime behavior before runtime decomposition
# - protects adapter/lifecycle/trace refactors from regressions
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Snapshot Regression"
echo "=============================="

PASSED=0
FAILED=0

if python3 -m unittest scripts/tests/runtime_snapshot_test.py; then
  echo "✅ Runtime snapshot test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime snapshot test"
  FAILED=$((FAILED + 1))
fi

echo
echo "=============================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo
  echo "❌ Runtime snapshot validation failed"
  exit 1
fi

echo
echo "🎉 Runtime snapshot validation passed"
