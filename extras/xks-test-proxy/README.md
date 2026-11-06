# XKS test proxy over TLS

Agent-side usage: [`xks-test-proxy-use` skill](skills/xks-test-proxy-use/SKILL.md), installed by
`make install-agent-context` at `$HOME/.agents/skills/xks-test-proxy-use/SKILL.md`.

Runs the pinned KMS test proxy image with SoftHSM, HTTPS on port `19443`,
SigV4 authentication enabled, and mutual TLS disabled. This matches the TLS
mode in `setup-kms-env.sh`, not the HTTP-only Testcontainers fixture.
It is a development fixture, not a production HSM or key service.

## Host setup

Prerequisites: Docker, the harness network and agent image/home, `mkcert` on
the host, and access to the private registry (or the pinned image already local).
Run from the fenced checkout:

```sh
make networks
make -f extras/xks-test-proxy/Makefile xks-test-proxy-build
make -f extras/xks-test-proxy/Makefile xks-test-proxy-ssh-setup
make -f extras/xks-test-proxy/Makefile xks-test-proxy-install-ssh
make -f extras/xks-test-proxy/Makefile xks-test-proxy-tls
make -f extras/xks-test-proxy/Makefile xks-test-proxy-up
make -f extras/xks-test-proxy/Makefile xks-test-proxy-install-ca
make install-agent-context
```

The TLS target creates a dedicated CA under `.local/tls/ca/` and a certificate
for `xks-proxy.test`. It does not install a CA into the host's system trust store.
Existing certificate material is reused, never silently rotated; incomplete
material fails. Keep this ignored directory safe, especially the CA private key.
Certificate expiry or hostname changes require deliberate replacement and
redistribution of the public CA when it changes.

Alternatively, point `XKS_PROXY_TLS_DIR` at an absolute directory containing
`server.pem`, `server-key.pem`, and its issuing `ca.pem`. Use a certificate with
the configured DNS name as a SAN. Do not run the generation target to replace
existing certificates. Only these three individual files are mounted; the CA
private key is never mounted. `xks-test-proxy-install-ca` copies only `ca.pem`
into `$HOME/.config/xks-test-proxy/ca.pem` in the agent home. It does not change
global trust or install credentials. Repeat it after replacing the agent home.

Defaults and overrides:

| Variable | Default |
| --- | --- |
| `XKS_PROXY_IMAGE` | `go-agent-xks-test-proxy` (local SSH-enabled image) |
| `XKS_PROXY_RUNTIME_IMAGE` | `go-agent-xks-test-proxy-runtime` (upstream image with proxy-specific preparation) |
| `XKS_PROXY_BASE_IMAGE` | `registry.internal.exoscale.ch/exoscale/kms-xks-proxy:015d4d11ba534da18cbc5e24cef2727e2209d0c1` |
| `XKS_PROXY_SSH_DIR` | This extra's `.local/ssh` (persistent client key and connection config) |
| `XKS_PROXY_CONTAINER` | `go-agent-xks-test-proxy` |
| `XKS_PROXY_HOSTNAME` | `xks-proxy.test` (Docker network alias and certificate SAN) |
| `XKS_PROXY_DATA_VOLUME` | `go-agent-xks-test-proxy-data` |
| `XKS_PROXY_TLS_DIR` | This extra's `.local/tls` directory |
| `XKS_PROXY_SETTINGS` | This extra's `settings.toml` |
| `AGENT_INTERNAL_NETWORK` | `go-agent-internal-net` |
| `AGENT_IMAGE`, `AGENTHOME`, `AGENT_HOME` | `go-agent`, `agenthome`, `/home/agent` |
| `AGENT_UID`, `AGENT_GID` | Host user's UID/GID (public CA ownership) |
| `XKS_PROXY_DOCKER_RUN_EXTRA` | Empty; optional extra Docker run arguments |

Use absolute paths for bind-mount overrides. Settings overrides must retain the
certificate paths and TLS port used by these targets. To run multiple independent
proxies, use distinct container names, DNS aliases, TLS directories and data volumes.
Do not assign the same alias to another proxy on the same network.

No host ports are published and no host `/etc/hosts` entry is required. Existing
containers such as `kms-xks-proxy` are not adopted or modified. `up` starts an
existing extra container without replacing it, then verifies HTTPS `/ping` with
the CA and hostname. Changes to mounts, image, alias, or settings require an
explicit `down` followed by `up`. Readiness failure leaves the container for
inspection; `/ping` does not prove authenticated crypto operations succeed.

## Client and KMS configuration

On the container network, use `https://xks-proxy.test:19443`. The URI path prefix
is `/example/uri/path/prefix`; the full XKS API prefix used by KMS is
`/example/uri/path/prefix/kms/xks/v1`. Key ID is `foo`. The supplied fixture signs for
region `ch-gva-2`, service `kms-xks-proxy`. Fixture access key and secret are in
`settings.toml`, intentionally matching the KMS test defaults. They and the
image's baked-in SoftHSM keys are public test data, never production credentials.
Provide any required credentials to the agent separately from its reference docs.

