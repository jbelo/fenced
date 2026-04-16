# FoundationDB addon

This folder contains optional tooling for running a FoundationDB container alongside the coding harness and, when needed, building an agent image with FoundationDB client libraries.

The main harness stays generic. FoundationDB support is kept here as an opt-in addon.

## What this addon provides

- instructions for building an arm64 FoundationDB server image from upstream source
- Make targets to run FoundationDB on the harness's internal Docker network
- a helper Dockerfile for building an optional `go-agent-fdb` image with FoundationDB client libraries

## Network model

The FoundationDB container is intended to join:

- `go-agent-internal-net`

This lets agent shells reach the database by container name while keeping the database off the host network by default.

Suggested hostname from the agent shell:

```text
go-agent-fdb:4500
```

## Prerequisite

Create the main harness networks first:

```sh
make networks
```

## 1. Build the FoundationDB server image on macOS ARM

The upstream FoundationDB project provides Docker packaging assets. Use an even release tag.

Example:

```sh
git clone https://github.com/apple/foundationdb.git
cd foundationdb
git checkout 7.3.68
cd packaging/docker
docker build \
  --platform linux/arm64 \
  --build-arg FDB_VERSION=7.3.68 \
  --target foundationdb \
  -t foundationdb/foundationdb:7.3.68 \
  .
```

You can also use the helper target in this folder if you already have a FoundationDB source checkout:

```sh
make -f extras/foundationdb/Makefile fdb-image-build-source \
  FDB_SOURCE=/path/to/foundationdb \
  FDB_VERSION=7.3.68
```

## 2. Start FoundationDB on the internal agent network

```sh
make -f extras/foundationdb/Makefile fdb-up FDB_VERSION=7.3.68
```

This starts a container named:

```text
go-agent-fdb
```

with a persistent Docker volume for data, attached to `go-agent-internal-net`.

By default the container is not exposed on the host.

If you want to publish the port for local debugging, pass extra Docker flags explicitly:

```sh
make -f extras/foundationdb/Makefile fdb-up \
  FDB_VERSION=7.3.68 \
  FDB_DOCKER_RUN_EXTRA='-p 4500:4500'
```

## 3. Initialize the database (first time only)

```sh
make -f extras/foundationdb/Makefile fdb-init
```

This runs:

```sh
fdbcli --exec "configure new single memory"
```

inside the running container.

## 4. Open `fdbcli`

```sh
make -f extras/foundationdb/Makefile fdb-cli
```

## 5. Tail database logs

```sh
make -f extras/foundationdb/Makefile fdb-logs
```

## 6. Build an agent image with FoundationDB client libraries

If your tests require FoundationDB client libraries inside the agent container, build the derived image with the desired FoundationDB version:

```sh
make -f extras/foundationdb/Makefile agent-fdb-build FDB_VERSION=7.3.68
```

The derived Dockerfile downloads the matching FoundationDB client package directly from the upstream GitHub release for that version.

This creates:

```text
go-agent-fdb
```

which extends the main `go-agent` image.

Run a shell with it:

```sh
story-shell --image go-agent-fdb
```

or, with the low-level launcher:

```sh
run-shell --image go-agent-fdb --host-root .
```

## Expected runtime wiring

- proxy: `go-agent-egress-proxy`
- database: `go-agent-fdb`
- internal network: `go-agent-internal-net`

From inside the agent shell, your tests should point at:

```text
go-agent-fdb:4500
```

## Common workflow

```sh
make networks
make -f extras/foundationdb/Makefile fdb-up FDB_VERSION=7.3.68
make -f extras/foundationdb/Makefile fdb-init
make -f extras/foundationdb/Makefile agent-fdb-build
story-shell --image go-agent-fdb
```

## Cleanup

Stop and remove the FoundationDB container:

```sh
make -f extras/foundationdb/Makefile fdb-down
```

Remove the persistent FoundationDB data volume:

```sh
make -f extras/foundationdb/Makefile fdb-clean-data
```

## Notes

- Keep the FoundationDB server version and client library version aligned.
- `agent-fdb-build` downloads the client package from the FoundationDB GitHub release matching `FDB_VERSION`.
- This addon is intentionally separate from the main harness so non-FoundationDB users do not pay the complexity cost.
- If you do not need client libraries in the agent image, you can skip `agent-fdb-build` and just run the database container for integration tests.
