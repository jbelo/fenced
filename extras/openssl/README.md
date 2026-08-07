# OpenSSL addon

This folder contains optional tooling for building an agent image with OpenSSL development support.

The main harness stays generic. OpenSSL headers and build-time libraries are kept here as an opt-in addon.

## What this addon provides

- a helper Dockerfile for building an optional `go-agent-openssl` image
- OpenSSL runtime tools via `openssl`
- OpenSSL headers and link libraries via `libssl-dev`
- `pkg-config` metadata for native builds that use `pkg-config --cflags --libs openssl`
- a build-time smoke test that compiles a C program including `<openssl/cms.h>`

## Build an agent image with OpenSSL development libraries

Build the derived image:

```sh
make -f extras/openssl/Makefile agent-openssl-build
```

This creates:

```text
go-agent-openssl
```

which extends the main `go-agent` image.

Run a shell with it:

```sh
story-shell --image go-agent-openssl
```

or, with the low-level launcher:

```sh
run-shell --image go-agent-openssl --host-root .
```

## Verify inside the agent shell

```sh
pkg-config --cflags --libs openssl
printf '#include <openssl/cms.h>\nint main(void){return 0;}\n' | \
  cc $(pkg-config --cflags openssl) -x c - $(pkg-config --libs openssl) -o /tmp/openssl-cms-smoke
rm -f /tmp/openssl-cms-smoke
```

## Combining with other agent extras

Build from another derived image by overriding `AGENT_IMAGE`.

For example, to add OpenSSL development support on top of the FoundationDB client image:

```sh
make -f extras/foundationdb/Makefile agent-fdb-build FDB_VERSION=7.3.68
make -f extras/openssl/Makefile agent-openssl-build \
  AGENT_IMAGE=go-agent-fdb \
  AGENT_OPENSSL_IMAGE=go-agent-fdb-openssl
story-shell --image go-agent-fdb-openssl
```

For FoundationDB, Redpanda, and OpenSSL together:

```sh
make -f extras/all/Makefile agent-all-build FDB_VERSION=7.3.68
story-shell --image go-agent-all
```

## Notes

- Debian Bookworm currently provides OpenSSL 3 through `libssl-dev`.
- The smoke test intentionally includes `<openssl/cms.h>` because CMS support requires headers that are not present in runtime-only OpenSSL packages.
