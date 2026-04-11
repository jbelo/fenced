AGENT_IMAGE := go-agent

AGENT_HOME := /home/agent

AGENTHOME := agenthome
GOMODCACHE := gomodcache

REPO_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
INSTALL_DIR ?= $(HOME)/.local/bin

UID := $(shell id -u)
GID := $(shell id -g)

.PHONY: help volumes init-volumes build install clean

help:
	@echo "make volumes                     Create Docker volumes"
	@echo "make init-volumes                Initialize writable volume ownership"
	@echo "make build                       Build the agent container image"
	@echo "make install [INSTALL_DIR=path]  Install the launcher scripts"
	@echo "make clean                       Remove persistent Docker volumes"

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

build:
	docker build -t $(AGENT_IMAGE) .

install:
	@mkdir -p "$(INSTALL_DIR)"
	@install -m 0755 "$(REPO_DIR)/bin/run-shell" "$(INSTALL_DIR)/run-shell"
	@install -m 0755 "$(REPO_DIR)/bin/story-shell" "$(INSTALL_DIR)/story-shell"
	@echo "Installed $(INSTALL_DIR)/story-shell"
	@echo "Installed $(INSTALL_DIR)/run-shell"
	@echo "Add $(INSTALL_DIR) to PATH if needed"

clean:
	-docker volume rm $(AGENTHOME)
	-docker volume rm $(GOMODCACHE)
