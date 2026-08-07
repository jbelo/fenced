# All extras addon

This folder builds an optional `go-agent-all` image with the currently common agent extras:

- Redpanda `rpk`
- FoundationDB client tools and libraries
- OpenSSL development support

The image extends the main `go-agent` image. It does not replace the standalone Redpanda or FoundationDB service containers.

## Build

Build the base image first:

```sh
make build
```

Then build the union image:

```sh
make -f extras/all/Makefile agent-all-build
```

This creates:

```text
go-agent-all
```

Override versions or image names when needed:

```sh
make -f extras/all/Makefile agent-all-build \
  REDPANDA_VERSION=v26.1.6 \
  FDB_VERSION=7.3.68 \
  AGENT_ALL_IMAGE=go-agent-all
```

## Use

Run an agent shell with the union image:

```sh
story-shell --image go-agent-all
```

or, with the low-level launcher:

```sh
run-shell --image go-agent-all --host-root .
```

## Notes

- Rebuild `go-agent-all` whenever the base `go-agent` image changes.
- Start Redpanda and FoundationDB separately when tests need the actual services.
- The FoundationDB client package is selected for `amd64` or `arm64` Docker builds.
