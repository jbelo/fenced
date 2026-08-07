ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

AGENT_IMAGE ?= go-agent
AGENT_ALL_IMAGE ?= go-agent-all
AGENT_ALL_DOCKERFILE ?= $(ROOT_DIR)/extras/all/Dockerfile.agent-all
REDPANDA_VERSION ?= v26.1.6
FDB_VERSION ?= 7.3.68

.PHONY: help agent-all-build

help:
	@echo "make -f extras/all/Makefile agent-all-build [AGENT_IMAGE=go-agent] [AGENT_ALL_IMAGE=go-agent-all] [REDPANDA_VERSION=v26.1.6] [FDB_VERSION=7.3.68]"

agent-all-build:
	docker build \
		--build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		--build-arg REDPANDA_VERSION=$(REDPANDA_VERSION) \
		--build-arg FDB_VERSION=$(FDB_VERSION) \
		-t $(AGENT_ALL_IMAGE) \
		-f $(AGENT_ALL_DOCKERFILE) \
		$(ROOT_DIR)/extras/all
