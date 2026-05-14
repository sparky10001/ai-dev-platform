#!/usr/bin/env bash
###################################################################
# runtime_dataset_tests.sh
#
# Phase 3D Runtime Dataset Validation Suite
#
# Validates:
# - single run export
# - bulk run export
# - query export
# - deterministic ordering
# - malformed run handling
# - replay compatibility
# - NDJSON integrity
# - schema validation
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

export AI_ADAPTER="mock"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"
MODEL="dataset_model_$$"
BAD_RUN="dataset_bad_trace_$$"

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
echo "🧪 Runtime Dataset Validation"
echo "============================="
echo ""

RUN_A=$(make_run "dataset alpha" "${TMP_DIR}/run_a.json")
RUN_B=$(make_run "Create a file for dataset beta" "${TMP_DIR}/run_b.json")

# ================================================================
# Single export + schema validation
# ================================================================

test_single_export() {
  RUN_A="$RUN_A" OUT="${TMP_DIR}/single.jsonl" python3 - <<'PY'
import json
import os
from runtime.datasets import export_run
from runtime.schemas import DatasetRecord

path = export_run(os.environ["RUN_A"], os.environ["OUT"])
lines = path.read_text(encoding="utf-8").splitlines()
assert len(lines) == 1
record = DatasetRecord.model_validate(json.loads(lines[0]))
assert record.run_id == os.environ["RUN_A"]
assert record.run["id"] == os.environ["RUN_A"]
assert record.eval.replay_valid is True
assert record.eval.schema_valid is True
assert len(record.trace) >= 3
PY
}

# ================================================================
# Bulk export + deterministic ordering
# ================================================================

test_bulk_export_ordering() {
  RUN_A="$RUN_A" RUN_B="$RUN_B" OUT="${TMP_DIR}/bulk.jsonl" python3 - <<'PY'
import json
import os
from runtime.datasets import export_runs
from runtime.schemas import DatasetRecord

path = export_runs([os.environ["RUN_B"], os.environ["RUN_A"]], os.environ["OUT"])
lines = path.read_text(encoding="utf-8").splitlines()
records = [DatasetRecord.model_validate(json.loads(line)) for line in lines]
ids = [record.run_id for record in records]
assert ids == sorted([os.environ["RUN_A"], os.environ["RUN_B"]])
assert len(lines) == 2
assert all(line.strip() for line in lines)
PY
}

# ================================================================
# Query export
# ================================================================

test_query_export() {
  MODEL="$MODEL" OUT="${TMP_DIR}/query.jsonl" python3 - <<'PY'
import json
import os
from runtime.datasets import export_query
from runtime.schemas import DatasetRecord

path = export_query({"model": os.environ["MODEL"], "sort_by": "created_at"}, os.environ["OUT"])
lines = path.read_text(encoding="utf-8").splitlines()
records = [DatasetRecord.model_validate(json.loads(line)) for line in lines]
assert len(records) == 2
assert all(record.run["model"] == os.environ["MODEL"] for record in records)
PY
}

# ================================================================
# Eval dataset
# ================================================================

test_eval_dataset() {
  RUN_A="$RUN_A" RUN_B="$RUN_B" OUT="${TMP_DIR}/evals.jsonl" python3 - <<'PY'
import json
import os
from runtime.datasets import build_eval_dataset
from runtime.schemas import EvalDatasetRecord

path = build_eval_dataset([os.environ["RUN_B"], os.environ["RUN_A"]], os.environ["OUT"])
lines = path.read_text(encoding="utf-8").splitlines()
records = [EvalDatasetRecord.model_validate(json.loads(line)) for line in lines]
assert [record.run_id for record in records] == sorted([os.environ["RUN_A"], os.environ["RUN_B"]])
assert all(record.eval.completed for record in records)
assert all(record.eval.replay_valid for record in records)
PY
}

# ================================================================
# Trace dataset + replay compatibility
# ================================================================

test_trace_dataset_replay_compatibility() {
  RUN_A="$RUN_A" OUT="${TMP_DIR}/traces.jsonl" python3 - <<'PY'
import json
import os
from runtime.datasets import build_trace_dataset
from runtime.schemas import TraceDatasetRecord
from runtime.validator import validate_event

path = build_trace_dataset([os.environ["RUN_A"]], os.environ["OUT"])
lines = path.read_text(encoding="utf-8").splitlines()
assert len(lines) >= 3
records = [TraceDatasetRecord.model_validate(json.loads(line)) for line in lines]
assert [record.event_index for record in records] == list(range(len(records)))
for record in records:
    validate_event(record.event)
PY
}

# ================================================================
# Malformed run handling
# ================================================================

test_malformed_run_handling() {
  local bad_dir="${ROOT_DIR}/runs/${BAD_RUN}"

  mkdir -p "$bad_dir"
  printf '{"id":"%s","status":"done","created_at":1,"completed_at":2}
' "$BAD_RUN" > "${bad_dir}/run.json"
  printf '{"status":"done"}
' > "${bad_dir}/result.json"
  printf 'not json
' > "${bad_dir}/trace.jsonl"

  BAD_RUN="$BAD_RUN" OUT="${TMP_DIR}/bad.jsonl" python3 - <<'PY'
import os
from runtime.datasets import export_run

try:
    export_run(os.environ["BAD_RUN"], os.environ["OUT"])
except RuntimeError as exc:
    assert "Replay failed" in str(exc)
else:
    raise AssertionError("malformed run export did not fail")
PY
}

# ================================================================
# Deterministic serialization
# ================================================================

test_deterministic_serialization() {
  RUN_A="$RUN_A" OUT1="${TMP_DIR}/det1.jsonl" OUT2="${TMP_DIR}/det2.jsonl" python3 - <<'PY'
import os
from runtime.datasets import export_run

p1 = export_run(os.environ["RUN_A"], os.environ["OUT1"])
p2 = export_run(os.environ["RUN_A"], os.environ["OUT2"])
assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")
PY
}

run_check "Single export" test_single_export
run_check "Bulk export ordering" test_bulk_export_ordering
run_check "Query export" test_query_export
run_check "Eval dataset" test_eval_dataset
run_check "Trace replay compatibility" test_trace_dataset_replay_compatibility
run_check "Malformed run handling" test_malformed_run_handling
run_check "Deterministic serialization" test_deterministic_serialization

echo ""
echo "============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Runtime dataset validation FAILED"
  exit 1
fi

echo "🎉 Runtime dataset validation passed"
