# Sandboxed Go Project Agent Environment

This repository provides a Docker-based environment for running a coding agent against Go project workspaces with two goals:

- **internal containment**: limit what the agent can read and write from the host
- **external egress control**: route outbound Internet access through a controlled proxy

It currently targets [Pi](https://pi.dev/) and is also customized for OpenAI / Codex CLI model access, but the overall harness shape should be easy to adapt to other coding-agent CLIs and model backends.

The agent does not run directly on the developer machine. Instead, it runs inside a constrained container with a limited workspace mount and proxy-mediated network access.

## Security model

This setup has two distinct security aspects.

### Internal isolation

The agent session runs in a container with:

- the chosen workspace mounted at `/workspace`
- a read-only container root filesystem
- writable temporary filesystems for `/tmp` and `/run`
- persistent writable Docker volumes for agent state and Go module cache
- no access to unrelated host directories unless explicitly mounted

This is intended to reduce the risk of unintended file access, credential disclosure, or accidental modification outside the workspace you choose to expose.

### External egress control

Outbound HTTPS is routed through a Squid CONNECT proxy.

- the agent session container joins the internal-only network `go-agent-internal-net`
- the proxy container runs as `go-agent-egress-proxy`
- the proxy is attached to two networks:
  - `go-agent-internal-net` for agent-to-proxy traffic
  - `go-agent-upstream-net` for outbound Internet access
- proxy URL inside the internal network is `http://go-agent-egress-proxy:3128`
- Squid allowlists approved destination domains
- TLS is tunneled with CONNECT; the proxy does **not** terminate TLS

Because the agent session is attached only to the internal network, it has no direct Internet access. Approved outbound access is available only through the proxy.

## Container / network topology

```text
Host
├─ mounted workspace root
├─ Docker volume: agenthome
├─ Docker volume: gomodcache
├─ Docker network: go-agent-internal-net (internal)
│  ├─ go-agent session container (ephemeral, started by run-shell)
│  │  ├─ /workspace -> selected host workspace root
│  │  ├─ /home/agent -> agenthome volume
│  │  └─ outbound HTTPS -> http://go-agent-egress-proxy:3128
│  └─ go-agent-egress-proxy
└─ Docker network: go-agent-upstream-net
   └─ go-agent-egress-proxy
      └─ CONNECT tunnels to approved Internet destinations
```

## Workspace model

Work is organized per story under:

```text
stories/<story>/
```

Each story workspace can contain:

- story-specific context and notes
- one or more Git worktrees created for that story

Typical workflow:

1. Create a story workspace under `stories/<story>/`
2. Add story context there
3. Create any needed Git worktrees inside that story workspace
4. Launch the container shell in that story workspace
5. Run the coding agent from there

`WORKSPACE_ROOT` is the host directory mounted at `/workspace`, and `SUBDIR` selects where inside `/workspace` the shell starts.

Example:

```sh
run-shell --workspace-root /path/to/workspace/root --subdir stories/my-story
```

## Git worktree note

Git worktrees created inside story workspaces must use relative paths.

That keeps the worktree metadata valid both:

- on the host
- inside the container under `/workspace`

## Requirements

- Docker or Colima (or another Docker-compatible runtime)
- Make

## Setup

One-time bootstrap:

```sh
make volumes
make build
make init-volumes
make egress-init
make install
```

This will:

- create persistent Docker volumes
- build the `go-agent` image
- initialize writable volume ownership
- create `go-agent-internal-net` and `go-agent-upstream-net`, then start `go-agent-egress-proxy`
- install `story-shell` and `run-shell`

By default the launchers are installed to:

```text
~/.local/bin/story-shell
~/.local/bin/run-shell
```

Override if needed:

```sh
make install INSTALL_DIR=/custom/bin
```

Make sure the install directory is on your `PATH`.

## Authentication note

If `/login` inside the container is awkward or unreliable, a practical workaround is to reuse an existing `auth.json` created by Codex CLI on the host.

Typical approach:

1. authenticate once on the host with the CLI that already works for you
2. locate the generated `auth.json` on the host
3. copy it into the persistent agent home volume so it appears in the container under the agent user's home directory

For example, if you already have a working Codex CLI credential on the host, the typical source location is:

```text
~/.codex/auth.json
```

Copy that host-side credential file into Pi's config directory inside the container home:

```text
$HOME/.pi/agent/auth.json
```

Because `/home/agent` is backed by the persistent `agenthome` Docker volume, credentials placed there survive across shell sessions.

Use this carefully:

- treat `auth.json` as a secret
- do not commit it into the workspace or repository
- prefer copying it into the agent home volume rather than into `/workspace`
- ensure file permissions are restricted to the agent user where possible

Depending on the specific agent CLI, the expected auth path may differ, but the same pattern applies: place the working host-generated auth material into the persistent container home instead of relying on interactive login inside the container.

## Usage

From inside a story workspace:

```sh
story-shell
```

You can also launch a specific directory explicitly:

```sh
story-shell /path/to/host/root/stories/<story>/<worktree>
```

Or invoke the low-level launcher directly:

```sh
run-shell --workspace-root /path/to/workspace/root --subdir stories/<story>/<worktree>
```

By default, `run-shell`:

- joins the internal network `go-agent-internal-net`
- sets proxy environment variables for the session
- expects `go-agent-egress-proxy` to be running

If the networks or proxy are not running yet:

```sh
make networks
make egress-init
```

If you explicitly want a shell without the proxy:

```sh
run-shell --no-egress-proxy --workspace-root /path/to/workspace/root --subdir stories/<story>/<worktree>
```

The launcher also prepares a user-local npm install path in the writable home volume:

- `NPM_CONFIG_PREFIX=$HOME/.local`
- `PATH` is prefixed with `$HOME/.local/bin`

This lets you override the image-baked Pi install without rebuilding the image:

```sh
npm install -g @mariozechner/pi-coding-agent@latest
which pi
```

The user-local install in `$HOME/.local/bin` will take precedence over the image-installed binary.

## Egress proxy operations

Available targets:

- `make networks` (creates `go-agent-internal-net` as internal and `go-agent-upstream-net` as outbound-capable)
- `make egress-proxy-up`
- `make egress-proxy-down`
- `make egress-proxy-logs`
- `make egress-init`
- `make egress-verify`

Current Squid allowlist covers CONNECT access to:

- `*.openai.com`
- `*.chatgpt.com`

Validate the setup:

```sh
make egress-verify
```

Tail proxy logs:

```sh
make egress-proxy-logs
```

## Task tracking

Tracked implementation work lives under `tasks/`.

Current task:

- `tasks/go-agent-egress-proxy/task.md`
- `tasks/go-agent-egress-proxy/progress.md`

## Cleanup

Remove persistent Docker volumes:

```sh
make clean
```
