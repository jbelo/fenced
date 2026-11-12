# All extras addon

This folder builds an optional `go-agent-all` image with the currently common agent extras:

- OpenBao 2.7.1 `bao` CLI (service managed separately)
- Gateway `agentctl` and read-only endpoint config ([portable CLI integration](../agent-gateway/README.md))
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

The legacy Make path uses the local ARM64 gateway default. For a fresh host, use
the portable build path below with the verified gateway/client pair.

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

## Portable build from recorded inputs

Build the locked base image using `host/build-images.py --inputs`, then build the
matching [portable gateway/client pair](../agent-gateway/portable/README.md). Keep
both completed receipts. On the same native host:

```sh
python3 extras/all/build-images.py --context default \
  --base-image fenced-amd64-agent:validation \
  --gateway-image fenced-amd64-client:validation \
  --base-receipt "$HOME/fenced-amd64-build-evidence/receipt.json" \
  --gateway-receipt "$HOME/fenced-amd64-gateway-evidence/receipt.json" \
  --terraform-tag fenced-amd64-terraform:validation \
  --all-tag fenced-amd64-all:validation \
  --output "$HOME/fenced-amd64-all-evidence"
```

Use unused output tags and a new output directory. The checked-in image-inputs.json
records registry digests for Java, Redpanda and OpenBao, plus the FoundationDB
release and package SHA-256. It contains native AMD64 and ARM64 inputs; missing
architectures fail explicitly. The FoundationDB checksum was recorded from the
versioned upstream HTTPS release, not independently signature-verified.

Terraform uses its existing per-architecture checksum and the base's frozen Debian
sources. Builds use no layer cache. The helper verifies matching native base/gateway
receipts and checks that local input tags did not change during assembly. Avoid
concurrent tag writers. Context contains only the two extra-owned Dockerfiles.

The receipt, build log, installed package inventory and offline tool checks are
retained. Failed builds keep partial evidence and any completed images; retry with
new output names. No services, credentials, registry publication, volume cleanup
or live gateway changes are performed. Use the resulting image explicitly in a
new host profile; changing an initialized profile requires a separate migration.

The combined image supplies client tools only. Successful offline checks do not
establish database connectivity, provider authentication or service availability.
Native validation evidence is recorded separately from these build instructions.
