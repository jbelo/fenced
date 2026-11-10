#!/bin/sh
# Run as the agent UID, with its persistent home mounted. Never uninstall legacy Pi.
set -eu
pi_version=${1:?Pi version}
action=${2:-install}
case "$action" in install|migrate|'') ;; *) echo 'Invalid action' >&2; exit 1;; esac
export NPM_CONFIG_PREFIX="${HOME:?}/.local"
entry="$HOME/.local/bin/pi"
root="$HOME/.pi/agent/install"
if [ -x "$entry" ] && { [ "$action" != migrate ] || [ "$(readlink "$entry" 2>/dev/null || true)" = ../../.pi/agent/bin/pi ]; }; then
    echo 'Preserving existing Pi installation'
    "$entry" --version
    exit
fi
mkdir -p "$HOME/.pi/agent"
lock="$HOME/.pi/agent/.fenced-install-lock"
mkdir "$lock" || { echo 'Another installation is running (or a stale lock needs inspection)' >&2; exit 1; }
stage=
link=
trap 'test -z "$stage" || rm -rf "$stage"; test -z "$link" || rm -f "$link"; rmdir "$lock"' EXIT
# Only replace the known npm symlink, never an unknown executable or wrapper.
if [ -e "$entry" ] || [ -L "$entry" ]; then
    target=$(readlink "$entry") || { echo 'Unrecognized Pi entry point' >&2; exit 1; }
    case "$target" in ../lib/node_modules/@earendil-works/pi-coding-agent/dist/cli.js|../lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js) ;;
        *) echo "Unrecognized Pi symlink; inspect before migration" >&2; exit 1;; esac
fi
if [ -e "$root" ] || [ -e "$HOME/.pi/agent/bin/pi" ]; then
    node - "$root/managed-install.json" <<'NODE'
const m = require(process.argv[2]);
if (m.kind !== 'pi-managed-install' || m.schemaVersion !== 1 || m.layout !== 'releases-v1')
    throw new Error('Unrecognized managed layout');
NODE
    "$HOME/.pi/agent/bin/pi" --version
fi
case "$pi_version" in ''|*[!0-9.]*|.*) echo 'Expected a numeric release version' >&2; exit 1;; esac
. "$(dirname "$0")/pi-managed-layout.sh"
PI_PACKAGE=@earendil-works/pi-coding-agent
PI_CMD=pi
PI_MANAGED_INSTALL_MARKER=managed-install.json
stage=$(mktemp -d "$HOME/.pi/agent/.fenced-stage.XXXXXX")
for artifact in package.json package-lock.json; do
    curl --fail --silent --show-error --location "https://pi.dev/api/installer/releases/$pi_version/$artifact" -o "$stage/$artifact"
done
validate_managed_install_artifacts "$stage/package.json" "$stage/package-lock.json" "$pi_version"
(cd "$stage" && npm ci --ignore-scripts --min-release-age=0 --omit=dev --include=optional --no-fund --no-audit)
test "$("$stage/node_modules/.bin/pi" --version)" = "$pi_version"
# Retain the original symlink and ALL its package files for rollback and active processes.
if [ -L "$entry" ]; then
    test ! -e "$HOME/.pi/agent/fenced-legacy-pi-target"
    readlink "$entry" > "$HOME/.pi/agent/fenced-legacy-pi-target"
fi
mkdir -p "$root/releases"
if [ -e "$root/releases/$pi_version" ]; then
    echo 'Requested managed release already exists; refusing to overwrite it' >&2
    exit 1
fi
mv "$stage" "$root/releases/$pi_version"
stage=
write_managed_install_marker "$root" symlink "$entry"
write_managed_install_launcher "$HOME/.pi/agent"
write_managed_current_version "$root" "$pi_version"
test "$("$HOME/.pi/agent/bin/pi" --version)" = "$pi_version"
mkdir -p "$HOME/.local/bin"
link="$HOME/.local/bin/.pi.next.$$"
ln -s ../../.pi/agent/bin/pi "$link"
# rename replaces the symlink atomically, without dereferencing it.
node -e 'require("fs").renameSync(process.argv[1], process.argv[2])' "$link" "$entry"
link=
"$entry" --version
echo 'Managed Pi ready. Legacy npm files retained; do not npm update/uninstall Pi.'
