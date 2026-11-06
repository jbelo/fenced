---
name: kms-connect
description: Configure clients for the local harness KMS zones and diagnose connection or authorization prerequisites, not provision KMS containers.
---

# Connect to KMS

For requested native KMS process startup inside the agent container, use
`$HOME/.agents/skills/kms-run/SKILL.md` instead.

Use the developer's overrides when supplied; these are local harness defaults, not live service status. Report missing services, tools, schemas, or credentials to the developer. Container provisioning and persistent-state cleanup remain host responsibilities.

Default endpoints:

- GVA (`ch-gva-2`): `http://go-agent-kms-gva2:8080`.
- FRA (`de-fra-1`): `http://go-agent-kms-fra1:8080`.

For KMS, choose the HTTP endpoint for the intended zone listed here.
Configure that URL in the calling application. Root keys, service configuration,
and `/etc/kms/` paths belong to the KMS container, not your agent container.
Use the project's client and the developer-provided identity when making API
requests; a reachable HTTP server alone does not confirm application readiness
or authorization. Do not create or modify keys merely to test connectivity.

Use Docker DNS for sibling containers; localhost is your agent container. Bypass the HTTP egress proxy using the client's NO_PROXY configuration or curl's --noproxy '*'. KMS stores its state in FoundationDB, not Cassandra.
