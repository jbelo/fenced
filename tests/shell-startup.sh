#!/usr/bin/env bash
# Capture launcher arguments without creating containers.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
for mode in default plain; do
  (
    exec() {
      test "$1" = docker
      local command="${!#}"
      if [[ $mode == default ]]; then
        [[ $command == *'tmux new-session -A -s agent'* ]]
        [[ $command == *'fi; exec /bin/bash' ]]
      else
        [[ $command != *tmux* ]]
      fi
      bash -n -c "$command"
    }
    options=()
    [[ $mode != plain ]] || options+=(--no-tmux)
    source "$repo/bin/run-shell" --no-egress-proxy --workspace-root "$repo" "${options[@]}"
  )
done
(
  exec() {
    test "$1" = "$repo/bin/run-shell"
    [[ " $* " == *' --no-tmux '* ]]
  }
  source "$repo/bin/story-shell" --workspace-root "$repo" --no-tmux "$repo"
)
echo 'Shell startup argument checks passed.'
