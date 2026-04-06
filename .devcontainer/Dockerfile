###################################################################
# AI Dev Platform — Dev Container Dockerfile
#
# Base: Ubuntu 22.04 (devcontainers)
# Includes: Python, Node.js, Goose, common dev tools
###################################################################

FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# ---- Base tools ----
RUN apt-get update && apt-get install -y \
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

# ---- Node.js 20 ----
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean

# ---- Python packages ----
RUN pip3 install --break-system-packages \
    requests \
    python-dotenv \
    httpx

# ---- Goose ----
# Official install — https://block.github.io/goose
RUN curl -fsSL https://github.com/block/goose/releases/latest/download/goose-linux-x86_64 \
    -o /usr/local/bin/goose \
    && chmod +x /usr/local/bin/goose \
    || echo "⚠️ Goose install failed — install manually after container starts"

# ---- Environment ----
ENV PATH="/usr/local/bin:/home/vscode/.local/bin:${PATH}"

# ---- Non-root user (devcontainers standard) ----
USER vscode