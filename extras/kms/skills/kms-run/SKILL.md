---
name: kms-run
description: Start and diagnose a supplied native KMS binary inside an agent container using prepared root keys, recovery material, and an existing FoundationDB service. Use for requested local process startup, not container or database provisioning.
---

# Run native KMS in an agent container

Use the selected KMS checkout and supplied Linux binary. Resolve its revision,
configuration path, working directory, and required native libraries (including
FoundationDB; `go-agent-all` includes the client). Check existing processes and
ports before starting another instance. Keep Docker lifecycle, database setup,
certificate generation, and key generation with the host; report missing inputs.

## Check configuration and persistent state

- Inspect the selected build's config structs, loader, and help. A config from
  another revision may parse while silently ignoring obsolete fields. Do not
  assume the checkout and supplied binary are the same revision.
- Use supplied root key files and confirm `rootkeysfolder`, `defaultrootkey`,
  and, where supported, `defaultrootkeyversion` select the intended material.
  Check readability without printing keys. Never replace or generate root keys
  to get an existing database to start.
- Require an explicit `foundationdbconfig.rootpath` naming the intended persistent
  database namespace and `foundationdbconfig.clusterfile` visible inside this
  container. Do not fall back to a shared default namespace. Startup may open or
  create database directories and start background jobs; it is not an offline
  validation step. Reuse supplied namespaces only within the requested scope;
  do not clear or reset them.
- Check coordinator addresses inside the cluster file, not just its path. Host
  localhost addresses usually cannot reach the sibling FoundationDB container.
  The installed `foundationdb-connect` skill covers client diagnostics.
- Set listener/metrics ports, zone, and cross-zone endpoints for the actual
  topology. Native KMS and Public API in the same agent container can use
  localhost; sibling services use Docker DNS. Avoid port conflicts. Preserve
  intended proxy bypass and HTTPS verification.

## Recovery compatibility

The current recovery config uses `recovery.recipients_file`, a path to a JSON
organization-to-recipient mapping. An older inline recovery mapping must be
adapted explicitly in an ignored local config, preserving supplied material and
existing files. Confirm the selected build's implementation before converting:

- Age uses organization UUIDs mapped to `age1...` public recipient strings.
- CMS uses organization UUIDs mapped to recipient certificate PEM strings;
  the current implementation validates RSA-4096 recipient certificates. It also
  uses `recovery.cms.signing_cert_file` and `signing_key_file` for supplied export
  signing material. Recipient private keys do not belong in the KMS process.

Do not rename an old mapping to `recipients_file` while retaining a map value,
or reinterpret Age recipients as CMS certificates. Inspect the build's recovery
wiring and loaders. If material is incompatible or missing, report the specific
prerequisite rather than silently disabling recovery. Record any authorized
omission and its effect on recovery testing.

## Optional dependencies

Check tracing exporter and billing/Kafka configuration against the selected
build. Use supplied reachable services, or supported local disable settings
within the requested scope. Report disabled tracing, billing, or other features
and the resulting limits on validation. Turning billing off may not remove
config-level requirements such as `kafkabrokers`; inspect validation separately
from runtime wiring. Never treat an unreachable optional dependency as harmless
without checking whether it prevents startup or causes repeated failures.

## Start and verify when requested

Use the supplied binary's supported config flag (the current CLI uses `-f`),
for example `<binary> -f <local-config>`. Run it in a named tmux window from the
selected checkout, with required environment variables explicitly set in that
process. Record the binary revision, config path, zone, ports, database namespace,
and process/window; omit secret contents. Preserve logs for diagnosis.

Probe the configured `/internal/health` for at most 60 seconds, then inspect logs
and report failure instead of repeatedly restarting. Health alone does not prove
Public API authorization or recovery/billing behavior. For integration readiness,
follow `$HOME/.agents/skills/public-api-run/SKILL.md`: ping, KMS health, then a
signed read-only KMS operation through Public API. Do not create keys just to
test readiness. Stop only the process you started when a stop/restart is requested.
