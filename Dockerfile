FROM golang:1.26.1-bookworm AS git-builder

ARG GIT_VERSION=2.48.1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    gettext \
    libssl-dev \
    zlib1g-dev \
    libcurl4-gnutls-dev \
    libexpat1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz" | tar -xJ && \
    cd "git-${GIT_VERSION}" && \
    make prefix=/usr/local -j"$(nproc)" all && \
    make prefix=/usr/local install && \
    cd / && rm -rf "git-${GIT_VERSION}"

FROM golang:1.26.1-bookworm

RUN echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/bookworm-backports.list

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    bash \
    vim \
    tmux \
    libcurl4 \
    libexpat1 \
    zlib1g \
    libssl3 \
    perl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=git-builder /usr/local /usr/local

# Install Node 24 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs

RUN npm install -g @mariozechner/pi-coding-agent @openai/codex

WORKDIR /workspace

ENV GOMODCACHE=/go/pkg/mod
ENV GOCACHE=/tmp/go-build
