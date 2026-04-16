ARG BASE_IMAGE=go-agent
FROM ${BASE_IMAGE}

ARG FDB_VERSION=7.3.68

RUN set -eux; \
    curl -fL -o /tmp/foundationdb-clients.deb \
      "https://github.com/apple/foundationdb/releases/download/${FDB_VERSION}/foundationdb-clients_${FDB_VERSION}-1_aarch64.deb"; \
    dpkg -i /tmp/foundationdb-clients.deb || (apt-get update && apt-get install -y -f); \
    rm -f /tmp/foundationdb-clients.deb; \
    rm -rf /var/lib/apt/lists/*
