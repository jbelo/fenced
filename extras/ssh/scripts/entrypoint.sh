#!/bin/sh
# Add local debugging SSH, then run the explicitly supplied application command.
set -eu
test "$#" -gt 0 || { echo 'An application command is required.' >&2; exit 1; }
mkdir -p /run/sshd
ssh-keygen -A
/usr/sbin/sshd -e
exec "$@"
