# Prepare and check a host

Use these commands on the machine that runs Docker: your Mac, or inside an
Ubuntu 26.04 ARM64/AMD64 VM. They prepare/check host prerequisites only. They do
not initialize the agent harness themselves. Profile initialization is described
below; the broader requirements are in [the setup specification](SPEC.md).

## Check readiness

Install Nix and enter the [host shell](NIX.md), then select the Docker context
and workspace explicitly:

```sh
fenced-doctor --context default --workspace /path/to/workspace --writable stories
```

Use your existing Colima context on macOS. The workspace and selected writable
subdirectories must already exist. Add `--image IMAGE` for each locally available
agent/proxy image to verify its architecture and report its immutable image ID.
Use `--json` for structured output. Exit status is nonzero if a check fails.

Doctor checks the host platform, tools, workspace access/free space, Docker
endpoint, daemon architecture and client/server compatibility. It rejects remote
Docker endpoints and conflicting host/context/TLS/API environment overrides before
contacting the daemon. It never pulls an image, runs a container or repairs state.

The default storage threshold is 5 GiB, adjustable with `--min-free-gib`. Workspace
permissions are host-side observations, not proof of container mount behavior.
On Linux, doctor also checks free space at Docker's reported storage path. On a
Mac, inspect the Colima disk separately using `agent-status vm`; Mac filesystem
space does not establish space inside Colima. Image, mount, egress and selected
extra checks remain separate from baseline readiness.

## Prepare a fresh Ubuntu VM

Use an existing Ubuntu 26.04 VM with a normal operator account and sudo access.
Nix installation is separate. First inspect the plan from the Fenced checkout:

```sh
bash host/bootstrap-ubuntu.sh --grant-docker-access
```

To apply that plan:

```sh
bash host/bootstrap-ubuntu.sh --apply --grant-docker-access
```

This installs Docker CE and its CLI, containerd, Buildx and Compose plugins from
[Docker's signed Ubuntu repository](https://docs.docker.com/engine/install/ubuntu/),
then enables/starts the new daemon. Docker manages its own networking/firewall
rules. No custom firewall policy, agent images, networks or volumes are installed.
The optional access flag adds the invoking operator to the Docker group, which
[grants root-equivalent access](https://docs.docker.com/engine/install/linux-postinstall/).
Reconnect with a fresh login before running doctor; existing SSH connections may
retain old group membership.

The adapter preserves an existing Docker CE installation: it does not upgrade
packages, rewrite daemon settings or restart services on repeated runs. Existing
conflicting packages, Docker state without the expected installation, or a partial
installation require operator inspection instead of automatic replacement. A
failed installation may leave apt prerequisites or a repository file; inspect that
state before retrying. There is no automatic rollback or data cleanup.

The daemon version comes from the configured apt repository and is printed after
installation; it is separate from the Nix-locked client. Record the actual package
versions in validation evidence. Package mirrors are operator configuration; this
script does not rewrite Ubuntu's apt sources or disable signature checks.

## Use the existing Mac runtime

Keep your current Colima setup and installed launchers. Enter the Nix shell and
run doctor against its explicit context; no Mac bootstrap changes are automated.
If a prerequisite is missing, install or start it separately. Run Linux bootstrap
inside the disposable VM, never against the existing Mac harness.

## Profile initialization (base harness)

`fenced-harness` provides `validate`, `plan`, `init --apply`, `launch`, and explicit
`start --apply` / `stop --apply` for receipt-owned service containers.
Supply `--profile /path/to/profile.json` using the fields in [SPEC.md](SPEC.md).
For plan, init and launch, also supply `--source /path/to/fenced` and
`--state-dir /path/to/private-state`; the state directory's parent must exist.
Use unique resource names and `extras: []` for the base harness, or
`"extras": ["story-setup"]` to check the host Git/tmux handoff prerequisites.
The `agent-gateway` extra also has a service adapter; see its
[profile lifecycle and enrollment requirements](../extras/agent-gateway/README.md#host-profile-lifecycle).
Other extras are rejected until their profile adapters are implemented.
Agent and proxy images must already exist locally and match the host architecture.
The agent image must provide Node, sh, stat and chown for isolated setup helpers.

Plan inspects resources without creating them. Init records ownership before
creating volumes, networks and the proxy. Retain the private state directory:
its receipt binds the profile, operator, Docker daemon and immutable image IDs.
Configuration changes require explicit migration; existing unowned resources are
never adopted. A completed installation with missing resources requires repair.

Only empty volume roots can receive ownership changes. Managed references update
only when unchanged since installation; user edits cause conflicts. Existing tmux
configuration and unlisted home files remain intact. Initialization does not
install Pi or enroll credentials. Launch selects the profile's image and mounts
through meta-shell, with a controlled environment and no optional template mount.

The base/story-setup path is verified on Ubuntu 26.04 AMD64. Earlier ARM64
evidence used Ubuntu 24.04; 26.04 ARM64 and Mac rechecks are deferred. External
Git authentication and other service extras remain separate validation work.

Selecting story-setup checks host tools and required agent skills before Docker
mutation. Initialization never applies setup requests or creates host tmux sessions.
Review the agent request, then run `story-setup apply REQUEST --workspace-root ROOT`
on the host; create the requested host tmux session first. See the
[story-setup guide](../extras/story-setup/README.md). Changing an existing profile's
extras changes its receipt binding: use a new isolated profile/state/resource set
until an explicit migration workflow is available.

## Build base images on a fresh host

From the Fenced checkout, use a local Docker context and unused output tags:

```sh
python3 host/build-images.py --context default \
  --agent-tag fenced-agent:local --proxy-tag fenced-proxy:local \
  --output "$HOME/fenced-build-evidence"
```

The default shows the plan. Add `--apply` to pull public base images and build
natively with cache disabled. The output directory must be new; existing output
tags are refused. Put the resulting tags in `image.reference` and `proxy.image`
in a new profile. Existing initialized profiles require explicit migration.

Only the two Dockerfiles, SSH wrapper, snapshot setup script, and npm manifest/lock
enter the build context.
The helper records their hashes, the context archive, resolved registry base
digests, output image IDs, package inventories and agent tool versions. Failed
runs retain an incomplete receipt and build log for diagnosis. No push, credential
enrollment, container replacement or cache cleanup is performed.

For a later run, `--go-image` and `--debian-image` can take the digest references
recorded in the receipt. Without an input file, this fixes only the base images; dependency acquisition
otherwise follows the legacy defaults. Use the recorded input file below to
freeze the remaining acquisition inputs. OCI image digests need not be identical
between builds. It builds the base agent and proxy;
gateway/all-image acquisition remains separate extra-owned work.

For the recorded ARM64 input set, add `--inputs host/image-inputs.json`. This
selects immutable base digests and explicit Node/Codex/Claude versions, and records
the input data in the receipt. Git and tmux archives are checked against SHA-256
before extraction. Their checksums were captured from the versioned upstream
HTTPS archives; no upstream release-signature verification is claimed. Overriding
a source version requires supplying its corresponding checksum.

The input file has separate ARM64 and AMD64 entries, including native Node archive
checksums. Missing native entries fail instead of selecting another architecture. This path uses dated Debian snapshots with package signature verification, an
official Node archive with SHA-256 verification, and npm ci with integrity-locked
packages and lifecycle scripts disabled. Claude is linked directly to its
integrity-verified native package; a missing or unusable binary fails the build. It does not execute the NodeSource setup
script. Historical Debian metadata expiry is disabled for the snapshot; signature
verification remains enabled. Upgrading inputs is an explicit reviewed change.
