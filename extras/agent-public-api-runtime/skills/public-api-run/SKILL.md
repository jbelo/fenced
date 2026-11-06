---
name: public-api-run
description: Run and diagnose a host-built Public API JAR inside the agent container, optionally in tmux, and prepare local runtime configuration when explicitly requested. Excludes builds and database provisioning.
---

# Run local Public API

Work inside the existing agent container. The developer normally supplies runtime
configuration and prepares the JAR, certificates, Cassandra schemas, and identity
data on the host. Generate local runtime configuration only when explicitly
requested, using the section below. Report other missing prerequisites rather
than rebuilding or provisioning them.

## Locate and check

First make one readiness inventory: selected checkout/JAR revision and Java,
effective config/profile, TLS files, Cassandra/schema/identity, KMS endpoint,
client credentials, discovery dependencies, and existing processes/ports. Report
all missing inputs together rather than repeatedly asking for one file at a time.
Separate listener startup from authenticated operation readiness and readiness of
the actual SDK/CLI. Do not require client credentials merely to test ping.

Find the requested Public API checkout in the mounted story directory (commonly
`/workspace/public-api`; repository names vary). Resolve these paths:

- Working directory: `<checkout>/modules/backend`.
- JAR: `target/public-api.jar` relative to that directory.
- Configuration: `<checkout>/.local/config.edn`, unless the developer specifies another.
- Request-client environment: `<checkout>/.local/credentials.env`.
- Default TLS files: `config/tls/ca.pem`, `cert.pem`, and `key.pk8` under the backend.

Check the JAR timestamp/build metadata against the selected checkout and inspect
bundled resources when necessary; source configuration and an older JAR can differ.
A host worktree's `.git` file may point outside the container: do not rewrite Git
metadata to make runtime setup work. Report revision uncertainty instead.

Check Java with `java -version` and verify required files are readable. Java 25
is included in `go-agent-java` and `go-agent-all`. Inspect the supplied config for
its listener port and service endpoints. Cassandra normally uses
`go-agent-cassandra:9042`; KMS uses `http://go-agent-kms-gva2:8080`.
The stock dev profile alone is not the prepared local config.
For missing TLS, check the selected checkout's Makefile: its host-side
`make prepare-tls` target creates self-signed local development material, whereas
`make tls` imports developer certificates. Explain the appropriate host command;
do not silently generate, replace, or weaken certificates. Check readable paths
before launching, not only whether the config spec accepts their strings.

Use container-visible paths for configuration and TLS files. Host environment
variables and home-directory secrets are not automatically available. JVM TLS
trust is separate from Go's `SSL_CERT_FILE`; use a developer-provided Java
truststore if required. Report stale JARs or missing runtime configuration.

Check existing processes/tmux panes and the configured port before launching;
reuse an existing instance when appropriate. Do not stop an unrelated process.

## Local files and credentials

Use `<checkout>/.local/` (with the leading dot) for generated runtime config,
credentials, logs, backups, and temporary setup files. Preserve existing files
and developer-supplied paths; verify generated files are ignored by Git. Create
credential files with `umask 077` and enforce mode `0600` on files containing
credentials, including backups. Do not expose secrets in logs or command output.

The working convention is `.local/credentials.env` containing shell-quoted
`export NAME=value` assignments for `EXO_KEY`, `EXO_SECRET`, `EXO_ORG_ID`, and
`ZONE`. Inspect it locally before sourcing; accept data assignments rather than
arbitrary commands or substitutions. If `credentials.edn` is supplied, read it
as EDN data, inspect its actual keys/nesting, and record the non-secret field
mapping to those four names. Never source EDN or assume it has env-file syntax.

Client credentials do not register a server identity. Verify the matching identity
exists in the Cassandra instance used by the application's effective config,
including nested dependencies. If prepared data appears missing, compare
`SELECT host_id FROM system.local;` through the setup and application connection
paths. A host ID identifies a node, so differing IDs require checking cluster
membership, keyspace, and contact points; they alone do not prove different
clusters. Inspect identity existence, organization, suspension, and applicable
policy without printing secrets. Missing identity data requires separately
requested host-side seeding using supplied credentials and the repository's
supported identity/policy format; never generate replacement credentials merely
to make a request succeed.

Schema initialization is not identity initialization: the current checkout's
`.docker/cassandra-init.sh` imports schemas only. Consult the backend README's
local key-import instructions, `doc/idstore.cql`, and the selected build's IAM
loader/test seed fixtures. The current IAM v3 loader still reads
`idstore.access_key`; do not assume an empty table is merely a legacy-store issue.
Which organization/role records are needed depends on the supplied identity type;
legacy imported-style keys may be converted by IAM v3 without a separate role.
Do not invent root privileges or unrestricted policies as an authentication fix.

