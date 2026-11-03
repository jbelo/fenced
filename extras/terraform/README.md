# Terraform agent extension

Adds the Terraform 1.11.4 CLI (meeting the >= 1.11 requirement) to `go-agent`
as `/usr/local/bin/terraform`. Linux amd64 and arm64 archives are verified
against pinned [HashiCorp checksums](https://releases.hashicorp.com/terraform/1.11.4/terraform_1.11.4_SHA256SUMS).
Only the binary is copied into the final image; providers are installed per project.

## Build and check

Run on the Docker host from the harness checkout. Build the base first if needed:

```sh
make build
make -f extras/terraform/Makefile agent-terraform-build
make -f extras/terraform/Makefile agent-terraform-check
```

The check runs as the host UID with a read-only filesystem and no network,
prints the version, and initializes and validates a temporary provider-free project.
Rebuild this image after updating its base. To layer Terraform on the combined image:

```sh
make -f extras/terraform/Makefile agent-terraform-build \
  AGENT_IMAGE=go-agent-all AGENT_TERRAFORM_IMAGE=go-agent-all-terraform
```

## Use

The [terraform-exoscale-run skill](skills/terraform-exoscale-run/SKILL.md) covers local Exoscale
provider builds, isolated CLI configuration, Public API/SDK discovery checks,
authorized plans and test runs, and cleanup. Install or refresh it with
`make install-agent-context`; agents read it at
`$HOME/.agents/skills/terraform-exoscale-run/SKILL.md`.
Its `resources.list` also installs the Go discovery probe and its offline tests
under `scripts/`. Run them from the selected provider module with its prepared
dependencies, as documented in the skill. The former `terraform-run` skill is
superseded; refresh does not automatically delete that old installed directory.

```sh
story-shell --image go-agent-terraform
```

Terraform uses the launcher's writable workspace and persistent home. Project
`.terraform` directories, lock files, and local state live in the workspace;
remote state depends on the project's backend. This extra creates no services,
credentials, state volumes, or provider cache, and performs no infrastructure changes.

`terraform init` may need registry, release, module-source, and backend access.
The default harness proxy allowlist does not allow Terraform registry/release
domains. Prepare providers/modules on the host or configure the host-managed
proxy for the endpoints the project needs. Provider APIs and backend credentials
must be supplied separately. Offline formatting works without those prerequisites.

To upgrade Terraform, update the pinned URL and both architecture checksums in
the Dockerfile together, then rebuild and run the check.
