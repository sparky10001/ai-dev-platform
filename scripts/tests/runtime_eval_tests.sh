#!/usr/bin/env bash
###################################################################
# runtime_eval_tests.sh
#
# Phase 3B Runtime Evaluation Validation Suite
#
# Validates:
# - evaluation generation
# - replay-derived metrics
# - comparison output
# - invalid run handling
# - malformed trace handling
# - evaluation schema validation
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

export AI_ADAPTER="mock"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
  rm -rf "${ROOT_DIR}/runs/eval_bad_trace_$$"          "${ROOT_DIR}/runs/eval_bad_schema_$$"
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

  AI_TRACE=1 "$RUNTIME" run "$prompt"     > "$output_file"     2> "${output_file}.stderr"

  jq -r '.meta.run_id' "$output_file"
}

echo ""
echo "🧪 Runtime Evaluation Validation"
echo "================================"
echo ""

RUN_A=$(make_run "runtime eval validation" "${TMP_DIR}/run_a.json")
RUN_B=$(make_run "Create a file for runtime eval validation" "${TMP_DIR}/run_b.json")

# ================================================================
# Evaluation generation
# ================================================================

test_evaluation_generation() {
  RUN_ID="$RUN_A" python3 - <<'PY'
import os
from runtime.evals import evaluate_run
from runtime.schemas import EvalSummary

summary = evaluate_run(os.environ["RUN_ID"])
assert isinstance(summary, EvalSummary)
assert summary.run_id == os.environ["RUN_ID"]
assert summary.status in {"done", "error"}
assert summary.completed is True
assert summary.replay_valid is True
assert summary.schema_valid is True
assert summary.schema_version == 1
PY
}

# ================================================================
# Replay-derived metrics
# ================================================================

test_replay_metrics() {
  RUN_ID="$RUN_B" python3 - <<'PY'
import os
from runtime.evals import evaluate_run

summary = evaluate_run(os.environ["RUN_ID"])
assert summary.total_events >= 5
assert summary.tool_calls >= 1
assert summary.tool_results >= 1
assert summary.runtime_seconds is None or summary.runtime_seconds >= 0
PY
}

# ================================================================
# Comparison output
# ================================================================

test_comparison_output() {
  RUN_A="$RUN_A" RUN_B="$RUN_B" python3 - <<'PY'
import os
from runtime.evals import compare_runs
from runtime.schemas import EvalComparison

comparison = compare_runs(os.environ["RUN_A"], os.environ["RUN_B"])
assert isinstance(comparison, EvalComparison)
assert comparison.run_a.run_id == os.environ["RUN_A"]
assert comparison.run_b.run_id == os.environ["RUN_B"]
assert comparison.delta_events == comparison.run_b.total_events - comparison.run_a.total_events
assert comparison.delta_tool_calls == comparison.run_b.tool_calls - comparison.run_a.tool_calls
assert comparison.delta_tool_results == comparison.run_b.tool_results - comparison.run_a.tool_results
assert comparison.both_completed is True
assert comparison.replay_valid is True
assert comparison.schema_valid is True
PY
}

# ================================================================
# Missing run handling
# ================================================================

test_missing_run() {
  python3 - <<'PY'
from runtime.evals import evaluate_run

try:
    evaluate_run("run_eval_missing")
except FileNotFoundError:
    pass
else:
    raise AssertionError("missing run did not raise FileNotFoundError")
PY
}

# ================================================================
# Malformed trace handling
# ================================================================

test_malformed_trace() {
  local bad_run="eval_bad_trace_$$"
  local bad_dir="${ROOT_DIR}/runs/${bad_run}"

  mkdir -p "$bad_dir"
  printf '{"id":"%s","status":"done","created_at":1,"completed_at":2}
' "$bad_run" > "${bad_dir}/run.json"
  printf '{"status":"done"}
' > "${bad_dir}/result.json"
  printf 'not json
' > "${bad_dir}/trace.jsonl"

  RUN_ID="$bad_run" python3 - <<'PY'
import os
from runtime.evals import evaluate_run

try:
    evaluate_run(os.environ["RUN_ID"])
except RuntimeError as exc:
    assert "Replay failed at line 1" in str(exc)
else:
    raise AssertionError("malformed trace did not fail")
PY
}

# ================================================================
# Schema validation during evaluation
# ================================================================

test_schema_validation() {
  local bad_run="eval_bad_schema_$$"
  local bad_dir="${ROOT_DIR}/runs/${bad_run}"

  mkdir -p "$bad_dir"
  printf '{"id":"%s","status":"done","created_at":1,"completed_at":2}
' "$bad_run" > "${bad_dir}/run.json"
  printf '{"status":"done"}
' > "${bad_dir}/result.json"
  printf '{"schema_version":1,"timestamp":1,"run_id":"%s","event":"tool_call","data":"write_file"}
' "$bad_run" > "${bad_dir}/trace.jsonl"

  RUN_ID="$bad_run" python3 - <<'PY'
import os
from runtime.evals import evaluate_run

try:
    evaluate_run(os.environ["RUN_ID"])
except RuntimeError as exc:
    assert "Field required" in str(exc) or "step" in str(exc)
else:
    raise AssertionError("invalid event schema did not fail")
PY
}

run_check "Evaluation generation" test_evaluation_generation
run_check "Replay-derived metrics" test_replay_metrics
run_check "Comparison output" test_comparison_output
run_check "Invalid run handling" test_missing_run
run_check "Malformed trace handling" test_malformed_trace
run_check "Schema validation" test_schema_validation

echo ""
echo "================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Runtime evaluation validation FAILED"
  exit 1
fi

echo "🎉 Runtime evaluation validation passed"