For a Go client using system roots (including the current external-proxy test
configuration), set `SSL_CERT_FILE` to the public CA path before starting the
process. For curl use `--cacert`. Append `xks-proxy.test` to both `NO_PROXY` and
`no_proxy` where appropriate: internal TLS traffic must not use the HTTP egress
proxy. Do not use `-k` or disable certificate verification.

For separately running KMS service containers, their trust must be configured
too; installing the CA in the agent home does not affect them. In a private copy
of each intended KMS zone configuration, add:

```yaml
xksproxytlscafile: /etc/kms/xks-ca.pem
createkeystoreenabled: true
```

Mount this extra's public `ca.pem` read-only at `/etc/kms/xks-ca.pem`, using
`KMS_GVA_DOCKER_RUN_EXTRA` / `KMS_FRA_DOCKER_RUN_EXTRA` and `KMS_CONFIG_DIR` from
the KMS extra. Preserve any existing extra arguments, and include proxy bypass
environment variables if that service uses an HTTP proxy. Leave client TLS
certificate/key unset because mTLS is disabled. Configure the external keystore
through the project's API with the endpoint, prefix, credentials and matching
signing region. Starting this proxy does not create an external keystore in KMS
or configure either zone automatically. KMS signs with its own configured zone:
for FRA, use a separate proxy with `region = "de-fra-1"` in its settings and a
distinct hostname, TLS directory, container and volume.

The external-proxy test knobs are `XKS_PROXY_USE_EXTERNAL=true`,
`XKS_PROXY_ENDPOINT=https://xks-proxy.test:19443`, `XKS_PROXY_ACCESS_KEY`, and
`XKS_PROXY_SECRET`. These only select the XKS dependency; other test dependencies
must be configured independently.

## Lifecycle and persistence

### Agent SSH access

The local image runs the proxy and `sshd` together. Port 22 is available only
on the container network by default. SSH grants a full root shell with key-only
authentication, including access to SoftHSM data and TLS keys. The agent has
authority to modify this local test proxy; its persistent data is not protected
from an agent using that access. The egress proxy remains unchanged.

The build target first prepares the upstream image using this extra's Dockerfile
(Perl repair and log directory), then applies the shared [SSH layer](../ssh/README.md).
The run target explicitly supplies `/usr/sbin/xks-proxy` as the application command.
SSH configuration, startup, and key preparation live under `extras/ssh`; the
Makefile generates the agent launcher and installs the key. Existing agent commands and keys
are unchanged. Recreate an existing container to apply the new authorized-key mount.

`xks-test-proxy-ssh-setup` creates and preserves the client key under `.local/ssh`.
Only its public authorized key is mounted into the proxy, read-only. SSH uses
`StrictModes no` because that file belongs to the host user, not container root.
Host keys are generated inside the container and replaced on recreation;
old host keys under `.local/ssh/server` are no longer used.
The entrypoint starts SSH in the background and executes the proxy as the main
process, without a supervisor. If SSH later exits, the proxy keeps running.
`xks-test-proxy-install-ssh` installs the client key,
SSH config, and `xks-test-proxy-ssh` helper into agent home. Numeric-UID support
belongs to the base agent's SSH client; use a current agent image. After upgrading
the base, rebuild derived agent images and recreate agent shells before refreshing
the helper. The installer removes the obsolete home-installed compatibility library.
Installation replaces these generated files only, leaving the general SSH config
alone. Key material is excluded from Git and Docker build context. The local
SSH client skips host-key verification, so recreating the proxy does not require
updating trust. HTTPS certificate verification remains enabled. Implementation
scripts live under this extra's and the shared SSH extra's `scripts/` directories.

From the agent:

```sh
xks-test-proxy-ssh
xks-test-proxy-ssh 'ls -lt /var/log/xks-proxy'
xks-test-proxy-ssh 'tail -n 200 /var/log/xks-proxy/xks-proxy.log.*'
```

File logs rotate hourly and remain in the container writable layer; removal of
the container discards them. Rotation does not delete old files: monitor their
size and remove/archive old logs deliberately for long-running sessions. Docker
stdout logs are additionally capped at three 10 MB files. Both SSH and proxy
output remain accessible with the host log target below.

For an existing container, build/setup/install first, then run `xks-test-proxy-down`
and `xks-test-proxy-up` to apply SSH and log settings. SoftHSM data remains in its
volume. The client key is reused from `.local/ssh` across recreation.

```sh
make -f extras/xks-test-proxy/Makefile xks-test-proxy-ready
make -f extras/xks-test-proxy/Makefile xks-test-proxy-status
make -f extras/xks-test-proxy/Makefile xks-test-proxy-logs
make -f extras/xks-test-proxy/Makefile xks-test-proxy-down
```

The named SoftHSM volume is populated from the image's fixture tokens on first
creation and persists across `down`/`up`; image upgrades do not replace existing
tokens. TLS files remain on the host. Neither is tied to the agent home. `down`
removes only the container. There is deliberately no automatic data cleanup or
key rotation target. Never remove the token volume while relying on its keys.

Only the agent-facing connection guide is installed by the harness. This host
README, settings, private material and runtime state stay out of that bundle.
