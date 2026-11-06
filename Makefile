AGENT_IMAGE := go-agent

AGENT_HOME := /home/agent

AGENTHOME := agenthome
GOMODCACHE := gomodcache
PI_VERSION ?= 1.0.4

REPO_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
INSTALL_DIR ?= $(HOME)/.local/bin
INSTALL_SCRIPTS := run-shell story-shell meta-shell agent-status agent-vm-status agent-docker-usage agent-container-stats

AGENT_INTERNAL_NETWORK := go-agent-internal-net
PROXY_UPSTREAM_NETWORK := go-agent-upstream-net
EGRESS_PROXY_CONTAINER := go-agent-egress-proxy
EGRESS_PROXY_IMAGE := go-agent-egress-proxy-image
SQUID_CONF := $(REPO_DIR)/squid.conf
PROXY_DOCKERFILE := $(REPO_DIR)/Dockerfile.squid
AGENT_CONTEXT_SOURCE := $(REPO_DIR)/agent-context.md
AGENT_CONTEXT_DEST := $(AGENT_HOME)/.go-agent-harness.md
AGENT_EXTRAS_SOURCE := $(REPO_DIR)/extras
AGENT_DOCS_DEST := $(AGENT_HOME)/.go-agent-harness
AGENT_TMUX_SOURCE := $(REPO_DIR)/config/tmux.conf
AGENT_TMUX_DEST := $(AGENT_HOME)/.tmux.conf

UID := $(shell id -u)
GID := $(shell id -g)

.PHONY: help volumes init-volumes install-agent-pi install-agent-context install-agent-tmux build install networks egress-proxy-build egress-proxy-up egress-proxy-down egress-proxy-logs egress-init egress-verify clean

help:
	@echo "make build                       Build the agent container image"
	@echo "make volumes                     Create Docker volumes"
	@echo "make init-volumes                Initialize writable volume ownership"
	@echo "make install-agent-context       Refresh harness context and reference docs in agent home"
	@echo "make install-agent-tmux          Install agent tmux config if missing"
	@echo "make install-agent-pi            Install Pi in the writable agent home if missing"
	@echo "make install [INSTALL_DIR=path]  Install launchers and resource helpers"
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
	$(MAKE) install-agent-context
	$(MAKE) install-agent-tmux
	$(MAKE) install-agent-pi

# Host-managed preparation uses Docker's default network for npm downloads.
install-agent-pi:
	@docker volume inspect "$(AGENTHOME)" >/dev/null || { echo "Run make init-volumes first." >&2; exit 1; }
	docker run --rm --read-only --tmpfs /tmp:rw,mode=1777 \
		--user $(UID):$(GID) --env HOME="$(AGENT_HOME)" \
		--mount "type=volume,src=$(AGENTHOME),target=$(AGENT_HOME)" \
		--mount "type=bind,src=$(REPO_DIR)/scripts/install-agent-pi.sh,target=/tmp/install-agent-pi.sh,readonly" \
		$(AGENT_IMAGE) sh /tmp/install-agent-pi.sh "$(PI_VERSION)"

