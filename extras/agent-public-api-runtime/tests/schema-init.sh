#!/usr/bin/env bash
# Offline regression checks: mock Docker, never contact or modify a database.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
init="$root/agent-public-api-runtime/scripts/init-schema.sh"
ready="$root/cassandra/scripts/wait-ready.sh"
fixture=$(mktemp -d)
trap 'rm -rf -- "$fixture"' EXIT
export SCHEMA_TEST_LOG="$fixture/calls"
export SCHEMA_TEST_RUNNING=true SCHEMA_TEST_FAIL=false
docker() {
    printf '%s\n' "$*" >> "$SCHEMA_TEST_LOG"
    if [[ $1 == container ]]; then
        printf '%s\n' "$SCHEMA_TEST_RUNNING"
    elif [[ $* == *'--request-timeout=30'* ]]; then
        cat >> "$SCHEMA_TEST_LOG"
        [[ $SCHEMA_TEST_FAIL == false ]]
    fi
}
export -f docker
bash "$ready" mock-db 1
if bash "$ready" mock-db 0; then exit 1; fi
SCHEMA_TEST_RUNNING=false
export SCHEMA_TEST_RUNNING
if bash "$ready" mock-db 1; then exit 1; fi
SCHEMA_TEST_RUNNING=true
export SCHEMA_TEST_RUNNING
: > "$SCHEMA_TEST_LOG"
if bash "$init" idstore mock-db 1 "$fixture/missing"; then exit 1; fi
test ! -s "$SCHEMA_TEST_LOG"
mkdir -p "$fixture/source/doc"
for schema in idstore dnsstore jobstore quotastore resourcelockstore resourcelockstore-v2 bucketstore inventorystore eventstore authstore; do
    printf 'CREATE TABLE %s (id int PRIMARY KEY);\n' "$schema" > "$fixture/source/doc/$schema.cql"
done
bash "$init" idstore mock-db 1 "$fixture/source"
test "$(grep -c -- '--request-timeout=30' "$SCHEMA_TEST_LOG")" -eq 1
: > "$SCHEMA_TEST_LOG"
bash "$init" public-api mock-db 1 "$fixture/source"
test "$(grep -c -- '--request-timeout=30' "$SCHEMA_TEST_LOG")" -eq 10
grep -q 'CREATE TABLE IF NOT EXISTS bucketstore' "$SCHEMA_TEST_LOG"
grep -q '^CREATE TABLE bucketstore' "$fixture/source/doc/bucketstore.cql"
SCHEMA_TEST_FAIL=true
export SCHEMA_TEST_FAIL
: > "$SCHEMA_TEST_LOG"
if bash "$init" public-api mock-db 1 "$fixture/source"; then exit 1; fi
test "$(grep -c -- '--request-timeout=30' "$SCHEMA_TEST_LOG")" -eq 1
echo 'Schema initialization checks passed (mock Docker).'
