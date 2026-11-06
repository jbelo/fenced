# Local Public API setup

Build on the host; run in the agent container. Host prerequisites: Java 25 JDK,
Clojure CLI, Git, Make, OpenSSL, and configured Maven/Git dependency access.

## 1. Prepare Cassandra

From fenced, using the **host path** to your checkout:

```sh
export PUBLIC_API_SOURCE=/path/to/story/public-api
make -f extras/cassandra/Makefile cassandra-up
make -f extras/agent-public-api-runtime/Makefile cassandra-init-public-api \
  PUBLIC_API_SOURCE="$PUBLIC_API_SOURCE"
```

Schema initialization creates missing objects and preserves existing data;
schema changes require separate migrations.

## 2. Use supplied credentials and seed only when authorized

Identity/database provisioning is a separate host-side action, not a consequence
of copying credentials or launching Public API. Use the developer-supplied
`EXO_KEY`, `EXO_SECRET`, `EXO_ORG_ID`, and `ZONE`; do not generate replacement keys.
Read `.local/credentials.env` only after inspecting its assignment-only shell
format. Parse supplied EDN as data and document its actual field mapping instead
of sourcing it. Keep generated runtime files under `<checkout>/.local/`, ignored
by Git, preserve existing files, and set credential files to mode `0600` (use
`umask 077` before creation and shell-safe quoting for env assignments).

For explicitly requested identity seeding:

1. Resolve Cassandra from Public API's effective configuration, including nested
   dependencies. Through both setup and application connection paths query
   `SELECT host_id FROM system.local;`. Host IDs identify nodes: check cluster
   membership, keyspaces, and contact points before treating a mismatch as a
   different cluster.
2. Inspect the selected checkout's README, idstore schema, and identity/policy
   fixtures. Check for an existing `idstore.access_key` row for the supplied key
   without displaying its secret. Verify organization, policy, and suspension.
3. Prepare the record using the supplied key, secret, organization UUID, and
   developer-supplied organization metadata. The current README documents
   `access_key`, `secret_key`, `organization_id`, `organization`,
   `organization_longid`, `cloudstack_user_id`, `policy`, `is_root`, and
   `suspended`. Preserve the repository-supported policy representation; do not
   invent a permissive policy or assume every scenario works with `policy: null`.
4. On the host, use the repository's supported seeding tooling or `cqlsh` against
   the verified local Cassandra, with `INSERT INTO idstore.access_key JSON ...
   IF NOT EXISTS`. Serialize JSON and escape CQL literals correctly; do not
   interpolate unescaped credentials into shell/CQL text. Keep any prepared
   input under `.local/` with mode `0600`, and do not log secrets. Existing-row
   changes need separate authorization; an ignored insert does not align a
   mismatched secret. Additional IAM fixtures may require organization/role rows.
5. Verify a signed read-only request with the supplied credentials. Report a
   mismatch rather than silently replacing the identity or changing policy.

## 3. Create certificates and build

From the Public API checkout:

```sh
cd "$PUBLIC_API_SOURCE"
umask 077
make prepare-tls
make build
```

`prepare-tls` **overwrites existing local certificates and keys** under
`modules/backend/config/tls/`. Keep private keys untracked.
The build produces `modules/backend/target/public-api.jar`.

## 4. Configure local services

Prepare `.local/config.edn` using the checkout's full application configuration,
preserving its Aero includes and references. Set:

- `[:cassandra :contact-points]` to `["go-agent-cassandra"]`.
- `[:client :kms :server]` to `"http://go-agent-kms-gva2:8080"`.
- TLS paths to `config/tls/ca.pem`, `config/tls/cert.pem`, and `config/tls/key.pk8`.
- Other required clients to local services/test doubles; remove remote defaults
  through the application's supported configuration.

Apply Cassandra/KMS settings directly in the chosen config: the stock `dev`
profile does not take them from `CASSANDRA_URL`/`KMS_URL`.
See the [KMS guide](../kms/README.md) to prepare KMS and FoundationDB.
The complete runtime config remains application-specific.

## 5. Run and check

Launch from the host:

```sh
run-shell --image go-agent-all --workspace-root /path/to/story
```

Inside the agent, ask it to use the `public-api-run` skill, or run:

```sh
cd /workspace/public-api/modules/backend
source ../../.local/credentials.env
java -jar target/public-api.jar --file ../../.local/config.edn --profile dev
```

From another pane:

```sh
curl --noproxy '*' --fail http://localhost:8040/v2/ping
```

Use the saved `EXO_KEY`/`EXO_SECRET` for signed requests to the local API.
Verify the operation under test as well as the ping. Stop Public API before
rebuilding its JAR, then restart it.
