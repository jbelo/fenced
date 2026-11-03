# OpenBao 2.7.1 extra

An optional, disposable OpenBao service for local integration tests, and an agent
image containing the matching `bao` CLI. Uses the official
`quay.io/openbao/openbao:2.7.1` image. The `go-agent-all` image also includes the `bao` CLI.

## Host lifecycle

```sh
make networks
make -f extras/openbao/Makefile openbao-up
make -f extras/openbao/Makefile openbao-ready
```

The service is `go-agent-openbao:8200` on `go-agent-internal-net`, without host
port publishing or upstream network access. It uses plain HTTP and dev mode:
initialized, unsealed, in-memory, with a fixed **local test-only** root token
`local-openbao-dev-only`. Use no real secrets. All internal-network peers can
reach it; the token is not a security boundary. Dev startup logs also expose test
credentials. The container runs as the image's `openbao` user, with a read-only
root filesystem and writable temporary home. No persistent data volume is used.

`openbao-up` refuses an existing container name instead of replacing its state.
Readiness may take a few seconds; retry `openbao-ready` during startup. Dev mode
creates the default `secret/` KV v2 mount; it does not configure application
policies, AppRole, transit, or application secrets. Provision those separately
only when explicitly authorized. No manual init or unseal is needed in this mode.

```sh
make -f extras/openbao/Makefile openbao-logs
make -f extras/openbao/Makefile openbao-down
```

Stopping or restarting the process loses all in-memory secrets and configuration.
`openbao-down` removes the container and its image-created anonymous volumes.
It does not touch agent-home or other service volumes. For persistent storage,
add a separately designed configuration with initialization/unseal key handling;
do not attach a volume and assume dev mode becomes persistent.

Override `OPENBAO_CONTAINER`, `OPENBAO_IMAGE`, `OPENBAO_VERSION`, or
`AGENT_INTERNAL_NETWORK` on Make invocations as needed. Pass the same overrides
to readiness and shutdown commands. The listener remains port 8200.

## Optional agent CLI

```sh
make -f extras/openbao/Makefile agent-openbao-build
story-shell --image go-agent-openbao
```

`AGENT_IMAGE` selects the base (default `go-agent`); `AGENT_OPENBAO_IMAGE` selects
the output tag. For all common tools including OpenBao CLI, use `go-agent-all`.
The CLI image does not start a server. HTTP clients can use the service without it.

## Agent connection

```sh
export BAO_ADDR=http://go-agent-openbao:8200
export BAO_TOKEN=local-openbao-dev-only
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}go-agent-openbao"
export no_proxy="$NO_PROXY"
bao status
bao token lookup -field=policies
```

Vault-based application clients may use `VAULT_ADDR`/`VAULT_TOKEN` instead;
confirm their configuration. Do not route the local endpoint through Squid.
The installed `openbao-connect` skill documents connection and read-only
diagnostics. `make install-agent-context` installs it with the agent overview.

