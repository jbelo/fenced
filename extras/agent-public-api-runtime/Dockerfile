ARG BASE_IMAGE=go-agent
ARG JAVA_IMAGE=eclipse-temurin:25-jre-jammy@sha256:6a11121e5419a1eb4def2bba2f74a4c1b560395b9c26b52e37485d2bf58f7958
FROM ${JAVA_IMAGE} AS java-runtime

FROM ${BASE_IMAGE}

# Add only the Public API Java runtime; keep the agent's tools, shell and entrypoint.
COPY --from=java-runtime /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"
RUN java -version