Use the `cassandra-connect` skill for read-only checks. If cqlsh is absent, the
supplied JAR's Cassandra driver can check the effective contact points with
read-only queries; do not download another client or initialize data just to
inspect it. Check only needed columns, never print secret_key. KMS uses FDB,
not Cassandra: follow `foundationdb-connect` and `kms-run`/`kms-connect` for that
separate dependency chain.

## Generate local configuration when explicitly requested

Resolve the actual checkout; do not assume a story-specific directory name.
Use its `modules/backend/resources/config.edn` as the starting point for
`<checkout>/.local/config.edn`, with local copies of `features.edn` and
`restrictions.edn` from the same resources directory when needed. Verify these
local files are ignored by Git. Preserve existing files; inspect and edit them
only within the requested scope instead of blindly copying over them.

Inspect the checkout's current Aero configuration and preserve its includes,
references, and unrelated settings. For the selected local profile:

- Set `[:cassandra :contact-points]` to the supplied Cassandra endpoint (normally
  `["go-agent-cassandra"]`). The stock `:dev` profile does not read this value
  from `CASSANDRA_URL`.
- Set `[:client :kms :server]` to the supplied KMS endpoint (normally
  `"http://go-agent-kms-gva2:8080"`). The stock `:dev` value is `nil`; setting
  `KMS_URL` alone does not override it. Use localhost only when KMS actually runs
  in the same container. For an explicitly supplied plain-HTTP KMS endpoint,
  configure the KMS client without TLS (remove its `:tls` entry or use the
  selected build's supported disabled value). Preserve certificate verification
  for HTTPS endpoints. Public API may still require its global TLS files during
  startup even when KMS uses HTTP; do not remove global TLS configuration.
- Check `[:restrictions :profile]`. If it lacks a `:dev` entry, add `:dev :test`
  for local testing; an unresolved profile can fail configuration validation.
  Preserve other profile mappings and do not disable restrictions as a workaround.
- Check other required clients for remote defaults and use the supplied local
  services or test doubles. Report missing endpoints rather than inventing them.

Run from `<checkout>/modules/backend`. Verify how the selected loader resolves
`features.edn`, `restrictions.edn`, and nested includes. Aero includes may resolve
relative to the configuration, while other loaders may use classpath resources.
In particular, `public-api.restrictions.config/read-config` uses `io/resource`:
copying `restrictions.edn` beside the config does not override the bundled file.
If an override is needed, explicitly arrange its classpath precedence with the
selected build's launch mechanism and verify the resolved resource URL.
Keep includes and TLS paths
consistent with the loader's working-directory/classpath behavior; normal TLS
paths are `config/tls/ca.pem`, `config/tls/cert.pem`, and `config/tls/key.pk8`.

The included `resource-lock/entities/config.edn` can have its own Cassandra
settings. Inspect that resource in the available dependency source or built JAR
and its selected profile; a top-level override may not reach it. If it reads
`CASSANDRA_URL`, supply the same container-visible host in the JAR process's
environment, for example `CASSANDRA_URL=go-agent-cassandra java -jar ...`.
If it reads `ID_META_CONTACT_POINTS`, supply that variable instead or as well,
as required by the actual resource. Do not assume those variables configure the
top-level dev profile.

Treat generated configuration as local diagnostic configuration, not a deployment
template. Do not print credential values. Configuration generation does not
authorize certificate generation, database seeding, or service provisioning.
Report what was prepared and any unresolved prerequisites; launch and check it
only when startup is part of the user's request.

## Offline configuration check

Before launching, use the built JAR's classes to load the chosen config and
validate `:public-api.config/config`, without building or starting the application
system. Use the same profile, working directory, environment, and resource paths
as the intended launch. For the current Aero-based build, from the backend:

```sh
java -cp target/public-api.jar clojure.main -e '
(require (quote aero.core) (quote clojure.java.io)
         (quote clojure.spec.alpha) (quote public-api.config))
(try
  (let [c (aero.core/read-config
            (clojure.java.io/file "../../.local/config.edn") {:profile :dev})]
    (if (clojure.spec.alpha/valid? :public-api.config/config c)
      (println "Configuration spec valid")
      (do (println "Configuration spec invalid") (System/exit 1))))
  (catch Throwable _
    (println "Configuration load failed; inspect locally without exposing secrets")
    (System/exit 1)))'
```

Inspect the resolved configuration locally, reporting only non-secret settings:
Cassandra contact points including nested dependencies, KMS endpoint and whether
client TLS is configured, restrictions profile, listener port, and advertised
API endpoints. Do not dump the full config, exception data, or spec explanation:
they may contain credentials. Adapt the loader to the selected JAR if its
configuration mechanism differs; do not substitute the deprecated
`public-api.config/read-config`, which treats its path as a classpath resource.
Spec validation does not verify certificate files, database schemas, or
connectivity, and does not prove that an advertised endpoint can be reached.
Report unrelated remote/preproduction defaults explicitly; changing Cassandra
and KMS alone does not make the whole configuration local.

For requested native KMS startup in the agent container, follow
`$HOME/.agents/skills/kms-run/SKILL.md`. For an existing sibling KMS service use
`$HOME/.agents/skills/kms-connect/SKILL.md`.

## Source-free local zone discovery

Use this only when the user requests an isolated discovery setup, including a
local config change, a disposable loopback backend, and a Public API restart.
Config preparation alone does not authorize starting processes. Database/identity
provisioning, certificate generation, and persistent-state changes remain
separately authorized. No source patch or JAR rebuild is needed for this recipe.

The developer reported this recipe verified for one `ch-gva-2` zone: Public API
at `http://127.0.0.1:8040/v2`, native KMS at `http://127.0.0.1:8080`, and discovery
backend at `http://127.0.0.1:18080/zone`, all in the same agent container. Recheck
the selected JAR's contract and endpoints when using another build/topology.
This is a discovery-only compute test double, not a compute service.

1. Check port 18080 and existing processes. Preserve the config in
   `.local/config.before-local-discovery.edn` without overwriting an existing
   backup; use a distinct backup name if necessary and record it.
2. Create `.local/zone-backend/zone` with this fixture, after checking existing files:

```json
{"zones":[{"id":"1747ef5e-5451-41fd-9f1a-58913bae9702","name":"ch-gva-2","api-endpoint":"http://127.0.0.1:8040/v2"}]}
```

3. From the checkout root, start this in a named tmux window (for example
   `zone-discovery`) and record its session/window:

```sh
python3 -u -c 'from functools import partial; from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer; SimpleHTTPRequestHandler.extensions_map[""] = "application/json"; ThreadingHTTPServer(("127.0.0.1", 18080), partial(SimpleHTTPRequestHandler, directory=".local/zone-backend")).serve_forever()'
```

The extension-map key must be the empty string: the extensionless `/zone` must
return `Content-Type: application/json`. Plain `python3 -m http.server` serves it
as `application/octet-stream`, which the bundled compute client rejects. Check
with `curl --noproxy '*' -i http://127.0.0.1:18080/zone`. Serve only this dedicated
fixture directory, with no credentials, unrelated files, or symlinks outside it.
The backend is loopback-only and unauthenticated; Public API authentication and
authorization remain enabled.

4. In `.local/config.edn`, change only the selected local/dev profile:
   - Add `{:command :list-zones :service :candidate}` to
     `:compute-client-enabled-operations`, preserving other entries. This setting
     is an EDN-encoded string in the current config; preserve its representation.
     Use candidate-only routing, not `:both`, to avoid CloudStack calls/comparisons.
     The stock dev profile hardcodes this setting; an environment flag alone does
     not override it.
   - Set `[:client :compute-orchestrator :host]` to `"127.0.0.1"`, `:port` to
     `18080`, and `:tls` to `nil` in that client map.
   - Keep `[:client :kms :server]` pointing at the real KMS service.
   - Set `:api-endpoint` to `"http://127.0.0.1:8040/v2"`. This advertises URLs;
     it does not supply zone data.
5. Run the offline configuration check, then restart only the intended Public
   API process, not KMS. From `modules/backend`, the verified launch was:

```sh
CASSANDRA_URL=go-agent-cassandra java -Xmx512m -jar target/public-api.jar --file ../../.local/config.edn --profile dev
```

6. Run all applicable acceptance checks below, including the real client's
   discovery behavior. Signed `/v2/zone` and signed `/v2/kms-key` succeeded in
   this setup, but unsigned discovery returned 403 because the anonymous IAM role
   was not prepared. That is a client-readiness gap, not a required security check.
   See the SDK bootstrap section before claiming SDK/CLI readiness.

Only the `GET /zone` fixture is supplied; other compute operations are unsupported.
SOS and unrelated advertised/service endpoints remain unchanged. Report remote
or preproduction defaults rather than describing the whole config as local.
Do not advertise a second zone without independently configured Public API/KMS
routing. Loopback advertised URLs work only for clients in this same container.

To roll back, compare the backup with later edits before restoring discovery
settings only when restoration is requested, restart the intended Public API
process if needed, and use the owned-process teardown checklist below for the
discovery backend. Original discovery again requires a working compute/CloudStack
backend. A process stop alone does not authorize restoring config. Leave database
state and unrelated KMS processes alone.

## SDK discovery and anonymous identity

Inspect the selected SDK and endpoint schema. In the version verified here,
`list-zones` is optional-auth, and egoscale's initial `ListZones` request is
intentionally unsigned. Its discovery helper retries signed only when a successful
list lacks the requested zone, not when the initial request returns 403.
Consequently, a signed Clojure probe can pass while the provider/CLI still fails.
A generic "Invalid key or request signature" response to that unsigned request
does not establish that supplied credentials are wrong.

Preferred full setup: have the host prepare the anonymous identity/role expected
by the selected JAR (`:anon-role-id` in the current config), with narrowly scoped
public-discovery permissions. Inspect the actual IAM loader and authorization
contract; do not disable authentication or grant anonymous KMS access. Database
seeding remains separately authorized. Verify unsigned discovery and a signed
protected operation with the actual client.

For an explicitly authorized, isolated local test, the discovery fixture above
can instead be the SDK bootstrap endpoint: set its supported endpoint override
to `http://127.0.0.1:18080` (no `/v2`). It serves unsigned `GET /zone` and advertises
`http://127.0.0.1:8040/v2`. Verify that the actual client follows that advertised
endpoint and signs protected calls to the real Public API. In the verified
provider's zone-switching path this worked; it is not a universal SDK behavior.
The fixture cannot handle protected operations. Report this test-double bootstrap
explicitly; it does not fix Public API's missing anonymous identity. See
`terraform-exoscale-run` for provider-specific configuration when that skill is available.

## Launch when requested

From a shell in the agent container, substituting the actual checkout path:

```sh
cd /workspace/public-api/modules/backend
java -jar target/public-api.jar --file ../../.local/config.edn --profile dev
```

For visible, persistent output, open a named tmux window and run the same command
there. For example, when attached to tmux:

```sh
tmux new-window -n public-api -c /workspace/public-api/modules/backend
```

Record the process PID/executable, tmux session, stable pane/window IDs and all
listener/metrics ports for each process you start, including the discovery backend.
Preserve its output for diagnosis. Pass any required Cassandra environment
variables into this process or its tmux window explicitly; an existing tmux server
may not inherit new shell exports.
Use Ctrl-C in that application's pane for a requested stop/restart, then wait for
it to exit. The developer must stop the process before replacing its JAR.

## Stop and clean up owned runtime processes

When teardown is requested, complete the whole owned-process checklist; do not
leave idle service windows for a separate user follow-up:

1. Match the recorded PID/executable and stable tmux pane/window IDs to the process
   this run started. Do not select unrelated processes by a broad name match or
   assume ownership of a reused service. Inspect all panes in a shared window.
2. Send Ctrl-C to the owned foreground application, then wait up to 60 seconds
   for it to exit. If it does not exit, report the specific process and obtain
   approval for escalation; do not blindly kill a session or another process.
3. Verify the recorded listener and metrics ports are no longer listening, using
   socket checks or the system's listener listing. A failed HTTP health request
   alone does not prove the listener is down. If another process owns a remaining
   listener, report it rather than stopping it without authorization.
4. Recheck pane foreground processes/background jobs and ownership. Close only
   this run's idle windows once every pane in them is owned and idle, using the
   recorded window IDs. Preserve shared/unrelated panes, sessions and user shells;
   if safe removal is uncertain, leave them and report why.
5. Record exit/listener/window results in the handover. Preserve databases,
   credentials, key material, configs/backups, logs and Terraform state. Stopping
   processes is not permission to destroy resources, reset data or restore config.

This checklist also applies to a discovery test double or native KMS process
started as part of the requested setup. Do not stop dependency containers merely
because they appear in the application's configuration.

## Verify and use

From another shell, using the configured port (default dev port `8040`):

```sh
curl --noproxy '*' --fail http://localhost:8040/v2/ping
```

Use bounded readiness probes (up to 60 seconds), then inspect the application's
output and report a startup failure rather than repeatedly relaunching it.

For signed requests, inspect the developer-provided environment file before
sourcing it as shell code, then load it in the request-client shell:

```sh
source /workspace/public-api/.local/credentials.env
```

For a Public API/KMS readiness check, verify and report these levels in order:

1. Public API `/v2/ping` succeeds.
2. The configured KMS `/internal/health` succeeds, using its actual endpoint and
   appropriate proxy bypass/TLS verification.
3. A signed, read-only KMS operation through Public API succeeds with the supplied
   identity, for example `list-kms-keys` using the project's client. An authorized
   empty result is valid. Do not create a key merely to establish readiness.

4. When a client needs discovery, check its actual signed/unsigned behavior,
   advertised endpoints, and subsequent API routing. Optional-auth `/v2/zone`
   may legitimately succeed unsigned with the prepared anonymous role. A 403
   requires diagnosis, not a passing readiness assertion. Report whether this
   check uses Public API directly or the limited fixture bootstrap.
5. Verify an unsigned protected operation such as `/v2/kms-key` is rejected;
   successful public discovery must not imply anonymous access to KMS.

Report each check separately as passed, failed, or not tested, as well as the
highest verified level. If credentials
are missing, stop at the level that can be verified and report that limitation.

For SDK/CLI discovery, verify responses advertise the intended local endpoints.
Changing the advertised endpoint does not necessarily make discovery work:
discovery itself may call other backends. Inspect errors and remote routing,
including unrelated preproduction defaults, before claiming end-to-end readiness.

`EXO_KEY` and `EXO_SECRET` must match the prepared local identity. Avoid displaying
credential values. A ping checks the HTTP listener, not authentication or all
downstream dependencies. Test the user-requested operation with the supplied
local credentials and report any missing schema, identity, or service to the
developer. Leave Docker lifecycle, certificate generation, and database seeding
to the host.

## Signed checks for the one-zone recipe

The verified workspace helper was `progress/checks/public_api_signed_readiness.clj`.
For workspaces without that file, place the following equivalent helper in
`.local/public_api_signed_readiness.clj`, preserving any existing file. It checks
only the one-zone loopback recipe above; adapt and verify expectations for other
setups. With supplied credentials in the process environment, from the backend:

```sh
java -cp target/public-api.jar clojure.main ../../.local/public_api_signed_readiness.clj
```

```clojure
;; Run with EXO_KEY/EXO_SECRET set and the Public API JAR on the classpath.
;; Signed discovery and KMS routing checks; not proof of unsigned SDK bootstrap.
;; /v2/zone is optional-auth. Anonymous access needs its own prepared IAM role.
(require '[exoscale.auth.sign :as sign]
         '[cheshire.core :as json])
(import '(java.net URI)
        '(java.net.http HttpClient HttpRequest HttpResponse$BodyHandlers)
        '(java.time Duration))

(let [key (System/getenv "EXO_KEY")
      secret (System/getenv "EXO_SECRET")
      client (-> (HttpClient/newBuilder) (.connectTimeout (Duration/ofSeconds 5)) (.build))
      request (fn [path signed?]
                (let [builder (-> (HttpRequest/newBuilder (URI/create (str "http://127.0.0.1:8040" path)))
                                  (.timeout (Duration/ofSeconds 10))
                                  (.GET))]
                  (when signed?
                    (.header builder "Authorization"
                             (sign/sig-auth-header {:access-key key :secret-key secret
                                                    :request-method :get :uri path})))
                  (.send client (.build builder) (HttpResponse$BodyHandlers/ofString))))]
  (assert (and (seq key) (seq secret)) "Missing client credentials")
  (let [response (request "/v2/kms-key" false)]
    (assert (#{401 403} (.statusCode response)) "KMS listing unexpectedly accepted an unsigned request")
    (println "PASS: unsigned KMS listing rejected"))
  (let [response (request "/v2/zone" true)]
    (assert (= 200 (.statusCode response)) (str "Signed discovery HTTP " (.statusCode response)))
    (let [zones (:zones (json/parse-string (.body response) true))]
      (assert (= 1 (count zones)) "Expected only the single local zone")
      (assert (= "ch-gva-2" (:name (first zones))))
      (assert (= "http://127.0.0.1:8040/v2" (:api-endpoint (first zones))))
      (println "PASS: signed discovery returns ch-gva-2 at http://127.0.0.1:8040/v2")))
  (let [response (request "/v2/kms-key" true)]
    (assert (= 200 (.statusCode response)) (str "Signed KMS list HTTP " (.statusCode response)))
    (println "PASS: signed KMS listing succeeds; resource contents not displayed")))
```

The helper fails at the first failed assertion. Report remaining checks as not
tested, or run them independently to collect separate results. Run ping and KMS
health separately; this helper does not check them or alter resources. It signs
its discovery request, so it cannot establish egoscale's unsigned bootstrap is
working. Follow it with the SDK/CLI's own read-only discovery check.
