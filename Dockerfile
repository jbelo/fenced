FROM golang:1.27.3-bookworm AS git-builder

ARG GIT_VERSION=2.48.1
ARG TMUX_VERSION=3.7c

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    gettext \
    libssl-dev \
    zlib1g-dev \
    libcurl4-gnutls-dev \
    libexpat1-dev \
    libevent-dev \
    libncurses-dev \
    bison \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz" | tar -xJ && \
    cd "git-${GIT_VERSION}" && \
    make prefix=/usr/local -j"$(nproc)" all && \
    make prefix=/usr/local install && \
    cd / && rm -rf "git-${GIT_VERSION}"

RUN curl -fL "https://github.com/tmux/tmux/releases/download/${TMUX_VERSION}/tmux-${TMUX_VERSION}.tar.gz" \
        -o /tmp/tmux.tar.gz && \
    tar -xzf /tmp/tmux.tar.gz -C /tmp && \
    cd "/tmp/tmux-${TMUX_VERSION}" && \
    ./configure --prefix=/usr/local && \
    make -j"$(nproc)" && \
    make install && \
    rm -rf /tmp/tmux.tar.gz "/tmp/tmux-${TMUX_VERSION}"

FROM golang:1.27.3-bookworm

RUN echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/bookworm-backports.list

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    bash \
    vim \
    libevent-core-2.1-7 \
    libtinfo6 \
    netcat-openbsd \
    libcurl4 \
    libexpat1 \
    zlib1g \
    libssl3 \
    perl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=git-builder /usr/local /usr/local
RUN tmux -V

# Install Node 24 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs

RUN npm install -g --allow-scripts=@anthropic-ai/claude-code @openai/codex @anthropic-ai/claude-code \
    && codex --version && claude --version

WORKDIR /workspace

ENV GOMODCACHE=/go/pkg/mod
ENV GOCACHE=/tmp/go-build

# SSH supports the numeric UID used by the read-only agent containers.
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client libnss-wrapper \
    && ln -s /usr/lib/$(gcc -dumpmachine)/libnss_wrapper.so /usr/local/lib/libnss_wrapper.so \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/ssh.sh /usr/local/bin/ssh
RUN chmod 0755 /usr/local/bin/ssh

# Template/story setup uses rsync to copy into writable workspaces.
RUN apt-get update && apt-get install -y --no-install-recommends rsync \
    && rm -rf /var/lib/apt/lists/*
