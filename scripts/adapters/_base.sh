#!/bin/bash
###################################################################
# _base.sh — Shared adapter utilities (v8 production)
#
# Fixes from v7:
# - Removed sanitize_input from build_response output (was mangling code)
# - Fixed FALLBACK_CHAIN comma-split (was space-split, breaking chain)
# - sanitize_input kept for tool names and user inputs only
# - No symlinks anywhere
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
# 🔥 FALLBACK CHAIN
#
# Fix v8: FALLBACK_CHAIN is comma-separated — use IFS split
# Previously used space iteration which broke with comma values
# ================================================================

run_fallback_chain() {
  local prompt="$1"
  local reason="$2"

  # Read comma-separated chain — consistent with switch-model.sh
  local CHAIN="${FALLBACK_CHAIN:-mock}"
  IFS=',' read -ra CHAIN_ARRAY <<< "$CHAIN"

  for provider in "${CHAIN_ARRAY[@]}"; do

    # Trim whitespace
    provider=$(echo "$provider" | tr -d ' ')

    local endpoint
    case "$provider" in
      mock)       endpoint="${MOCK_ENDPOINT:-http://localhost:8000/v1}" ;;
      local)      endpoint="${LOCAL_LLM_ENDPOINT:-http://localhost:11434/v1}" ;;
      ollama)     endpoint="${OLLAMA_ENDPOINT:-http://host.docker.internal:11434}/v1" ;;
      http-agent) endpoint="${MODEL_ENDPOINT:-}" ;;
      *)          continue ;;
    esac

    [ -z "$endpoint" ] || [ "$endpoint" = "none/v1" ] && continue

    local RESPONSE
    RESPONSE=$(curl -sS --max-time 10 \
      -X POST "${endpoint}/chat/completions" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg model "fallback-${provider}" \
        --arg prompt "$prompt" \
        '{
          model: $model,
          messages: [{role:"user", content:$prompt}],
          temperature: 0.7
        }')" \
      2>/dev/null || true)

    if json_valid "$RESPONSE"; then
      local OUTPUT
      OUTPUT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')

      if [ -n "$OUTPUT" ]; then
        build_response "done" "[FALLBACK ${provider}] ${OUTPUT}" "" \
          "$(jq -n \
            --arg mode "fallback" \
            --arg provider "$provider" \
            --arg reason "$reason" \
            '{mode:$mode, provider:$provider, reason:$reason}')"
        return 0
      fi
    fi

  done

  # All fallbacks exhausted
  build_response "error" "All fallback providers failed (chain: ${CHAIN})" "api_error" \
    "$(jq -n --arg reason "$reason" '{reason:$reason}')"
}

# ================================================================
# 🔁 ADAPTER ENTRYPOINT
# ================================================================

attempt_with_fallback() {
  local prompt="$1"
  local reason="${2:-unknown_failure}"

  # Prevent recursion
  if [ "${FALLBACK_ACTIVE:-false}" = "true" ]; then
    build_response "error" "Fallback recursion prevented" "api_error"
    return
  fi

  export FALLBACK_ACTIVE=true

  run_fallback_chain "$prompt" "$reason"
  adapter_exit
}

# ================================================================
# 🚪 EXIT (always 0 — errors in payload not exit code)
# ================================================================

adapter_exit() {
  exit 0
}
