# Optional extras

Each extra keeps its setup commands, configuration, and documentation in its
own directory. Run its Makefile from the harness repository; consult its README
for dependencies and available overrides.

Extras that build an image use a plain `Dockerfile` in their directory.

For use inside an agent container, start with the [extras overview](AGENT.md),
then read the relevant installed skill for connection and usage instructions.
`make install-agent-context` copies the files explicitly listed in
`extras/agent-docs.list` to `$HOME/.go-agent-harness/extras/` in the agent home
volume. This bundle contains only agent-facing connection, client configuration,
and diagnostic guidance. Host-facing READMEs and service configuration templates
stay in this repository.

The same target installs the self-contained `SKILL.md` files from directories
listed in `extras/agent-skills.list` into `$HOME/.agents/skills/<name>/`.
These skills cover service clients, diagnostics, and agent-side application execution; host provisioning stays
in the extra's README/setup guide. Refresh replaces each listed skill file.
Refresh installs current entries only; it does not remove older files from
existing agent homes.

- [Cassandra](cassandra/README.md): persistent database service, lifecycle, and readiness checks.
- [Public API agent tooling](agent-public-api/README.md): Java 25, Clojure CLI, host-prepared repo-local dependency caches and offline resolution checks.
- [Public API runtime agent extension](agent-public-api-runtime/README.md): Java 25 only, for running host-built Public API uberjars from the shared checkout.
  Its [local host setup guide](agent-public-api-runtime/SETUP.md) covers schemas, fixed local test credentials, certificates, and build/run steps.
- [FoundationDB](foundationdb/README.md): database service and agent client libraries.
- [Redpanda](redpanda/README.md): broker service and agent CLI.
- [KMS](kms/README.md): one or two local KMS zones.
- [XKS test proxy](xks-test-proxy/README.md): TLS/SigV4 proxy with SoftHSM test keys and agent root SSH access for local debugging.
- [SSH support](ssh/README.md): reusable local-service SSH image layer and client-key setup.
- [OpenSSL agent extension](agent-openssl/README.md): agent development libraries.
- [Combined agent image](all/README.md): OpenSSL, FoundationDB and Redpanda tooling, plus the Java 25 runtime.

Database service containers and their data volumes are separate from the agent
home volume. Follow each extra's lifecycle instructions to manage them.
