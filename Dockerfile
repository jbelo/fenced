FROM golang:1.26.1-bookworm

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    bash \
    vim \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Install Node 24 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs

RUN npm install -g @mariozechner/pi-coding-agent @openai/codex

WORKDIR /workspace

ENV GOMODCACHE=/go/pkg/mod
ENV GOCACHE=/tmp/go-build
