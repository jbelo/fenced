ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

AGENT_IMAGE ?= go-agent
AGENT_OPENSSL_IMAGE ?= go-agent-openssl
AGENT_OPENSSL_DOCKERFILE ?= $(ROOT_DIR)/extras/agent-openssl/Dockerfile

.PHONY: help agent-openssl-build

help:
	@echo "make -f extras/agent-openssl/Makefile agent-openssl-build [AGENT_IMAGE=go-agent] [AGENT_OPENSSL_IMAGE=go-agent-openssl]"

agent-openssl-build:
	docker build \
		--build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		-t $(AGENT_OPENSSL_IMAGE) \
		-f $(AGENT_OPENSSL_DOCKERFILE) \
		$(ROOT_DIR)/extras/agent-openssl
