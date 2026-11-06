---
name: xks-test-proxy-use
description: Use the local TLS/SigV4 XKS test proxy, configure client trust, and inspect logs over its authorized root SSH connection.
---

# Use the XKS test proxy

Use the developer's overrides when supplied; these are local harness defaults, not live service status. Report missing services, tools, schemas, or credentials to the developer. Container provisioning and persistent-state cleanup remain host responsibilities.

The local test proxy supports full root SSH access via `xks-test-proxy-ssh`
(requires a current base agent image with numeric-UID SSH support)
(installed in `$HOME/.local/bin`). It uses a dedicated key with host-key checking
disabled for this local development connection
for `xks-proxy.test`. This proxy is an explicitly developer-authorized exception
to the usual external-service access model; stay within the user's task.
Read logs with `xks-test-proxy-ssh 'tail -n 200 /var/log/xks-proxy/xks-proxy.log.*'`.
Hourly log files are inside the proxy container. Root access also reaches
persistent SoftHSM keys; changes to those keys survive container recreation.
Report missing SSH setup to the developer. HTTPS certificate verification is
still required. This access does not grant Docker or egress-proxy access.

This is a test-only HTTPS dependency, not a production HSM. It uses server TLS
and SigV4 authentication, not mutual TLS. The default URI path prefix is
`/example/uri/path/prefix` (full XKS API prefix:
`/example/uri/path/prefix/kms/xks/v1`), key ID `foo`, signing region `ch-gva-2`, and signing
service `kms-xks-proxy`. Use developer-provided signing credentials; do not assume
the proxy or an external keystore in KMS has already been configured.

The public CA is normally provided separately at
`$HOME/.config/xks-test-proxy/ca.pem`. When available, check HTTPS without modifying
keys or data:

```sh
curl --noproxy '*' --cacert "$HOME/.config/xks-test-proxy/ca.pem" \
  --connect-timeout 2 --max-time 5 https://xks-proxy.test:19443/ping
```

`/ping` is unauthenticated and only checks reachability/TLS, not SigV4 or crypto
operations. Report missing CA files, credentials, or certificate errors to the
developer; do not disable certificate verification.

For Go clients using system roots, set `SSL_CERT_FILE` to that public CA before
starting the client. Append `xks-proxy.test` to existing `NO_PROXY` / `no_proxy`
values to bypass the egress proxy. The current KMS test client's external-proxy
settings are `XKS_PROXY_USE_EXTERNAL=true`,
`XKS_PROXY_ENDPOINT=https://xks-proxy.test:19443`, `XKS_PROXY_ACCESS_KEY` and
`XKS_PROXY_SECRET`. Obtain the latter two from the developer; these settings do
not configure other test dependencies. A client with its own explicit CA pool
must include the public CA there instead.

Agent-side trust does not configure sibling KMS services. If KMS itself reports
XKS TLS errors, tell the developer which zone needs its trust configuration
checked. KMS signs with its own zone; FRA therefore needs a matching `de-fra-1`
proxy configuration supplied by the developer, not this GVA default. No private
keys or server settings are part of this guide.
