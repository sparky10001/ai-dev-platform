###################################################################
# AI Dev Platform — Dev Container Dockerfile
# Base: Ubuntu 22.04
###################################################################

ARG BASE_IMAGE=mcr.microsoft.com/devcontainers/base:ubuntu-22.04
FROM ${BASE_IMAGE}

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

# ---- Docker CLI (Docker-outside-of-Docker) ----
# Allows running docker compose from inside the devcontainer
# Connects to host Docker daemon via mounted socket (/var/run/docker.sock)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
       | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
       "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
       https://download.docker.com/linux/ubuntu \
       $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends \
       docker-ce-cli \
       docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---- Add vscode user to docker group ----
# Required for Docker-outside-of-Docker without sudo
# Note: group membership activates on next shell — post-create.sh
# handles the case where it's not yet active on first run
RUN groupadd -f docker && usermod -aG docker vscode

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
        uvicorn

# Fix venv ownership
RUN chown -R vscode:vscode /opt/venv
        
# Add venv bin to PATH
ENV PATH="/opt/venv/bin:${PATH}"

# ---- Goose CLI ----
# Official install script — handles arch detection, extracts to ~/.local/bin
# bzip2 required to extract the tar.bz2 archive
RUN apt-get update && apt-get install -y --no-install-recommends \
    bzip2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \
       | CONFIGURE=false bash \
    || echo "⚠️ Goose install failed — run manually after container starts"

# ---- Switch to non-root vscode user ----
USER vscode

# Ensure bash is used for RUN/CMD after this point
SHELL ["/bin/bash", "-c"]
