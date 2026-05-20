#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "🧪 Runtime Ledger Cutover Decision Gate"
echo "========================================="

if python3 -m unittest runtime/tests/runtime_ledger_cutover_decision_gate_test.py; then
  echo "✅ Runtime ledger cutover decision gate tests"
  echo ""
  echo "========================================="
  echo "✅ Passed: 1"
  echo "❌ Failed: 0"
  echo ""
  echo "🎉 Runtime ledger cutover decision gate validation passed"
else
  echo "❌ Runtime ledger cutover decision gate tests failed"
  exit 1
fi
