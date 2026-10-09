ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

AGENT_IMAGE ?= go-agent
AGENT_ALL_IMAGE ?= go-agent-all
AGENT_ALL_DOCKERFILE ?= $(ROOT_DIR)/extras/all/Dockerfile
REDPANDA_VERSION ?= v26.1.6
FDB_VERSION ?= 7.3.68
# Empty uses the pinned Java runtime in the Dockerfile.
JAVA_IMAGE ?=

.PHONY: help agent-all-build agent-all-check

help:
	@echo "make -f extras/all/Makefile agent-all-build [AGENT_IMAGE=go-agent] [AGENT_ALL_IMAGE=go-agent-all] [REDPANDA_VERSION=v26.1.6] [FDB_VERSION=7.3.68] [JAVA_IMAGE=...]"
	@echo "make -f extras/all/Makefile agent-all-check  # Offline tool/version checks"

agent-all-build:
	docker build \
		--build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		--build-arg REDPANDA_VERSION=$(REDPANDA_VERSION) \
		--build-arg FDB_VERSION=$(FDB_VERSION) \
		$(if $(JAVA_IMAGE),--build-arg "JAVA_IMAGE=$(JAVA_IMAGE)") \
		-t $(AGENT_ALL_IMAGE) \
		-f $(AGENT_ALL_DOCKERFILE) \
		$(ROOT_DIR)/extras/all

agent-all-check:
	docker run --rm --network none --read-only --user "$$(id -u):$$(id -g)" \
		--tmpfs /tmp:rw,mode=1777 --env HOME=/tmp "$(AGENT_ALL_IMAGE)" \
		sh -c 'set -eu; java -version; go version; pkg-config --modversion openssl; fdbcli --version; rpk --version'
