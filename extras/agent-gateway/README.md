# Agent gateway integration

Installs the gateway-delivered `agentctl` CLI and endpoint configuration into agent
images. The already deployed gateway is managed by its operator, not this extra.
The ARM64 deployment uses **live GitHub and Shortcut providers** as of 2026-11-04.
No provider credentials are installed or agent egress rules changed.

For fresh hosts, use the [portable source and image build](portable/README.md).
It avoids the legacy Mac-cache dependency and preserves the delivered API.

## Build and use

The local ARM64 gateway image below must already exist in Docker. This is not a
published/multi-architecture release; AMD64 builds deliberately fail. Obtain a
verified matching handoff before changing the source image or CLI checksum.

```sh
make -f extras/agent-gateway/Makefile agent-gateway-build
make -f extras/all/Makefile agent-all-build
story-shell --image go-agent-all
```

The standalone image is `go-agent-gateway`. Both it and `go-agent-all` contain
`/usr/local/bin/agentctl`, root-owned `/etc/agentctl/config.json`, and
`AGENTCTL_CONFIG=/etc/agentctl/config.json`. Normal harness containers have a
read-only root filesystem. The endpoint is `http://agent-gateway:8080`, currently
at `172.22.255.10` on `go-agent-internal-net`. The CLI bypasses ambient HTTP proxy
variables itself. No launcher wrapper or writable home binary is needed.

`make install-agent-context` installs the supplied `agent-gateway` skill. In this
live deployment the allowed targets are `exoscale/kms` (verified PR 539) and
workspace alias `exoscale` (verified story 184613). Follow the skill for the read commands, including PR feedback, pagination,
and error handling. Missing services/configuration are reported to the operator.
Endpoint configuration is public client configuration, not gateway policy or
credentials. The image must not receive gateway configuration, policy or secrets.

## Historical mock verification

The following verifier requires a separate mock deployment; do not run it against
the current live gateway.

```sh
make -f extras/agent-gateway/Makefile agent-gateway-check
```

The host-side verifier uses disposable instances of the actual agent image,
checks the running mock gateway, and cleans up its own containers and networks. It exercises
six operations, policy denial, invalid cursor, proxy bypass, protected client
files, absent server files/socket, direct-provider restrictions, and direct vs
delegated access removal. It does not stop or reconfigure the deployed gateway.
An isolated clone of the delivered image is also checked with two internal
network interfaces: the intended listener works, the other interface refuses
connections, and HTTPS CONNECT forwarding is rejected. This is not a test of a
live external-network attachment or packet-level routing attacks. Live-provider,
AMD64 and active-request shutdown verification remain gateway release follow-through;
mock checks do not certify live behavior.

The successful 2026-10-31 run and exact image IDs are recorded in
[verification.json](verification.json). All temporary test resources were removed.

## Historical delivery provenance

- Gateway worktree HEAD: `8d745c5a1d8bbc228ca86ffc3a14dcaf8ebd947d`.
  The delivery includes uncommitted implementation; HEAD alone is not its revision.
- Reviewed SPEC SHA-256: `658849fb9fc7108b4d4fb2223aad82fb201235da51dc8c97db3ad2c2a3eb4db6`.
- Local mock image ID: `sha256:0e986137eb422012efad5325c145360723bc54e371025711b69000a58ba9da50`.
- CLI SHA-256: `680c303326d8e9b35ae4ccb511b3b72e0d85955d3f061b5e4d0e1d481fecb0b6`.
- Supplied skill SHA-256: `dcb2b4afec7c5f196bb3ec303aea33c8f3732949bef1a2368277a0aa73cbd732`.
  The installed skill adds Fenced endpoint and live target guidance.

Delivery details and operator management commands remain in gateway's
`progress/MOCK-DEPLOYMENT.md`; integration results are recorded in its
`progress/EXCHANGE.md` Mock delivery topic. Live deployment now uses the updated `deploy/compose.live.yaml` and maintained
`runtime-stage`/`runtime-check` helpers. Host source credentials remain operator-owned
0400; `agent-gateway-live-credentials` stores Linux UID 10001 credentials at 0400
and is mounted read-only only in the gateway. Agents receive no credentials.
The live candidate image is
`sha256:329fc0d902d09c12f61535fd65d964ff47b6c2fa5ffc3f537e9dbc5055bd87c8`.
The installed CLI checksum is unchanged. See [live-verification.json](live-verification.json)
for sanitized live results and explicit remaining verification gaps.

