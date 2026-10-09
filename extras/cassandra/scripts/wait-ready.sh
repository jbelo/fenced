#!/usr/bin/env bash
set -euo pipefail

container=${1:?Expected container name}
attempts=${2:?Expected readiness attempt count}

if [[ ! $attempts =~ ^[1-9][0-9]*$ ]]; then
    echo "Readiness attempts must be a positive integer without leading zeros" >&2
    exit 1
fi

ready=false
for ((attempt = 1; attempt <= attempts; attempt++)); do
    if [[ $(docker container inspect -f '{{.State.Running}}' "$container") != true ]]; then
        echo "Cassandra container is not running: $container" >&2
        exit 1
    fi
    if docker exec "$container" cqlsh --connect-timeout=2 --request-timeout=2 \
        -e 'SELECT release_version FROM system.local;' >/dev/null 2>&1; then
        ready=true
        break
    fi
    echo "Waiting for Cassandra ($attempt/$attempts)..."
    if ((attempt < attempts)); then sleep 2; fi
done
if [[ $ready != true ]]; then
    echo "Cassandra did not become ready; inspect docker logs $container" >&2
    exit 1
fi
echo "Cassandra is ready: $container"
