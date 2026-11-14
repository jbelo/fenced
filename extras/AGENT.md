# Extras overview for agents

Optional services share `go-agent-internal-net` with your agent container.
The developer manages their setup; report missing services, tools, schemas, or
credentials. Defaults below may be overridden and do not imply a running service.
Use Docker DNS for sibling containers; `localhost` is your agent container.

Read the relevant skill at `$HOME/.agents/skills/<skill-name>/SKILL.md`.
These installed files are self-contained; access to the fenced checkout is not needed.

| Extra | Purpose / default endpoint | Skill |
| --- | --- | --- |
| Story setup | Prepare story briefs and JSON requests under `/workspace/stories`; await host Git and tmux setup receipts | `story-implementation-setup`, `story-review-setup` |
| Agent gateway | Live GitHub/Shortcut reads including PR feedback (`exoscale/kms`, workspace `exoscale`); `http://agent-gateway:8080`; `agentctl` in gateway/all images | `agent-gateway` |
| Cassandra | Identities/API keys in `idstore`; `go-agent-cassandra:9042` | `cassandra-connect` |
| OpenBao | Disposable secrets API: HTTP `go-agent-openbao:8200`; separate verified TLS `go-agent-openbao-tls:8443`, CA/token in `$HOME/.openbao-test/` | `openbao-connect` |
| FoundationDB | Database storage; use `$HOME/.fdb.cluster`, not just `go-agent-fdb:4500` | `foundationdb-connect` |
| KMS | GVA: `http://go-agent-kms-gva2:8080`; FRA: `http://go-agent-kms-fra1:8080` | `kms-connect` |
| Native KMS | Requested process startup with supplied binary/material and explicit FDB namespace | `kms-run` |
| Terraform | Local provider testing, SDK discovery, authorized plans and test runs | `terraform-exoscale-run` |
| Redpanda | Kafka-compatible broker; `go-agent-redpanda:9092` | `redpanda-connect` |
| XKS test proxy | TLS/SigV4 test keystore; `https://xks-proxy.test:19443`; authorized root SSH | `xks-test-proxy-use` |
| Public API runtime | Run a host-built JAR; prepare local config when explicitly requested | `public-api-run` |
| Public API tooling | Clojure CLI with host-prepared repo-local dependency caches | `public-api-clojure` |

Image additions are separate from services: OpenSSL adds development libraries,
FoundationDB adds clients, and Redpanda adds `rpk`. `go-agent-java` adds Java 25;
`go-agent-all` combines these tools with the Java runtime, Terraform 1.11.4, and OpenBao 2.7.1 `bao`, without Clojure tooling.
Check tool availability before assuming it exists.
When configured by the operator, profile-aware launchers mount the host Memty template; `$HOME/memty` is a read-only host template.
Read its guidance and copy only needed template content into an authorized
writable story directory, preserving existing files. It contains project-specific
references and skills, not just empty templates. Report a missing mount to the
developer; it is optional and its nested skills are not installed globally.
`go-agent-terraform` adds Terraform 1.11.4 (`terraform version`). Providers,
modules, backend access, and credentials are project-specific prerequisites;
the default egress proxy does not allow Terraform registry/release downloads.
Report missing prerequisites to the developer.

Service data and the agent home are persistent state. Do not reset them unless
asked. This overview and installed skills are refreshed from repository sources;
keep personal notes elsewhere.

With a host-managed gateway profile, `agent-gateway:8080` is the profile-local
endpoint. A running agent session may outlive a stopped gateway; report
unavailability to the host operator. Provider credentials and policy remain
outside the agent. Readiness does not establish provider authentication.

Story setup sessions expose `FENCED_HOST_WORKSPACE` and, for profile launches,
`FENCED_HOST_CHECKOUT` as host-path metadata for exact host handoff commands.
These paths do not grant host access; follow the installed story setup skill.
