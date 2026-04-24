###################################################################
# LiteLLM Service Container
#
# Routes AI requests to any provider:
#   - Ollama (local, http://ollama:11434)
#   - OpenAI (cloud, requires OPENAI_API_KEY)
#   - Anthropic/Claude (cloud, requires ANTHROPIC_API_KEY)
#
# API: OpenAI-compatible on port 4000
###################################################################

FROM ghcr.io/berriai/litellm:main-latest

# ---- Labels ----
LABEL maintainer="ai-dev-platform"
LABEL description="LiteLLM routing service — any model, one API"
LABEL version="1.0.0"

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

# ---- Copy config and entrypoint ----
COPY config.yaml /app/config.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ---- Environment defaults ----
ENV LITELLM_PORT=4000
ENV LITELLM_CONFIG=/app/config.yaml
ENV ACTIVE_MODEL=fast

# ---- Expose port ----
EXPOSE 4000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD curl -sf http://localhost:4000/health || \
      curl -sf http://localhost:4000/v1/models || exit 1

ENTRYPOINT ["/entrypoint.sh"]
