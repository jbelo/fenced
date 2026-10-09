#!/bin/sh
# Seed the agent tmux configuration as root; preserve existing files and symlinks.
set -eu
source_file=${1:?Source configuration}
destination=${2:?Destination configuration}
agent_uid=${3:?Agent UID}
agent_gid=${4:?Agent GID}
if [ -e "$destination" ] || [ -L "$destination" ]; then
    echo "Preserving existing $destination"
else
    mkdir -p "$(dirname "$destination")"
    install -m 0644 -o "$agent_uid" -g "$agent_gid" "$source_file" "$destination"
    echo "Installed $destination"
fi
