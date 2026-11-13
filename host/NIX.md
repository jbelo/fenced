# Use the Nix host shell

For normal operation, use the checkout launcher described in
[clone-and-setup installation](INSTALL.md): `~/fenced/fenced plan ...`,
`~/fenced/fenced meta`, or `~/fenced/fenced exec story-setup ...`.
It selects this locked environment automatically. Use `~/fenced/fenced shell`
when you want an interactive host shell. The explicit Nix commands below are
also available for development and diagnostics.

Use this shell to develop and run Fenced with a consistent set of host tools.
It provides Bash, Git, tmux, Neovim (`nvim`), Python, rsync, Make, the Docker client,
OpenSSH and shell utilities, together with Fenced launchers and extra-owned host
commands, including the read-only `fenced-doctor`. See [host preparation](README.md)
for readiness checks and Ubuntu bootstrap. Entering the shell does not install or
start the Docker harness.

The targets are macOS/ARM64, Ubuntu 26.04/ARM64 and Ubuntu 26.04/AMD64. Run the
commands below from the Fenced Git checkout on the machine you are using. Nix
must already be installed and its daemon accessible.

## Prepare the checkout

Use the repository's `flake.lock` when present: it selects the package-source
revision shared by all three targets. Do not generate a separate lock per host.

If this is the initial setup and the lock is missing, create it once:

```sh
git add flake.nix
nix --extra-experimental-features 'nix-command flakes' flake lock
git add flake.lock
```

Git-backed Nix requires new source files to be tracked. Keep credentials, runtime
profiles and private workspaces out of tracked source. Do not use `path:.` to
bypass this requirement: it can copy untracked content into the Nix store.
Commit the flake and lock together after validation.

## Enter and leave

```sh
nix --extra-experimental-features 'nix-command flakes' develop --no-update-lock-file .#host
fenced-host-info
nvim
# Return to your previous shell:
exit
```

The shell puts its tools first in `PATH`; it does not replace Homebrew programs
or edit your shell startup files. `exit` returns to the previous environment.
Your editor configuration remains yours. Shell aliases and functions can override
commands; use `type -a git nvim` to inspect their resolution.

This shell has your normal host permissions and credential access. Docker,
Colima and their configuration remain operator-managed. Existing launcher defaults
and hooks still apply; for example, meta-shell expects `go-agent-all`, and
`agent-status vm` requires Colima. Container tools are supplied by the agent image,
not this shell. See [portable host setup](SPEC.md) for the wider setup design.

## Verify on each host

```sh
bash host/check-nix.sh
```

The script evaluates all three targets, builds checks for the current machine,
prints tool versions and paths, checks launcher help, and verifies the caller's
PATH and Git selection are preserved. It needs Nix downloads/builds but no Docker
daemon, and it does not launch agent containers.

Run it natively on the Mac, a separate local Ubuntu ARM64 VM, and the remote
Ubuntu AMD64 VM. For VM testing, obtain the same Fenced sources and lock inside
the guest and run the checks there. Evaluating another platform's outputs is not
a native build or a full harness test.

## Update dependencies

Normal entry refuses lock changes. To deliberately update the package set:

```sh
nix --extra-experimental-features 'nix-command flakes' flake update nixpkgs
bash host/check-nix.sh
```

Review the lock diff and tool versions, then validate on all three targets before
adopting the update. The input branch is `nixos-26.05`; the lock records the exact
revision and content hash. Platform binaries differ even with the same lock.
