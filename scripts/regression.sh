#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="./evals/results"

LATEST=$(ls -t $RESULTS_DIR/*.json | head -n 1)
PREV=$(ls -t $RESULTS_DIR/*.json | head -n 2 | tail -n 1)

if [ -z "$LATEST" ] || [ -z "$PREV" ]; then
  echo "Not enough results to compare"
  exit 1
fi

echo "Comparing:"
echo "BASELINE: $PREV"
echo "CURRENT : $LATEST"

./scripts/compare.sh "$PREV" "$LATEST"