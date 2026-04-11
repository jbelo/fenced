# Sandboxed Go Project Agent Environment

This repository provides a Docker-based environment for running the coding agent against Go project workspaces while reducing the agent's access to sensitive data on the host.

The goal is to keep the agent fenced inside a limited project mount instead of running directly on the developer machine, helping reduce the risk of unintended file access, credential disclosure, or accidental modification outside the intended workspace.

## What it includes

- A `Dockerfile` with:
  - Go 1.26.1
  - Node.js 24
  - `@mariozechner/pi-coding-agent`
  - common CLI tools (`git`, `bash`, `vim`, `curl`)
- A `Makefile` for building and launching the environment
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

Each story workspace can contain:

- story-specific context and notes
- one or more Git worktrees created for that story

The expected workflow is:

1. Create a story workspace under `stories/<story>/`
2. Set up the story context there
3. Create the needed Git worktrees inside that story workspace
4. Launch the container shell in that story workspace
5. Run the coding harness from there

The `SUBDIR` make variable is used to start the shell in the desired story workspace.

## Why `SUBDIR` matters

The full host project root is mounted into the container at `/workspace`, but the shell starts in a chosen subdirectory.

This distinction supports a layout where:

- the mounted host root contains the broader project area
- the active task is performed inside `stories/<story>/...`
- Git worktrees and story context live together inside that story workspace

Example:

```sh
make shell SUBDIR=stories/my-story
```

## Git worktree notes

Git worktrees created inside story workspaces should use relative links so that the host-side layout and the container-side layout remain consistent.

Because the same workspace tree is used both:

- on the host
- and inside the container under `/workspace`

relative linking helps ensure the worktrees resolve correctly in both places.

## Persistent volumes

Two Docker volumes are used so data survives across `make shell` invocations:

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

## Daily usage

Open a shell in the default project root:

```sh
make shell
```

Open a shell in a story workspace:

```sh
make shell SUBDIR=stories/<story>
```

Open a shell in a specific worktree inside a story workspace:

```sh
make shell SUBDIR=stories/<story>/<worktree>
```

## Cleanup

Remove the persistent Docker volumes:

```sh
make clean
```
