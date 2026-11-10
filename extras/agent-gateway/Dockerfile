ARG BASE_IMAGE=go-agent
# Verified ARM64 feedback delivery; local image ID, not a registry release digest.
ARG GATEWAY_IMAGE=sha256:421c381f611379447bfc0ecc77469ffa69a3234fa26c55cdb3c9c14ab8af9a3d
FROM ${GATEWAY_IMAGE} AS gateway
FROM ${BASE_IMAGE}
COPY --from=gateway /usr/local/bin/agentctl /usr/local/bin/agentctl
RUN test "$(dpkg --print-architecture)" = arm64 && \
    echo 'b41301ae9176288f8d7ee3368de4e264e97a462b19c2f5a503dfb4adb14cdd2b  /usr/local/bin/agentctl' | sha256sum -c -
COPY agentctl.json /etc/agentctl/config.json
RUN chmod 0755 /usr/local/bin/agentctl && chmod 0644 /etc/agentctl/config.json
ENV AGENTCTL_CONFIG=/etc/agentctl/config.json
