###################################################################
# AI Dev Platform — Dev Container Dockerfile
# Base: Ubuntu 22.04
###################################################################

FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# ---- Create workspace folder ----
RUN mkdir -p /workspace
WORKDIR /workspace

# ---- Base tools ----
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    git \
    jq \
    htop \
    make \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ✅ Ensure /bin/sh points to bash (must be ROOT)
RUN ln -sf /bin/bash /bin/sh

# ---- Python virtual environment ----
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install \
        requests \
        python-dotenv \
        httpx \
    && /opt/venv/bin/pip install \
        fastapi \
        pydantic \
        uvicorn  # ← Added for mock_openai.py server

# Add venv bin to PATH
ENV PATH="/opt/venv/bin:${PATH}"

# ---- Goose CLI ----
RUN curl -fsSL https://github.com/block/goose/releases/latest/download/goose-linux-x86_64 \
    -o /usr/local/bin/goose \
    && chmod +x /usr/local/bin/goose \
    || echo "⚠️ Goose install failed — install manually after container starts"

# ---- Switch to non-root vscode user ----
USER vscode

# Ensure bash is used for RUN/CMD after this point
SHELL ["/bin/bash", "-c"]