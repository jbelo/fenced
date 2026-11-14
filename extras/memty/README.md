# Memty template access

The standard `run-shell` launcher (also used by `story-shell`) mounts
`~/personal/memty` read-only at `/home/agent/memty` (`$HOME/memty` inside the
standard agent container). No image rebuild or template copy is needed.
The extra owns a launch hook; `make install` installs it alongside the launchers.
Set `MEMTY_ENABLE=0` to disable the mount. If the default source is missing, the
launcher warns and continues. An explicitly supplied invalid `MEMTY_SOURCE` fails.

## Profile-aware launchers

Select the host directory once, outside the container:

```sh
~/fenced/fenced template "$HOME/memty"          # VM
~/fenced/fenced template "$HOME/personal/memty" # Mac: use its actual host path
```

These are alternatives for their respective hosts. The selected path is stored in
`~/.config/fenced/memty.json`, outside profile receipts and Nix. It must contain
readable `AGENTS.md` and `brief/STORY_TEMPLATE.md`. No template contents are copied.
`fenced template` shows the setting; `fenced template --off` disables it for new
sessions. A stale/invalid configured path fails launch rather than silently omitting
the required template. With no setting, profile launches do not mount a template.

New `fenced meta` and `fenced story` sessions mount the selected source read-only at
`/home/agent/memty`, regardless of the host path. Relaunch an existing session to
receive a changed mount. No image rebuild, service restart or profile migration is
needed. This setting applies to profile launches on this host; it does not change
legacy launcher defaults described below. Any previous home-volume template is
hidden by the mount, not deleted. Keep private template content out of Git/Nix.

## Install and use

Install the standard harness launchers and their extra hooks:

```sh
make install
make install-agent-context
story-shell --image go-agent-all --workspace-root /path/to/workspace
```

Override the source per launch if needed:

```sh
MEMTY_SOURCE=/path/to/memty story-shell --workspace-root /path/to/workspace
```

`INSTALL_DIR` defaults to `~/.local/bin`. Source paths with spaces are supported;
commas are rejected because Docker's mount specification uses commas as delimiters.
The source must contain readable `AGENTS.md`; the agent UID must be able to read
the template files. The destination follows the standard harness home path.

## Behavior

The whole selected directory is visible, including hidden files and any Git
metadata. Select a prepared template directory if you want a smaller export.
Host edits appear through the bind mount; there is no separate refresh/sync step.
Start a new session after installing the updated launchers; existing containers do not
gain it. It temporarily hides anything already at `/home/agent/memty` without
deleting it. No template is stored in the agent-home volume, and standard
`story-shell` sessions expose it when available.

Agents should read the template and copy only the needed content into an
authorized writable story directory, preserving existing files. The template
contains project-specific reference material and nested skills; they are not
automatically installed as global agent skills. The read-only mount prevents
container writes to the host template; no worktree helper is included.

Disabling the mount leaves both host template and agent-home data intact.
The optional `memty-shell` compatibility wrapper requires the template and delegates
to `story-shell`; it can be installed with `make -f extras/memty/Makefile memty-install`.

## Missing template, tools, or Git write access

Existing containers created before the launch hook was installed have no Memty
mount. Run `make install` and start a new session; updating the image does not
add mounts to running containers. Current base images include `rsync` for copying templates; rebuild
the base and any derived image, then start a new container to get that tool.

`story-shell` defaults to a read-only workspace with only its selected writable
paths exposed. To create a branch in a sibling repository, explicitly add that
repository (or its actual Git metadata directory) using `--workspace-rw`. To create
a worktree, its destination also needs a writable parent. Explicit writable paths
replace the default START_DIR selection, so include the story directory too:

```sh
story-shell --image go-agent-all --workspace-root /path/to/workspace \
  --workspace-rw kms --workspace-rw stories/my-story \
  /path/to/workspace/stories/my-story
```

These grants permit changes to the selected host repository. They do not fix
host/container path mismatches in Git worktree metadata. Prefer host-side worktree
creation when worktrees must also work on the host; use identical path layouts
before attempting cross-environment worktree management. Do not change filesystem
permissions to work around a read-only Docker mount.
