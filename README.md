# Fenced, a development-agent harness

Fenced provides coding agents with tools, persistent state, and controlled access
to services within an otherwise isolated container environment. Developers choose
which workspaces, capabilities, and network destinations agents can access.

## What the harness provides

- A Go-oriented base image with development tools and coding-agent CLIs.
- Shell and tmux launchers with selected workspace mounts and persistent home/cache volumes.
- Controlled outbound networking through a destination-allowlisted proxy.
- Installed context and skills explaining the environment and available capabilities.
- [Optional extras](extras/README.md) for additional agent tooling and supporting services.

The harness supplies the execution environment, the coding agent runs inside it, not directly on the developer machine.

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

### Trust boundary

The host and Docker administrator are trusted. Isolation limits access outside
the resources you expose; it does not protect writable workspace files from the
agent or isolate sessions that share the same home volume and credentials.
Reachable development services have their own access controls; sharing an
internal network does not make them safe or mutually isolated. Additional mounts or Docker options can widen the boundary.

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

## Portable host setup

[Portable host setup](host/SPEC.md) describes the planned setup for macOS/ARM64,
a local Ubuntu 24.04/ARM64 VM and remote Ubuntu 24.04/AMD64 VMs. Profile-based
setup is not implemented yet; existing commands below remain unchanged.

[Use the Nix host shell](host/NIX.md) explains how to prepare, enter and verify
the host-tool environment. Initial locking and native validation remain pending.

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
- initialize writable volume ownership, install Pi and harness context, and seed missing tmux configuration in `agenthome`
- create `go-agent-internal-net` and `go-agent-upstream-net`, then start `go-agent-egress-proxy`
- install `story-shell`, `meta-shell`, `run-shell`, and the resource helpers

Build the repo-owned Squid proxy image when needed:

```sh
make egress-proxy-build
```

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

## Resource helpers

`make install` also installs `agent-status` and its helpers into `~/.local/bin`
(or `INSTALL_DIR`). Run it on the host. Each subcommand accepts `--help` to
explain its purpose and output.

```sh
agent-status vm                # Default Colima VM: CPU load, available RAM, disk headroom
agent-status storage           # Docker storage summary
agent-status storage --verbose # Individual images, volumes, containers, and build cache
agent-status containers        # One snapshot of running containers' CPU and memory usage
agent-status containers --live # Continuous updates; Ctrl-C to stop
```

The wrapper invokes `agent-vm-status`, `agent-docker-usage`, and
`agent-container-stats`, which remain available directly. The Docker helpers use
the current Docker context or `DOCKER_HOST`; `agent-status vm` specifically
inspects the default Colima VM. All are read-only.
For memory, use the VM's **available** figure; for disk, check `/var/lib/docker`.
Docker's reclaimable volumes may still contain valuable persistent data.

## Agent SSH client

The base image also supplies an SSH client wrapper that resolves the launcher's
numeric UID through a temporary passwd file. This works with a read-only root
filesystem and does not require a permanent account in the image.

## Agent tmux configuration

`run-shell` and `story-shell` open an `agent` tmux session automatically.
Use `--no-tmux` for plain Bash. Detaching returns to Bash inside the container;
reattach with `tmux attach -t agent`. Exiting that outer shell removes the
ephemeral container and stops its applications. If tmux is unavailable, the
launcher falls back to Bash.

The default agent configuration is versioned in `config/tmux.conf`.
`make init-volumes` copies it to `/home/agent/.tmux.conf` in the `agenthome`
volume only when the destination is missing. Existing files and symlinks are
preserved, so reinitializing volumes does not overwrite your customizations.
The installed file is owned by your host UID/GID.
New tmux sessions and panes start non-login Bash, preserving the container's
toolchain `PATH`. The launcher sets `LANG=C.UTF-8` and `LC_CTYPE=C.UTF-8`
in the container environment, inherited by tmux sessions and panes.

After recreating the agent home volume, run `make init-volumes` to restore it.
To install just the missing tmux configuration, run:

```sh
make install-agent-tmux
```

Changes made inside the agent home are not copied back to the repository;
update `config/tmux.conf` to keep the defaults you want restored in the future.
No image rebuild is needed for this installation step.

When nesting agent tmux inside host tmux, keep `set -s set-clipboard on` in
the **host's** `~/.tmux.conf` so clipboard requests can reach your terminal app.
The agent default also uses `on`, forwarding clipboard requests from applications
and nested tmux sessions as well as its own selections.

## Harness context for agents

`make init-volumes` installs the harness context, bundled references, and skills into the persistent agent home volume:

```text
/home/agent/.go-agent-harness.md
/home/agent/.go-agent-harness/extras/AGENT.md
/home/agent/.agents/skills/<skill-name>/SKILL.md
```

