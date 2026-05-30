ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

REDPANDA_VERSION ?= v26.1.6
REDPANDA_IMAGE ?= docker.redpanda.com/redpandadata/redpanda:$(REDPANDA_VERSION)
REDPANDA_CONTAINER ?= go-agent-redpanda
REDPANDA_DATA_VOLUME ?= go-agent-redpanda-data
REDPANDA_PORT ?= 9092
REDPANDA_DOCKER_RUN_EXTRA ?=
REDPANDA_MEMORY ?= 512M
REDPANDA_SMP ?= 1

AGENT_INTERNAL_NETWORK ?= go-agent-internal-net
AGENT_IMAGE ?= go-agent
AGENT_REDPANDA_IMAGE ?= go-agent-redpanda
AGENT_REDPANDA_DOCKERFILE ?= $(ROOT_DIR)/extras/redpanda/Dockerfile.agent-redpanda

.PHONY: help networks redpanda-up redpanda-down redpanda-logs redpanda-rpk redpanda-ready redpanda-clean-data agent-redpanda-build

help:
	@echo "make -f extras/redpanda/Makefile redpanda-up [REDPANDA_VERSION=v26.1.6]"
	@echo "make -f extras/redpanda/Makefile redpanda-down"
	@echo "make -f extras/redpanda/Makefile redpanda-logs"
	@echo "make -f extras/redpanda/Makefile redpanda-rpk RPK_ARGS='cluster info'"
	@echo "make -f extras/redpanda/Makefile redpanda-ready"
	@echo "make -f extras/redpanda/Makefile redpanda-clean-data"
	@echo "make -f extras/redpanda/Makefile agent-redpanda-build [AGENT_IMAGE=go-agent] [AGENT_REDPANDA_IMAGE=go-agent-redpanda]"

networks:
	$(MAKE) -C $(ROOT_DIR) networks

redpanda-up: networks
	@docker volume inspect $(REDPANDA_DATA_VOLUME) >/dev/null 2>&1 || docker volume create $(REDPANDA_DATA_VOLUME)
	@docker rm -f $(REDPANDA_CONTAINER) >/dev/null 2>&1 || true
	docker run -d \
		--name $(REDPANDA_CONTAINER) \
		--network $(AGENT_INTERNAL_NETWORK) \
		--mount type=volume,src=$(REDPANDA_DATA_VOLUME),target=/var/lib/redpanda/data \
		$(REDPANDA_DOCKER_RUN_EXTRA) \
		$(REDPANDA_IMAGE) \
		redpanda start \
			--overprovisioned \
			--smp $(REDPANDA_SMP) \
			--memory $(REDPANDA_MEMORY) \
			--reserve-memory 0M \
			--node-id 0 \
			--check=false \
			--kafka-addr internal://0.0.0.0:$(REDPANDA_PORT) \
			--advertise-kafka-addr internal://$(REDPANDA_CONTAINER):$(REDPANDA_PORT)

redpanda-down:
	-docker stop $(REDPANDA_CONTAINER)
	-docker rm $(REDPANDA_CONTAINER)

redpanda-logs:
	docker logs -f $(REDPANDA_CONTAINER)

redpanda-rpk:
	docker exec -it $(REDPANDA_CONTAINER) rpk $(RPK_ARGS)

redpanda-ready:
	docker run --rm \
		--network $(AGENT_INTERNAL_NETWORK) \
		--entrypoint rpk \
		$(REDPANDA_IMAGE) \
		cluster info -X brokers=$(REDPANDA_CONTAINER):$(REDPANDA_PORT)

redpanda-clean-data:
	-docker volume rm $(REDPANDA_DATA_VOLUME)

agent-redpanda-build:
	docker build \
		--build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		--build-arg REDPANDA_VERSION=$(REDPANDA_VERSION) \
		-t $(AGENT_REDPANDA_IMAGE) \
		-f $(AGENT_REDPANDA_DOCKERFILE) \
		$(ROOT_DIR)/extras/redpanda
