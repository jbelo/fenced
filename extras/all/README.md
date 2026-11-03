# All extras addon

This folder builds an optional `go-agent-all` image with the currently common agent extras:

- OpenBao 2.7.1 `bao` CLI (service managed separately)
- Gateway `agentctl` and read-only endpoint config ([ARM64 mock handoff](../agent-gateway/README.md))
- Redpanda `rpk`
- FoundationDB client tools and libraries
- OpenSSL development support
- Terraform 1.11.4 CLI (from the checksum-verified [Terraform extra](../terraform/README.md))
- Java 25 JRE (the same pinned runtime as [agent-public-api-runtime](../agent-public-api-runtime/README.md))

The image extends the main `go-agent` image. It does not replace the standalone Redpanda or FoundationDB service containers.

## Build

Build the base image first:

```sh
make build
```

Then build the union image:

The gateway CLI currently requires the local ARM64 mock image documented in the
[agent-gateway extra](../agent-gateway/README.md). This limits this build to ARM64
until a verified multi-architecture handoff is available.

The build refreshes `go-agent-gateway` and then refreshes `go-agent-terraform` from the selected base image,
then copies its Terraform binary into the combined image. Override
`AGENT_TERRAFORM_IMAGE` if you need a different intermediate image name.

```sh
make -f extras/all/Makefile agent-all-build
make -f extras/all/Makefile agent-all-check
```

This creates:

```text
go-agent-all
```

Override versions or image names when needed:

```sh
make -f extras/all/Makefile agent-all-build \
  REDPANDA_VERSION=v26.1.6 \
  FDB_VERSION=7.3.68 \
  AGENT_ALL_IMAGE=go-agent-all
```

`OPENBAO_IMAGE` overrides the official OpenBao image used as the CLI source.

## Use

Run an agent shell with the union image:

```sh
story-shell --image go-agent-all
```

or, with the low-level launcher:

```sh
run-shell --image go-agent-all --host-root .
```

## Notes

- `JAVA_IMAGE` overrides the pinned Java runtime source. The combined image adds
  the JRE, not Clojure CLI or the Public API dependency-cache tooling. Host-built
  Java applications still need their own configuration and credentials.
- `agent-all-check` verifies installed tools without networking or service access.
  It also initializes and validates a temporary provider-free Terraform project.
- Terraform providers, modules, backend access, and credentials are supplied separately.
  See the [Terraform network prerequisites](../terraform/README.md#use).
- Rebuild `go-agent-all` whenever the base `go-agent` image changes.
- Start Redpanda and FoundationDB separately when tests need the actual services.
- The FoundationDB client package is selected for `amd64` or `arm64` Docker builds.
