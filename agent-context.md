# Go Agent Harness Context

You are running inside a Docker-based local coding harness.

Important paths:

- `/workspace` is the mounted host workspace root.
- `$HOME` is persistent via a Docker volume, usually `/home/agent`.
- `/go/pkg/mod` is a persistent Go module cache volume.
- `/tmp` and `/run` are writable but ephemeral.
- The container root filesystem may be read-only.

Workspace write access:

- `/workspace` is read-only by default. `story-shell` overlays its selected start
  directory read-write; `run-shell` grants no writable workspace paths by default.
- The host can grant additional writable directories with `WORKSPACE_RW_PATHS`
  (colon-separated paths relative to the workspace root, or absolute paths beneath
  it) or repeated `--workspace-rw PATH` options. Explicit CLI paths replace
  `story-shell`'s default start-directory grant; the environment list adds to it.
- `WORKSPACE_RW_ENABLE=true` (or `1`) grants whole-workspace writes; it defaults
  to `false`. Explicit `--workspace-readonly`/`--workspace-readwrite` flags override
  that setting. A read-only root can still have explicitly writable submounts.
- Inspect the actual mount covering each target with
  `findmnt -T /workspace/path -o TARGET,OPTIONS` (or `/proc/self/mountinfo` if
  `findmnt` is unavailable). For a new path, inspect its nearest existing parent.
  Do not infer write access from Unix mode bits, a writable parent mount, or the
  launcher defaults alone. A read-write mount can still have permission limits.
- Git operations may need writes outside the checkout: inspect
  `git rev-parse --path-format=absolute --git-common-dir` and
  `git rev-parse --absolute-git-dir`, then check those paths' mounts too.
  Branch creation needs writable Git metadata; adding a worktree also needs a
  writable destination parent. Host/container path differences in worktree
  metadata are a separate issue that writable mounts do not resolve.
- If a required path is read-only, report its exact path and the blocked operation
  to the developer. Request a new host-launched session with the smallest needed
  grant, for example `WORKSPACE_RW_PATHS=kms story-shell --image go-agent-all`
  from the story directory. Changing these variables inside the container cannot
  alter its mounts. Do not try chmod, sudo, or remounting to bypass the restriction.
- Writable mounts expose real host files; access is not authorization to modify
  unrelated repositories. Keep writes within the user's task. `$HOME/memty`, when
  mounted, remains a read-only template even if the workspace is writable.

Project-local environment profiles:

- Repository documentation should remain generic and use native-host examples. Harness-specific endpoints, proxy/trust settings and credentials come from this context and the installed connection skills, not committed project instructions.
- A checkout may be shared with its native host. Keep host settings under the ignored repository path `.local/host/` and agent settings under `.local/harness/`. Both are visible from the host through the mounted checkout; avoid machine-specific absolute paths in shared profiles when repository-relative paths suffice.
- Before running tests in a repository that provides `.local/harness/env`, change to that repository's root (for example `branch/`) and source that profile in the same shell as the test command. Do not source `.local/host/env`, auto-detect/switch profiles, or overwrite host settings from the agent.
- If the harness profile is missing, report it rather than silently falling back to host settings. Create or update it only within the task's authorization, using supplied overrides and the relevant installed connection skills. Keep credentials and local profiles ignored; never commit or print them.
- Use platform-specific Go temp/cache directories. In the agent, use a writable executable workspace-local `GOTMPDIR` and enable CGO for test runs. Do not mix native-host build artifacts with agent artifacts.
- Test environment profiles and application YAML are different inputs: Go tests generally construct their own fixtures from environment settings; manual application runs must explicitly select the matching runtime YAML, such as `-f .local/harness/config.yaml` when that file has been prepared. Do not rewrite native-host YAML or key paths to container-only paths to run agent tests.

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

- In meta-shell, use `story-implementation-setup` or `story-review-setup` to prepare briefs and host setup requests under `/workspace/stories`. The host performs authenticated Git fetches and worktree creation; wait for a successful result receipt before finishing setup. Template: `$HOME/memty`. Story windows are created by the host helper in `main` (implementation) or `review` (review); the meta shell itself stays in `agent`.

