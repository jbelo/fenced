#!/usr/bin/env bash
# Create an isolated development CA and TLS certificate, without changing host trust.
set -euo pipefail
tls_dir=${1:?TLS directory required}
hostname=${2:?DNS hostname required}
mkdir -p "$tls_dir"
for file in ca.pem server.pem server-key.pem; do
    if [[ -e "$tls_dir/$file" ]]; then
        for required in ca.pem server.pem server-key.pem; do
            [[ -s "$tls_dir/$required" ]] || {
                echo "Incomplete TLS material in $tls_dir; refusing to overwrite it." >&2
                exit 1
            }
        done
        echo "Using existing TLS material in $tls_dir (no certificate rotation)."
        exit 0
    fi
done
command -v mkcert >/dev/null || { echo 'mkcert is required for xks-test-proxy-tls.' >&2; exit 1; }
umask 077
export CAROOT="$tls_dir/ca"
mkdir -p "$CAROOT"
mkcert -cert-file "$tls_dir/server.pem" -key-file "$tls_dir/server-key.pem" "$hostname"
cp "$CAROOT/rootCA.pem" "$tls_dir/ca.pem"
chmod 644 "$tls_dir/ca.pem" "$tls_dir/server.pem"
