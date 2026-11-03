ARG BASE_IMAGE=go-agent
ARG AGENT_GATEWAY_IMAGE=go-agent-gateway
ARG TERRAFORM_IMAGE=go-agent-terraform
ARG OPENBAO_IMAGE=quay.io/openbao/openbao:2.7.1
ARG REDPANDA_VERSION=v26.1.6
ARG JAVA_IMAGE=eclipse-temurin:25-jre-jammy@sha256:6a11121e5419a1eb4def2bba2f74a4c1b560395b9c26b52e37485d2bf58f7958

FROM ${JAVA_IMAGE} AS java-runtime

FROM docker.redpanda.com/redpandadata/redpanda:${REDPANDA_VERSION} AS redpanda

FROM ${TERRAFORM_IMAGE} AS terraform

FROM ${OPENBAO_IMAGE} AS openbao

FROM ${AGENT_GATEWAY_IMAGE} AS gateway-client

FROM ${BASE_IMAGE}

ARG FDB_VERSION=7.3.68
ARG TARGETARCH

COPY --from=redpanda /usr/bin/rpk /usr/local/bin/rpk
COPY --from=redpanda /opt/redpanda/libexec/rpk /opt/redpanda/libexec/rpk

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
    deb_arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "${deb_arch}" in \
      amd64) fdb_arch=amd64 ;; \
      arm64) fdb_arch=aarch64 ;; \
      *) echo "unsupported architecture=${deb_arch}" >&2; exit 1 ;; \
    esac; \
    curl -fL -o /tmp/foundationdb-clients.deb \
      "https://github.com/apple/foundationdb/releases/download/${FDB_VERSION}/foundationdb-clients_${FDB_VERSION}-1_${fdb_arch}.deb"; \
    dpkg -i /tmp/foundationdb-clients.deb || apt-get install -y -f; \
    rm -f /tmp/foundationdb-clients.deb; \
    rm -rf /var/lib/apt/lists/*

# Same Java 25 runtime as agent-public-api-runtime; no Clojure build tools.
COPY --from=java-runtime /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"
RUN java -version

# Reuse the checksum-verified binary built by the Terraform extra.
COPY --from=terraform /usr/local/bin/terraform /usr/local/bin/terraform
RUN CHECKPOINT_DISABLE=1 terraform version

# OpenBao client only; the service is managed separately.
COPY --from=openbao /usr/bin/bao /usr/local/bin/bao
RUN bao version

COPY --from=gateway-client /usr/local/bin/agentctl /usr/local/bin/agentctl
COPY --from=gateway-client /etc/agentctl/config.json /etc/agentctl/config.json
ENV AGENTCTL_CONFIG=/etc/agentctl/config.json
