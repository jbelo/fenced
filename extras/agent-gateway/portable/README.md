# Portable feedback delivery

Copy this entire directory to the fresh Ubuntu 26.04 ARM64 or AMD64 host. It
contains the immutable source archive itself; no Mac Docker cache, registry
publication, Git checkout, provider credential or runtime state is required.

The archive SHA-256 is
`0511e56f774d806a2db21a27cd3e9c77741b1e28ed98b7599bbb36867f4f1268`.
The manifest SHA-256 is
`1124ede0ed55b639730d57e69c19b4e1d5d357e06a3db08e0a50cf512409a9b6`.
This is the exact 2026-11-09 feedback snapshot based on
`ebff15fdca815a46c43e566c61a3c7db889bb0cf` plus recorded changes, NOT that
commit alone. Historical contract baseline:
`8d745c5a1d8bbc228ca86ffc3a14dcaf8ebd947d`.

## Build

Install Python 3.12+ and the official **Go 1.27.3** distribution for the host
architecture, verifying its published checksum before installation. Put its `bin`
directory first in PATH. No third-party Go modules are needed. Run:

```sh
python3 build.py
```

The script verifies the archive and complete source manifest, extracts into a
fresh temporary directory, disables module downloads and automatic toolchain
selection, then builds static Linux binaries for both architectures. It verifies
all six results against `SHA256SUMS`; any difference fails the build. Outputs are
in `out/`. Transfer those outputs with the checksum file if building elsewhere.
Use `agentctl-linux-arm64` on ARM64 and `agentctl-linux-amd64` on AMD64, installed
as executable `/usr/local/bin/agentctl` in the agent image. The matching gateway
and healthcheck binaries belong in the gateway image. Do not mix revisions.

For gateway image assembly, extract the archive (`tar -xzf source-snapshot.tar.gz`)
and use its Dockerfile with a publicly obtainable, verified digest-pinned Go
1.27.3 image matching the host architecture:

```sh
docker build --pull --no-cache --build-arg GO_IMAGE="$GO_IMAGE" \
  --build-arg TARGETARCH=arm64 -t agent-gateway:portable ./agent-gateway
# Use TARGETARCH=amd64 on AMD64.
```

GO_IMAGE must be supplied by the operator; no local image ID is a delivery input.
The image includes its builder's CA bundle; its image digest is therefore not
claimed reproducible by the binary checksum manifest. Extract and checksum the
three binaries from the resulting image before integration. The direct source
build above is the fully pinned binary delivery path.

## Compatibility and validation limits

This preserves the delivered `github pr feedback` API, pagination/completeness
semantics and client configuration (`deploy/agentctl.json`), including the
`http://agent-gateway:8080` endpoint. Templates/examples are source examples,
not an operator's runtime policy. No live configuration or secrets are bundled.

Local Go 1.27.3 cross-build validation is recorded in the shared exchange.
Fresh Ubuntu ARM64 and AMD64 native startup, executable feedback traversal,
image isolation and provider checks remain Fenced's next step. Existing ARM64
live evidence applies to the original delivery only. No new live verification,
image publication or deployment is implied. The separate PR 566 diff failure
and previously recorded lifecycle gaps are not fixed by this packaging.

## Fenced native image integration

From a complete Fenced checkout, first build the base agent using the recorded
host image inputs. Then run this extra-owned helper with an explicit local Docker
context, a digest-pinned native Go 1.27.3 image, unused output tags and a new output
directory:

```sh
python3 extras/agent-gateway/portable/build-images.py \
  --context default --go-image "$GO_IMAGE" \
  --base-image fenced-locked-agent:arm64-test \
  --gateway-tag fenced-portable-gateway:local \
  --agent-tag fenced-portable-client:local \
  --output "$HOME/fenced-gateway-build"
```

Use the appropriate native Go digest from verified host inputs. The helper verifies
archive identity and every manifest-listed source file, builds with no cache, runs
native source tests, and checks the service/client/healthcheck binary checksums.
It builds the consumer image with the existing public agentctl configuration.
Build contexts contain only explicitly selected delivery files/configuration.
The receipt records actual base, service and consumer image IDs; existing tags are
refused. No service is started, no image is published and no credentials are read.

BuildKit uses local tags to assemble the consumer image; the helper verifies their
identities remain unchanged across assembly. Keep builds isolated from concurrent
tag writers. A failed build retains its receipt/log and any completed image; use
new tags/output paths for another attempt. No automatic cleanup is performed.

The legacy extra Dockerfile/Make target remains unchanged. To compose an all image,
pass the newly verified consumer tag as AGENT_GATEWAY_IMAGE to its existing build
interface; the other all-image dependencies require their own portable validation.
Selecting the gateway service in a host profile remains unsupported until a safe
service lifecycle adapter and operator credential enrollment are implemented.

Native consumer verification now covers Ubuntu 24.04 ARM64 and Ubuntu 26.04
AMD64: source tests, binary checksums, image assembly and executable mock feedback
pagination/replies/isolation. The primary Linux target moved to 26.04; local ARM64
rechecks are deferred. This is not authenticated live-provider evidence.
