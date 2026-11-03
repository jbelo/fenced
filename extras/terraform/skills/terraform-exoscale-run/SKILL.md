---
name: terraform-exoscale-run
description: Build or select a local Exoscale Terraform provider, isolate Terraform state and environment, verify SDK discovery against a local Public API stack, and run requested test scenarios.
---

# Run Terraform against a local Exoscale stack

Use a private local-state sandbox, not an existing infrastructure configuration.
Keep credentials, state, plans and logs out of Git. Don’t apply, import, destroy
or change dependencies unless requested; a failed apply may still leave changes.
Missing tools, certificates, identities or services are prerequisites to report,
not permission to provision them. Read the harness context for local paths/networking.

## Use the local provider

XKS write-only attributes require Terraform 1.11+ (or a stricter provider requirement).
Build from the provider module root, or reuse a binary with a known revision:

```sh
mkdir -p "$HOME/.cache/terraform-run/go-build" "$HOME/.cache/terraform-run/go-tmp" \
  "$HOME/.local/terraform-run/bin"
GOCACHE="$HOME/.cache/terraform-run/go-build" \
  GOGC=20 GOTMPDIR="$HOME/.cache/terraform-run/go-tmp" \
  go build -p 1 -o "$HOME/.local/terraform-run/bin/terraform-provider-exoscale" .
```

Both GOCACHE and GOTMPDIR must be on executable storage: this harness's noexec
`/tmp/go-build` can prevent cached `go run` binaries from executing even when
GOTMPDIR is elsewhere. Serial compilation/low GOGC limit memory use. For prepared
vendored dependencies, use `-mod=vendor`, `GOTOOLCHAIN=local`, `GOPROXY=off` and
`GOSUMDB=off` to avoid downloads.

Create a case-specific `terraform.rc`; HCL needs literal absolute paths, not `$HOME`:

```hcl
provider_installation {
  dev_overrides {
    "exoscale/exoscale" = "/absolute/path/to/provider-bin"
  }
  direct {}
}
```

The directory must contain `terraform-provider-exoscale`. The development-override
warning is expected. A minimal sandbox `main.tf` is:

```hcl
terraform {
  required_version = ">= 1.11"
  required_providers {
    exoscale = { source = "exoscale/exoscale" }
  }
}
provider "exoscale" {}
```

With this local backend, development override and no modules, schema/validate
work without `terraform init` (verified with 1.11.4). Init may still fetch a registry
provider; use it only if the configuration's modules/backend require initialization.

### Scoped Terraform environment (Bash)

A new directory does not isolate inherited TF_* controls: CLI arguments can select
another state or planning mode, TF_VAR_* supplies inputs, and TF_LOG* can expose
secrets. Run the case in this scope; reintroduce only intended inputs:

```bash
SANDBOX=/absolute/path/to/approved-empty-case
CLI_CONFIG=/absolute/path/to/approved-terraform.rc
(
  set +x
  umask 077
  while IFS= read -r name; do
    case "$name" in
      TF_*) printf 'Clearing inherited control: %s\n' "$name"; unset "$name" || exit 1 ;;
    esac
  done < <(compgen -e)
  cd "$SANDBOX" || exit 1
  export TF_CLI_CONFIG_FILE="$CLI_CONFIG"
  export TF_DATA_DIR="$(mktemp -d "$SANDBOX/.terraform-data.XXXXXX")"
  test -d "$TF_DATA_DIR" || exit 1
  export TF_WORKSPACE=default TF_INPUT=0 TF_IN_AUTOMATION=1
  export CHECKPOINT_DISABLE=1
  printf '%s\n' "$TF_DATA_DIR" > tf-data-dir.txt
  # Reintroduce intended TF_VAR_* inputs without echoing them.
  terraform providers schema -json > provider-schema.json && terraform validate
  # Run the case's plan/apply/cleanup commands here too.
)
```

To resume, clear inherited controls again and reuse the recorded data directory,
CLI config, default workspace and local state. Do not create fresh metadata for
every command, delete state or disable locking to bypass errors.

## Connect to Public API

For KMS, the path is Terraform → provider → **Public API** → KMS → FoundationDB
(and XKS proxy for external-key operations). Public API authenticates against
Cassandra. Do not point Terraform at KMS's internal listener.

Companion skills under `$HOME/.agents/skills/` own service setup and diagnosis:

- `public-api-run/SKILL.md`: host-built JAR, config/TLS, credentials/identity and discovery fixture.
- `kms-run/SKILL.md` / `kms-connect/SKILL.md`: native startup / existing KMS service.
- `cassandra-connect/SKILL.md` / `foundationdb-connect/SKILL.md`: database checks.
- `xks-test-proxy-use/SKILL.md`: proxy credentials, SigV4 zone, path and TLS trust.
- `redpanda-connect/SKILL.md`: Kafka when billing is exercised.

Public API convention: `.local/credentials.env` contains EXO_KEY, EXO_SECRET,
EXO_ORG_ID and ZONE. Inspect assignments before sourcing; parse EDN credentials as
data instead. The file does **not** register the matching Cassandra identity.
Keep API credentials separate from XKS proxy credentials.

After loading the supplied credentials in the test process:

```sh
export EXOSCALE_API_KEY="$EXO_KEY"
export EXOSCALE_API_SECRET="$EXO_SECRET"
export EXOSCALE_API_ENDPOINT=http://127.0.0.1:8040/v2
```

Explicit provider key/secret attributes win. The tested provider's environment
fallback order is:

