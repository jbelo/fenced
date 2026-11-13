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

Create `~/.config/fenced/development.json` using the [profile fields](SPEC.md#setup-inputs).
Set its workspace root to the absolute path of `~/workspace`, writable paths to
`["stories"]`, and use unique development container/network/volume names. Select
`story-setup` for review setup and `agent-gateway` for provider reads. The latter also
requires its extra-owned service configuration and separately enrolled credentials;
see [gateway profile setup](../extras/agent-gateway/README.md#host-profile-lifecycle).
Do not store secret values in the profile. JSON does not expand `~` or `$HOME`.

Use a new profile and state directory instead of editing an initialized validation
profile. Existing receipts bind their profile and resource identities. Do not reuse
validation container/network/agent-home names in the new profile. An existing
operator-staged credential volume can be referenced according to the gateway guide.

## Set up and launch

Review the plan first:

```sh
"$HOME/fenced/fenced" plan \
  --profile "$HOME/.config/fenced/development.json" \
  --state-dir "$HOME/.local/state/fenced/development"
```

Then initialize with one explicit setup command:

```sh
"$HOME/fenced/fenced" init --apply \
  --profile "$HOME/.config/fenced/development.json" \
  --state-dir "$HOME/.local/state/fenced/development"
```

Launch from any host directory:

```sh
"$HOME/fenced/fenced" launch \
  --profile "$HOME/.config/fenced/development.json" \
  --state-dir "$HOME/.local/state/fenced/development"
```

No manual Nix shell or `--source` argument is needed. Initialization retains its
existing ownership/conflict checks; this entry point does not migrate old profiles.
To stop/start receipt-owned services, replace `launch` with `stop --apply` or
`start --apply`. Closing an agent session is separate from stopping services.

For a review, provide the agent with the Shortcut story and PR references. Review
its generated request and run the returned host-side command through the launcher:

```sh
"$HOME/fenced/fenced" exec story-setup apply /absolute/path/to/request.json \
  --workspace-root "$HOME/workspace"
```

The requested host tmux session must already exist. Host Git credentials and any
private templates are separately enrolled prerequisites. Follow the
[story-setup guide](../extras/story-setup/README.md) for request review and handoff.
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
