# Extras overview for agents

Optional services share `go-agent-internal-net` with your agent container.
The developer manages their setup; report missing services, tools, schemas, or
credentials. Defaults below may be overridden and do not imply a running service.
Use Docker DNS for sibling containers; `localhost` is your agent container.

Read the relevant skill at `$HOME/.agents/skills/<skill-name>/SKILL.md`.
These installed files are self-contained; access to the fenced checkout is not needed.

| Extra | Purpose / default endpoint | Skill |
| --- | --- | --- |
| Cassandra | Identities/API keys in `idstore`; `go-agent-cassandra:9042` | `cassandra-connect` |
| FoundationDB | Database storage; use `$HOME/.fdb.cluster`, not just `go-agent-fdb:4500` | `foundationdb-connect` |
| KMS | GVA: `http://go-agent-kms-gva2:8080`; FRA: `http://go-agent-kms-fra1:8080` | `kms-connect` |
| Redpanda | Kafka-compatible broker; `go-agent-redpanda:9092` | `redpanda-connect` |
| XKS test proxy | TLS/SigV4 test keystore; `https://xks-proxy.test:19443`; authorized root SSH | `xks-test-proxy-use` |
| Public API runtime | Host-built JAR running inside your agent container | `public-api-run` |
| Public API tooling | Clojure CLI with host-prepared repo-local dependency caches | `public-api-clojure` |

Image additions are separate from services: OpenSSL adds development libraries,
FoundationDB adds clients, and Redpanda adds `rpk`. `go-agent-java` adds Java 25;
`go-agent-all` combines these tools with the Java runtime, without Clojure tooling.
Check tool availability before assuming it exists.

Service data and the agent home are persistent state. Do not reset them unless
asked. This overview and installed skills are refreshed from repository sources;
keep personal notes elsewhere.
