ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server procps less \
    && rm -f /etc/ssh/ssh_host_* \
    && rm -rf /var/lib/apt/lists/*
COPY sshd_config /etc/ssh/sshd_config
COPY scripts/entrypoint.sh /usr/local/bin/ssh-entrypoint
RUN chmod 0755 /usr/local/bin/ssh-entrypoint
ENTRYPOINT ["/usr/local/bin/ssh-entrypoint"]
CMD []
