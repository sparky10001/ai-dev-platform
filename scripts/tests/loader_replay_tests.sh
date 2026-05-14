#!/usr/bin/env bash
###################################################################
# loader_replay_tests.sh
#
# Phase 3 Replay Loader Validation Suite
#
# Validates:
# - full run loading
# - replay-backed trace loading
# - strict invalid NDJSON handling
# - schema validation during load
# - missing run handling
# - replay ordering preservation
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
  rm -rf "${ROOT_DIR}/runs/loader_bad_json_$$"          "${ROOT_DIR}/runs/loader_bad_schema_$$"
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

echo ""
echo "🧪 Replay Loader Validation"
echo "============================"
echo ""

OUTPUT_FILE="${TMP_DIR}/output.json"

AI_TRACE=1 "$RUNTIME" run "loader replay validation"   > "$OUTPUT_FILE"   2> "${TMP_DIR}/stderr.log"

RUN_ID=$(jq -r '.meta.run_id' "$OUTPUT_FILE")

# ================================================================
# Successful replay-aware loading
# ================================================================

test_successful_full_load() {
  RUN_ID="$RUN_ID" python3 - <<'PY'
import os
from runtime.loader import load_full_run

bundle = load_full_run(os.environ["RUN_ID"])
assert set(bundle.keys()) == {"run", "result", "trace"}
assert bundle["run"]["id"] == os.environ["RUN_ID"]
assert bundle["result"]["status"] in {"done", "error"}
assert len(bundle["trace"]) >= 3
assert all(evt.schema_version == 1 for evt in bundle["trace"])
PY
}

# ================================================================
# Compatibility alias
# ================================================================

test_load_run_trace_alias() {
  RUN_ID="$RUN_ID" python3 - <<'PY'
import os
from runtime.loader import load_trace, load_run_trace

trace = load_trace(os.environ["RUN_ID"])
alias_trace = load_run_trace(os.environ["RUN_ID"])
assert [evt.event for evt in trace] == [evt.event for evt in alias_trace]
PY
}

# ================================================================
# Ordering preservation
# ================================================================

test_ordering_preserved() {
  RUN_ID="$RUN_ID" python3 - <<'PY'
import os
from runtime.loader import load_trace

trace = load_trace(os.environ["RUN_ID"])
events = [evt.event for evt in trace]
assert events[0] == "session_start"
assert events[-1] == "session_end"
assert "agent_output" in events
assert events.index("agent_output") < events.index("session_end")
assert [evt.timestamp for evt in trace] == sorted(evt.timestamp for evt in trace)
PY
}

# ================================================================
# Invalid NDJSON should raise deterministic replay error
# ================================================================

test_invalid_ndjson() {
  local bad_run="loader_bad_json_$$"
  local bad_dir="${ROOT_DIR}/runs/${bad_run}"

  mkdir -p "$bad_dir"
  printf '{"id":"%s"}
' "$bad_run" > "${bad_dir}/run.json"
  printf '{"status":"done"}
' > "${bad_dir}/result.json"
  printf '{"schema_version":1,"timestamp":1,"run_id":"%s","event":"session_start","data":{}}
' "$bad_run" > "${bad_dir}/trace.jsonl"
  printf 'not json
' >> "${bad_dir}/trace.jsonl"

  RUN_ID="$bad_run" python3 - <<'PY'
import os
from runtime.loader import load_trace

try:
    load_trace(os.environ["RUN_ID"])
except RuntimeError as exc:
    assert "Replay failed at line 2" in str(exc)
else:
    raise AssertionError("invalid NDJSON did not fail")
PY
}

# ================================================================
# Invalid event schema should fail during replay loading
# ================================================================

test_invalid_schema() {
  local bad_run="loader_bad_schema_$$"
  local bad_dir="${ROOT_DIR}/runs/${bad_run}"

  mkdir -p "$bad_dir"
  printf '{"id":"%s"}
' "$bad_run" > "${bad_dir}/run.json"
  printf '{"status":"done"}
' > "${bad_dir}/result.json"
  printf '{"schema_version":1,"timestamp":1,"run_id":"%s","event":"unknown","data":{}}
' "$bad_run" > "${bad_dir}/trace.jsonl"

  RUN_ID="$bad_run" python3 - <<'PY'
import os
from runtime.loader import load_trace

try:
    load_trace(os.environ["RUN_ID"])
except RuntimeError as exc:
    assert "Unknown event type" in str(exc)
else:
    raise AssertionError("invalid event schema did not fail")
PY
}

# ================================================================
# Missing run should raise FileNotFoundError
# ================================================================

test_missing_run() {
  python3 - <<'PY'
from runtime.loader import load_full_run

try:
    load_full_run("run_loader_missing")
except FileNotFoundError:
    pass
else:
    raise AssertionError("missing run did not raise FileNotFoundError")
PY
}

run_check "Successful replay loading" test_successful_full_load
run_check "Compatibility alias loading" test_load_run_trace_alias
run_check "Replay ordering preservation" test_ordering_preserved
run_check "Invalid NDJSON handling" test_invalid_ndjson
run_check "Schema validation during load" test_invalid_schema
run_check "Missing run handling" test_missing_run

echo ""
echo "============================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Replay loader validation FAILED"
  exit 1
fi

echo "🎉 Replay loader validation passed"
