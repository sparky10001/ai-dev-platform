#!/bin/bash
###################################################################
# mock.sh — Mock AI adapter for offline/testing use
#
# Mirrors goose.sh interface exactly — swap with no code changes
# Perfect for: plane mode, CI/CD testing, development without AI
###################################################################

COMMAND=$1
shift

case "$COMMAND" in
  run)
    echo "[MOCK] Would run: $@"
    ;;

  explain)
    echo "[MOCK] Would explain: $@"
    ;;

  refactor)
    echo "[MOCK] Would refactor: $@"
    ;;

  fix)
    echo "[MOCK] Would fix: $@"
    ;;

  query)
    echo "[MOCK] Would query: $@"
    ;;

  "")
    echo "[MOCK] No command provided"
    echo "Usage: mock.sh [run|explain|refactor|fix|query] <args>"
    ;;

  *)
    echo "[MOCK] Unknown command: $COMMAND"
    echo "Usage: mock.sh [run|explain|refactor|fix|query] <args>"
    ;;
esac