The context and extras overview help agents discover available capabilities;
installed skills provide detailed usage instructions without requiring access to this repository. `extras/agent-docs.list` selects reference files, preserving their directory structure, and `extras/agent-skills.list` selects skills to install.
Host setup instructions, service templates, runtime secrets, and data are not
copied. Refresh replaces the listed files but does not remove older references
or skills; keep personal notes separately.

Refresh the context, references, and skills without reinitializing volumes:

```sh
make install-agent-context
```

In project `AGENTS.md` files, point agents at it with:

```md
# Harness Context

Read `$HOME/.go-agent-harness.md` before making assumptions about local harness-specific paths, services, networks, volumes, launchers, or persistence behavior.

Use it as the source of truth for conventions such as `/workspace`, persistent home/cache volumes, `go-agent-internal-net`, egress proxy behavior, and local service hostnames.
```

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

For workspace-level research and story drafting:

```sh
meta-shell
```

This opens `~/exoscale` at `/workspace` using `go-agent-all`, with `stories`
writable and the rest of the workspace read-only by default. It starts at the
workspace root in the usual `agent` tmux session. Both directories must exist.
Use `--workspace-root PATH` to select another workspace, `--workspace-rw threads`
to add a writable directory, or `--workspace-readwrite` for whole-workspace writes.
`WORKSPACE_ROOT`/`HOST_ROOT`, `AGENT_IMAGE`, and the usual `run-shell` environment
options also apply. The gateway supports research reads; story creation through
the gateway is not supported.

From inside a story workspace:

```sh
story-shell
```

You can also launch a specific directory explicitly:

```sh
story-shell /path/to/host/root/stories/<story>/<worktree>
```

If you need a different agent image, pass it through directly:

```sh
story-shell --image go-agent-fdb
```

For an image with all optional agent extras installed:

```sh
make -f extras/all/Makefile agent-all-build
story-shell --image go-agent-all
```

The low-level launcher supports the same image override:

```sh
run-shell --image go-agent-fdb --workspace-root /path/to/workspace/root --subdir stories/<story>/<worktree>
```

Or invoke the low-level launcher directly:

```sh
run-shell --workspace-root /path/to/workspace/root --subdir stories/<story>/<worktree>
```

By default, `story-shell` mounts the whole workspace read-only and grants write
access to the selected start directory:

```sh
story-shell stories/<story>/<worktree>
```

This mounts the workspace root read-only at `/workspace`, then overlays
`/workspace/stories/<story>/<worktree>` as a read-write bind mount.

Grant write access to additional workspace subdirectories with repeated
`--workspace-rw` options:

```sh
story-shell \
  --workspace-rw stories/<story>/<worktree> \
  --workspace-rw stories/<story>/notes
```

Use `--workspace-readwrite` only when you intentionally want the older behavior where
the whole workspace root is writable:

```sh
story-shell --workspace-readwrite stories/<story>/<worktree>
```

Both launchers default `WORKSPACE_RW_ENABLE` to `false`. Set it to `true` (or `1`)
to make the entire workspace writable, including sibling repositories' Git
metadata:

```sh
WORKSPACE_RW_ENABLE=true story-shell stories/<story>/<worktree>
WORKSPACE_RW_ENABLE=true run-shell --workspace-root /path/to/workspace/root
```

`false` and `0` disable whole-workspace writes. Explicit `--workspace-readonly`
or `--workspace-readwrite` flags override the environment setting. The lower-level
`run-shell` now defaults to read-only too; use `--workspace-rw PATH` for selective
writes. `story-shell` still grants writes to its start directory by default.
This setting does not change the read-only Memty mount or resolve Git worktree
path differences between host and container. Existing containers must be relaunched.

To keep other repositories read-only, leave `WORKSPACE_RW_ENABLE=false` and list
only the writable paths in `WORKSPACE_RW_PATHS` (empty by default):

```sh
WORKSPACE_RW_PATHS=kms:public-api story-shell stories/my-story
WORKSPACE_RW_PATHS=kms run-shell --workspace-root "$HOME/exoscale"
```

Paths are colon-separated, relative to the workspace root or absolute beneath it;
spaces are supported, colons and newlines in path names are not. Paths must already
exist and resolve inside the workspace. The list adds to `--workspace-rw` flags;
`story-shell` also keeps its usual writable start directory when no such flags are
given. Unlisted paths stay read-only unless whole-workspace writes are enabled
(or the workspace root itself is listed). Listing a repository grants writes to
its files and Git metadata.

Pass extra `docker run` arguments with repeated `--docker-arg` options. Each Docker
argument token should be passed separately:

```sh
story-shell \
  --docker-arg -v \
  --docker-arg /host/path:/container/path:ro
```

The lower-level launcher supports the same passthrough:

```sh
run-shell \
  --workspace-root /path/to/workspace/root \
  --subdir stories/<story>/<worktree> \
  --docker-arg --mount \
  --docker-arg type=bind,src=/host/path,target=/container/path,readonly
```

Claude Code can use its default config path under the agent home:

```text
/home/agent/.claude
```