## Existing containers without agentctl

For an already-running read-only-root container, the operator can install the
checksum-verified image CLI at `$HOME/.local/lib/agent-gateway/agentctl`, copy the
nonsecret agentctl.json to that directory as config.json, and install home-agentctl
as `$HOME/.local/bin/agentctl`. The launcher supplies the fallback configuration
when AGENTCTL_CONFIG is unset and uses /usr/local/bin/agentctl only when it matches the current delivered checksum.
Older image CLIs are bypassed by this home launcher.
No provider credentials or server configuration are installed. Shared agenthome
means the fallback is visible to other containers using that volume; it is writable
home state, not the image-protected installation. Existing processes without the
home bin directory on PATH must invoke the launcher by its absolute home path.

## PR feedback delivery (2026-11-09)

The current gateway/client build uses the supplied PR feedback source snapshot,
not the historical Git HEAD alone (source changes were uncommitted).

- Source base: `ebff15fdca815a46c43e566c61a3c7db889bb0cf`.
- Source manifest SHA-256: `1124ede0ed55b639730d57e69c19b4e1d5d357e06a3db08e0a50cf512409a9b6`.
- Snapshot SHA-256: `0511e56f774d806a2db21a27cd3e9c77741b1e28ed98b7599bbb36867f4f1268`.
- Gateway image: `sha256:421c381f611379447bfc0ecc77469ffa69a3234fa26c55cdb3c9c14ab8af9a3d`.
- ARM64 gateway SHA-256: `de40864cd513ceb13a134038da107f87a4e7523ec8aeaf9fb44ab06eaf0cdca3`.
- ARM64 CLI SHA-256: `b41301ae9176288f8d7ee3368de4e264e97a462b19c2f5a503dfb4adb14cdd2b`.
- Supplied skill SHA-256: `cf4112f95c6a6aff899b33e363078bc6a97cb8b80923180d576a24d7f97c296a`;
  installed skill adds Fenced endpoint/home fallback guidance.

The gateway image was built with the supplied snapshot Dockerfile and
`GO_IMAGE=golang@sha256:972b4110ba0f47539a975c31e52c64765e1ff19f2d74469ae4a595c6676e80a5`,
`TARGETARCH=arm64`. Every image binary matched the supplied artifact checksum.
Update service and CLI together; no new credentials or config keys are needed.
Rebuilding images does not replace a running container's image-installed binary.
The shared-home fallback is refreshed separately for older images. Existing agents
can invoke `$HOME/.local/bin/agentctl` explicitly to bypass a stale image CLI.

Host verification: `make -f extras/agent-gateway/Makefile agent-gateway-feedback-check`.
It performs read-only live collection of exoscale/kms PR 566, complete pagination,
refresh, smaller-page traversal and policy denial using a disposable agent client.
Bodies and cursors remain in process memory; only sanitized summaries are saved.
See feedback-verification.json for actual results and limits. Historical mock
verification is not the release check for this delivery.

Live verification completed on 2026-11-09: PR 566 returned 2 reviews, 1 discussion
comment and 14 inline comments in 14 threads. The full refresh matched; limit 4
completed in five pages. No live replies were present; an isolated executable
fixture verified cross-page root/reply merging. resolved/outdated remain unknown.
A separate compatibility issue is open: PR 566 diff returned upstream_unavailable
twice while PR 539 diff and other legacy operations passed. This does not prevent
feedback collection; no cause or feature regression is claimed.

## Fenced container name

The live container is `go-agent-gateway`; the client DNS alias remains
`agent-gateway`, so endpoint configuration does not change. Use the Fenced override
on every deployment/recreation, after the gateway-owned live Compose file:

```sh
docker-compose -p agent-gateway-live \
  -f /path/to/gateway/deploy/compose.live.yaml \
  -f /path/to/fenced/extras/agent-gateway/compose.fenced.yaml up -d
```

Supply the same GATEWAY_IMAGE, GATEWAY_RUNTIME_DIR, GATEWAY_SECRETS_VOLUME,
GATEWAY_AGENT_IP and AGENT_NETWORK settings as the existing deployment.
GATEWAY_CONTAINER_NAME overrides the name when explicitly needed; pass the same
name to verify-feedback.py --gateway. This is Fenced deployment configuration;
the upstream generic Compose artifact remains unchanged.
