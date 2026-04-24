#!/bin/bash
###################################################################
# _base.sh — Shared adapter utilities (v8.1 production)
#
# # v8.1 change:
# - Fallback logic is preserved for reference only
# - NO adapters should call these directly anymore
# - LiteLLM + router.sh are now the single source of truth
###################################################################

ADAPTER_NAME="${ADAPTER_NAME:-unknown}"

# ================================================================
# 🧰 JSON HELPERS
# ================================================================

json_escape() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

json_valid() {
  echo "$1" | jq empty >/dev/null 2>&1
}

ensure_json_object() {
  local input="$1"
  if json_valid "$input"; then echo "$input"; else echo "{}"; fi
}

strip_markdown_json() {
  echo "$1" | sed -E 's/^```[a-zA-Z]*//; s/```$//'
}

# ================================================================
# 🔐 INPUT SANITIZATION
# Only use for user-supplied inputs and tool names
# NOT for model output — would mangle code/paths/commands
# ================================================================

sanitize_input() {
  echo "$1" | tr -d ';|&<>`$()'
}

sanitize_tool_name() {
  echo "$1" | grep -Eo '^[a-zA-Z0-9_\-]+' || echo ""
}

# ================================================================
# 🛡️ TOOL VALIDATION
# ================================================================

validate_tool_call() {
  local name="$1"
  local input="$2"

  [ -z "$name" ] && return 1

  local safe_name
  safe_name=$(sanitize_tool_name "$name")

  [ "$safe_name" != "$name" ] && return 1
  ! json_valid "$input" && return 1

  return 0
}

# ================================================================
# 🛡️ SAFE RESPONSE (never-fail fallback)
# ================================================================

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

# ================================================================
# 📦 STANDARD RESPONSE
# NOTE: output is NOT sanitized here — model output must pass
# through clean to preserve code, paths, commands, etc.
# ================================================================

build_response() {
  local status="$1"
  local output="$2"
  local error_type="${3:-}"
  local extra_meta="${4:-null}"

  # Validate extra_meta is JSON or null
  if ! json_valid "$extra_meta" 2>/dev/null; then
    extra_meta="null"
  fi

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

# ================================================================
# 🛠️ TOOL CALL
# ================================================================

build_tool_call() {
  local tool_name="$1"
  local tool_input="${2:-{}}"
  local output_msg="${3:-Calling tool}"

  tool_name=$(sanitize_tool_name "$tool_name")
  tool_input=$(ensure_json_object "$tool_input")

  if ! validate_tool_call "$tool_name" "$tool_input"; then
    safe_build_response "Invalid tool call generated"
    return
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
    }'
}

# ================================================================
# 🔍 TOOL EXTRACTION
# ================================================================

extract_tool_call() {
  local raw="$1"
  local cleaned

  cleaned=$(strip_markdown_json "$raw")

  if json_valid "$cleaned"; then
    echo "$cleaned" | jq -c '
      if .tool_call then .tool_call
      elif .name and .input then {name: .name, input: (.input // {})}
      elif .tool then {name: .tool, input: (.args // .input // {})}
      else empty end
    ' 2>/dev/null && return 0
  fi

  return 1
}

# ================================================================
# 🧠 ERROR CLASSIFICATION
# ================================================================

classify_error() {
  local type="$1"
  local msg="$2"

  case "$type" in
    insufficient_quota)     echo "insufficient_quota" ;;
    rate_limit_exceeded)    echo "rate_limit_exceeded" ;;
    authentication_error)   echo "invalid_api_key" ;;
    invalid_request_error)
      if echo "$msg" | grep -qi "api key"; then
        echo "invalid_api_key"
      else
        echo "invalid_request"
      fi
      ;;
    *) echo "api_error" ;;
  esac
}

# ================================================================
# 💤 FALLBACK SYSTEM (DORMANT — LITE LLM NOW HANDLES ROUTING)
# ================================================================

run_fallback_chain() {
  echo "[base.sh] fallback disabled (handled by LiteLLM/router)" >&2
  return 1
}

attempt_with_fallback() {
  echo "[base.sh] attempt_with_fallback disabled (use router.sh)" >&2
  return 1
}

# ================================================================
# 🚪 EXIT (always 0 — errors in payload not exit code)
# ================================================================

adapter_exit() {
  exit 0
}
