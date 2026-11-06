# KMS addon

Agent-side usage: [`kms-connect` skill](skills/kms-connect/SKILL.md), installed by
`make install-agent-context` at `$HOME/.agents/skills/kms-connect/SKILL.md`.
For requested native process startup inside the agent container, the installed
[`kms-run` skill](skills/kms-run/SKILL.md) covers a supplied binary, root keys,
recovery compatibility, explicit FoundationDB namespace, and optional dependencies.
This uses an existing FoundationDB service; it does not provision containers.

Run one or two local KMS zones beside the agent on `go-agent-internal-net`. Both
zones use the same KMS image and FoundationDB cluster, with separate FoundationDB
root paths. The default configuration follows the two zones in
`setup-kms-env.sh`: `ch-gva-2` and `de-fra-1`.

The services are reachable from an agent shell at:

- `http://go-agent-kms-gva2:8080`
- `http://go-agent-kms-fra1:8080`

They are not published on the host by default. The two services use port 8080
inside their own containers, and their `zoneresolutionoverride` values point to
each other's Docker DNS names. Unlike the host-oriented setup script, the zone
configs do not use `localhost` for cross-zone calls.

## Prerequisites

- A KMS source checkout (default: `branch-kms/` beside `extras/`).
- The `earthly` CLI, or an already built local KMS image.
- FoundationDB running on the agent network and initialized. See
  [the FoundationDB addon](../foundationdb/README.md).
- Redpanda running on the agent network, since the included zone configs enable
  billing. See [the Redpanda addon](../redpanda/README.md).
- A local secrets directory containing the root key material file named
  `5383347d-35c9-4e56-86a2-d504e540c2f1`. By default this is
  `branch-kms/secrets/`, as produced by the developer's `setup-kms-env.sh` when
  run from the KMS checkout. The addon never writes or commits key material.

Do not copy the host-oriented `config.yaml` and `config-b.yaml` into these
containers unchanged: their `localhost` endpoints and paths are not valid for
container-to-container traffic. The templates in `config/` already use the
container paths and names. If you use a different root key ID, update both
config files and set `KMS_ROOT_KEY_ID` when running Make.

## Start both zones

From the harness root:

```sh
make networks
make -f extras/foundationdb/Makefile fdb-up
make -f extras/foundationdb/Makefile fdb-init  # first use only
make -f extras/redpanda/Makefile redpanda-up

make -f extras/kms/Makefile kms-image-build
make -f extras/kms/Makefile kms-cluster-sync
make -f extras/kms/Makefile kms-up
make -f extras/kms/Makefile kms-status
```

`kms-cluster-sync` copies the FoundationDB cluster file from
`go-agent-fdb:/var/fdb/fdb.cluster` to the ignored
`extras/kms/.local/fdb.cluster`. Both KMS containers bind-mount that file and
the secrets directory read-only. If the database container changes its
coordinator address, sync again and recreate the KMS containers. A cluster
file pointing to `localhost` is rejected because it would refer to the KMS
container itself.

`kms-image-build` uses the KMS checkout's `+kms-image-build-local` Earthly
target, which saves an image named `kms`. On an amd64 Docker host, pass
`KMS_FDB_ARCH=amd64`; the default is `aarch64` for an arm64 Docker host.
Alternatively, pass `KMS_IMAGE=your-local-image` to the other targets.

To use a different KMS checkout or secrets directory, pass absolute paths:

```sh
make -f extras/kms/Makefile kms-up \
  KMS_SOURCE=/path/to/kms \
  KMS_SECRETS_DIR=/path/to/kms/secrets
```

## One zone and lifecycle

Start just one zone with `kms-gva-up` or `kms-fra-up`. Both config files still
advertise both supported zones; cross-zone operations need the other zone to be
running. `kms-up` recreates both KMS containers. KMS data resides in
FoundationDB, so `kms-down` removes only the KMS containers.

```sh
make -f extras/kms/Makefile kms-gva-up
make -f extras/kms/Makefile kms-gva-logs
make -f extras/kms/Makefile kms-fra-logs
make -f extras/kms/Makefile kms-down
```

For host access, publish distinct host ports explicitly. Both containers still
listen on port 8080 internally:

```sh
make -f extras/kms/Makefile kms-up \
  KMS_GVA_DOCKER_RUN_EXTRA='-p 8080:8080' \
  KMS_FRA_DOCKER_RUN_EXTRA='-p 9090:8080'
```

The setup script also configures tracing, recovery, XKS, and root key rewrap.
Those are optional additions to the zone configs here; provide their runtime
services, certificates, and mounted files before enabling them. Avoid putting
private keys or root key material into the tracked `config/` directory.
