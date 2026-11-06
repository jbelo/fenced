ARG BASE_IMAGE=go-agent
# Same Java major/tools.deps family as Public API CI; pin the multi-platform image.
ARG CLOJURE_IMAGE=clojure:temurin-25-tools-deps-bookworm-slim@sha256:a44f70a920e0a6b7f1b1970a1fbcfbcb4d7386bc05138c5a08389fa9f62d7c3a
FROM ${CLOJURE_IMAGE} AS clojure-tools

FROM ${BASE_IMAGE}

# Copy only the toolchain, preserving the base agent's Git, Node, tmux and shell.
COPY --from=clojure-tools /opt/java/openjdk /opt/java/openjdk
COPY --from=clojure-tools /usr/local/lib/clojure /usr/local/lib/clojure
COPY --from=clojure-tools /usr/local/bin/clojure /usr/local/bin/clj /usr/local/bin/

ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      libnss-wrapper \
      make \
      openssh-client \
      openssl \
      rlwrap \
      unzip \
      zip \
    && nss_library="$(dpkg-query -L libnss-wrapper | sed -n '/\/libnss_wrapper\.so$/p')" \
    && test -f "$nss_library" \
    && ln -s "$nss_library" /usr/local/lib/libnss_wrapper.so \
    && rm -rf /var/lib/apt/lists/* \
    && java -version && javac -version && clojure -Sdescribe

COPY scripts/entrypoint.sh /usr/local/bin/public-api-agent-entrypoint
COPY bin/public-api-clojure /usr/local/bin/public-api-clojure
RUN chmod 0755 /usr/local/bin/public-api-agent-entrypoint /usr/local/bin/public-api-clojure
ENTRYPOINT ["/usr/local/bin/public-api-agent-entrypoint"]
CMD ["/bin/bash"]