- Key: EXOSCALE_KEY → EXOSCALE_API_KEY → CLOUDSTACK_KEY → CLOUDSTACK_API_KEY.
- Secret: EXOSCALE_SECRET → EXOSCALE_SECRET_KEY → EXOSCALE_API_SECRET → CLOUDSTACK_SECRET → CLOUDSTACK_SECRET_KEY.

Remove conflicting higher-priority aliases only in the test process. Preserve
local proxy bypass and HTTPS verification.

## Verify discovery and signed routing

Check Public API `/v2/ping` and KMS `/internal/health`, then run the SDK probe below.
Schema loading or a resource-free Terraform plan does not exercise zone discovery.

The tested egoscale SDK initially sends ListZones **unsigned**. It retries signed
only when a successful list lacks the zone—not after HTTP 403. Thus signed Clojure
discovery can pass while Terraform fails with "Invalid key or request signature".
That alone does not mean the supplied credentials are wrong.

Choose the bootstrap endpoint once:

| Mode | EXOSCALE_API_ENDPOINT | Expected real zone API |
|---|---|---|
| Direct local Public API | `http://127.0.0.1:8040/v2` | `http://127.0.0.1:8040/v2` |
| Local discovery fixture | `http://127.0.0.1:18080` (no `/v2`) | `http://127.0.0.1:8040/v2` |

Direct discovery requires the build's prepared anonymous identity/role with
public-discovery-only permission. Host-side seeding is separate; do not grant
anonymous KMS access. Unsigned protected KMS calls must still be rejected.

The fixture setup is in `public-api-run`: loopback-only GET /zone, JSON Content-Type,
and the real API advertised in the response. It supports discovery only. The tested
provider's zone-switching path follows that advertised endpoint for signed calls;
other resource/client paths may not. This fallback does not fix anonymous IAM.
Use only locally backed zones/endpoints; loopback URLs require same-container clients.

### Runnable read-only SDK probe

[scripts/check_discovery.go](scripts/check_discovery.go) uses the selected module's
SDK, asserts the discovered endpoint before a signed ListKmsKeys request, rejects
redirects and bounds requests to 15 seconds. With credentials loaded, the fixture
example is:

```sh
export ZONE=ch-gva-2
export EXOSCALE_API_ENDPOINT=http://127.0.0.1:18080
export EXPECTED_API_ENDPOINT=http://127.0.0.1:8040/v2
SDK_CHECK="$HOME/.agents/skills/terraform-exoscale-run/scripts/check_discovery.go"
# From the provider module root with its prepared vendor tree:
mkdir -p "$HOME/.cache/terraform-run/go-build" "$HOME/.cache/terraform-run/go-tmp"
GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off GOGC=20 \
  GOCACHE="$HOME/.cache/terraform-run/go-build" \
  GOTMPDIR="$HOME/.cache/terraform-run/go-tmp" \
  go run -mod=vendor -p 1 "$SDK_CHECK"
```

Repeat without clearing caches; both runs must pass. Adjust the bootstrap for
direct mode and resolve SDK_CHECK relative to the loaded skill if installed
elsewhere. Without a vendor tree, use an approved prepared module cache or report
the missing prerequisite. Other SDK versions may need an adapted probe.

Offline routing/redirect/endpoint-mismatch tests:

```sh
mkdir -p "$HOME/.cache/terraform-run/go-build" "$HOME/.cache/terraform-run/go-tmp"
GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off GOGC=20 \
  GOCACHE="$HOME/.cache/terraform-run/go-build" \
  GOTMPDIR="$HOME/.cache/terraform-run/go-tmp" \
  go test -mod=vendor -p 1 "$SDK_CHECK" "${SDK_CHECK%.go}_test.go"
```

## Run the scenario

For XKS write-only secrets, use sensitive **ephemeral** input variables and the
secret-version attribute. Sensitive alone does not prevent plan/state persistence.
Within the isolated Terraform scope above:

```sh
terraform validate
terraform plan -input=false -out=case.tfplan
terraform show -json case.tfplan > case-plan.json
# Inspect addresses/actions; apply only the requested action set.
terraform apply -input=false case.tfplan
terraform plan -detailed-exitcode
```

Plan JSON can contain secrets; keep it private. Saved-plan apply has no further
approval prompt, and `-target` is not an isolation boundary. Convergence exit codes:
0 = no changes, 2 = changes, 1 = error.

An auth/discovery failure does not reproduce a create-time validation defect.
For expected failures, check source ordering/API evidence as well as state: empty
state alone does not prove that no remote object was created.

## KMS cleanup and test limits

KMS key deletion is scheduled (minimum seven days in the tested API). Names stay
reserved and referenced stores cannot be deleted until references are actually
gone. Do not shorten the delay or reset FDB for cleanup. Preserve failed-apply state
until remote outcomes are understood; replacement can make old ciphertext unusable.

Before enabling TF_ACC, inspect tests for hardcoded remote zones/proxy defaults and
whether endpoint overrides are honored. Local credentials alone do not make them
local tests. Keep TF_ACC unset/empty for unit-only runs.

For process teardown, use **Stop and clean up owned runtime processes** in
`$HOME/.agents/skills/public-api-run/SKILL.md`: stop/wait, verify listener and metrics
ports down, then remove only owned idle windows. Preserve reused services and
persistent data/state; stopping processes does not authorize resource destruction.

Report the loaded provider revision/binary, sandbox/state, bootstrap versus real
API endpoint, checks/results and cleanup status. Distinguish schema/negative/mock
checks from live routing or full XKS lifecycle coverage.
