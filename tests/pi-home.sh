#!/usr/bin/env bash
# Real downloads and migration in a disposable home; never touches agenthome.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
agent_image=${1:-go-agent}
test_volume=$(docker volume create)
trap 'docker volume rm "$test_volume" >/dev/null' EXIT
run() {
 docker run --rm --read-only --tmpfs /tmp:rw,mode=1777 --user 501:20 \
   -e HOME=/home/agent --mount "type=volume,src=$test_volume,target=/home/agent" "$agent_image" "$@"
}
docker run --rm --network none --mount "type=volume,src=$test_volume,target=/home/agent" "$agent_image" chown 501:20 /home/agent
setup() { make -C "$repo_dir" "$@" AGENT_IMAGE="$agent_image" AGENTHOME="$test_volume" UID=501 GID=20; }
setup install-agent-pi PI_VERSION=1.5.0
# Reproduce the live home: managed 1.5.0 coexists with npm 1.5.2 selected on PATH.
run sh -c 'rm "$HOME/.local/bin/pi"; npm --prefix "$HOME/.local" install -g --ignore-scripts @earendil-works/pi-coding-agent@1.5.2; touch "$HOME/.local/lib/node_modules/@earendil-works/pi-coding-agent/.preserve-test"'
setup install-agent-pi
run sh -c 'test "$(readlink "$HOME/.local/bin/pi")" = ../lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
# Failed download must leave the npm command and previous managed release usable.
if setup migrate-agent-pi PI_VERSION=0.0.0; then echo 'Expected failure' >&2; exit 1; fi
run sh -c 'test "$("$HOME/.local/bin/pi" --version)" = 1.5.2; test "$("$HOME/.pi/agent/bin/pi" --version)" = 1.5.0'
setup migrate-agent-pi
setup migrate-agent-pi
run sh -c '
set -eu
test "$(readlink "$HOME/.local/bin/pi")" = ../../.pi/agent/bin/pi
test "$("$HOME/.local/bin/pi" --version)" = 1.5.2
test -f "$HOME/.local/lib/node_modules/@earendil-works/pi-coding-agent/.preserve-test"
# Existing processes retain both their old managed and old npm modules.
test "$(node "$HOME/.local/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js" --version)" = 1.5.2
test "$("$HOME/.pi/agent/install/releases/1.5.0/node_modules/.bin/pi" --version)" = 1.5.0
test -f "$HOME/.pi/agent/fenced-legacy-pi-target"
'
echo 'Managed installation, coexistence migration, failure preservation and idempotence passed.'
