#!/usr/bin/env bash
set -euo pipefail

mode=${1:?Expected idstore or public-api}
container=${2:?Expected container name}
attempts=${3:?Expected readiness attempt count}
source_dir=${4:?Expected Public API source path}

if [[ ! $attempts =~ ^[1-9][0-9]*$ ]]; then
    echo "Readiness attempts must be a positive integer without leading zeros" >&2
    exit 1
fi

schemas=()
case "$mode" in
    idstore) schemas=(idstore) ;;
    public-api)
        schemas=(idstore dnsstore jobstore quotastore resourcelockstore
                 resourcelockstore-v2 bucketstore inventorystore eventstore authstore)
        ;;
    *) echo "Unknown mode: $mode" >&2; exit 1 ;;
esac

# Validate all inputs before making any schema changes.
# The conditional array expansion also supports macOS Bash 3.2 with nounset.
for schema in ${schemas[@]+"${schemas[@]}"}; do
    if [[ ! -r "$source_dir/doc/$schema.cql" ]]; then
        echo "Missing schema: $source_dir/doc/$schema.cql; set PUBLIC_API_SOURCE" >&2
        exit 1
    fi
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
bash "$script_dir/../../cassandra/scripts/wait-ready.sh" "$container" "$attempts"

for schema in ${schemas[@]+"${schemas[@]}"}; do
    echo "Applying $schema.cql"
    if [[ $schema == bucketstore ]]; then
        # Upstream bucketstore declarations lack the guards used by other schemas.
        # Adapt only this stream; never rewrite the source checkout.
        sed -E '/^CREATE (KEYSPACE|TABLE|INDEX) IF NOT EXISTS /!s/^(CREATE (KEYSPACE|TABLE|INDEX)) /\1 IF NOT EXISTS /' \
            "$source_dir/doc/$schema.cql" |
            docker exec -i "$container" cqlsh --request-timeout=30
    else
        docker exec -i "$container" cqlsh --request-timeout=30 \
            < "$source_dir/doc/$schema.cql"
    fi
done
echo "Schema initialization completed: $mode"