- The agent gateway at `http://agent-gateway:8080` provides live read-only GitHub/Shortcut access, including paginated PR feedback (`agentctl github pr feedback`), for `exoscale/kms` and workspace alias `exoscale`. `go-agent-all` and `go-agent-gateway` include `agentctl` and read-only endpoint configuration via `AGENTCTL_CONFIG`. Read the installed `agent-gateway` skill; the CLI bypasses ambient proxies. Provider credentials and server policy stay outside agents.
- For older running containers, an operator-installed fallback may be available at `$HOME/.local/bin/agentctl`, with binary and endpoint configuration under `$HOME/.local/lib/agent-gateway/`. Invoke that path explicitly if it is not on PATH; the launcher supplies `AGENTCTL_CONFIG`. It uses the image CLI only when it matches the current delivered checksum; otherwise it uses the updated home binary. This shared-home fallback is writable persistent state, not the image-protected installation.

- Verified disposable OpenBao TLS is `https://go-agent-openbao-tls:8443`, with CA `$HOME/.openbao-test/ca.crt` and protected test token file `$HOME/.openbao-test/token`. Bypass the proxy for that hostname and preserve TLS verification. TokenReview helpers in agents use a host-assigned unique internal-network alias and bind `0.0.0.0:18443`; no host port is needed. See `openbao-connect` for callback trust and cleanup ownership.
- OpenBao 2.7.1 provides a local secrets API at `http://go-agent-openbao:8200`; bypass the egress proxy for this hostname. The default extra uses disposable dev mode. The installed `openbao-connect` skill contains its fixed local test token and connection commands; preserve task-supplied credentials for other instances. `go-agent-openbao` and `go-agent-all` include the `bao` CLI.
- The Memty extra exposes a read-only template at `$HOME/memty` in new sessions when the host template is available. Copy needed content into authorized writable story paths; do not edit the template or assume it is present.
- `go-agent-terraform` adds the Terraform 1.11.4 CLI. Providers, modules, backend access, and credentials must be prepared separately; see the installed extras overview.
- Use `$HOME/.agents/skills/terraform-exoscale-run/SKILL.md` for local Exoscale provider testing, isolated CLI configuration, discovery checks, and authorized test runs.
- The separate `go-agent-java` image adds only Java 25 for host-built Public API uberjars in the shared story checkout. It does not provide Clojure build tools or manage service configuration.
- Use `$HOME/.agents/skills/public-api-run/SKILL.md` to launch and check the prepared Public API JAR inside your container, or prepare local runtime configuration when explicitly requested.
- The Public API agent image adds Java 25, Clojure CLI and `public-api-clojure` for host-prepared repo-local `.deps-cache` dependencies. Use the wrapper for those caches; service configuration remains separate. See the installed extras guide.
- FoundationDB provides database storage; KMS uses it for key-management state.
- For explicitly requested native KMS startup inside this container, use `$HOME/.agents/skills/kms-run/SKILL.md` with supplied key material and an explicit persistent database namespace.
- KMS can run as one or two local zones; Redpanda provides Kafka-compatible messaging.
- The XKS test proxy exposes a TLS/SigV4 endpoint with SoftHSM test keys; its public CA and credentials must be supplied separately. See the installed extras guide for client trust and proxy bypass.
- Use `xks-test-proxy-ssh` for authorized root-shell access to the local XKS test proxy, including its logs. This does not grant Docker or egress-proxy access.
- Cassandra hosts the `idstore` keyspace for identities/API keys and optionally the other Public API schemas. Schema initialization does not seed identities or credentials.
- OpenSSL, FoundationDB, and Redpanda agent image variants add development libraries or client tools; `go-agent-all` includes all three plus the Java 25 runtime, Terraform 1.11.4, and OpenBao 2.7.1 CLI, without Clojure build tooling.
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

## Pi installation and shell identity

Pi is persistent shared-home state. The host uses `make migrate-agent-pi` to move
legacy npm installations to managed releases without restarting agents. The command
remains `$HOME/.local/bin/pi`; use `pi update` afterward, never npm update/uninstall
for Pi. Migration retains legacy modules and older releases for running processes.
Do not delete those files or run updates concurrently with host migration.
New shell launches resolve unknown numeric UIDs as `agent-<uid>` through
`libnss_wrapper`; this does not change file ownership or permissions. Existing tmux
servers keep their environment until restarted; a missing username is cosmetic
for the prompt and does not require interrupting a running task.
