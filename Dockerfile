ARG GO_IMAGE=golang:1.27.4-bookworm
FROM ${GO_IMAGE} AS git-builder

ARG DEBIAN_SNAPSHOT
COPY host/images/apt-snapshot.sh /tmp/fenced-apt-snapshot.sh
RUN sh /tmp/fenced-apt-snapshot.sh "$DEBIAN_SNAPSHOT"

ARG GIT_VERSION=2.48.1
ARG TMUX_VERSION=3.7c
ARG GIT_SHA256=1c5d545f5dc1eb51e95d2c50d98fdf88b1a36ba1fa30e9ae5d5385c6024f82ad
ARG TMUX_SHA256=7c60cae9a0e25288e2e24750aafc9e8800fc7fd4555e447e1b29ee4201cfb3bf

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

RUN curl -fL "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz" -o /tmp/git.tar.xz && \
    echo "${GIT_SHA256}  /tmp/git.tar.xz" | sha256sum -c - && \
    tar -xJf /tmp/git.tar.xz && \
    cd "git-${GIT_VERSION}" && \
    make prefix=/usr/local -j"$(nproc)" all && \
    make prefix=/usr/local install && \
    cd / && rm -rf "git-${GIT_VERSION}"

RUN curl -fL "https://github.com/tmux/tmux/releases/download/${TMUX_VERSION}/tmux-${TMUX_VERSION}.tar.gz" \
        -o /tmp/tmux.tar.gz && \
    echo "${TMUX_SHA256}  /tmp/tmux.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/tmux.tar.gz -C /tmp && \
    cd "/tmp/tmux-${TMUX_VERSION}" && \
    ./configure --prefix=/usr/local && \
    make -j"$(nproc)" && \
    make install && \
    rm -rf /tmp/tmux.tar.gz "/tmp/tmux-${TMUX_VERSION}"

# Bundle pinned Git checkouts; runtime agents load plugins without network access.
FROM git-builder AS tmux-plugins
RUN set -eu; \
    mkdir -p /opt/tmux-plugins; \
    for entry in \
      tpm:e261deb1b47614eed3400089ce7197dc68acc4eb \
      tmux-resurrect:cff343cf9e81983d3da0c8562b01616f12e8d548 \
      tmux-continuum:0698e8f4b17d6454c71bf5212895ec055c578da0; do \
      plugin="${entry%%:*}"; revision="${entry#*:}"; \
      destination="/opt/tmux-plugins/$plugin"; \
      git init "$destination"; \
      git -C "$destination" remote add origin "https://github.com/tmux-plugins/$plugin.git"; \
      git -C "$destination" fetch --depth 1 origin "$revision"; \
      git -C "$destination" checkout --detach FETCH_HEAD; \
      test "$(git -C "$destination" rev-parse HEAD)" = "$revision"; \
    done; \
    chmod -R a+rX /opt/tmux-plugins

FROM ${GO_IMAGE}
ARG DEBIAN_SNAPSHOT
COPY host/images/apt-snapshot.sh /tmp/fenced-apt-snapshot.sh
RUN sh /tmp/fenced-apt-snapshot.sh "$DEBIAN_SNAPSHOT"

RUN if [ -z "$DEBIAN_SNAPSHOT" ]; then echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/bookworm-backports.list; fi

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    bash \
    vim \
    ripgrep \
    fd-find \
    xz-utils \
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
COPY --from=tmux-plugins /opt/tmux-plugins /opt/tmux-plugins
RUN tmux -V && rg --version && fdfind --version

# Install Node 24 LTS
ARG NODE_DIST_VERSION
ARG NODE_SHA256
ARG LOCKED_NPM=0
ARG NODE_VERSION
ARG CODEX_VERSION=latest
ARG CLAUDE_VERSION=latest
RUN if [ -n "$NODE_SHA256" ]; then \
      case "$(dpkg --print-architecture)" in arm64) node_arch=arm64;; amd64) node_arch=x64;; *) exit 1;; esac; \
      curl -fL "https://nodejs.org/dist/v${NODE_DIST_VERSION}/node-v${NODE_DIST_VERSION}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz && \
      echo "$NODE_SHA256  /tmp/node.tar.xz" | sha256sum -c - && \
      tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && rm /tmp/node.tar.xz; \
    else curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
      apt-get install -y "nodejs${NODE_VERSION:+=$NODE_VERSION}"; fi

COPY host/images/package.json host/images/package-lock.json /opt/fenced-tools/
RUN if [ "$LOCKED_NPM" = 1 ]; then \
      npm ci --prefix /opt/fenced-tools --ignore-scripts --no-audit --no-fund && \
      ln -s /opt/fenced-tools/node_modules/.bin/codex /usr/local/bin/codex && \
      case "$(dpkg --print-architecture)" in arm64) cli_arch=arm64;; amd64) cli_arch=x64;; *) exit 1;; esac && \
      test -x "/opt/fenced-tools/node_modules/@anthropic-ai/claude-code-linux-${cli_arch}/claude" && \
      ln -s "/opt/fenced-tools/node_modules/@anthropic-ai/claude-code-linux-${cli_arch}/claude" /usr/local/bin/claude; \
    else npm install -g --allow-scripts=@anthropic-ai/claude-code "@openai/codex@${CODEX_VERSION}" "@anthropic-ai/claude-code@${CLAUDE_VERSION}"; fi \
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

# tuicr: pinned static release binaries for local terminal code review.
RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
      arm64) tuicr_arch=aarch64; tuicr_sha=94c0cc1672015bc41511657a81b4223596232372715d36131fd16f950b260313 ;; \
      amd64) tuicr_arch=x86_64; tuicr_sha=48ba2ee347400a780756bc0c7726792a1a117b59d7920c10b0157bcf085b5128 ;; \
      *) echo 'Unsupported tuicr architecture' >&2; exit 1 ;; \
    esac; \
    curl -fL --retry 3 "https://github.com/agavra/tuicr/releases/download/v0.29.0/tuicr-0.29.0-${tuicr_arch}-unknown-linux-musl.tar.gz" -o /tmp/tuicr.tar.gz; \
    echo "${tuicr_sha}  /tmp/tuicr.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/tuicr.tar.gz -C /usr/local/bin tuicr; \
    chmod 0755 /usr/local/bin/tuicr; \
    rm /tmp/tuicr.tar.gz; \
    tuicr --version