install-agent-context: volumes
	docker run --rm \
		--user 0:0 \
		--mount type=volume,src="$(AGENTHOME)",target="$(AGENT_HOME)" \
		--mount type=bind,src="$(AGENT_CONTEXT_SOURCE)",target=/tmp/go-agent-harness.md,readonly \
		--mount type=bind,src="$(AGENT_EXTRAS_SOURCE)",target=/tmp/harness-extras,readonly \
		$(AGENT_IMAGE) \
		sh -c 'set -eu; \
			mkdir -p "$(AGENT_HOME)"; \
			install -m 0644 -o $(UID) -g $(GID) /tmp/go-agent-harness.md "$(AGENT_CONTEXT_DEST)"; \
			install -d -m 0755 -o $(UID) -g $(GID) "$(AGENT_DOCS_DEST)" "$(AGENT_DOCS_DEST)/extras"; \
			while IFS= read -r relative || [ -n "$$relative" ]; do \
				[ -n "$$relative" ] || continue; \
				destination="$(AGENT_DOCS_DEST)/extras/$$relative"; \
				install -d -m 0755 -o $(UID) -g $(GID) "$$(dirname "$$destination")"; \
				install -m 0644 -o $(UID) -g $(GID) "/tmp/harness-extras/$$relative" "$$destination"; \
			done < /tmp/harness-extras/agent-docs.list; \
			install -d -m 0755 -o $(UID) -g $(GID) "$(AGENT_HOME)/.agents" "$(AGENT_HOME)/.agents/skills"; \
			while IFS= read -r relative || [ -n "$$relative" ]; do \
				[ -n "$$relative" ] || continue; \
				case "$$relative" in /*|..|../*|*/../*|*/..) echo "Invalid skill path: $$relative" >&2; exit 1;; esac; \
				skill=$$(basename "$$relative"); \
				destination="$(AGENT_HOME)/.agents/skills/$$skill"; \
				install -d -m 0755 -o $(UID) -g $(GID) "$$destination"; \
				install -m 0644 -o $(UID) -g $(GID) "/tmp/harness-extras/$$relative/SKILL.md" "$$destination/SKILL.md"; \
				if [ -f "/tmp/harness-extras/$$relative/resources.list" ]; then \
					while IFS= read -r resource || [ -n "$$resource" ]; do \
						[ -n "$$resource" ] || continue; \
						case "$$resource" in /*|..|../*|*/../*|*/..) echo "Invalid skill resource: $$resource" >&2; exit 1;; esac; \
						source="/tmp/harness-extras/$$relative/$$resource"; \
						[ -f "$$source" ] && [ ! -L "$$source" ] || { echo "Invalid skill resource: $$resource" >&2; exit 1; }; \
						install -d -m 0755 -o $(UID) -g $(GID) "$$(dirname "$$destination/$$resource")"; \
						install -m 0644 -o $(UID) -g $(GID) "$$source" "$$destination/$$resource"; \
					done < "/tmp/harness-extras/$$relative/resources.list"; \
				fi; \
			done < /tmp/harness-extras/agent-skills.list'
	@echo "Installed harness context and reference docs in volume $(AGENTHOME)"

install-agent-tmux: volumes
	docker run --rm \
		--user 0:0 \
		--mount type=volume,src="$(AGENTHOME)",target="$(AGENT_HOME)" \
		--mount type=bind,src="$(AGENT_TMUX_SOURCE)",target=/tmp/agent-tmux.conf,readonly \
		--mount "type=bind,src=$(REPO_DIR)/scripts/install-agent-tmux.sh,target=/tmp/install-agent-tmux.sh,readonly" \
		$(AGENT_IMAGE) sh /tmp/install-agent-tmux.sh \
			/tmp/agent-tmux.conf "$(AGENT_TMUX_DEST)" "$(UID)" "$(GID)"

install:
	@mkdir -p "$(INSTALL_DIR)"
	@set -e; for script in $(INSTALL_SCRIPTS); do \
		install -m 0755 "$(REPO_DIR)/bin/$$script" "$(INSTALL_DIR)/$$script"; \
		echo "Installed $(INSTALL_DIR)/$$script"; \
	done
	@mkdir -p "$(INSTALL_DIR)/run-shell.d"
	@set -e; for hook in "$(REPO_DIR)"/extras/*/run-shell.d/*.sh; do \
		[ -f "$$hook" ] || continue; \
		install -m 0644 "$$hook" "$(INSTALL_DIR)/run-shell.d/"; \
	done
	@set -e; for script in "$(REPO_DIR)"/extras/*/host-bin/*; do \
		[ -f "$$script" ] || continue; \
		install -m 0755 "$$script" "$(INSTALL_DIR)/$$(basename "$$script")"; \
	done
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

.PHONY: egress-go-verify
egress-go-verify:
	docker run --rm --network $(AGENT_INTERNAL_NETWORK) --read-only \
		--tmpfs /tmp:rw,mode=1777 \
		-e HTTPS_PROXY=http://$(EGRESS_PROXY_CONTAINER):3128 \
		-e HTTP_PROXY=http://$(EGRESS_PROXY_CONTAINER):3128 \
		-e HOME=/tmp -e GOPATH=/tmp/go -e GOCACHE=/tmp/build-cache \
		-e GOMODCACHE=/tmp/go/pkg/mod \
		-e GOPROXY=https://proxy.golang.org -e GOSUMDB=sum.golang.org \
		-e GOTOOLCHAIN=local $(AGENT_IMAGE) sh -ec '\
		curl -fsS https://sum.golang.org/lookup/golang.org/x/text@v0.14.0 >/dev/null; \
		go mod download -json golang.org/x/text@v0.14.0; \
		code=$$(curl -sS -o /dev/null -w "%{http_connect}" https://example.com 2>/dev/null || true); \
		test "$$code" = 403'

clean:
	-docker volume rm $(AGENTHOME)
	-docker volume rm $(GOMODCACHE)
