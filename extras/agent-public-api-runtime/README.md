# Public API runtime agent extension

Adds only a Java 25 JRE to `go-agent`, for host-built Public API applications.
Build the Public API uberjar on the host,
then run it from the shared story checkout inside an agent container. No Clojure
CLI, credentials or application files are added to the image. This extra extends
the base `go-agent` image directly and uses the host's build tools.

Follow the [local host setup guide](SETUP.md) to set local test credentials,
prepare Cassandra and certificates, build, and run.

This extra owns `cassandra-init-idstore` and `cassandra-init-public-api`, which
apply schemas from `PUBLIC_API_SOURCE` to an existing Cassandra container.
The Cassandra extra itself only manages the database lifecycle and readiness.

`make install-agent-context` installs the [public-api-run skill](skills/public-api-run/SKILL.md)
at `$HOME/.agents/skills/public-api-run/SKILL.md` in the agent home. The agent can
use it to launch the prepared JAR, keep output in tmux, and check the HTTP listener.
When explicitly requested, it can also prepare ignored local runtime configuration
from the selected checkout, preserving existing files. Certificates, schemas,
identity data, and service provisioning remain host responsibilities.
The skill includes an offline JAR-based configuration/spec check, layered KMS
readiness, discovery routing diagnostics, and a link to the native `kms-run`
companion. Spec checks do not establish certificate validity or live connectivity.
It also includes the developer-verified, source-free one-zone discovery recipe:
a loopback-only fixture backend, explicit compute routing, signed acceptance
checks, and rollback. This requires a requested disposable test-double setup;
it does not authorize identity provisioning or certificate generation.
Readiness checks distinguish optional-auth zone discovery from protected KMS
operations and verify the actual SDK/CLI bootstrap path. The skill describes
anonymous-role prerequisites and the explicitly scoped fixture-bootstrap option;
successful signed probes alone do not establish SDK readiness.

## Build and verify on the host

```sh
make -f extras/agent-public-api-runtime/Makefile agent-java-build
make -f extras/agent-public-api-runtime/Makefile public-api-build PUBLIC_API_SOURCE=/path/to/story/repo-x
make -f extras/agent-public-api-runtime/Makefile public-api-jar-check PUBLIC_API_SOURCE=/path/to/story/repo-x
```

The host needs Java 25, Clojure CLI, and the project's normal Maven/Git access.
`public-api-build` delegates to the repository's `make build`, using the host's
normal Maven/Git caches. The expected output is
`modules/backend/target/public-api.jar`.

`agent-java-check` checks Java alone. `public-api-jar-check` runs
the actual JAR's `--help` entry point in Linux with a numeric UID, read-only root,
no network and no credentials. It checks startup/class loading, not HTTP service
readiness or every optional native-library path. If a native dependency is
host-specific, build with Linux artifacts or use a host-managed Linux builder.

Overrides: `AGENT_IMAGE` selects another compatible base agent,
`AGENT_JAVA_IMAGE` changes the output tag, `JAVA_IMAGE` overrides
the pinned Temurin JRE source, and `PUBLIC_API_JAR` selects another artifact.
Default source: the harness's `branch-public-api` checkout. Existing containers
are not replaced.

## Run in an agent shell

Launch the usual shared story folder with `--image go-agent-java`.
For example:

```sh
run-shell --image go-agent-java --workspace-root /path/to/story
```

Inside the shell, after supplying a suitable runtime configuration:

```sh
cd /workspace/repo-x/modules/backend
java -jar target/public-api.jar --file /path/in/container/config.edn --profile dev
```

The configuration and paths must be valid **inside** the container. Configure
Cassandra/KMS clients using their container DNS names; do not reuse host localhost
addresses. Supply schemas, credentials and TLS material separately. JVM trust
uses a Java truststore. See the [agent guide](../AGENT.md) for service addresses.
The dev profile's default configuration is not a complete local harness setup.

Rebuild on the host and restart the Java process after code changes. Stop the
process before replacing its JAR; do not overwrite a live application's artifact.
The JAR persists in the shared checkout. No extra volume, dependency download
access, Docker socket or automatic service lifecycle is required by this extra.
Runtime calls to external services still require an explicitly permitted route.

`make install-agent-context` refreshes the runtime image awareness in agent home.
Host build/provisioning instructions stay in this README and `SETUP.md`.
