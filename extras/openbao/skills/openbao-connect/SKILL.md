---
name: openbao-connect
description: Connect to the local harness OpenBao service and diagnose health, authentication, or missing secret mounts.
---

# Local OpenBao

The default service is OpenBao 2.7.1 at `http://go-agent-openbao:8200` on the
harness internal network. This is local test infrastructure. Use the developer's
supplied endpoint and credentials when they differ; do not assume it is running.

```sh
export BAO_ADDR=http://go-agent-openbao:8200
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}go-agent-openbao"
export no_proxy="$NO_PROXY"
curl --noproxy go-agent-openbao -sS -o /tmp/openbao-health.json \
  -w '%{http_code}\n' "$BAO_ADDR/v1/sys/health"
```

Health HTTP 200 indicates an initialized, unsealed active server; 501 means
uninitialized, 503 sealed, and 429 standby. Connection failures and proxy errors
are not initialization failures. Report the status and relevant health fields.
Health alone does not verify credentials or access to a particular secret engine.

For the harness's default disposable dev instance only, the fixed test root token
is `local-openbao-dev-only`. It is intentionally public local-test configuration,
not a production credential. When working with that instance, set:

```sh
export BAO_TOKEN=local-openbao-dev-only
```

The launcher does not export it automatically. Preserve any credentials supplied
for the task; do not send this default token to other endpoints. Root access does
not authorize unrelated mutations. If it is rejected, report the mismatch instead
of resetting the service or changing authentication.

Both `go-agent-openbao` and `go-agent-all` supply `bao` 2.7.1; older running
containers and other agent images may not.
When available, `bao status` is read-only (exit 0 unsealed, 2 sealed, 1 error).
Use `BAO_TOKEN` supplied for the task; never print it or persist it with `bao login`
unless explicitly requested. For an authorized authentication check, use
`bao token lookup -field=policies` so the token itself is not displayed.
Applications using Vault client libraries may instead require `VAULT_ADDR` and
`VAULT_TOKEN`; inspect their actual configuration before setting them.

Keep TLS verification enabled for HTTPS overrides. The default local endpoint
uses plain HTTP, so no TLS certificates are needed for it.

## Verified HTTPS and test callbacks

A separately provisioned disposable instance is available at
`https://go-agent-openbao-tls:8443`. It has independent in-memory state from the
legacy HTTP instance. The operator supplies `$HOME/.openbao-test/ca.crt` and a
mode-0600 `$HOME/.openbao-test/token` in a mode-0700 directory. Only public CA and
test token are delivered, never server/CA private keys. Do not assume files exist.

```sh
export BAO_ADDR=https://go-agent-openbao-tls:8443
export BAO_CACERT="$HOME/.openbao-test/ca.crt"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}go-agent-openbao-tls"
export no_proxy="$NO_PROXY"
export BAO_TOKEN="$(cat "$HOME/.openbao-test/token")"
bao status
bao token lookup -field=policies
```

Read the token without shell tracing; do not print it or pass it as a CLI argument.
It is a disposable root credential shared by the agent-home user. The fixed HTTP
token does not authenticate to this TLS instance. SAN matches `go-agent-openbao-tls`;
use that hostname and the supplied CA. Never disable verification. Vault clients
may require `VAULT_CACERT` or an explicitly configured TLS root pool instead.
The operator owns certificate renewal, credential delivery, and server lifecycle.
Report expired/untrusted certificates or missing files; do not regenerate them.

For an authorized TokenReview integration fixture inside the agent, ask the host
owner for a unique network alias (example `bao-tokenreview-mytest`) on the shared
internal network. Bind the helper to `0.0.0.0:18443`, not loopback. OpenBao-visible
base URL: `http://bao-tokenreview-mytest:18443`, or HTTPS with a certificate SAN
matching that alias and its CA supplied as Kubernetes-auth `kubernetes_ca_cert`.
The helper receives POST `/apis/authentication.k8s.io/v1/tokenreviews`; use synthetic
reviewer credentials, validating them in the fixture. The OpenBao CA does not
implicitly trust the helper certificate. No host port publishing is required.
Other shared-network members can reach the helper; aliases must be unique.
`localhost` never denotes the other container. Test clients should bypass proxies
for the helper alias. Agents do not alter Docker membership or host routing.

The test owns its helper process, synthetic credentials, and authorized test auth
mounts/roles; clean up only those resources after testing. The host owns containers,
aliases and the disposable OpenBao service. No production clusters or credentials
are in scope. Report missing routing rather than exposing the helper on a host port.

Report missing service, credentials, initialization, unsealing, secret mounts,
policies, or data to the developer. Do not provision or reset them to make a
readiness check pass. Secret writes, authentication configuration, and policy
changes need task authorization. Never assume dev-mode data persists.
