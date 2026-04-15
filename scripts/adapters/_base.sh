#!/bin/bash
###################################################################
# _base.sh — Shared adapter utilities (v2.1 - production hardened)
#
# Guarantees:
# - Contract-compliant JSON output
# - Zero non-zero exits for logical errors
# - Safe JSON handling (no jq crashes)
# - Shared error classification
###################################################################

# ---- Adapter identity (must be set by adapter) ----
ADAPTER_NAME="${ADAPTER_NAME:-unknown}"

# ---- JSON helpers ----
json_escape() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

json_valid() {
  echo "$1" | jq empty >/dev/null 2>&1
}

# ---- Safe fallback (NEVER BREAK CONTRACT) ----
safe_build_response() {
  local msg="${1:-Unknown adapter failure}"

  jq -n \
    --arg output "$msg" \
    --arg adapter "$ADAPTER_NAME" \
    '{
      status: "error",
      output: $output,
      next_input: null,
      tool_call: null,
      meta: {
        adapter: $adapter,
        error_type: "invalid_json",
        timestamp: (now | todate)
      }
    }'
}

# ---- Contract: standard response ----
build_response() {
  local status="$1"
  local output="$2"
  local error_type="${3:-}"
  local extra_meta="${4:-null}"

  jq -n \
    --arg status "$status" \
    --arg output "$output" \
    --arg error_type "$error_type" \
    --arg adapter "$ADAPTER_NAME" \
    --argjson extra "$extra_meta" \
    '{
      status: $status,
      output: $output,
      next_input: null,
      tool_call: null,
      meta: (
        {
          adapter: $adapter,
          error_type: (if $error_type == "" then null else $error_type end),
          timestamp: (now | todate)
        }
        + (if $extra == null then {} else $extra end)
      )
    }' || safe_build_response "build_response failed"
}

# ---- Contract: tool call ----
build_tool_call() {
  local tool_name="$1"
  local tool_input="${2:-{}}"
  local output_msg="${3:-Calling tool}"

  # Ensure tool_input is valid JSON
  if ! echo "$tool_input" | jq empty >/dev/null 2>&1; then
    tool_input="{}"
  fi

  jq -n \
    --arg name "$tool_name" \
    --argjson input "$tool_input" \
    --arg msg "$output_msg" \
    --arg adapter "$ADAPTER_NAME" \
    '{
      status: "tool_call",
      output: $msg,
      next_input: null,
      tool_call: {
        name: $name,
        input: $input
      },
      meta: {
        adapter: $adapter,
        timestamp: (now | todate)
      }
    }' || safe_build_response "build_tool_call failed"
}

# ---- Shared error classification ----
classify_error() {
  local type="$1"
  local msg="$2"

  case "$type" in
    insufficient_quota)
      echo "insufficient_quota"
      ;;
    rate_limit_exceeded)
      echo "rate_limit_exceeded"
      ;;
    invalid_request_error)
      if echo "$msg" | grep -qi "api key"; then
        echo "invalid_api_key"
      else
        echo "invalid_request"
      fi
      ;;
    authentication_error)
      echo "invalid_api_key"
      ;;
    *)
      echo "api_error"
      ;;
  esac
}

# ---- Safe exit (MANDATORY pattern) ----
adapter_exit() {
  exit 0
}