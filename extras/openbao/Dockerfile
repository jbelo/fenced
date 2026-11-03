ARG BASE_IMAGE=go-agent
ARG OPENBAO_IMAGE=quay.io/openbao/openbao:2.7.1
FROM ${OPENBAO_IMAGE} AS openbao
FROM ${BASE_IMAGE}
COPY --from=openbao /usr/bin/bao /usr/local/bin/bao
RUN bao version
