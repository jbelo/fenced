# Go Agent Harness Context

You are running inside a Docker-based local coding harness.

Important paths:

- `/workspace` is the mounted host workspace root.
- `$HOME` is persistent via a Docker volume, usually `/home/agent`.
- `/go/pkg/mod` is a persistent Go module cache volume.
- `/tmp` and `/run` are writable but ephemeral.
- The container root filesystem may be read-only.

Networking:

- Agent containers normally run on `go-agent-internal-net`.
- Outbound internet, when enabled, is routed through `go-agent-egress-proxy:3128`.
- Local harness services may be reachable by Docker DNS names:
  - `go-agent-fdb:4500`
  - `go-agent-kms-gva2:8080`
  - `go-agent-kms-fra1:8080`
  - `go-agent-redpanda:9092`
  - `go-agent-cassandra:9042`
  - `https://xks-proxy.test:19443` (TLS; requires its public CA)

Optional extras:

- The separate `go-agent-java` image adds only Java 25 for host-built Public API uberjars in the shared story checkout. It does not provide Clojure build tools or manage service configuration.
- Use `$HOME/.agents/skills/public-api-run/SKILL.md` to launch and check the prepared Public API JAR inside your container.
- The Public API agent image adds Java 25, Clojure CLI and `public-api-clojure` for host-prepared repo-local `.deps-cache` dependencies. Use the wrapper for those caches; service configuration remains separate. See the installed extras guide.
- FoundationDB provides database storage; KMS uses it for key-management state.
- KMS can run as one or two local zones; Redpanda provides Kafka-compatible messaging.
- The XKS test proxy exposes a TLS/SigV4 endpoint with SoftHSM test keys; its public CA and credentials must be supplied separately. See the installed extras guide for client trust and proxy bypass.
- Use `xks-test-proxy-ssh` for authorized root-shell access to the local XKS test proxy, including its logs. This does not grant Docker or egress-proxy access.
- Cassandra hosts the `idstore` keyspace for identities/API keys and optionally the other Public API schemas. Schema initialization does not seed identities or credentials.
- OpenSSL, FoundationDB, and Redpanda agent image variants add development libraries or client tools; `go-agent-all` includes all three plus the Java 25 runtime, without Clojure build tooling.
- Extras are optional: do not assume a service is running or its schema is initialized. Clients in agent containers use the service's Docker DNS name, not `localhost`.
- Read `$HOME/.go-agent-harness/extras/AGENT.md` for the extras overview and skill names. Detailed client configuration and diagnostics live in `$HOME/.agents/skills/<skill-name>/SKILL.md`.
- These local references do not require access to the fenced repository. They describe defaults, not live service status; host overrides may change addresses.
- Target the service containers with your clients. The developer manages their setup and lifecycle; report missing services, tools, schemas, or credentials. Service data volumes are separate from the agent home volume.

Launchers:

- `story-shell` is the common launcher for story/worktree shells.
- `run-shell` is the lower-level launcher.

Persistence and safety:

- Treat `$HOME`, `/go/pkg/mod`, service databases, and Docker volumes as persistent developer state.
- Do not delete, reset, or reinitialize persistent harness state unless explicitly asked.
- Treat `/workspace` as the only intended mounted project/workspace surface.
