#!/bin/sh
# Initialize Pi in the writable agent home; run inside Docker as the agent UID.
set -eu
pi_version=${1:?Pi version}
export NPM_CONFIG_PREFIX="${HOME:?}/.local"
if [ -x "$HOME/.local/bin/pi" ]; then
    echo "Preserving existing Pi installation"
else
    npm install -g --ignore-scripts "@earendil-works/pi-coding-agent@$pi_version"
fi
"$HOME/.local/bin/pi" --version
