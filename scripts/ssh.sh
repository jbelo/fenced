#!/usr/bin/env bash
# Let OpenSSH resolve arbitrary container UIDs without modifying /etc/passwd.
set -euo pipefail
if getent passwd "$(id -u)" >/dev/null; then
    exec /usr/bin/ssh "$@"
fi
identity_dir=$(mktemp -d /tmp/agent-ssh-user.XXXXXX)
trap 'rm -rf -- "$identity_dir"' EXIT
cp /etc/passwd "$identity_dir/passwd"
cp /etc/group "$identity_dir/group"
printf 'agent-%s:x:%s:%s:Agent:%s:/bin/bash\n' \
    "$(id -u)" "$(id -u)" "$(id -g)" "${HOME:?}" >> "$identity_dir/passwd"
export NSS_WRAPPER_PASSWD="$identity_dir/passwd"
export NSS_WRAPPER_GROUP="$identity_dir/group"
export LD_PRELOAD="/usr/local/lib/libnss_wrapper.so${LD_PRELOAD:+:$LD_PRELOAD}"
/usr/bin/ssh "$@"
