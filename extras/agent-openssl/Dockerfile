ARG BASE_IMAGE=go-agent
FROM ${BASE_IMAGE}

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential \
      libssl-dev \
      openssl \
      pkg-config; \
    pkg-config --cflags --libs openssl; \
    printf '#include <openssl/cms.h>\nint main(void){return 0;}\n' | \
      cc $(pkg-config --cflags openssl) -x c - $(pkg-config --libs openssl) -o /tmp/openssl-cms-smoke; \
    rm -f /tmp/openssl-cms-smoke; \
    rm -rf /var/lib/apt/lists/*
