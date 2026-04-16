#!/bin/bash
###################################################################
# _base.sh — Shared adapter utilities (v4 production, unified core)
#
# Guarantees:
# - Contract-compliant JSON output
# - Zero non-zero exits for logical errors
# - Safe JSON handling (no jq crashes)
# - Strong tool-call extraction + normalization
# - Cross-adapter behavioral consistency
###################################################################

# ---- Adapter identity ----
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
  if json_valid "$input"; then
    echo "$input"
  else
    echo "{}"
  fi
}

# Strip ```json ... ``` or ``` ... ```
strip_markdown_json() {
  echo "$1" | sed -E 's/^```[a-zA-Z]*//; s/```$//'
}

# ================================================================
# 🛡️ SAFE FALLBACK
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
# 📦 CONTRACT: STANDARD RESPONSE
# ================================================================

build_response() {
  local status="$1"
  local output="$2"
  local error_type="${3:-}"
  local extra_meta="${4:-null}"

  # sanitize extra_meta
  if ! json_valid "$extra_meta"; then
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
# 🛠️ CONTRACT: TOOL CALL
# ================================================================

build_tool_call() {
  local tool_name="$1"
  local tool_input="${2:-{}}"
  local output_msg="${3:-Calling tool}"

  tool_input=$(ensure_json_object "$tool_input")

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

# ================================================================
# 🔍 TOOL CALL EXTRACTION (HARDENED CORE)
# ================================================================

extract_tool_call() {
  local raw="$1"
  local cleaned
  local candidate

  # ---- Step 1: strip markdown wrappers ----
  cleaned=$(strip_markdown_json "$raw")

  # ---- Step 2: direct JSON parse ----
  if json_valid "$cleaned"; then

    # Case A: full contract shape
    if echo "$cleaned" | jq -e '.tool_call.name' >/dev/null 2>&1; then
      echo "$cleaned" | jq -c '.tool_call'
      return 0
    fi

    # Case B: already normalized
    if echo "$cleaned" | jq -e '.name and .input' >/dev/null 2>&1; then
      echo "$cleaned" | jq -c '{name: .name, input: (.input // {})}'
      return 0
    fi

    # Case C: alt schema (tool/args)
    if echo "$cleaned" | jq -e '.tool and (.args or .input)' >/dev/null 2>&1; then
      echo "$cleaned" | jq -c '{name: .tool, input: (.args // .input // {})}'
      return 0
    fi
  fi

  # ---- Step 3: extract first JSON object from text ----
  candidate=$(echo "$cleaned" | grep -o '{.*}' | head -n 1)

  if json_valid "$candidate"; then

    if echo "$candidate" | jq -e '.tool_call.name' >/dev/null 2>&1; then
      echo "$candidate" | jq -c '.tool_call'
      return 0
    fi

    if echo "$candidate" | jq -e '.name and .input' >/dev/null 2>&1; then
      echo "$candidate" | jq -c '{name: .name, input: (.input // {})}'
      return 0
    fi
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

# ================================================================
# 🚪 SAFE EXIT
# ================================================================

adapter_exit() {
  exit 0
}