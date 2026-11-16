# Fenced — reproducible environments for development agents

Fenced gives developers a consistent set of host tools and a container environment
for coding agents. You choose the workspace, tools, services, and network access
available to the agent.

## Two parts of Fenced

The **host tools**, or outer ring, provide pinned tools through Nix and
manage Docker, configuration, credentials, and Git worktrees. `fenced shell`
opens a shell with those tools and your normal host permissions.

The **agent harness**, or inner ring, runs agents in containers with development
tools, tmux, persistent home directories, and controlled workspace and network
access. `fenced meta` and `fenced story` open agent shells in containers, where
you run your coding agent.

The host prepares the workspace and services, the harness controls what agents
can access.

## From a repository to a story

Suppose you want an agent to review a pull request for a Shortcut story. You start
with a **workspace** on the host: a directory containing your repositories and a
`stories` directory for individual tasks. Each **story workspace** holds the
task's notes and Git worktrees—working copies of the repositories at the revisions
needed for that task.

```text
~/fenced/                         Fenced installation
~/workspace/                      Development workspace
├── kms/                          Repository checkout
└── stories/
    └── my-story/                 Story notes and Git worktrees
```

A Fenced **environment** is the reusable setup in which you run agent sessions.
You configure it once so that each new session gets the same tools, workspace
access, persistent agent home and supporting services without assembling those
pieces again.

For example, your development environment can connect:

- `~/workspace`, exposed to agents at `/workspace`, with rules for which paths they can write;
- an agent **image**, which supplies the operating system and installed tools;
- Docker volumes for the agent's persistent home and Go module cache;
- a Docker network and outbound proxy, plus any configured service extras.

`fenced configure` records these choices. `fenced init` creates the configured
volumes, networks and services. Later, `fenced meta` and `fenced story` create
agent containers that use those resources. Exiting a session leaves the environment
available for the next one, including its workspace files and persistent data.

A **profile** is the configuration describing that setup; the usual configuration
command generates it for you. Fenced also keeps ownership records for the Docker
resources it creates. See [Configure once](host/INSTALL.md#configure-once) for
where these files live and how to set up an environment.

**Supporting services** run alongside agent containers. The outbound proxy
controls Internet access; an optional gateway provides access to GitHub and
Shortcut. Other services, such as a database, can support the code being developed.
**Extras** add these capabilities, along with tools and agent skills that provide
instructions for particular workflows.

You open a **meta session** to work across the workspace and ask the agent to
prepare the review. With the story-setup extra, it creates a request for you to
apply on the host, where Git credentials and worktree operations live. You then
open a **story session** focused on that task's directory. Both sessions use the
same environment's image, home, cache, network and services.
The difference is their workspace access: the meta session can write to configured
subdirectories such as `stories`, while the story session can write only to its
selected story directory. Creating a story does not require a new environment.

Sessions are temporary, but their work persists. Files remain in the host
workspace; agent settings and credentials remain in a **persistent home** stored
in a Docker volume. Supporting services have their own lifecycle, so you can
leave an agent shell and open another while those services keep running.

## Install

Fenced supports macOS on ARM64 and Ubuntu 26.04 on ARM64 or AMD64. It requires
Nix and a local Docker runtime; on macOS, Docker can run through Colima.

Follow the [installation guide](host/INSTALL.md) to clone Fenced into `~/fenced`,
prepare images, and configure your workspace. Keep your development repositories
outside the Fenced checkout. The `fenced` command loads its pinned Nix tools
automatically.

The examples below assume installation and configuration are complete. Use
`~/fenced/fenced` if you have not added `fenced` to your PATH.

## Everyday workflow

Run these commands on the host:

```sh
fenced plan                         # Check the configured environment
fenced init                         # Initialize it and start supporting services
fenced meta                         # Open a workspace-level agent shell
```

Inside the agent shell, start your coding agent. For the review workflow above,
give it the Shortcut story and GitHub PR references, then follow the
[story-setup handoff](extras/story-setup/README.md) to prepare the worktrees.

Once a story workspace exists, open its agent shell from the host:

```sh
fenced story "$HOME/workspace/stories/my-story"
```

Both agent shells use the configured image, services, persistent home, and cache.
They open tmux by default; add `--no-tmux` for a plain shell. Agent installation
and login are separate setup steps.

To work directly on the host with the pinned tools:

```sh
fenced shell
```

Use `fenced stop` to stop supporting services and `fenced start` to restart them.
Stopping services preserves their data.

## Workspace access and storage

The workspace appears at `/workspace` inside agent containers. A meta session can
write to the configured subdirectories, usually `stories`. A story session can
write to its selected story directory. The rest of the workspace stays read-only.
Git worktrees need relative metadata paths so they work on both host and container;
the story-setup helper handles this.

Agent home directories and caches live in Docker volumes and survive shell exits.
Workspace files stay on the host. Configuration, credentials, and runtime state
are kept outside the Fenced checkout. Removing persistent volumes deletes the
agent data they contain.

## Security boundaries

Agent containers have a read-only root filesystem, writable temporary directories,
and access to the workspace paths and volumes you expose. The host and Docker
administrator control these boundaries. Sessions sharing a home volume also
share the state and credentials stored there.

Outbound HTTPS goes through a proxy that allows configured destination domains.
The proxy tunnels TLS without decrypting it. Agent containers use an internal
Docker network with no direct Internet access. Supporting services apply their
own access controls; additional mounts and Docker options can widen access.

## Optional capabilities

[Extras](extras/README.md) add development tools, services, or agent skills. These
include database environments, gateway access to GitHub and Shortcut, and story
workspace setup. Each extra documents its configuration and prerequisites.

## Documentation

- [Installation and configuration](host/INSTALL.md)
- [Host preparation and image builds](host/README.md)
- [Nix host tools](host/NIX.md)
- [Host and profile specification](host/SPEC.md)
- [Harness launcher reference](HARNESS.md): Make setup, mount options, tmux,
  agent context, Pi maintenance, and proxy operations
- [Optional extras](extras/README.md)
