#!/bin/sh
# Runs only inside a Docker build; blank timestamp preserves legacy sources.
set -eu
stamp=${1:-}
[ -n "$stamp" ] || exit 0
case "$stamp" in *[!0-9TZ]*|'') exit 1;; esac
[ ${#stamp} -eq 16 ] || exit 1
# Replace the image's source definitions, never a host's configuration.
rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources
cat > /etc/apt/sources.list.d/fenced-snapshot.list <<EOF
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/$stamp/ bookworm main
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/$stamp/ bookworm-updates main
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/$stamp/ bookworm-backports main
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/$stamp/ bookworm-security main
EOF
# Signature verification stays enabled. Historical Release expiry is expected.
