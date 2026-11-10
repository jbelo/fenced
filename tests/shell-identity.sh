#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
exec() {
  docker run --rm --network none --read-only --tmpfs /tmp:rw,mode=1777 \
    --user 501:20 -e HOME=/home/agent go-agent bash -c "${identity_command}"'
set -eu
test "$(id -un)" = agent-501
test "$(id -u)" = 501
tmux -L identity new-session -d -s check "sleep 10"
test "$(tmux -L identity show-environment -g LD_PRELOAD)" = LD_PRELOAD=/usr/local/lib/libnss_wrapper.so
tmux -L identity kill-server
echo "Numeric UID resolves in the shell and NSS environment reaches tmux."
'
}
source "$repo/bin/run-shell" --no-egress-proxy --workspace-root "$repo" --no-tmux
