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
  - `go-agent-redpanda:9092`

Launchers:

- `story-shell` is the common launcher for story/worktree shells.
- `run-shell` is the lower-level launcher.

Persistence and safety:

- Treat `$HOME`, `/go/pkg/mod`, service databases, and Docker volumes as persistent developer state.
- Do not delete, reset, or reinitialize persistent harness state unless explicitly asked.
- Treat `/workspace` as the only intended mounted project/workspace surface.
