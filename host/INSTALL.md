# Install from a checkout

Use a clean, committed Fenced checkout on the machine running Docker. The checkout
is the installation: keep it for commands, pinned dependencies, image build inputs
and agent references. Your repositories, credentials, profiles and mutable state
live elsewhere. No Nix package installation is required.

## Clone a selected revision

Install Nix first and open a new login shell. On the host:

```sh
git clone https://github.com/jbelo/fenced.git "$HOME/fenced"
git -C "$HOME/fenced" checkout --detach <commit-or-tag>
"$HOME/fenced/fenced" --help
```

Replace `<commit-or-tag>` with the committed revision selected for your installation.
Use your configured Git authentication if the repository requires it. A clean
checkout avoids using uncommitted validation changes as an installation. Do not
copy private runtime files into the checkout. The launcher and these instructions
must be present in the selected revision.

The `fenced` launcher enters this checkout's locked Nix host environment for each
command. It preserves the calling directory and arguments and supplies the checkout
as the harness's source. Nix's initial dependency download may take time. Normal
commands never update flake.lock. If Nix is absent from PATH, the launcher tries
Nix's standard installed shell setup before reporting a missing prerequisite.

Optionally add a convenient command, after checking that the destination is unused:

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$HOME/fenced/fenced" "$HOME/.local/bin/fenced"
```

Ensure `~/.local/bin` is on your PATH, or keep using `~/fenced/fenced` directly.
The launcher resolves its symlink back to the checkout. It does not edit shell
startup files. You do not need to enter `nix develop` manually.

## Prepare the host and workspace

On a fresh Ubuntu 26.04 ARM64/AMD64 VM, follow [host preparation](README.md#prepare-a-fresh-ubuntu-vm)
to install Docker explicitly; reconnect after changing Docker group membership.
On macOS/ARM64, keep the existing Colima installation and choose its local context.

```sh
mkdir -p "$HOME/workspace/stories"
mkdir -p "$HOME/.config/fenced" "$HOME/.local/state/fenced"
chmod 700 "$HOME/.config/fenced" "$HOME/.local/state/fenced"
"$HOME/fenced/fenced" doctor --context default \
  --workspace "$HOME/workspace" --writable stories
```

Clone development repositories as direct children of `~/workspace`, using host Git
authentication. Gateway provider tokens do not authenticate host Git clones or coding
agent logins. The root checkout is read-only to the agent; `stories` contains writable
review/implementation worktrees. Keep Fenced's installation outside this workspace.

## Prepare images and a profile

Images must exist locally before initialization. For a fresh host, start with the
[recorded-input base build](README.md#build-base-images-on-a-fresh-host). Run it through
the launcher, using absolute script/input paths when outside the Fenced checkout:

```sh
"$HOME/fenced/fenced" exec python3 "$HOME/fenced/host/build-images.py" \
  --context default --inputs "$HOME/fenced/host/image-inputs.json" \
  --agent-tag fenced-agent:local --proxy-tag fenced-proxy:local \
  --output "$HOME/.local/state/fenced/base-build"
```

This shows a plan; add `--apply` to build. Output directories and output tags must
be unused. For the combined development image and gateway, follow the
[combined image instructions](../extras/all/README.md#portable-build-from-recorded-inputs) and
[gateway guide](../extras/agent-gateway/README.md). Run their host commands through
`fenced exec`, or use `fenced shell` for a sequence of commands. Existing verified
native images can be referenced by immutable image ID; rebuilding is not required
for every profile. No image is pulled or service replaced by this launcher itself.

## Configure once

For a fresh base/story environment, specify the workspace and desired capabilities:

```sh
~/fenced/fenced configure --workspace "$HOME/workspace" --extra story-setup \
  --image fenced-agent:local --proxy-image fenced-proxy:local
```

Images must already exist. Omit image flags to use the legacy local names
`go-agent-all` and `go-agent-egress-proxy-image`. The default Docker context is the
current context; use `--context` to choose another local one. Configuration detects
the host platform, generates distinct Docker names, and lets Docker allocate the
base internal network subnet. It does not start services or pull images.

Your choices are recorded in `~/.config/fenced/settings.json`; the generated
infrastructure profile and ownership records stay under `~/.local/state/fenced/`.
Do not edit generated state. Reconfiguration of an existing environment remains
an explicit migration: `configure` refuses to overwrite it and changed settings
are rejected rather than silently recreating resources.

Service extras such as the gateway still require their separately enrolled
configuration, policy and credentials. See the [gateway setup guide](../extras/agent-gateway/README.md#host-profile-lifecycle)
for that one-time operator setup; `configure --extra agent-gateway` does not invent
or enroll those settings. Existing `~/.config/fenced/development.json` profiles,
including an enrolled gateway, are used automatically without rewriting their
receipts or moving resources. This supports the already initialized development
VM. The simplified interface does not migrate legacy Mac environments automatically.

## Everyday commands

```sh
~/fenced/fenced plan       # Read-only checks
~/fenced/fenced init       # Initialize and start supporting services
~/fenced/fenced meta       # Open the workspace-level agent container
~/fenced/fenced story "$HOME/workspace/stories/rv-example"
~/fenced/fenced stop       # Stop supporting services; retain data
~/fenced/fenced start      # Restart supporting services
```

`story` defaults to the current directory, which must be below `workspace/stories`.
Only the selected directory is writable in that session; the rest of the workspace
remains read-only. `meta` has the configured writable workspace subdirectories.
Both use the same environment's image, networks, home and cache. Add `--no-tmux`
for a plain container shell. `launch` remains an alias for `meta`.

No manual Nix shell, profile/state arguments or `--apply` is needed for these
commands. `init`, `start` and `stop` already express intent; `plan` never changes
resources. The lower-level `fenced-harness` command retains `--apply` for existing
automation, and the checkout launcher supplies it. Initial configuration never
happens implicitly during a launch. Starting a container does not log in a coding
agent, start a code review or install private templates.

Advanced users can select another environment explicitly:

```sh
~/fenced/fenced meta --profile /path/to/profile.json --state-dir /path/to/state
```

An explicit profile requires its state directory; it never defaults to development
state. The [profile schema](SPEC.md#setup-inputs) remains supported for custom
images, service enrollment and multiple isolated environments. Existing ownership,
conflict, mount and credential checks still apply.

For a review, give meta the Shortcut story and PR references. Select the copied private workspace template once with
`~/fenced/fenced template "$HOME/memty"` (on Mac, use its actual path, such as
`$HOME/personal/memty`). New sessions mount it read-only at `$HOME/memty` in the
container. The requested host tmux session must also exist. Review its generated request and
run the returned host-side command through the launcher:

```sh
~/fenced/fenced exec story-setup apply /absolute/path/to/request.json \
  --workspace-root "$HOME/workspace"
```

Follow the [story-setup guide](../extras/story-setup/README.md) for request review
and handoff. After host setup completes, use `fenced story` at the story directory.
Gateway feedback access does not require a successful full aggregate PR diff;
compute full diffs from the local Git repository when needed.

## Maintain the installation

Keep the selected commit and flake.lock. Do not auto-pull before launches. For an
upgrade, review the new revision and profile compatibility first; changing source
references or service configuration may need an explicit migration. Keep the old
checkout/profile until the new setup is verified. Credentials and agent data stay
outside Git and Nix's store.

For Fenced development or an interactive sequence of host commands:

```sh
"$HOME/fenced/fenced" shell
# Pinned host tools are now on PATH. Leave with:
exit
```
