ARG BASE_IMAGE=go-agent
ARG REDPANDA_VERSION=v26.1.6

FROM docker.redpanda.com/redpandadata/redpanda:${REDPANDA_VERSION} AS redpanda

FROM ${BASE_IMAGE}

COPY --from=redpanda /usr/bin/rpk /usr/local/bin/rpk
COPY --from=redpanda /opt/redpanda/libexec/rpk /opt/redpanda/libexec/rpk
