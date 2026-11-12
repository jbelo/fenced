#!/usr/bin/env bash
# Prepare an existing Ubuntu VM; no agent images, volumes or networks are created.
set -euo pipefail
usage() {
  cat <<'HELP'
Usage: bash host/bootstrap-ubuntu.sh [--apply] [--grant-docker-access]

Default: print the plan without modifying the machine.
--apply                Install Docker Engine from Docker's signed Ubuntu repository.
--grant-docker-access  Add the invoking non-root user to the docker group (root-equivalent access).

Run as the normal VM operator, not root. sudo is used only with --apply.
Existing Docker installations are preserved; incompatible packages/configuration
require an explicit manual migration. Nix is a separate prerequisite.
HELP
}
apply=0
grant=0
for arg in "$@"; do
  case "$arg" in
    --apply) apply=1 ;;
    --grant-docker-access) grant=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done
[[ $(uname -s) == Linux ]] || { echo 'Requires Ubuntu 24.04 or 26.04.' >&2; exit 1; }
. /etc/os-release
[[ $ID == ubuntu && ( $VERSION_ID == 24.04 || $VERSION_ID == 26.04 ) ]] || { echo 'Requires Ubuntu 24.04 or 26.04.' >&2; exit 1; }
case "$VERSION_ID" in 24.04) suite=noble ;; 26.04) suite=resolute ;; esac
arch=$(dpkg --print-architecture)
case "$arch" in arm64|amd64) ;; *) echo 'Requires ARM64 or AMD64.' >&2; exit 1 ;; esac
[[ $(id -u) != 0 ]] || { echo 'Run as the normal operator; the apply step invokes sudo.' >&2; exit 1; }
operator=$(id -un)
installed() { [[ $(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || true) == 'install ok installed' ]]; }
# Refuse implicit package replacement. This adapter owns only a fresh Docker CE install.
for package in docker.io podman-docker containerd runc; do
  if installed "$package"; then
    echo "Existing $package package: preserve it; arrange a manual Docker migration if needed." >&2
    exit 1
  fi
done
fresh=1
if installed docker-ce; then fresh=0; fi
if [[ $fresh == 1 ]]; then
  for package in docker-ce-cli containerd.io; do
    if installed "$package"; then
      echo "Partial existing Docker installation ($package); inspect it before proceeding." >&2
      exit 1
    fi
  done
  if [[ -e /var/lib/docker || -e /etc/docker/daemon.json || -S /var/run/docker.sock ]]; then
    echo 'Existing Docker state/configuration found; automatic installation refused.' >&2
    exit 1
  fi
  # A prior operator repository should not be silently replaced or combined.
  if grep -rqs 'download.docker.com' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
    echo 'An existing Docker apt source needs operator review; no repository changes made.' >&2
    exit 1
  fi
  printf '%s\n' 'Plan: install curl/CA certificates; add Docker signed Ubuntu apt source; install Docker CE and plugins; enable/start the new daemon.'
else
  printf '%s\n' 'Plan: preserve installed Docker packages, daemon configuration, state and running services.'
fi
if [[ $grant == 1 ]]; then
  printf 'Plan: ensure %s belongs to the docker group (root-equivalent access).\n' "$operator"
else
  printf '%s\n' 'Docker group membership is unchanged; select --grant-docker-access if needed.'
fi
[[ $apply == 1 ]] || { echo 'Plan only. Re-run with --apply to execute.'; exit 0; }
if [[ $fresh == 1 ]]; then
  sudo apt-get -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update
  sudo apt-get install -y --no-upgrade ca-certificates curl
  key=$(mktemp)
  source_file=$(mktemp)
  trap 'rm -f "$key" "$source_file"' EXIT
  curl --fail --silent --show-error --location --connect-timeout 15 --max-time 60 \
    https://download.docker.com/linux/ubuntu/gpg -o "$key"
  sudo install -d -m 0755 /etc/apt/keyrings
  sudo install -m 0644 "$key" /etc/apt/keyrings/fenced-docker.asc
  cat > "$source_file" <<SOURCE
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $suite
Components: stable
Architectures: $arch
Signed-By: /etc/apt/keyrings/fenced-docker.asc
SOURCE
  sudo install -m 0644 "$source_file" /etc/apt/sources.list.d/fenced-docker.sources
  sudo apt-get -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update
  sudo apt-get install -y --no-upgrade docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
fi
if [[ $grant == 1 ]] && ! id -nG "$operator" | tr ' ' '\n' | grep -qx docker; then
  getent group docker >/dev/null || { echo 'Docker group missing; inspect installation.' >&2; exit 1; }
  sudo usermod -aG docker "$operator"
  echo 'Docker access granted. Reconnect with a fresh login before running doctor.'
fi
# Report versions and service health; never restart an existing daemon on re-run.
dpkg-query -W -f='${Package} ${Version}\n' docker-ce docker-ce-cli containerd.io
systemctl is-active --quiet docker || { echo 'Docker is inactive; inspect the service before starting it.' >&2; exit 1; }
echo 'Docker service is active. Enter the Nix host shell and run fenced-doctor.'
