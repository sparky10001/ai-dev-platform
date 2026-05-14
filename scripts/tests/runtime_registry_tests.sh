#!/usr/bin/env bash
###################################################################
# runtime_registry_tests.sh
#
# Phase 3C Runtime Registry Validation Suite
#
# Validates:
# - run enumeration
# - metadata lookup
# - filtering
# - sorting and limits
# - invalid run tolerance in queries
# - summary generation
# - deterministic ordering
# - replay/eval integration
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

export AI_ADAPTER="mock"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"
MODEL="registry_model_$$"
BAD_RUN="registry_bad_run_$$"

cleanup() {
  rm -rf "$TMP_DIR"
  rm -rf "${ROOT_DIR}/runs/${BAD_RUN}"
}

trap cleanup EXIT

pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

run_check() {
  local name="$1"
  shift

  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

make_run() {
  local prompt="$1"
  local output_file="$2"

  AI_TRACE=1 "$RUNTIME" run "$prompt" --model="$MODEL"     > "$output_file"     2> "${output_file}.stderr"

  jq -r '.meta.run_id' "$output_file"
}

echo ""
echo "🧪 Runtime Registry Validation"
echo "=============================="
echo ""

RUN_A=$(make_run "registry alpha" "${TMP_DIR}/run_a.json")
RUN_B=$(make_run "Create a file for registry beta" "${TMP_DIR}/run_b.json")

# Invalid directory should not break query/index scans.
mkdir -p "${ROOT_DIR}/runs/${BAD_RUN}"
printf 'not json
' > "${ROOT_DIR}/runs/${BAD_RUN}/run.json"

# ================================================================
# Run enumeration
# ================================================================

test_run_enumeration() {
  RUN_A="$RUN_A" RUN_B="$RUN_B" python3 - <<'PY'
import os
from runtime.registry import list_runs

runs = list_runs()
assert os.environ["RUN_A"] in runs
assert os.environ["RUN_B"] in runs
assert runs == sorted(runs)
PY
}

# ================================================================
# Metadata lookup
# ================================================================

test_get_run() {
  RUN_A="$RUN_A" MODEL="$MODEL" python3 - <<'PY'
import os
from runtime.registry import get_run, get_latest_run

run = get_run(os.environ["RUN_A"])
assert run["id"] == os.environ["RUN_A"]
assert run["model"] == os.environ["MODEL"]
latest = get_latest_run()
assert latest is None or "id" in latest
PY
}

# ================================================================
# Filtering
# ================================================================

test_filtering() {
  RUN_A="$RUN_A" RUN_B="$RUN_B" MODEL="$MODEL" python3 - <<'PY'
import os
from runtime.registry import query_runs
from runtime.schemas import RunQueryResult

result = query_runs(
    model=os.environ["MODEL"],
    command="run",
    status="done",
    completed=True,
    sort_by="created_at",
)
ids = [run["id"] for run in result.runs]
assert isinstance(result, RunQueryResult)
assert ids == [os.environ["RUN_A"], os.environ["RUN_B"]]
assert result.total == 2
assert result.filters["model"] == os.environ["MODEL"]
PY
}

# ================================================================
# Sorting and limit support
# ================================================================

test_sorting_and_limit() {
  RUN_B="$RUN_B" MODEL="$MODEL" python3 - <<'PY'
import os
from runtime.registry import query_runs

result = query_runs(
    model=os.environ["MODEL"],
    sort_by="created_at",
    descending=True,
    limit=1,
)
assert result.total == 1
assert result.limit == 1
assert result.descending is True
assert result.runs[0]["id"] == os.environ["RUN_B"]
PY
}

# ================================================================
# Invalid run tolerance
# ================================================================

test_invalid_run_tolerance() {
  BAD_RUN="$BAD_RUN" python3 - <<'PY'
import os
from runtime.registry import get_run, query_runs

result = query_runs(sort_by="id")
assert os.environ["BAD_RUN"] not in [run.get("id") for run in result.runs]

try:
    get_run(os.environ["BAD_RUN"])
except Exception:
    pass
else:
    raise AssertionError("strict get_run did not fail for invalid run")
PY
}

# ================================================================
# Summary generation and eval integration
# ================================================================

test_summary_generation() {
  MODEL="$MODEL" python3 - <<'PY'
import os
from runtime.registry import summarize_runs
from runtime.schemas import RunSummary

summary = summarize_runs(model=os.environ["MODEL"])
assert isinstance(summary, RunSummary)
assert summary.total_runs == 2
assert summary.completed_runs == 2
assert summary.success_rate == 1.0
assert summary.total_tool_calls >= 1
assert summary.replay_valid_runs == 2
assert summary.schema_valid_runs == 2
assert summary.average_runtime is None or summary.average_runtime >= 0
PY
}

# ================================================================
# Deterministic ordering
# ================================================================

test_deterministic_ordering() {
  MODEL="$MODEL" python3 - <<'PY'
import os
from runtime.registry import query_runs

first = query_runs(model=os.environ["MODEL"], sort_by="created_at")
second = query_runs(model=os.environ["MODEL"], sort_by="created_at")
assert [run["id"] for run in first.runs] == [run["id"] for run in second.runs]
PY
}

run_check "Run enumeration" test_run_enumeration
run_check "Run metadata lookup" test_get_run
run_check "Filtering" test_filtering
run_check "Sorting and limit" test_sorting_and_limit
run_check "Invalid run tolerance" test_invalid_run_tolerance
run_check "Summary generation" test_summary_generation
run_check "Deterministic ordering" test_deterministic_ordering

echo ""
echo "=============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Runtime registry validation FAILED"
  exit 1
fi

echo "🎉 Runtime registry validation passed"
