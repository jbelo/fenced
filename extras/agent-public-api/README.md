# Public API agent tooling

Agent-side usage: [`public-api-clojure` skill](skills/public-api-clojure/SKILL.md), installed by
`make install-agent-context` at `$HOME/.agents/skills/public-api-clojure/SKILL.md`.

Extends `go-agent` with Java 25, Clojure CLI (`clojure`/`clj`), rlwrap, Make,
SSH, OpenSSL, zip and unzip. The base agent tools remain available. This is
a development image, not a Public API service container; it includes no project
source, credentials or application dependencies.

The intended workflow is **prepare dependencies on the host, then use the
repo-local caches inside the agent**. No additional agent egress is required
for dependencies that have been fully prepared.

## Quick start (host)

```sh
make -f extras/agent-public-api/Makefile agent-public-api-build
make -f extras/agent-public-api/Makefile public-api-deps PUBLIC_API_SOURCE=/path/to/public-api
make -f extras/agent-public-api/Makefile public-api-deps-check PUBLIC_API_SOURCE=/path/to/public-api
run-shell --image go-agent-public-api --workspace-root /path/to/public-api
```

The base `go-agent` image must already exist. Preparation requires Java 25,
Git 2.48+, curl, tar, and access to Maven Central, Clojars, `artifacts.exoscale.ch`,
GitHub's private dependencies and `download.clojure.org`. Maven credentials stay
in the host's `~/.m2/settings.xml` (server ID `exoscale`); Git uses the host's
authorized credentials and verified host keys. Nothing copies those credentials
into the checkout or agent home.

## Targets and overrides

| Target | Purpose |
| --- | --- |
| `agent-public-api-build` | Build the tooling image |
| `agent-public-api-check` | Offline, non-root/read-only image smoke test |
| `public-api-deps` | Prepare all three backend profiles below, sequentially |
| `public-api-deps-runtime` | Prepare `-P -M` |
| `public-api-deps-dev` | Prepare `-P -M:test` |
| `public-api-deps-build` | Prepare `-P -M` and `-P -T:project` |
| `public-api-deps-check` | Resolve a selected profile in Linux with networking disabled |
| `public-api-cache-test` | Offline wrapper and Git-worktree relocation regression test |

Preparation uses Clojure `-P`: it downloads dependencies but does not run the
application, tests or build tasks. Failed downloads can be retried incrementally.
Don't run preparation and container resolution concurrently in the same checkout.

Defaults: `PUBLIC_API_SOURCE=branch-public-api` in the harness checkout,
`AGENT_IMAGE=go-agent`, `AGENT_PUBLIC_API_IMAGE=go-agent-public-api`.
`AGENT_IMAGE=go-agent-all` can layer these tools on the combined Bookworm image.
`CLOJURE_IMAGE` overrides the Dockerfile's pinned tooling source. Its paths and
runtime must remain compatible; keep `PUBLIC_API_CLI_VERSION=1.12.6.1673` aligned
with it. Host preparation installs that CLI locally, not into the global system.
The application Clojure version is independently selected by its `deps.edn`.

The dependency check defaults to `PUBLIC_API_MODULE=modules/backend` and
`PUBLIC_API_CLJ_ARGS='-P -M:test'`. Check runtime or build tools by substituting
`'-P -M'` or `'-P -T:project'`. It uses a temporary home, no host credentials,
and a writable checkout for generated caches. Passing proves resolution for
that profile, not full application startup: dynamic tool downloads and Linux
native-library classifiers may need further preparation. Other module/alias
combinations require their own host preparation through the wrapper.

## Repo-local caches

Preparation creates an ignored `.deps-cache/` inside the Public API checkout:

- `m2/`: downloaded Maven artifacts, not `settings.xml`.
- `gitlibs/`: Git repositories and dependency worktrees.
- `tools/`: the isolated host CLI.
- `config/`: generated Clojure configuration, separated by environment and path.

Use `public-api-clojure` instead of plain `clojure` from the intended module
inside the agent. For the application's Makefile, select `CLJ=public-api-clojure`.
The equivalent host invocation is:

```sh
cd /path/to/public-api/modules/backend
PUBLIC_API_CLOJURE=/path/to/public-api/.deps-cache/tools/clojure-1.12.6.1673/bin/clojure \
  bash /path/to/fenced/extras/agent-public-api/bin/public-api-clojure -M:test
```

The wrapper selects `GITLIBS`, `:mvn/local-repo`, and an isolated `CLJ_CONFIG`,
including for nested tools.deps calls. It regenerates classpaths with `-Sforce`
and does not load personal `~/.clojure/deps.edn` aliases. Do not override its
cache settings. Git 2.48+ creates relative worktree links so container mount
paths can differ from host paths; don't seed this cache with old absolute-path
`.gitlibs` worktrees without repairing them first.

Keep the checkout/cache/output paths writable. Repeat preparation after
dependency or alias changes, not ordinary source edits. Rebuilding the image
does not remove caches; no cleanup runs automatically. Keep secrets and tokens
out of the cache and Git URLs, and don't publish cached private dependencies.

## Runtime and agent guidance

Launch a new shell to use a rebuilt image. Its entrypoint supplies a temporary
passwd/group entry via `libnss-wrapper` for arbitrary harness UIDs; retain the
entrypoint and writable `/tmp` and `HOME` provided by the normal launcher.

Public API still needs configured services, schemas, identities and TLS material.
See the [Cassandra setup](../cassandra/README.md) and [agent client guide](../AGENT.md).
The dev profile hardcodes Cassandra localhost and a nil KMS server; configure
those clients before starting the app. Its documented dev listener is port
8040. JVM trust uses a Java truststore, not Go's `SSL_CERT_FILE`.

This extra does not grant internet access or Docker daemon access, run
Testcontainers, or include deployment/remote-access tooling. Missing dependencies
must be prepared on the host, not worked around by changing agent network policy.
`make install-agent-context` refreshes the installed connection/tool guidance;
this host README and setup scripts are not copied into the agent home.

## Layout

`bin/` contains the installed runtime wrapper, `scripts/` contains preparation
and container startup helpers, and `tests/` contains offline checks. The
Dockerfile and Makefile are the build and host-operation entry points.
