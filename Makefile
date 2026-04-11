AGENT_IMAGE := go-agent

AGENT_HOME := /home/agent

AGENTHOME := agenthome
GOMODCACHE := gomodcache

HOST_ROOT := $(CURDIR)
CONTAINER_ROOT := /workspace
SUBDIR ?= .

PROJECT_DIR := $(CURDIR)

UID := $(shell id -u)
GID := $(shell id -g)

.PHONY: help volumes init-volumes build shell clean

help:
	@echo "make volumes                       Create Docker volumes"
	@echo "make init-volumes                  Initialize writable volume ownsership"
	@echo "make build                         Build the agent container image"
	@echo "make shell                         Open a shell at /work"
	@echo "make shell SUBDIR=stories/x/branch Open a shell in a specific subdirectory"
	@echo "make clean                         Remove Go cache volumes"

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

shell: init-volumes
	docker run --rm -it \
		--user "$(UID):$(GID)" \
		--cap-drop=ALL \
		--security-opt=no-new-privileges \
		--read-only \
		--tmpfs /tmp:rw,size=1g,mode=1777 \
		--tmpfs /run:rw,size=64m \
		--mount type=bind,src="$(PROJECT_DIR)",target=/workspace \
		--mount type=volume,src="$(AGENTHOME)",target="$(AGENT_HOME)" \
		--mount type=volume,src="$(GOMODCACHE)",target=/go/pkg/mod \
		-e HOME="$(AGENT_HOME)" \
		-w "$(CONTAINER_ROOT)/$(SUBDIR)" \
		$(AGENT_IMAGE) \
		bash

clean:
	-docker volume rm $(AGENTHOME)
	-docker volume rm $(GOMODCACHE)
