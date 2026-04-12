#!/bin/bash
###################################################################
# mock.sh — Contract-based Mock AI Adapter
#
# Offline + CI-safe adapter
# Emits structured JSON responses (agent contract)
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

# ---- Validate ----
if [ -z "$COMMAND" ]; then
  echo '{"status":"error","output":"Missing command","next_input":null,"tool_call":null,"meta":{"adapter":"mock"}}'
  exit 1
fi

# ---- JSON-safe builder ----
build_response () {
  local status="$1"
  local output="$2"
  local next_input="${3:-}"

  jq -n \
    --arg status "$status" \
    --arg output "$output" \
    --arg next_input "$next_input" \
    '{
      status: $status,
      output: $output,
      next_input: (if $next_input == "" then null else $next_input end),
      tool_call: null,
      meta: {
        adapter: "mock",
        mode: "offline",
        timestamp: (now | todate)
      }
    }'
}

# ---- Behavior simulation ----
case "$COMMAND" in

  run)
    build_response "done" "[MOCK RUN] Executing task: $INPUT"
    ;;

  explain)
    build_response "done" "[MOCK EXPLAIN] Explanation for: $INPUT"
    ;;

  refactor)
    build_response "done" "[MOCK REFACTOR] Refactoring: $INPUT"
    ;;

  fix)
    build_response "done" "[MOCK FIX] Fixing issue: $INPUT"
    ;;

  query)
    build_response "done" "[MOCK QUERY] Searching for: $INPUT"
    ;;

  *)
    build_response "error" "[MOCK ERROR] Unknown command: $COMMAND"
    ;;
esac