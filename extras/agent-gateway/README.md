# Agent gateway integration

Installs the gateway-delivered `agentctl` CLI and endpoint configuration into agent
images. The already deployed gateway is managed by its operator, not this extra.
The ARM64 deployment uses **live GitHub and Shortcut providers** as of 2026-11-04.
No provider credentials are installed or agent egress rules changed.

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
workspace alias `exoscale` (verified story 184613). Follow the skill for the six read commands, pagination,
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

## Provenance

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
