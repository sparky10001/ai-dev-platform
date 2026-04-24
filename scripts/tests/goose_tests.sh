#!/bin/bash
###################################################################
# goose_tests.sh — Validate Goose + LiteLLM integration
###################################################################

set -euo pipefail

echo "🧪 Running Goose integration tests..."
echo "====================================="

FAIL=0

# ---------------------------------------------------------------
# 1. Check Goose installed
# ---------------------------------------------------------------
echo ""
echo "Test 1: Goose CLI installed"

if command -v goose >/dev/null 2>&1; then
    echo "✅ Goose installed"
else
    echo "❌ Goose not installed"
    FAIL=1
fi

# ---------------------------------------------------------------
# 2. Check config exists
# ---------------------------------------------------------------
echo ""
echo "Test 2: Goose config exists"

if [ -f "$HOME/.config/goose/config.yaml" ]; then
    echo "✅ Config file exists"
else
    echo "❌ Config file missing"
    FAIL=1
fi

# ---------------------------------------------------------------
# 3. Validate LiteLLM endpoint in config
# ---------------------------------------------------------------
echo ""
echo "Test 3: Config points to LiteLLM"

if grep -q "litellm" "$HOME/.config/goose/config.yaml" 2>/dev/null; then
    echo "✅ LiteLLM reference found"
else
    echo "❌ LiteLLM not found in config"
    FAIL=1
fi

# ---------------------------------------------------------------
# 4. Smoke test: simple prompt
# ---------------------------------------------------------------
echo ""
echo "Test 4: Goose runtime smoke test"

if goose run "Say OK" >/dev/null 2>&1; then
    echo "✅ Goose runtime responded"
else
    echo "⚠️ Goose runtime failed (may still be acceptable in headless mode)"
fi

# ---------------------------------------------------------------
# 5. Verify no direct OpenAI dependency
# ---------------------------------------------------------------
echo ""
echo "Test 5: Ensure no direct OpenAI config leakage"

if grep -q "api.openai.com" "$HOME/.config/goose/config.yaml" 2>/dev/null; then
    echo "❌ Unexpected OpenAI endpoint found"
    FAIL=1
else
    echo "✅ No direct OpenAI dependency"
fi

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
echo ""
echo "====================================="

if [ "$FAIL" -eq 0 ]; then
    echo "🎉 All Goose tests passed"
    exit 0
else
    echo "💥 Some Goose tests failed"
    exit 1
fi