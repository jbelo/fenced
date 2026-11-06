ARG BASE_IMAGE=registry.internal.exoscale.ch/exoscale/kms-xks-proxy:015d4d11ba534da18cbc5e24cef2727e2209d0c1
FROM ${BASE_IMAGE}
USER root
# Upstream copies /usr/bin and /usr/lib from its builder without /usr/share;
# restore a consistent Perl installation before OpenSSH's user-creation hooks.
RUN apt-get update && apt-get install -y --reinstall perl-base perl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/xks-proxy
