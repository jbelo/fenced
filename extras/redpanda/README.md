# Redpanda addon

This folder contains optional tooling for running a Redpanda container alongside the coding harness and, when useful, building an agent image with the `rpk` CLI.

Redpanda is Kafka API-compatible and is suitable for projects whose tests need a local Kafka broker, such as `branch-kms` billing integration coverage.

## What this addon provides

- Make targets to run Redpanda on the harness's internal Docker network
- a helper Dockerfile for building an optional `go-agent-redpanda` image with `rpk`

## Network model

The Redpanda container is intended to join:

- `go-agent-internal-net`

This lets agent shells reach the broker by container name while keeping the broker off the host network by default.

Suggested broker address from the agent shell:

```text
go-agent-redpanda:9092
```

## Prerequisite

Create the main harness networks first:

```sh
make networks
```

The addon targets also run this prerequisite automatically.

## 1. Start Redpanda on the internal agent network

```sh
make -f extras/redpanda/Makefile redpanda-up
```

This starts a container named:

```text
go-agent-redpanda
```

with a persistent Docker volume for data, attached to `go-agent-internal-net`.

By default the container is not exposed on the host. Agent shells should use:

```sh
export KAFKA_USE_EXTERNAL=true
export KAFKA_BROKERS=go-agent-redpanda:9092
```

## 2. Check broker readiness

From the host, using a short-lived Redpanda image on the internal network:

```sh
make -f extras/redpanda/Makefile redpanda-ready
```

Or from an agent image that includes `rpk`:

```sh
rpk cluster info -X brokers=go-agent-redpanda:9092
```

## 3. Open `rpk` inside the Redpanda container

```sh
make -f extras/redpanda/Makefile redpanda-rpk RPK_ARGS='cluster info'
```

Examples:

```sh
make -f extras/redpanda/Makefile redpanda-rpk RPK_ARGS='topic list'
make -f extras/redpanda/Makefile redpanda-rpk RPK_ARGS='topic create exo.kms.fct.inventory.0'
```

## 4. Tail broker logs

```sh
make -f extras/redpanda/Makefile redpanda-logs
```

## 5. Build an agent image with `rpk`

If you want `rpk` available inside the agent shell, build the derived image:

```sh
make -f extras/redpanda/Makefile agent-redpanda-build
```

This creates:

```text
go-agent-redpanda
```

which extends the main `go-agent` image.

For projects that also need FoundationDB client libraries, build from the FoundationDB-derived image instead:

```sh
make -f extras/foundationdb/Makefile agent-fdb-build
make -f extras/redpanda/Makefile agent-redpanda-build \
  AGENT_IMAGE=go-agent-fdb \
  AGENT_REDPANDA_IMAGE=go-agent-fdb-redpanda
```

Then run a shell with it:

```sh
story-shell --image go-agent-fdb-redpanda
```

## branch-kms workflow

`branch-kms` already has Redpanda testcontainer support. Use this addon when you prefer a long-lived broker instead of having the tests start their own container.

Start FoundationDB and Redpanda from the host:

```sh
make -f extras/foundationdb/Makefile fdb-up FDB_VERSION=7.3.68
make -f extras/foundationdb/Makefile fdb-init
make -f extras/foundationdb/Makefile fdb-cluster-install-agenthome
make -f extras/redpanda/Makefile redpanda-up
```

Optionally build a combined agent image:

```sh
make -f extras/foundationdb/Makefile agent-fdb-build FDB_VERSION=7.3.68
make -f extras/redpanda/Makefile agent-redpanda-build \
  AGENT_IMAGE=go-agent-fdb \
  AGENT_REDPANDA_IMAGE=go-agent-fdb-redpanda
```

Inside the agent shell:

```sh
export FDB_USE_EXTERNAL=true
export FDB_CLUSTER_FILE=$HOME/.fdb.cluster
export KAFKA_USE_EXTERNAL=true
export KAFKA_BROKERS=go-agent-redpanda:9092

cd branch-kms
go test ./test
```

## Cleanup

Stop and remove the Redpanda container:

```sh
make -f extras/redpanda/Makefile redpanda-down
```

Remove the persistent Redpanda data volume:

```sh
make -f extras/redpanda/Makefile redpanda-clean-data
```

## Notes

- Sarama is a pure Go Kafka client, so the agent image does not need native Kafka libraries.
- `Dockerfile.agent-redpanda` only adds the `rpk` CLI for debugging and broker inspection.
- The default broker listener is internal-only and advertised as `go-agent-redpanda:9092`.
- If a project uses testcontainers by default, set its external Kafka environment variables to force use of this long-lived broker.
