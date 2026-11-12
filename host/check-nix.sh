#!/usr/bin/env bash
# Build and inspect host tools only. No Docker daemon or live harness mutation.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$repo"
if [[ ! -f flake.lock ]]; then
  printf '%s\n' 'Missing flake.lock: run nix --extra-experimental-features "nix-command flakes" flake lock, then git add flake.lock.' >&2
  exit 1
fi
nix_args=(--extra-experimental-features 'nix-command flakes')
# Evaluate all three systems; build only the native system below.
nix "${nix_args[@]}" flake check --no-update-lock-file --all-systems --no-build
nix "${nix_args[@]}" flake check --no-update-lock-file
before_path=$PATH
before_git=$(command -v git)
nix "${nix_args[@]}" develop --no-update-lock-file .#host --command bash --noprofile --norc -c '
  set -euo pipefail
  for tool in bash git tmux nvim python3 rsync make docker ssh run-shell story-shell meta-shell story-setup fenced-doctor; do
    selected=$(command -v "$tool")
    case "$selected" in
      /nix/store/*/bin/*) ;;
      *) printf "Expected pinned %s; found %s\n" "$tool" "$selected" >&2; exit 1 ;;
    esac
  done
  fenced-host-info
  run-shell --help >/dev/null
  story-shell --help >/dev/null
  meta-shell --help >/dev/null
  story-setup --help >/dev/null
  fenced-doctor --help >/dev/null
'
[[ $PATH == "$before_path" && $(command -v git) == "$before_git" ]]
printf '%s\n' 'Native host-tool checks passed; caller PATH and Git selection preserved.'
