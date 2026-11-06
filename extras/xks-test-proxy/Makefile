ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
EXTRA_DIR := $(ROOT_DIR)/extras/xks-test-proxy

XKS_PROXY_BASE_IMAGE ?= registry.internal.exoscale.ch/exoscale/kms-xks-proxy:015d4d11ba534da18cbc5e24cef2727e2209d0c1
XKS_PROXY_IMAGE ?= go-agent-xks-test-proxy
XKS_PROXY_RUNTIME_IMAGE ?= $(XKS_PROXY_IMAGE)-runtime
XKS_PROXY_SSH_DIR ?= $(EXTRA_DIR)/.local/ssh
XKS_PROXY_CONTAINER ?= go-agent-xks-test-proxy
XKS_PROXY_HOSTNAME ?= xks-proxy.test
XKS_PROXY_DATA_VOLUME ?= go-agent-xks-test-proxy-data
XKS_PROXY_TLS_DIR ?= $(EXTRA_DIR)/.local/tls
XKS_PROXY_SETTINGS ?= $(EXTRA_DIR)/settings.toml
XKS_PROXY_DOCKER_RUN_EXTRA ?=
AGENT_INTERNAL_NETWORK ?= go-agent-internal-net
AGENT_IMAGE ?= go-agent
AGENTHOME ?= agenthome
AGENT_HOME ?= /home/agent
AGENT_UID ?= $(shell id -u)
AGENT_GID ?= $(shell id -g)

.DEFAULT_GOAL := help
.PHONY: xks-test-proxy-build xks-test-proxy-ssh-setup xks-test-proxy-install-ssh
.PHONY: help xks-test-proxy-tls xks-test-proxy-check xks-test-proxy-up xks-test-proxy-ready xks-test-proxy-install-ca xks-test-proxy-status xks-test-proxy-logs xks-test-proxy-down

help:
	@echo "make -f extras/xks-test-proxy/Makefile xks-test-proxy-build xks-test-proxy-ssh-setup xks-test-proxy-install-ssh"
	@echo "TLS/SigV4 XKS test proxy (SoftHSM fixtures, not production keys)."
	@echo "make -f extras/xks-test-proxy/Makefile xks-test-proxy-tls"
	@echo "make -f extras/xks-test-proxy/Makefile xks-test-proxy-up"
	@echo "make -f extras/xks-test-proxy/Makefile xks-test-proxy-ready"
	@echo "make -f extras/xks-test-proxy/Makefile xks-test-proxy-install-ca"
	@echo "make -f extras/xks-test-proxy/Makefile xks-test-proxy-status | xks-test-proxy-logs | xks-test-proxy-down"

xks-test-proxy-tls:
	bash "$(EXTRA_DIR)/scripts/tls.sh" "$(XKS_PROXY_TLS_DIR)" "$(XKS_PROXY_HOSTNAME)"

xks-test-proxy-check:
	@test -s "$(XKS_PROXY_SSH_DIR)/server/authorized_keys" || { echo "Run xks-test-proxy-ssh-setup first." >&2; exit 1; }
	@test -s "$(XKS_PROXY_SETTINGS)" || { echo "Missing XKS_PROXY_SETTINGS" >&2; exit 1; }
	@for file in ca.pem server.pem server-key.pem; do \
		test -s "$(XKS_PROXY_TLS_DIR)/$$file" || { echo "Missing $$file; run xks-test-proxy-tls" >&2; exit 1; }; \
	done

xks-test-proxy-up: xks-test-proxy-check
	@docker network inspect "$(AGENT_INTERNAL_NETWORK)" >/dev/null || { echo "Run make networks first." >&2; exit 1; }
	@if docker container inspect "$(XKS_PROXY_CONTAINER)" >/dev/null 2>&1; then \
		docker start "$(XKS_PROXY_CONTAINER)"; \
	else \
		docker run -d --name "$(XKS_PROXY_CONTAINER)" \
			--network "$(AGENT_INTERNAL_NETWORK)" --network-alias "$(XKS_PROXY_HOSTNAME)" \
			--mount "type=volume,src=$(XKS_PROXY_DATA_VOLUME),target=/var/lib/softhsm/tokens" \
			--mount "type=bind,src=$(XKS_PROXY_SSH_DIR)/server/authorized_keys,target=/etc/ssh/authorized_keys,readonly" \
			--log-opt max-size=10m --log-opt max-file=3 \
			--mount "type=bind,src=$(XKS_PROXY_SETTINGS),target=/var/local/xks-proxy/.secret/settings.toml,readonly" \
			--mount "type=bind,src=$(XKS_PROXY_TLS_DIR)/server.pem,target=/certs/server.pem,readonly" \
			--mount "type=bind,src=$(XKS_PROXY_TLS_DIR)/server-key.pem,target=/certs/server-key.pem,readonly" \
			--mount "type=bind,src=$(XKS_PROXY_TLS_DIR)/ca.pem,target=/certs/ca.pem,readonly" \
			$(XKS_PROXY_DOCKER_RUN_EXTRA) "$(XKS_PROXY_IMAGE)" /usr/sbin/xks-proxy; \
	fi
	$(MAKE) -f "$(EXTRA_DIR)/Makefile" xks-test-proxy-ready

