ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
OPENBAO_VERSION ?= 2.7.1
OPENBAO_IMAGE ?= quay.io/openbao/openbao:$(OPENBAO_VERSION)
OPENBAO_CONTAINER ?= go-agent-openbao
AGENT_INTERNAL_NETWORK ?= go-agent-internal-net
AGENT_IMAGE ?= go-agent
AGENT_OPENBAO_IMAGE ?= go-agent-openbao

.PHONY: help openbao-up openbao-down openbao-ready openbao-logs agent-openbao-build
help:
	@echo "openbao-up: start disposable OpenBao $(OPENBAO_VERSION), internal network only"
	@echo "openbao-down: remove service and discard its in-memory data"
	@echo "openbao-ready: check initialized/unsealed status"
	@echo "openbao-logs: show service logs (dev logs contain test credentials)"
	@echo "openbao-tls-up/ready/install/down/clean: separate verified-TLS disposable instance"
	@echo "agent-openbao-build: add bao CLI to AGENT_IMAGE"

openbao-up:
	@docker network inspect "$(AGENT_INTERNAL_NETWORK)" >/dev/null
	docker run -d --name "$(OPENBAO_CONTAINER)" \
		--network "$(AGENT_INTERNAL_NETWORK)" --user openbao \
		--cap-drop ALL --security-opt no-new-privileges --read-only \
		--tmpfs /tmp:rw,mode=1777 -e HOME=/tmp \
		--entrypoint bao "$(OPENBAO_IMAGE)" server -dev \
		-dev-listen-address=0.0.0.0:8200 -dev-root-token-id=local-openbao-dev-only

openbao-down:
	docker rm -f -v "$(OPENBAO_CONTAINER)"

openbao-ready:
	docker run --rm --network "$(AGENT_INTERNAL_NETWORK)" \
		-e BAO_ADDR=http://$(OPENBAO_CONTAINER):8200 \
		--entrypoint bao "$(OPENBAO_IMAGE)" status

openbao-logs:
	docker logs -f "$(OPENBAO_CONTAINER)"

agent-openbao-build:
	docker build --build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		--build-arg OPENBAO_IMAGE=$(OPENBAO_IMAGE) -t $(AGENT_OPENBAO_IMAGE) \
		-f $(ROOT_DIR)/extras/openbao/Dockerfile $(ROOT_DIR)/extras/openbao

# Separate TLS test instance; preserves the existing plain-HTTP service.
.PHONY: openbao-tls-up openbao-tls-install openbao-tls-ready openbao-tls-down openbao-tls-clean
export AGENT_IMAGE OPENBAO_IMAGE AGENT_INTERNAL_NETWORK
openbao-tls-up:
	python3 $(ROOT_DIR)/extras/openbao/scripts/tls.py up
openbao-tls-install:
	python3 $(ROOT_DIR)/extras/openbao/scripts/tls.py install
openbao-tls-ready:
	python3 $(ROOT_DIR)/extras/openbao/scripts/tls.py ready
openbao-tls-down:
	python3 $(ROOT_DIR)/extras/openbao/scripts/tls.py down
openbao-tls-clean:
	python3 $(ROOT_DIR)/extras/openbao/scripts/tls.py clean
