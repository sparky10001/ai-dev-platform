###################################################################
# Ollama Service Container
#
# TWO BUILD MODES via OLLAMA_IMAGE build arg:
#
#   Full (default) — official ollama/ollama (~4GB, CUDA included)
#     docker compose build
#     docker compose build --build-arg OLLAMA_IMAGE=ollama/ollama:latest
#
#   Lightweight — alpine/ollama (~70MB, CPU-only, no CUDA)
#     docker compose build --build-arg OLLAMA_IMAGE=alpine/ollama:latest
#     or set in .env: OLLAMA_IMAGE=alpine/ollama:latest
#
# Auto-pulls tinyllama on first start via entrypoint
# Persistent model storage via named volume
# OpenAI-compatible API on port 11434
###################################################################

ARG OLLAMA_IMAGE=ollama/ollama:latest

FROM ${OLLAMA_IMAGE}

# ---- Labels ----
LABEL maintainer="ai-dev-platform"
LABEL description="Ollama local LLM service with tinyllama"
LABEL version="1.1.0"

# ---- Install curl for healthcheck ----
# Handles both debian-based (ollama/ollama) and alpine-based (alpine/ollama)
RUN if command -v apt-get > /dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends curl \
        && apt-get clean && rm -rf /var/lib/apt/lists/*; \
    elif command -v apk > /dev/null 2>&1; then \
        apk add --no-cache curl; \
    else \
        echo "⚠️ Unknown package manager — curl may not be available"; \
    fi

# ---- Copy entrypoint ----
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ---- Environment defaults ----
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/root/.ollama/models
ENV DEFAULT_MODEL=tinyllama

# ---- Expose port ----
EXPOSE 11434

# ---- Healthcheck ----
# Checks tinyllama is loaded, not just server is up
# start_period=180s covers tinyllama pull time on first run
HEALTHCHECK --interval=15s --timeout=5s --start-period=180s --retries=10 \
    CMD curl -sf http://localhost:11434/api/tags \
        | grep -q "tinyllama" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
