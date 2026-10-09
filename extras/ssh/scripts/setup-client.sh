#!/usr/bin/env bash
# Prepare a reusable client key and config for a local development service.
set -euo pipefail
ssh_dir=${1:?SSH directory}
hostname=${2:?Service hostname}
alias=${3:?SSH host alias}
identity_file=${4:?Agent-side identity file path}
umask 077
mkdir -p "$ssh_dir/server" "$ssh_dir/client"
key="$ssh_dir/client/id_ed25519"
if [[ ! -e $key ]]; then
    ssh-keygen -q -t ed25519 -N '' -f "$key"
fi
ssh-keygen -y -f "$key" > "$key.pub"
cp "$ssh_dir/client/id_ed25519.pub" "$ssh_dir/server/authorized_keys"
printf 'Host %s\n  HostName %s\n  User root\n  IdentityFile "%s"\n  StrictHostKeyChecking no\n  UserKnownHostsFile /dev/null\n  LogLevel ERROR\n' "$alias" "$hostname" "$identity_file" > "$ssh_dir/client/config"