Upstream references: [server/dev mode](https://openbao.org/docs/commands/server/),
[2.7.1 release](https://github.com/openbao/openbao/releases/tag/v2.7.1).

## Verified HTTPS test instance

The separate **disposable** service `go-agent-openbao-tls` exposes
`https://go-agent-openbao-tls:8443` on the same internal network. It has independent
in-memory data: it is not an HTTPS alias for the existing HTTP instance. Existing
`http://go-agent-openbao:8200` consumers are unchanged. Neither endpoint publishes
host ports. Only local synthetic secrets and test identities belong here.

Host/operator lifecycle:

```sh
make -f extras/openbao/Makefile openbao-tls-up
make -f extras/openbao/Makefile openbao-tls-ready
make -f extras/openbao/Makefile openbao-tls-install
```

Startup creates a dedicated `go-agent-openbao-tls-private` Docker volume containing
a test CA, a 30-day server certificate with DNS SAN `go-agent-openbao-tls`, private
keys, and a random dev root token. The service uses OpenBao 2.7.1 in-memory dev mode
with a configured native TLS listener on 8443. Private material is mounted only in
the server and short-lived operator setup/install containers. No system trust store
is modified. Startup output (which can contain the dev token) stays in the server's
private `/tmp/server.log`, not Docker logs. Do not print or collect that file.

The install target selectively delivers just the CA and test token to the configured
`AGENTHOME` volume (default `agenthome`), owned by the invoking host UID/GID:

- `$HOME/.openbao-test/ca.crt`: public trust anchor, mode 0644.
- `$HOME/.openbao-test/token`: random disposable root credential, mode 0600.
- Parent directory: mode 0700. No CA/server private keys enter agent home.

The token is available to that agent-home user, not scoped to a single agent sharing
the home. Use a separate `AGENTHOME` and TLS instance for separately trusted tests.
Do not put token values in arguments, Docker environment configuration, source, chat,
or logs. Read the file inside the test process; do not enable shell tracing.

```sh
export BAO_ADDR=https://go-agent-openbao-tls:8443
export BAO_CACERT="$HOME/.openbao-test/ca.crt"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}go-agent-openbao-tls"
export no_proxy="$NO_PROXY"
export BAO_TOKEN="$(cat "$HOME/.openbao-test/token")"
bao status
bao token lookup -field=policies
```

For Vault clients use the corresponding `VAULT_ADDR`, `VAULT_CACERT`, `VAULT_TOKEN`
settings, or configure their TLS root pool explicitly. Never use skip-verify or
`curl -k`. `curl --cacert "$BAO_CACERT"` verifies both chain and hostname. For Go
clients that use the public CA pool rather than a client-specific CA option,
explicitly load this CA; merely setting `BAO_CACERT` does not configure arbitrary SDKs.

`OPENBAO_TLS_CONTAINER` overrides the container name **and** certificate DNS SAN;
use that name in the endpoint. All commands must use the same override. `AGENT_IMAGE`
is the setup helper image (must contain OpenSSL); `OPENBAO_IMAGE` is the server image.
A duplicate container name fails instead of replacing active state. Certificates and
root token survive container recreation while this dedicated private volume exists;
OpenBao secrets, auth configuration, and issued tokens do not. Reused material is
checked for chain, expiry, and hostname before startup.

To stop the TLS instance and optionally remove its dedicated key material:

```sh
make -f extras/openbao/Makefile openbao-tls-down
make -f extras/openbao/Makefile openbao-tls-clean
```

The operator owns certificate generation, credential delivery, service lifecycle,
renewal, and cleanup. After removing private material, explicitly remove the stale
`.openbao-test/ca.crt` and `.openbao-test/token` from the selected agent home, or run
up/ready/install to replace them with fresh material. Never remove the entire agent
home. For expired certificates, stop/clean/up/ready/install renews the disposable
instance; coordinate this because its in-memory data and trust anchor change.

## OpenBao callbacks to an agent-hosted TokenReview helper

The test owner reserves a **unique per-test** network alias and a helper port. For
example, launch the agent from its story directory on the normal internal network:

```sh
story-shell --image go-agent-all \
  --docker-arg --network-alias --docker-arg bao-tokenreview-mytest
```

Run the authorized test helper inside that agent, binding `0.0.0.0:18443` (or its
container interface), not `127.0.0.1`. OpenBao's Kubernetes-auth `kubernetes_host`
then uses `http://bao-tokenreview-mytest:18443` or, for verified helper TLS,
`https://bao-tokenreview-mytest:18443`. It posts TokenReview requests to
`/apis/authentication.k8s.io/v1/tokenreviews`. Both containers must join the same
`go-agent-internal-net`. No `-p`/host port, host forwarding, or shared-proxy change
is needed. The hostname is the agent's Docker network alias, not OpenBao's hostname.
Neither container's localhost reaches the other.

For HTTPS helpers, their server certificate SAN must include that **helper alias**,
and the test must supply the helper CA as Kubernetes-auth `kubernetes_ca_cert`.
The OpenBao server CA is not automatically the helper's CA. With
`disable_local_ca_jwt=true`, OpenBao 2.7.1 requires a nonempty valid
`kubernetes_ca_cert` even for an HTTP fixture; supply a test CA explicitly.
Synthetic login JWTs must carry valid `nbf`, `iat`, and `exp` claims. Keep helper private
keys/reviewer credentials in protected ignored test files, and have the fixture
validate its expected reviewer credential. Use synthetic review tokens; never point
this contract at a real cluster. HTTP helper mode is only for this explicitly
isolated, disposable fixture on the shared test network.

The shared bridge is not per-agent isolation: other members can reach the helper.
Aliases must not collide across active tests. If an existing agent lacks an alias,
its Docker container name can be used if known; otherwise the host owner relaunches
it with the alias. Agents do not change Docker membership. Add the helper alias to
proxy bypass for test clients; the OpenBao TLS service starts without proxy variables.

The agent/test owns helper process startup/shutdown, its synthetic fixtures, and
cleanup of its own OpenBao auth mounts/roles when authorized. The host owns container
membership/aliases and OpenBao lifecycle. Stop the helper after the test and remove
its local credentials; do not stop other agents or reset shared services. Agent
container removal releases its network alias. Missing routes, trust files, or service
instances are reported to the host owner instead of weakening TLS verification.

## Verified on 2026-11-03

On an isolated TLS instance and separate temporary agent home: trusted health and
authenticated token lookup passed; missing CA and wrong hostname were rejected.
Agent token mode was 0600 and no private keys were delivered. A TokenReview POST
from the OpenBao network namespace reached the agent alias, and an actual
OpenBao Kubernetes-auth login succeeded using a synthetic signed JWT and the
agent-hosted HTTP TokenReview fixture. Temporary containers/volumes were removed.
HTTPS helper routing/trust is documented but that separate helper-TLS mode was not
exercised by this test. The named TLS service and its installed CA/token were then
provisioned separately; existing HTTP consumers were not restarted or modified.
