ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

FDB_VERSION ?= 7.3.68
FDB_IMAGE ?= foundationdb/foundationdb:$(FDB_VERSION)
FDB_CONTAINER ?= go-agent-fdb
FDB_DATA_VOLUME ?= go-agent-fdb-data
FDB_PORT ?= 4500
FDB_SOURCE ?=
FDB_DOCKER_RUN_EXTRA ?=

AGENT_INTERNAL_NETWORK ?= go-agent-internal-net
AGENT_IMAGE ?= go-agent
AGENT_FDB_IMAGE ?= go-agent-fdb
AGENT_FDB_DOCKERFILE ?= $(ROOT_DIR)/extras/foundationdb/Dockerfile.agent-fdb

.PHONY: help networks fdb-image-build-source fdb-up fdb-down fdb-init fdb-cli fdb-logs fdb-clean-data agent-fdb-build

help:
	@echo "make -f extras/foundationdb/Makefile fdb-image-build-source FDB_SOURCE=/path/to/foundationdb [FDB_VERSION=7.3.68]"
	@echo "make -f extras/foundationdb/Makefile fdb-up [FDB_VERSION=7.3.68]"
	@echo "make -f extras/foundationdb/Makefile fdb-down"
	@echo "make -f extras/foundationdb/Makefile fdb-init"
	@echo "make -f extras/foundationdb/Makefile fdb-cli"
	@echo "make -f extras/foundationdb/Makefile fdb-logs"
	@echo "make -f extras/foundationdb/Makefile fdb-clean-data"
	@echo "make -f extras/foundationdb/Makefile agent-fdb-build"

networks:
	$(MAKE) -C $(ROOT_DIR) networks

fdb-image-build-source:
	@test -n "$(FDB_SOURCE)" || (echo "error: set FDB_SOURCE=/path/to/foundationdb" >&2; exit 1)
	docker build \
		--platform linux/arm64 \
		--build-arg FDB_VERSION=$(FDB_VERSION) \
		--target foundationdb \
		-t $(FDB_IMAGE) \
		$(FDB_SOURCE)/packaging/docker

fdb-up: networks
	@docker volume inspect $(FDB_DATA_VOLUME) >/dev/null 2>&1 || docker volume create $(FDB_DATA_VOLUME)
	@docker rm -f $(FDB_CONTAINER) >/dev/null 2>&1 || true
	docker run -d \
		--name $(FDB_CONTAINER) \
		--network $(AGENT_INTERNAL_NETWORK) \
		--mount type=volume,src=$(FDB_DATA_VOLUME),target=/var/fdb/data \
		$(FDB_DOCKER_RUN_EXTRA) \
		$(FDB_IMAGE)

fdb-down:
	-docker stop $(FDB_CONTAINER)
	-docker rm $(FDB_CONTAINER)

fdb-init:
	docker exec $(FDB_CONTAINER) fdbcli --exec "configure new single memory"

fdb-cli:
	docker exec -it $(FDB_CONTAINER) fdbcli

fdb-logs:
	docker logs -f $(FDB_CONTAINER)

fdb-clean-data:
	-docker volume rm $(FDB_DATA_VOLUME)

agent-fdb-build:
	docker build \
		--build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		--build-arg FDB_VERSION=$(FDB_VERSION) \
		-t $(AGENT_FDB_IMAGE) \
		-f $(AGENT_FDB_DOCKERFILE) \
		$(ROOT_DIR)/extras/foundationdb
