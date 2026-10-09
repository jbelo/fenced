---
name: cassandra-connect
description: Connect to local harness Cassandra and inspect idstore schema availability, not initialize schemas or seed identities.
---

# Connect to Cassandra

Use the developer's overrides when supplied; these are local harness defaults, not live service status. Report missing services, tools, schemas, or credentials to the developer. Container provisioning and persistent-state cleanup remain host responsibilities.

Connect to `go-agent-cassandra` on port `9042`, using keyspace `idstore` for
identities. Creating the schema does not create API keys, roles, or organizations.
Database files live in a separate volume from your agent home.

If `cqlsh` is already available, this read-only query checks connectivity and
lists the idstore tables:

```sh
cqlsh go-agent-cassandra 9042 -e "SELECT table_name FROM system_schema.tables WHERE keyspace_name = 'idstore';"
```

An empty result means the keyspace has no tables; it does not authorize creating
them. No client credentials or seed data are included with this guide.

Use the native Cassandra protocol, not the HTTP egress proxy. Cassandra does not connect to KMS; applications configure their Cassandra and KMS clients separately.
