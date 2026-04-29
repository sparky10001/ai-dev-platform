#!/usr/bin/env bash
set -euo pipefail

EXECUTOR="./scripts/tool_executor.py"

BASELINE="$1"
CURRENT="$2"

python3 "$EXECUTOR" compare_results "$(jq -n \
  --arg b "$BASELINE" \
  --arg c "$CURRENT" \
  '{baseline: $b, current: $c}')"