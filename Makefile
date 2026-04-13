AGENT_IMAGE := go-agent

AGENT_HOME := /home/agent

AGENTHOME := agenthome
GOMODCACHE := gomodcache

REPO_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
INSTALL_DIR ?= $(HOME)/.local/bin

AGENT_INTERNAL_NETWORK := go-agent-internal-net
PROXY_UPSTREAM_NETWORK := go-agent-upstream-net
EGRESS_PROXY_CONTAINER := go-agent-egress-proxy
EGRESS_PROXY_IMAGE := go-agent-egress-proxy-image
SQUID_CONF := $(REPO_DIR)/squid.conf
PROXY_DOCKERFILE := $(REPO_DIR)/Dockerfile.squid

UID := $(shell id -u)
GID := $(shell id -g)

.PHONY: help volumes init-volumes build install networks egress-proxy-build egress-proxy-up egress-proxy-down egress-proxy-logs egress-init egress-verify clean

help:
	@echo "make build                       Build the agent container image"
	@echo "make volumes                     Create Docker volumes"
	@echo "make init-volumes                Initialize writable volume ownership"
	@echo "make install [INSTALL_DIR=path]  Install the launcher scripts"
	@echo "make networks                    Create the internal agent network and proxy upstream network"
	@echo "make egress-proxy-build          Build the Squid egress proxy image"
	@echo "make egress-proxy-up             Start the Squid egress proxy"
	@echo "make egress-proxy-down           Stop and remove the Squid egress proxy"
	@echo "make egress-proxy-logs           Tail Squid proxy logs"
	@echo "make egress-init                 Create network and start the proxy"
	@echo "make egress-verify               Probe allowed and denied domains through the proxy"
	@echo "make clean                       Remove persistent Docker volumes"

build:
	docker build -t $(AGENT_IMAGE) .

volumes:
	@docker volume inspect $(AGENTHOME) >/dev/null 2>&1 || docker volume create $(AGENTHOME)
	@docker volume inspect $(GOMODCACHE) >/dev/null 2>&1 || docker volume create $(GOMODCACHE)

init-volumes: volumes
	docker run --rm \
		--user 0:0 \
		--mount type=volume,src="$(AGENTHOME)",target="$(AGENT_HOME)" \
		--mount type=volume,src="$(GOMODCACHE)",target=/go/pkg/mod \
		$(AGENT_IMAGE) \
		sh -lc 'mkdir -p "$(AGENT_HOME)" /go/pkg/mod && chown -R $(UID):$(GID) "$(AGENT_HOME)" /go/pkg/mod'

install:
	@mkdir -p "$(INSTALL_DIR)"
	@install -m 0755 "$(REPO_DIR)/bin/run-shell" "$(INSTALL_DIR)/run-shell"
	@install -m 0755 "$(REPO_DIR)/bin/story-shell" "$(INSTALL_DIR)/story-shell"
	@echo "Installed $(INSTALL_DIR)/story-shell"
	@echo "Installed $(INSTALL_DIR)/run-shell"
	@echo "Add $(INSTALL_DIR) to PATH if needed"

networks:
	@docker network inspect $(AGENT_INTERNAL_NETWORK) >/dev/null 2>&1 || docker network create --internal $(AGENT_INTERNAL_NETWORK)
	@docker network inspect $(PROXY_UPSTREAM_NETWORK) >/dev/null 2>&1 || docker network create $(PROXY_UPSTREAM_NETWORK)

egress-proxy-build:
	docker build -t $(EGRESS_PROXY_IMAGE) -f $(PROXY_DOCKERFILE) $(REPO_DIR)

egress-proxy-up: networks
	@docker rm -f $(EGRESS_PROXY_CONTAINER) >/dev/null 2>&1 || true
	docker run -d \
		--name $(EGRESS_PROXY_CONTAINER) \
		--network $(PROXY_UPSTREAM_NETWORK) \
		--mount type=bind,src="$(SQUID_CONF)",target=/etc/squid/squid.conf,readonly \
		$(EGRESS_PROXY_IMAGE)
	docker network connect $(AGENT_INTERNAL_NETWORK) $(EGRESS_PROXY_CONTAINER)

egress-proxy-down:
	-docker stop $(EGRESS_PROXY_CONTAINER)
	-docker rm $(EGRESS_PROXY_CONTAINER)

egress-proxy-logs:
	docker exec -it $(EGRESS_PROXY_CONTAINER) sh -lc 'touch /var/log/squid/access.log /var/log/squid/cache.log && tail -n +1 -f /var/log/squid/access.log /var/log/squid/cache.log'

egress-init: networks egress-proxy-up

egress-verify: egress-init
	@echo "Checking approved destination via proxy..."
	docker run --rm --network $(AGENT_INTERNAL_NETWORK) \
		-e HTTPS_PROXY=http://$(EGRESS_PROXY_CONTAINER):3128 \
		-e HTTP_PROXY=http://$(EGRESS_PROXY_CONTAINER):3128 \
		curlimages/curl:8.12.1 -sSI https://api.openai.com >/dev/null
	@echo "Approved destination succeeded"
	@echo "Checking denied destination via proxy..."
	@if docker run --rm --network $(AGENT_INTERNAL_NETWORK) \
		-e HTTPS_PROXY=http://$(EGRESS_PROXY_CONTAINER):3128 \
		-e HTTP_PROXY=http://$(EGRESS_PROXY_CONTAINER):3128 \
		curlimages/curl:8.12.1 -fsSI https://example.com >/dev/null; then \
		echo "Denied destination unexpectedly succeeded" >&2; \
		exit 1; \
	else \
		echo "Denied destination correctly blocked"; \
	fi

clean:
	-docker volume rm $(AGENTHOME)
	-docker volume rm $(GOMODCACHE)