xks-test-proxy-ready:
	@docker exec "$(XKS_PROXY_CONTAINER)" curl --fail --silent --show-error \
		--noproxy '*' --cacert /certs/ca.pem \
		--resolve "$(XKS_PROXY_HOSTNAME):19443:127.0.0.1" \
		--connect-timeout 2 --max-time 5 --retry 15 --retry-connrefused --retry-delay 1 --retry-max-time 30 \
		"https://$(XKS_PROXY_HOSTNAME):19443/ping"

# Install only the public trust anchor, never server/CA private keys or settings.
xks-test-proxy-install-ca:
	@test -s "$(XKS_PROXY_TLS_DIR)/ca.pem" || { echo "Missing ca.pem; run xks-test-proxy-tls" >&2; exit 1; }
	@docker volume inspect "$(AGENTHOME)" >/dev/null || { echo "Initialize the agent home first." >&2; exit 1; }
	docker run --rm --network none --user 0:0 \
		--mount "type=volume,src=$(AGENTHOME),target=$(AGENT_HOME)" \
		--mount "type=bind,src=$(XKS_PROXY_TLS_DIR)/ca.pem,target=/tmp/xks-ca.pem,readonly" \
		"$(AGENT_IMAGE)" sh -c 'set -eu; \
			install -d -m 0755 -o $(AGENT_UID) -g $(AGENT_GID) "$(AGENT_HOME)/.config/xks-test-proxy"; \
			install -m 0644 -o $(AGENT_UID) -g $(AGENT_GID) /tmp/xks-ca.pem "$(AGENT_HOME)/.config/xks-test-proxy/ca.pem"'

xks-test-proxy-status:
	docker ps -a --filter "name=^/$(XKS_PROXY_CONTAINER)$$"

xks-test-proxy-logs:
	docker logs -f "$(XKS_PROXY_CONTAINER)"

xks-test-proxy-down:
	@if docker container inspect "$(XKS_PROXY_CONTAINER)" >/dev/null 2>&1; then \
		docker stop "$(XKS_PROXY_CONTAINER)" && docker rm "$(XKS_PROXY_CONTAINER)"; \
	fi

xks-test-proxy-build:
	docker build --build-arg "BASE_IMAGE=$(XKS_PROXY_BASE_IMAGE)" -t "$(XKS_PROXY_RUNTIME_IMAGE)" "$(EXTRA_DIR)"
	docker build --build-arg "BASE_IMAGE=$(XKS_PROXY_RUNTIME_IMAGE)" -t "$(XKS_PROXY_IMAGE)" "$(ROOT_DIR)/extras/ssh"

xks-test-proxy-ssh-setup:
	bash "$(ROOT_DIR)/extras/ssh/scripts/setup-client.sh" "$(XKS_PROXY_SSH_DIR)" "$(XKS_PROXY_HOSTNAME)" \
		xks-test-proxy '~/.config/xks-test-proxy/ssh/id_ed25519'

xks-test-proxy-install-ssh:
	@test -s "$(XKS_PROXY_SSH_DIR)/client/id_ed25519" || { echo "Run xks-test-proxy-ssh-setup first." >&2; exit 1; }
	docker run --rm --network none --user 0:0 \
		--mount "type=volume,src=$(AGENTHOME),target=$(AGENT_HOME)" \
		--mount "type=bind,src=$(XKS_PROXY_SSH_DIR)/client,target=/ssh-client,readonly" \
		"$(AGENT_IMAGE)" sh -c 'set -eu; \
			install -d -m 0700 -o $(AGENT_UID) -g $(AGENT_GID) "$(AGENT_HOME)/.config/xks-test-proxy/ssh"; \
			for file in id_ed25519 config; do \
				install -m 0600 -o $(AGENT_UID) -g $(AGENT_GID) "/ssh-client/$$file" "$(AGENT_HOME)/.config/xks-test-proxy/ssh/$$file"; \
			done; \
			rm -f -- "$(AGENT_HOME)/.config/xks-test-proxy/ssh/libnss_wrapper.so"; \
			install -d -m 0755 -o $(AGENT_UID) -g $(AGENT_GID) "$(AGENT_HOME)/.local/bin"; \
			printf "%s\n" "#!/bin/sh" "# Connect to the local XKS test proxy." \
				"exec ssh -F \"\$${HOME:?}/.config/xks-test-proxy/ssh/config\" xks-test-proxy \"\$$@\"" \
				> "$(AGENT_HOME)/.local/bin/xks-test-proxy-ssh"; \
			chmod 0755 "$(AGENT_HOME)/.local/bin/xks-test-proxy-ssh"; \
			chown $(AGENT_UID):$(AGENT_GID) "$(AGENT_HOME)/.local/bin/xks-test-proxy-ssh"'
