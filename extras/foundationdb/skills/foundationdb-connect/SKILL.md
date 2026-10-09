---
name: foundationdb-connect
description: Connect to the local harness FoundationDB and diagnose cluster-file or connectivity problems from an agent container.
---

# Connect to FoundationDB

Use the developer's overrides when supplied; these are local harness defaults, not live service status. Report missing services, tools, schemas, or credentials to the developer. Container provisioning and persistent-state cleanup remain host responsibilities.

For FoundationDB, use the actual cluster connection file, normally
`$HOME/.fdb.cluster`, installed separately by the host. A hostname alone is not
a complete FoundationDB connection string. When that file exists:

```sh
export FDB_CLUSTER_FILE="$HOME/.fdb.cluster"
```

If the cluster file is missing or points to an unreachable coordinator, report
that to the developer. When `fdbcli` is available, inspect connectivity with:

```sh
fdbcli -C "$FDB_CLUSTER_FILE" --exec 'status minimal'
```
