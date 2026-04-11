# Sandboxed Go Project Agent Environment

This repository provides a Docker-based environment for running the coding agent against Go project workspaces while reducing the agent's access to sensitive data on the host.

The goal is to keep the agent fenced inside a limited project mount instead of running directly on the developer machine, helping reduce the risk of unintended file access, credential disclosure, or accidental modification outside the intended workspace.

## What it includes

- A `Dockerfile` with:
  - Go 1.26.1
  - Node.js 24
  - `@mariozechner/pi-coding-agent`
  - common CLI tools (`git`, `bash`, `vim`, `curl`)
- A `Makefile` for building, installing, and maintaining the environment
- Persistent Docker volumes for:
  - the agent home directory
  - the Go module cache

## Security / isolation model

The coding harness runs inside a container with:

- the project root mounted at `/workspace`
- a read-only container root filesystem
- a writable bind mount for the exposed project workspace at `/workspace`
- writable temporary filesystems for `/tmp` and `/run`
- persistent writable Docker volumes for agent state and Go module cache
- no direct access to unrelated host directories unless they are explicitly mounted

This is intended to limit the coding harness to the repository/workspace area that the developer chooses to expose, while still allowing it to modify files in the mounted story workspace.

## Workspace model

Work is organized per story under:

```text
stories/<story>/
```

Each `STORY_ROOT` can contain:

- story-specific context and notes
- one or more Git worktrees created for that story

The expected workflow is:

1. Create a story workspace under `stories/<story>/`
2. Set up the story context there
3. Create the needed Git worktrees inside that story workspace
4. Launch the container shell in that story workspace
5. Run the coding harness from there

The launcher scripts determine the story workspace to open inside the container. `WORKSPACE_ROOT` selects which host directory is mounted at `/workspace`, `STORY_ROOT` refers to a per-story directory under `stories/<story>/`, and `SUBDIR` selects where inside the mounted workspace the shell starts.

## Why `SUBDIR` matters

The full `WORKSPACE_ROOT` is mounted into the container at `/workspace`, but the shell starts in a chosen subdirectory.

This distinction supports a layout where:

- the mounted `WORKSPACE_ROOT` contains the broader project area
- the active task is performed inside a `STORY_ROOT` at `stories/<story>/...`
- Git worktrees and story context live together inside that story workspace

Example when invoking the low-level launcher directly:

```sh
run-shell --workspace-root /path/to/workspace/root --subdir stories/my-story
```

## Git worktree notes

Git worktrees created inside story workspaces must use relative paths.

This is required so that the worktree metadata resolves correctly both:

- on the host
- and inside the container under `/workspace`

Because the same workspace tree is used in both places, absolute host paths in worktree links will not match the container path layout. Relative links keep the worktrees valid in both environments.

## Persistent volumes

Two Docker volumes are used so data survives across shell invocations:

- `agenthome`: persistent home directory for the coding agent
- `gomodcache`: persistent Go module cache

This allows the environment to be initialized once and then reused across sessions without losing agent state or re-downloading Go dependencies each time.

## Requirements

- Docker or Colima (or another Docker-compatible runtime)
- Make

## One-time setup

Create the persistent volumes:

```sh
make volumes
```

Build the container image:

```sh
make build
```

Initialize ownership/permissions on the writable volumes:

```sh
make init-volumes
```

After this initial setup, the environment can be reused for later sessions.

## Launcher installation

Because this environment repository is separate from the `WORKSPACE_ROOT` that contains `stories/<story>/...`, day-to-day usage happens through installed scripts rather than through `make`.

Install the launcher scripts:

```sh
make install
```

By default this installs standalone copies at:

```text
~/.local/bin/story-shell
~/.local/bin/run-shell
```

Override the install location if needed:

```sh
make install INSTALL_DIR=/custom/bin
```

Make sure the install directory is on your `PATH`.

## Daily usage

From inside a story workspace, run:

```sh
story-shell
```

This launcher:

- infers `WORKSPACE_ROOT` from the path prefix before `stories/` when possible
- computes the relative `SUBDIR`
- invokes the installed `run-shell` helper next to it

The installed scripts do not depend on this repository remaining in the same location after installation.

You can also provide a specific start directory explicitly:

```sh
story-shell /path/to/host/root/stories/<story>/<worktree>
```

Or provide the workspace root yourself:

```sh
story-shell --workspace-root /path/to/workspace/root /path/to/workspace/root/stories/<story>
```

If you prefer to invoke the low-level launcher directly, pass both values explicitly:

```sh
run-shell --workspace-root /path/to/workspace/root --subdir stories/<story>/<worktree>
```

`story-shell` is the convenience wrapper. `run-shell` is the low-level launcher that performs the actual `docker run`.

## Cleanup

Remove the persistent Docker volumes:

```sh
make clean
```
