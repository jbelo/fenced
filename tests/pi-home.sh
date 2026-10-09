#!/usr/bin/env bash
# Exercise home initialization against an isolated volume; initial install needs npm access.
set -euo pipefail
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
agent_image=${1:-go-agent}
test_volume=$(docker volume create)
trap 'docker volume rm "$test_volume" >/dev/null' EXIT
docker run --rm --network none --mount "type=volume,src=$test_volume,target=/home/agent" \
    "$agent_image" chown 501:20 /home/agent
make -C "$repo_dir" install-agent-pi AGENT_IMAGE="$agent_image" AGENTHOME="$test_volume" UID=501 GID=20
docker run --rm --network none --read-only --user 501:20 \
    --tmpfs /tmp:rw,mode=1777 --mount "type=volume,src=$test_volume,target=/home/agent" \
    -e HOME=/home/agent "$agent_image" bash -c '
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export NPM_CONFIG_PREFIX="$HOME/.local"
pi --version
hash -r
test "$(command -v pi)" = "$HOME/.local/bin/pi"
test "$(npm prefix -g)" = "$HOME/.local"
package="$HOME/.local/lib/node_modules/@earendil-works/pi-coding-agent"
test -w "$package/package.json"
test -w "$HOME/.local/bin"
node --input-type=module -e "
const config = await import(process.env.HOME + \"/.local/lib/node_modules/@earendil-works/pi-coding-agent/dist/config.js\");
const command = config.getSelfUpdateCommand(config.PACKAGE_NAME);
if (!command) throw new Error(\"Pi rejected self-update for its home installation\");
console.log(command.display);
"
touch "$package/.preserve-test"
test ! -e /usr/bin/pi
test ! -e /usr/local/bin/pi
echo "Pi is home-installed, writable, and accepts self-updates."
'
make -C "$repo_dir" install-agent-pi AGENT_IMAGE="$agent_image" AGENTHOME="$test_volume" UID=501 GID=20
docker run --rm --network none --read-only --user 501:20 \
    --mount "type=volume,src=$test_volume,target=/home/agent,readonly" "$agent_image" \
    test -f /home/agent/.local/lib/node_modules/@earendil-works/pi-coding-agent/.preserve-test
