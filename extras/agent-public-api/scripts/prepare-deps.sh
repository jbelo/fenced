#!/usr/bin/env bash
# Host-only preparation: install an isolated CLI, then download deps without running the app.
set -euo pipefail
repo_root=$(cd "${1:?Public API checkout required}" && pwd -P)
mode=${2:-all}
cli_version=${3:-1.12.6.1673}
extra_dir=$(cd "$(dirname "$0")/.." && pwd -P)
[[ -f "$repo_root/modules/backend/deps.edn" ]] || { echo 'Missing backend/deps.edn' >&2; exit 1; }
[[ $cli_version =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Invalid CLI version' >&2; exit 1; }
case "$mode" in runtime|dev|build|all) ;; *) echo "Unknown preparation mode: $mode" >&2; exit 1;; esac
cache_root="$repo_root/.deps-cache"
mkdir -p "$cache_root"
if [[ ! -e "$cache_root/.gitignore" ]]; then printf '*\n' > "$cache_root/.gitignore"; fi

# Match the container's CLI defaults without upgrading the host's global installation.
cli_dir="$cache_root/tools/clojure-$cli_version"
if [[ ! -x "$cli_dir/bin/clojure" ]]; then
    mkdir -p "$cache_root/tools"
    stage=$(mktemp -d "$cache_root/tools/install.XXXXXX")
    trap 'rm -rf -- "$stage"' EXIT
    curl --fail --location --retry 2 \
        "https://download.clojure.org/install/clojure-tools-$cli_version.tar.gz" -o "$stage/tools.tar.gz"
    tar -xzf "$stage/tools.tar.gz" -C "$stage"
    mkdir -p "$stage/installed/bin" "$stage/installed/libexec"
    cp "$stage/clojure-tools/"*.edn "$stage/installed/"
    cp "$stage/clojure-tools/"*.jar "$stage/installed/libexec/"
    escaped_prefix=${cli_dir//\\/\\\\}
    escaped_prefix=${escaped_prefix//&/\\&}
    escaped_prefix=${escaped_prefix//@/\\@}
    sed "s@PREFIX@$escaped_prefix@g" "$stage/clojure-tools/clojure" > "$stage/installed/bin/clojure"
    chmod 755 "$stage/installed/bin/clojure"
    [[ ! -e "$cli_dir" ]] || { echo "Incomplete CLI installation at $cli_dir; inspect it before retrying." >&2; exit 1; }
    mv "$stage/installed" "$cli_dir"
fi
export PUBLIC_API_SOURCE="$repo_root"
export PUBLIC_API_CLOJURE="$cli_dir/bin/clojure"
cd "$repo_root/modules/backend"
prepare() { bash "$extra_dir/bin/public-api-clojure" -P "$@"; }
case "$mode" in
    runtime) prepare -M ;;
    dev) prepare -M:test ;;
    build) prepare -M; prepare -T:project ;;
    all) prepare -M; prepare -M:test; prepare -T:project ;;
esac
echo "Prepared $mode dependencies in $cache_root (application not started)."
