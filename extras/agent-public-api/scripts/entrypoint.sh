#!/usr/bin/env bash
# Give arbitrary harness UIDs a user entry for SSH/REPL tools, without root writes.
set -euo pipefail
agent_uid=$(id -u)
agent_gid=$(id -g)
if ! getent passwd "$agent_uid" >/dev/null; then
    identity_dir=$(mktemp -d /tmp/public-api-user.XXXXXX)
    cp /etc/passwd "$identity_dir/passwd"
    cp /etc/group "$identity_dir/group"
    printf 'agent-%s:x:%s:%s:Agent:%s:/bin/bash\n' \
        "$agent_uid" "$agent_uid" "$agent_gid" "${HOME:?HOME is required}" >> "$identity_dir/passwd"
    if ! getent group "$agent_gid" >/dev/null; then
        printf 'agent-%s:x:%s:\n' "$agent_gid" "$agent_gid" >> "$identity_dir/group"
    fi
    export NSS_WRAPPER_PASSWD="$identity_dir/passwd"
    export NSS_WRAPPER_GROUP="$identity_dir/group"
    export LD_PRELOAD="/usr/local/lib/libnss_wrapper.so${LD_PRELOAD:+:$LD_PRELOAD}"
fi
exec "$@"
