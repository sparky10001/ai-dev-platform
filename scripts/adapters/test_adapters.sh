#!/bin/bash
set -e

echo "== Basic Tests =="

./mock.sh run "hello" | jq .
./mock.sh explain "test" | jq .

echo "== Tool Call Test =="

TOOL_CALL=$(./mock.sh run "read README")
echo "$TOOL_CALL" | jq .

echo "== Tool Result Test =="

./mock.sh run '{"type":"tool_result","tool":"read_file","result":"ok"}' | jq .

echo "== Done =="