Because `/home/agent` is already backed by the persistent `agenthome` Docker volume,
Claude auth/config files written there survive across agent shells. No extra mount is
needed for that default setup.

If you explicitly want to share the host's Claude config instead, bind-mount it:

```sh
mkdir -p "$HOME/.claude"
story-shell \
  --image go-agent-all \
  --docker-arg --mount \
  --docker-arg type=bind,src="$HOME/.claude",target=/home/agent/.claude
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

The launcher also prepares a user-local npm install path in the writable home volume without replacing the image's existing toolchain `PATH` entries (such as Go):

- `NPM_CONFIG_PREFIX=$HOME/.local`
- `PATH` is prefixed with `$HOME/.local/bin`

The proxy allowlist includes npm registry access so user-local npm installs can work through Squid.

`make init-volumes` installs managed Pi into `$HOME/.pi/agent/install`, using
`make install-agent-pi` (default `PI_VERSION=1.5.2`). Versioned releases use Pi's
published lockfile and `npm ci --ignore-scripts`. `$HOME/.local/bin/pi` selects
the managed launcher. Existing installations are preserved during initialization.

To migrate an existing npm installation, run on the host:

```sh
make migrate-agent-pi
```

This temporary preparation container uses Docker's default network. Migration
validates and smoke-tests the new release before atomically switching the command.
It retains the legacy npm package tree and older managed releases: running agents
are not restarted and their module paths remain available. Settings, sessions,
authentication and extensions are left alone. Do not run concurrent Pi updates
while migrating. Failed downloads leave the existing command selected; unexpected
layouts stop for inspection. A stale `.pi/agent/.fenced-install-lock` after an
interruption must be inspected before retrying.

For migrated npm installs, the old link target is recorded in
`$HOME/.pi/agent/fenced-legacy-pi-target`. To roll back command selection, atomically
replace `$HOME/.local/bin/pi` with a symlink to that recorded target; do not delete
either installation while processes may still use it. This does not roll back
settings changed later by Pi. Never use npm update/uninstall for the retained Pi
package: npm can replace or remove the managed command link.

After migration, update with `pi update`. Updates require `pi.dev` and npm registry
access through the proxy. The home is shared: new invocations in every container
using it select the new version; existing Pi processes stay on their loaded version.
Migration does not rebuild images or restart containers.

New shells use the image's `libnss_wrapper` to resolve an otherwise unknown numeric
UID as `agent-<uid>`, avoiding the “I have no name!” prompt. Identity files are
container-local under `/tmp`; host UID/GID permissions remain unchanged. Existing
containers and tmux servers retain their startup environment.

## Egress proxy operations

Available targets:

- `make networks` (creates `go-agent-internal-net` as internal and `go-agent-upstream-net` as outbound-capable)
- `make egress-proxy-build`
- `make egress-proxy-up`

`make egress-proxy-up` starts the proxy container but does not rebuild the image automatically. Re-run `make egress-proxy-build` when `Dockerfile.squid` changes.
- `make egress-proxy-down`
- `make egress-proxy-logs`
- `make egress-init`
- `make egress-verify`

Current Squid allowlist covers CONNECT access to:

- `*.openai.com`
- `*.chatgpt.com`
- `*.npmjs.org` (including `registry.npmjs.org`)
- `*.anthropic.com`
- `*.claude.com`
- `*.claude.ai`
- `*.sentry.io`
- `proxy.golang.org`, `sum.golang.org`, and `storage.googleapis.com` for public
  Go module downloads, checksum verification, and redirected module ZIPs.
  These are exact hosts. HTTPS CONNECT filtering allows all paths on each host,
  including other buckets on `storage.googleapis.com`.

Go clients can use `GOPROXY=https://proxy.golang.org` and `GOSUMDB=sum.golang.org`
through the shell's existing proxy environment. Direct VCS fallback and private
module hosts still require separate access; checksum verification stays enabled.
After changing `squid.conf`, validate and reload the running proxy with
`docker exec go-agent-egress-proxy squid -k parse` followed by
`docker kill --signal=HUP go-agent-egress-proxy` (reload only; Squid runs as PID 1,
which its `-k reconfigure` command rejects). No agent image rebuild
or shell restart is needed. Run `make egress-go-verify` to check fresh downloads
and checksum verification through the existing proxy.

Validate the setup:

```sh
make egress-verify
```

Tail proxy logs:

```sh
make egress-proxy-logs
```

`make egress-proxy-logs` tails Squid's access and cache logs from inside the running proxy container.

This setup runs Squid as the non-privileged `proxy` user and prepares the required runtime and log directories in the repo-owned proxy image.

The proxy runs from a small repo-owned image defined in `Dockerfile.squid` rather than relying on upstream container entrypoint behavior.

## Optional extras

Extras extend agent images with tools, provide separate service containers, or
install agent guidance. See the [extras overview](extras/README.md) for available
capabilities and their setup instructions. Extra-specific configuration and
documentation stay under `extras/`.

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
