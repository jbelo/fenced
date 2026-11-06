ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
AGENT_IMAGE ?= go-agent
AGENT_GATEWAY_IMAGE ?= go-agent-gateway
AGENT_ALL_IMAGE ?= go-agent-all

.PHONY: agent-gateway-build agent-gateway-check
agent-gateway-build:
	docker build --build-arg BASE_IMAGE=$(AGENT_IMAGE) -t $(AGENT_GATEWAY_IMAGE) \
		-f $(ROOT_DIR)/extras/agent-gateway/Dockerfile $(ROOT_DIR)/extras/agent-gateway

agent-gateway-check:
	python3 $(ROOT_DIR)/extras/agent-gateway/scripts/verify.py --image $(AGENT_ALL_IMAGE)
