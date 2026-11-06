---
name: public-api-clojure
description: Use Public API Clojure tooling with host-prepared repo-local dependency caches in an agent container. Use for CLI or development-client configuration, not host builds or provisioning.
---

# Use Public API Clojure tooling

Use the developer's overrides when supplied; these are local harness defaults, not live service status. Report missing services, tools, schemas, or credentials to the developer. Container provisioning and persistent-state cleanup remain host responsibilities.

The optional `go-agent-public-api` image adds Java 25 (JDK), Clojure CLI/tools.deps,
`clj` with `rlwrap`, Make, SSH, OpenSSL, zip and unzip. It retains the base agent
tools. It does not include Public API source, credentials or resolved project
dependencies. Check tools without downloading dependencies with `java -version`,
`javac -version`, and `clojure -Sdescribe`. The project `deps.edn` chooses its
Clojure runtime version independently from the installed CLI version.
The image supplies a temporary user entry for the harness's numeric UID so SSH
and REPL tools can resolve it; no changes to the container's `/etc/passwd` are needed.

Public API's backend module is `modules/backend`; its development dependencies
are in the `:test` alias. For developer-prepared repo-local dependencies, use
`public-api-clojure` instead of plain `clojure` from the intended module. It
selects `<checkout>/.deps-cache/m2` and `<checkout>/.deps-cache/gitlibs`, using
paths appropriate to the container, and regenerates classpath caches. The
developer populates these caches on the host; they contain no provisioned
credentials. They persist in the mounted checkout, not the agent home.
The wrapper uses isolated generated Clojure configuration instead of personal
`~/.clojure/deps.edn`. Git 2.48+ is required for its relocatable worktrees.
Check wrapper configuration with `public-api-clojure -Sdescribe`; this does not
download application dependencies. Cache/output locations must be writable.
Report missing artifacts or aliases to the developer for preparation; don't
copy host classpaths, reset caches, or attempt to bypass network restrictions.

Plain `clojure` still uses its ordinary home caches and does not select the
repo-local Maven cache. If the developer explicitly provides online dependency
access, Maven credentials belong in `.m2/settings.xml` and Git needs its own
authorized access. Do not print credentials or disable SSH host-key checks.

The default egress policy does not permit Maven/Clojars/private artifact downloads.
Java/Maven does not automatically inherit the shell's HTTP proxy configuration;
use developer-provided proxy settings/caches and preserve local-service bypass.
Raw SSH to GitHub is not carried by the HTTPS-only egress proxy. Report missing
dependency access instead of changing network policy. JVM TLS trust is separate
from Go's `SSL_CERT_FILE`; use a developer-provided Java truststore if required.
Tool availability alone does not mean the application or its dependencies are ready.

## Application clients

Public API consumes Cassandra and calls KMS; Cassandra itself does not point
to KMS. KMS uses FoundationDB, not Cassandra, for its own storage.

Public API test profiles accept `CASSANDRA_URL=go-agent-cassandra`. The current
development profile instead hardcodes Cassandra localhost and a nil KMS server;
`CASSANDRA_URL` and `KMS_URL` alone do not override that development profile.
For a development client, the relevant overrides to the loaded configuration are:

```clojure
(-> @dev/config
    (assoc-in [:cassandra :contact-points] ["go-agent-cassandra"])
    (assoc-in [:client :kms :server] "http://go-agent-kms-gva2:8080"))
```

Choose the other KMS endpoint for the other zone. This configures two clients,
not a complete Public API environment: its other schemas, dependencies, and
credentials must also be present. Use the client's existing configuration entry
point to apply these values; inspect the current project if its configuration differs.
