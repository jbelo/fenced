# Portable host setup

Fenced should provide the same Docker-based agent environment on a Mac or Linux
VM, with reproducible host tools and repeatable setup that preserves existing
work. Nix selects host tools; Docker isolates agents.

This specification guides the portable setup implementation. Baseline readiness
checks and Ubuntu bootstrap are described in [host preparation](README.md).
Profile loading and base initialization are implemented; story-setup is the first
selected host capability. Other extra lifecycle adapters remain planned.
For the development shell, see [Nix host tools](NIX.md).

## Where Fenced runs

| Host | Runtime | Purpose |
| --- | --- | --- |
| macOS/ARM64 | Existing Colima | Preserve the current local workflow |
| Ubuntu 24.04 LTS/ARM64 | Docker Engine in a separate local VM | Test Linux setup and behavior on the Mac |
| Ubuntu 24.04 LTS/AMD64 | Docker Engine in a remote VM | Validate native AMD64 operation |

On either Linux VM, connect over SSH and run Fenced inside the guest. Its
workspace, Git credentials, tmux sessions and Docker storage belong to that VM.
The local test VM must be separate from the existing Colima harness.

Bind mounts require paths available to the Docker daemon. Portable setup must
accept only a local Unix-socket endpoint, reject conflicting Docker context/host
settings, and check host, daemon and image architectures. It must not assume Mac
paths exist on a remote daemon or force AMD64 images on ARM64 hosts.

These are implementation targets, not claims of completed validation. Other
platforms, rootless Docker, VM creation and fleet management are outside this
milestone. ARM64 Linux tests do not replace native AMD64 validation.

## What each part owns

| Part | Responsibilities |
| --- | --- |
| Host operator | OS and Nix installation, Docker access, credentials, migrations and cleanup |
| Nix host shell | Host tools and launchers; no service startup or global tool replacement |
| Fenced host setup | Workspace mounts, images, networks, proxy, persistent volumes and managed context files |
| Host story setup | Git authentication, worktree creation, host tmux windows and request/result receipts |
| Agent harness | Container toolchains, interactive shell/tmux, and work inside explicitly writable paths |
| Extras | Their artifacts, service configuration, lifecycle and usage documentation under `extras/` |

Keep existing launcher defaults, CLI/environment precedence and `make install`
working. Preserve numeric UID/GID handling, relative Git worktree access and the
host story-setup handoff. Keep application `.local/host` and `.local/harness`
settings separate; provisioning must not rewrite either environment.

Agents retain a read-only root filesystem, dropped capabilities,
no-new-privileges, explicit writable mounts and proxy-controlled egress. They
receive neither the Docker socket nor host provider credentials. Credentials,
mutable workspaces and runtime profiles stay outside images and the Nix store.
The Nix shell itself retains the operator's host access.

## Setup inputs

Portable commands take an explicit, nonsecret JSON profile. Version 1 contains:

| Fields | Meaning |
| --- | --- |
| `version`, `platform` | Integer `1`; `macos-arm64`, `ubuntu-24.04-arm64` or `ubuntu-24.04-amd64` |
| `runtime.context` | Docker context resolving to a local socket and matching daemon architecture |
| `workspace.root`, `workspace.writable` | Existing root and explicitly writable subdirectories |
| `image.reference` | Agent image tag or digest; verify architecture and report its resolved ID |
| `state.agenthome`, `state.gomodcache` | Distinct named volumes for persistent agent state and Go modules |
| `network.internal`, `network.upstream` | Distinct internal-only agent and proxy upstream networks |
| `proxy.image`, `proxy.container` | Architecture-matched proxy image and container name; derive its URL using port 3128 |
| `extras` | Unique identifiers of explicitly selected extras |

All fields are required. Resolve a relative workspace root against the profile's
location and writable paths against that root. Canonicalize paths and reject
symlink escapes. Whole-workspace writes require a separate explicit action.

Validate the entire profile before mutation: reject unknown or duplicate fields,
invalid types, unsupported versions/platforms and inconsistent settings. Profiles
are data, never executable shell code. They contain no credentials, arbitrary
Docker arguments or embedded service configuration.

Profile values control the portable commands; do not auto-discover profiles or
merge conflicting environment overrides. Derive UID/GID from the operator.
Pass the chosen image explicitly to meta-shell and require its writable `stories`
directory. Missing images or extras must produce a clear error, not a fallback.
Legacy direct launcher behavior remains unchanged.

## Setup and repeated runs

The setup path has three stages:

1. **Check readiness.** Inspect tools, platform, runtime, images, workspace access,
   resource configuration and storage. Report missing prerequisites with nonzero
   status. Do not pull images, start containers, change files or enroll credentials.
2. **Show the plan.** Identify missing resources, conflicts and required changes
   before applying them. Keep privileged bootstrap and credential enrollment separate.
3. **Apply and record.** Recheck assumptions, create only selected missing resources,
   and record completed steps in a host-side receipt so interrupted work can resume.

Repeated initialization must preserve repositories, credentials, caches, service
data and agent-authored changes. Verify ownership and configuration before reusing
resources; matching names alone do not establish ownership.

Set ownership only on newly created empty volumes. Seed missing managed files;
update an existing file only if its hash matches the last installed version.
Report user-modified files as conflicts. Preserve tmux configuration and installed
home programs, including Pi. Do not restart a running proxy, recreate networks,
rotate credentials or delete existing state during ordinary initialization.
Migrations and destructive cleanup are separate explicit operations.

Reuse Make targets selectively: `init-volumes` recursively changes ownership and
refreshes context; `egress-init` recreates the proxy; `egress-verify` calls
`egress-init`. They cannot serve as read-only checks or unconditional repeat-init
steps. Preserve their legacy behavior while adding portable orchestration.

## Artifacts and validation

Every selected image or binary must be obtainable on a fresh host from documented
inputs, with its architecture, source revision and digest/checksum recorded.
A local image cache is insufficient, even for another ARM64 machine. Gateway
artifacts come through the existing gateway exchange; extra-specific build and
acquisition instructions stay under `extras/`. Private templates require separate
operator enrollment.

Validate the local ARM64 Linux VM first, then the remote AMD64 VM, and retain Mac
regression coverage. Use separate test images, volumes, networks, workspaces and
launcher installation paths. Completion requires evidence that:

- The locked host shell runs natively on all three targets and reports tool paths
  and versions; exiting preserves the caller's environment.
- Fresh setup reaches meta-shell and completes the host Git/tmux handoff.
- Invalid profiles and incompatible resources fail before mutation.
- Allowed writes and proxy traffic succeed; other writes, direct/provider egress,
  host credentials and Docker socket access remain restricted.
- Repeated init and container recreation preserve data, permissions and user edits.
- The existing Mac workflow still works, and cleanup removes only test-owned resources.

Record actual revisions, results and limitations for each platform. Argument
checks, cross-compilation and emulation do not establish native runtime behavior.
