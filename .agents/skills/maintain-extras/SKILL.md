---
name: maintain-extras
description: Add or change fenced extras and keep their documentation, agent context, and installed agent-home references synchronized. Use when introducing, modifying, or removing an extra, or maintaining its agent-facing reference bundle.
---

# Maintain extras and agent references

Agents inside this harness cannot access the fenced checkout. Keep the necessary
connection and usage information in the context and reference files installed
in their home. Paths below are relative to the repository root unless noted.

## Placement

- Keep extra-specific scripts, Makefiles, configuration, and detailed docs under
  `extras/<name>/`. Keep top-level installation plumbing generic. The brief
  overview and endpoints in `agent-context.md` are the discovery exception.
- Inspect the affected extra and its client/source configuration before choosing
  versions, schemas, addresses, or environment variables. Distinguish agent-image
  client tools from independently running service containers.

## Keep these files synchronized

Whenever an extra is added or its behavior changes, review and update the
affected entries in all of the following:

| File | Purpose |
| --- | --- |
| `extras/<name>/README.md` | Prerequisites, lifecycle commands, defaults/overrides, connections, initialization, persistence |
| `extras/README.md` | Discoverable link and short description |
| `extras/AGENT.md` | Brief overview, default endpoints, and installed skill names |
| `agent-context.md` | Brief awareness, relevant default endpoints, and pointers to installed references |
| `extras/agent-docs.list` | Explicit paths relative to `extras/` for agent-facing usage guides only |
| `extras/agent-skills.list` | Skill directories whose `SKILL.md` is installed in the agent home |

Agents read the installed copies at:

```text
$HOME/.go-agent-harness.md
$HOME/.go-agent-harness/extras/AGENT.md
```

Agents only target existing service containers. Their installed guides must
contain connection details, client configuration, available client tools, and
read-only diagnostics. Tell agents to report missing services, tools, schemas,
or credentials to the developer. Do not include image builds, provisioning,
service startup/shutdown, schema initialization, cleanup commands, or server
configuration templates in the agent bundle, even labeled as host-only.

Keep that operational material in the repository's host-facing READMEs. Do not
copy those READMEs wholesale or link agents to uninstalled host documents. Keep
`extras/AGENT.md` as a discovery overview. Put detailed agent usage in
`extras/<extra>/skills/<skill-name>/SKILL.md` and register the directory in
`extras/agent-skills.list`. Each skill must be self-contained: the installer
copies its `SKILL.md` to `$HOME/.agents/skills/<skill-name>/SKILL.md` and any
supporting files explicitly listed in that skill's `resources.list` (one relative
file path per line). Preserve those relative paths inside the installed skill.
List only intentional regular files; no secrets, symlinks, or entire directories.
Simple image additions need only an overview entry, not a separate skill.

Only add intentional, regular reference files within `extras/` to the manifest.
Never copy entire directories, runtime `.local` state, secrets, credentials,
private keys, or database files into the documentation bundle.

## Relevant operational guidance

- Default endpoints are not live availability checks. Agent clients use sibling
  containers' Docker DNS names; `localhost` addresses the agent container itself.
- Document actual client configuration, including profile-specific environment
  handling and HTTP proxy bypass where needed.
- Explain schema creation, migrations, data seeding, and repeatability in host
  documentation. Agent guidance only states the required schema/data and how to
  recognize and report missing prerequisites.
- Separate service data volumes from agent-home state. Document shutdown and
  destructive cleanup only in the host-facing reference.
- Lifecycle Make targets run on the host from the fenced checkout. Agents
  normally lack Docker daemon access. Documentation changes alone do not
  authorize starting or reconfiguring existing services.

## Verify and refresh

Check manifest entries exist and required relative links resolve within the
installed bundle. Run `git diff --check` and validation appropriate to the
change. For new persistent database extras, verify readiness, initialization
failures, repeat initialization where supported, network access, and persistence
across container recreation with isolated test resources. Documentation-only
changes need no service deployment or image rebuild.

After modifying bundled references, refresh the configured agent home when
Docker is available and the task permits updating it:

```sh
make install-agent-context
```

`make init-volumes` also invokes this target. The generated copies are replaced
on refresh; edit repository sources, not installed copies. Verify the installed
files match their sources and are readable by the agent UID. If installation
cannot run, report that only sources were updated and give the refresh command.

When removing or renaming references or skills, update the active manifests.
Refresh does not remove older installed files; report any manual cleanup needed
for existing homes. Do not maintain historical retirement manifests.
Scan the active bundle for accidentally included host setup commands. Report
the changes, validation, and whether installed context was refreshed.
