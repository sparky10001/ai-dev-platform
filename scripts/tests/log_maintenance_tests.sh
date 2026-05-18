#!/usr/bin/env bash
###################################################################
# log_maintenance_tests.sh
#
# Operational Log Maintenance Validation
#
# Validates:
# - log_manager cleanup safety + lock behavior
# - maintenance_gate throttling + timeout + error handling
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PASSED=0
FAILED=0

pass() {
  echo "✅ $1"
  PASSED=$((PASSED + 1))
}

fail() {
  echo "❌ $1"
  FAILED=$((FAILED + 1))
}

run_case() {
  local name="$1"
  shift

  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

case_log_manager_suite() {
  python3 -m unittest discover -s scripts/maintenance -p "log_manager_test.py"
}

case_maintenance_gate_suite() {
  python3 -m unittest discover -s scripts/maintenance -p "maintenance_gate_test.py"
}

echo ""
echo "🧪 Log Maintenance Validation"
echo "============================="

run_case "python log_manager unittest suite" case_log_manager_suite
run_case "python maintenance_gate unittest suite" case_maintenance_gate_suite

echo ""
echo "============================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo ""
  echo "❌ Log maintenance validation failed"
  exit 1
fi

echo ""
echo "🎉 Log maintenance validation passed"
