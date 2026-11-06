ARG BASE_IMAGE=go-agent
# Local ARM64 mock handoff. This is an image ID, not a registry release digest.
ARG GATEWAY_IMAGE=sha256:0e986137eb422012efad5325c145360723bc54e371025711b69000a58ba9da50
FROM ${GATEWAY_IMAGE} AS gateway
FROM ${BASE_IMAGE}
COPY --from=gateway /usr/local/bin/agentctl /usr/local/bin/agentctl
RUN test "$(dpkg --print-architecture)" = arm64 && \
    echo '680c303326d8e9b35ae4ccb511b3b72e0d85955d3f061b5e4d0e1d481fecb0b6  /usr/local/bin/agentctl' | sha256sum -c -
COPY agentctl.json /etc/agentctl/config.json
RUN chmod 0755 /usr/local/bin/agentctl && chmod 0644 /etc/agentctl/config.json
ENV AGENTCTL_CONFIG=/etc/agentctl/config.json
