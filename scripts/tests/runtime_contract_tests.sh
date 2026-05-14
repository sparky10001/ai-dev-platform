#!/usr/bin/env bash
###################################################################
# runtime_contract_tests.sh
#
# Phase 3E Runtime Contract Validation Suite
#
# Validates:
# - contract model definitions
# - contract validation helpers
# - validator delegation consistency
# - compatibility assertions
# - canonical JSON serialization
# - dataset/eval contract validation
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

export AI_ADAPTER="mock"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"
MODEL="contract_model_$$"

cleanup() {
  rm -rf "$TMP_DIR"
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
echo "🧪 Runtime Contract Validation"
echo "=============================="
echo ""

RUN_ID=$(make_run "contract validation run" "${TMP_DIR}/run.json")

# ================================================================
# Contract model basics
# ================================================================

test_contract_models() {
  python3 - <<'PY'
from runtime.contracts import CONTRACT_VERSION
from runtime.contracts import DatasetContract
from runtime.contracts import EvalContract
from runtime.contracts import EventContract
from runtime.contracts import RegistryContract
from runtime.contracts import ResponseContract

assert CONTRACT_VERSION == 1
assert EventContract().contract_version == 1
assert ResponseContract().contract_version == 1
assert DatasetContract().contract_version == 1
assert EvalContract().contract_version == 1
assert RegistryContract().contract_version == 1
PY
}

# ================================================================
# Event/response validation delegation consistency
# ================================================================

test_validator_delegation() {
  RUN_ID="$RUN_ID" python3 - <<'PY'
import os
from runtime.contracts import validate_event_contract
from runtime.contracts import validate_response_contract
from runtime.validator import validate_event
from runtime.validator import validate_response

run_id = os.environ['RUN_ID']

event_payload = {
    'schema_version': 1,
    'timestamp': 1.0,
    'run_id': run_id,
    'event': 'session_start',
    'data': {'command': 'run', 'input': 'x'},
}

response_payload = {
    'schema_version': 1,
    'status': 'done',
    'output': 'ok',
    'meta': {
        'schema_version': 1,
        'run_id': run_id,
        'run_path': '/workspace/runs/' + run_id,
        'error': False,
        'trace': [],
    },
}

c_evt = validate_event_contract(event_payload)
v_evt = validate_event(event_payload)
assert c_evt.model_dump(mode='json') == v_evt.model_dump(mode='json')

c_rsp = validate_response_contract(response_payload)
v_rsp = validate_response(response_payload)
assert c_rsp.model_dump(mode='json') == v_rsp.model_dump(mode='json')
PY
}

# ================================================================
# Dataset and eval contract validation
# ================================================================

test_dataset_eval_validation() {
  RUN_ID="$RUN_ID" python3 - <<'PY'
import os
from runtime.contracts import validate_dataset_record
from runtime.contracts import validate_eval_record
from runtime.datasets import build_eval_dataset
from runtime.datasets import build_trace_dataset
from runtime.datasets import export_run

run_id = os.environ['RUN_ID']

single = export_run(run_id, '/tmp/contract_single.jsonl')
payload = single.read_text(encoding='utf-8').strip()
validated = validate_dataset_record(__import__('json').loads(payload))
assert validated.run_id == run_id

erec = build_eval_dataset([run_id])[0]
assert validate_eval_record(erec.eval.model_dump(mode='json')).run_id == run_id

trace_records = build_trace_dataset([run_id])
assert trace_records
assert validate_dataset_record(trace_records[0].model_dump(mode='json')).run_id == run_id
PY
}

# ================================================================
# Compatibility assertions
# ================================================================

test_compatibility_helpers() {
  python3 - <<'PY'
from runtime.contracts import assert_backward_compatible
from runtime.contracts import assert_no_breaking_changes

old = {'a': 1, 'b': {'c': 'x'}, 'd': [1]}
new = {'a': 2, 'b': {'c': 'y', 'z': 1}, 'd': [9], 'e': True}
assert_backward_compatible(old, new)

try:
    assert_backward_compatible({'a': 1, 'b': 2}, {'a': 1})
except ValueError:
    pass
else:
    raise AssertionError('missing key compatibility check failed')

assert_no_breaking_changes()
PY
}

# ================================================================
# Canonical serialization determinism
# ================================================================

test_canonical_json() {
  python3 - <<'PY'
from runtime.contracts import to_canonical_json

one = {'b': 2, 'a': 1}
two = {'a': 1, 'b': 2}
assert to_canonical_json(one) == to_canonical_json(two)
assert to_canonical_json(one) == '{"a":1,"b":2}'
PY
}

run_check "Contract model definitions" test_contract_models
run_check "Validator delegation" test_validator_delegation
run_check "Dataset/eval validation" test_dataset_eval_validation
run_check "Compatibility helpers" test_compatibility_helpers
run_check "Canonical JSON determinism" test_canonical_json

echo ""
echo "=============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Runtime contract validation FAILED"
  exit 1
fi

echo "🎉 Runtime contract validation passed"
