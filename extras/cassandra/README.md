# Cassandra

Agent-side usage: [`cassandra-connect` skill](skills/cassandra-connect/SKILL.md), installed by
`make install-agent-context` at `$HOME/.agents/skills/cassandra-connect/SKILL.md`.

Run Cassandra beside the agent on `go-agent-internal-net`, using the default
`cassandra:4.1.10` image. This extra manages the database lifecycle and readiness;
application schemas and seed data are managed separately.
The node uses one token, matching its fixed initial token, so recreating the
container with an existing data volume keeps a consistent token count.

## Start and check readiness

Run these commands on the Docker host, from the harness repository:

```sh
make -f extras/cassandra/Makefile cassandra-up
make -f extras/cassandra/Makefile cassandra-ready
```

Readiness uses bounded CQL probes and requires no application checkout.
The extra does not create application keyspaces, tables, or identities.

## Connect from an agent

Use `go-agent-cassandra` on port `9042` and the keyspace prepared for your
application. Agent containers already join `go-agent-internal-net`; no host port
or HTTP proxy is required. No agent image rebuild is needed.

Open a CQL shell from the host using the client included in the database image:

```sh
make -f extras/cassandra/Makefile cassandra-cqlsh
```

## Lifecycle and storage

```sh
make -f extras/cassandra/Makefile cassandra-ready
make -f extras/cassandra/Makefile cassandra-status
make -f extras/cassandra/Makefile cassandra-logs
make -f extras/cassandra/Makefile cassandra-down
```

`cassandra-up` creates or starts the named container. It does not replace an
existing container or automatically import schemas. `cassandra-down` stops it
gracefully and removes only the container. Data stays in
`go-agent-cassandra-data`, mounted at `/var/lib/cassandra`, independently of the
agent home volume. Run `down` followed by `up` to apply changed container options.

To permanently delete the database, first stop/remove the container, then:

```sh
make -f extras/cassandra/Makefile cassandra-clean-data \
  CONFIRM_DELETE=go-agent-cassandra-data
```

## Overrides

| Variable | Default |
| --- | --- |
| `CASSANDRA_VERSION` | `4.1.10` |
| `CASSANDRA_IMAGE` | `cassandra:$(CASSANDRA_VERSION)` |
| `CASSANDRA_CONTAINER` | `go-agent-cassandra` |
| `CASSANDRA_DATA_VOLUME` | `go-agent-cassandra-data` |
| `CASSANDRA_HEAP` | `1G` (both minimum and maximum JVM heap) |
| `CASSANDRA_WAIT_ATTEMPTS` | `60`, with two seconds between failed probes |
| `AGENT_INTERNAL_NETWORK` | `go-agent-internal-net` |
| `CASSANDRA_DOCKER_RUN_EXTRA` | Empty |

The JVM needs memory beyond its heap. Increase readiness attempts if your Docker
VM starts slowly. Startup inherits the image's architecture selection.

Host ports are not published by default. For a host-side client, optionally
publish CQL on loopback when creating the container:

```sh
make -f extras/cassandra/Makefile cassandra-up \
  CASSANDRA_DOCKER_RUN_EXTRA='-p 127.0.0.1:9042:9042'
```

Use different container and volume names for independent databases. Carry the
same container overrides when applying application schemas and during lifecycle
commands. The historical cluster name `public_api` is retained for compatibility
with existing data volumes; it does not imply an application dependency.
