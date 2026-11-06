ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
EXTRA_DIR := $(ROOT_DIR)/extras/agent-public-api
AGENT_IMAGE ?= go-agent
AGENT_PUBLIC_API_IMAGE ?= go-agent-public-api
# Leave empty to use the pinned default in the Dockerfile.
CLOJURE_IMAGE ?=
PUBLIC_API_SOURCE ?= $(ROOT_DIR)/branch-public-api
PUBLIC_API_CLI_VERSION ?= 1.12.6.1673
PUBLIC_API_MODULE ?= modules/backend
PUBLIC_API_CLJ_ARGS ?= -P -M:test
PREPARE_TARGETS := public-api-deps public-api-deps-runtime public-api-deps-dev public-api-deps-build

.DEFAULT_GOAL := help
.PHONY: help agent-public-api-build agent-public-api-check
.PHONY: $(PREPARE_TARGETS) public-api-deps-check public-api-cache-test

help:
	@echo "Public API JVM/Clojure tooling layered on the base agent (no services or credentials)."
	@echo "make -f extras/agent-public-api/Makefile agent-public-api-build [AGENT_IMAGE=go-agent] [AGENT_PUBLIC_API_IMAGE=go-agent-public-api] [CLOJURE_IMAGE=...]"
	@echo "make -f extras/agent-public-api/Makefile agent-public-api-check"
	@echo "make -f extras/agent-public-api/Makefile public-api-deps [PUBLIC_API_SOURCE=/path/to/checkout]"
	@echo "public-api-deps-runtime | public-api-deps-dev | public-api-deps-build: prepare selected backend dependencies on host"
	@echo "public-api-deps-check: resolve a selected profile in the container with networking disabled"
	@echo "public-api-cache-test: offline wrapper/relocation regression tests"

agent-public-api-build:
	docker build --build-arg "BASE_IMAGE=$(AGENT_IMAGE)" \
		$(if $(CLOJURE_IMAGE),--build-arg "CLOJURE_IMAGE=$(CLOJURE_IMAGE)") \
		-t "$(AGENT_PUBLIC_API_IMAGE)" "$(EXTRA_DIR)"

# Offline check: arbitrary UID, read-only root, disposable writable home/cache.
agent-public-api-check:
	docker run --rm --network none --read-only --user 12345:12345 \
		--tmpfs /tmp:rw,mode=1777 --env HOME=/tmp/agent-home --workdir /tmp \
		--mount "type=bind,src=$(EXTRA_DIR)/tests/smoke.sh,target=/tmp/public-api-smoke.sh,readonly" \
		"$(AGENT_PUBLIC_API_IMAGE)" bash /tmp/public-api-smoke.sh

public-api-deps: PREPARE_MODE = all
public-api-deps-runtime: PREPARE_MODE = runtime
public-api-deps-dev: PREPARE_MODE = dev
public-api-deps-build: PREPARE_MODE = build

$(PREPARE_TARGETS):
	bash "$(EXTRA_DIR)/scripts/prepare-deps.sh" "$(PUBLIC_API_SOURCE)" "$(PREPARE_MODE)" "$(PUBLIC_API_CLI_VERSION)"

public-api-cache-test:
	bash "$(EXTRA_DIR)/tests/cache-wrapper.sh"

# No host home, credentials, or network: prove the selected profile resolves from the checkout.
public-api-deps-check:
	docker run --rm --network none --read-only --user "$$(id -u):$$(id -g)" \
		--tmpfs /tmp:rw,mode=1777 --env HOME=/tmp/agent-home \
		--env PUBLIC_API_SOURCE=/workspace --workdir "/workspace/$(PUBLIC_API_MODULE)" \
		--mount "type=bind,src=$(abspath $(PUBLIC_API_SOURCE)),target=/workspace" \
		"$(AGENT_PUBLIC_API_IMAGE)" public-api-clojure $(PUBLIC_API_CLJ_ARGS)
